"""Batch orchestration: organize multiple book roots from one INPUT."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from abs_organize.discovery import (
    collect_book_audio,
    discover_book_root,
    discover_book_roots,
    list_copy_sidecars,
    sidecar_root,
)
from abs_organize.heuristics import infer_sequence_from_folder_name
from abs_organize.metadata import (
    MetadataError,
    MetadataOverrides,
    ResolvedMetadata,
    ValidationError,
    apply_gap_fill,
    resolve_book_metadata,
)
from abs_organize.organize import OrganizeIOError, OrganizeResult, organize
from abs_organize.organize import _resolve_gap_fill_sources, _validate_input_path, _validate_library

_GAP_FILL_CLI_FIELDS = ("series", "narrator", "year")
_FORBIDDEN_MULTI_CLI_FIELDS = ("author", "title", "sequence")


@dataclass(frozen=True)
class BookOutcome:
    """Result of organizing one book in a batch."""

    book_input: Path
    ok: bool
    result: OrganizeResult | None
    warnings: tuple[str, ...]
    error: str | None
    io_error: bool = False


@dataclass(frozen=True)
class BatchResult:
    """Aggregated outcomes for a batch run."""

    outcomes: tuple[BookOutcome, ...]

    @property
    def ok_count(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.ok)

    @property
    def failed_count(self) -> int:
        return sum(1 for outcome in self.outcomes if not outcome.ok)

    @property
    def had_io_error(self) -> bool:
        return any(outcome.io_error for outcome in self.outcomes)


def validate_batch_override_policy(
    roots: list[Path], overrides: MetadataOverrides | None
) -> None:
    """Reject CLI flags that cannot apply safely to multi-book batch runs."""
    if len(roots) <= 1 or overrides is None:
        return
    forbidden: list[str] = []
    for field in _FORBIDDEN_MULTI_CLI_FIELDS:
        if getattr(overrides, field) is not None:
            forbidden.append(f"--{field}")
    if not forbidden:
        return
    flags = ", ".join(forbidden)
    raise ValidationError(
        f"Cannot use {flags} with multi-book --batch "
        f"({len(roots)} book roots detected). "
        "These flags apply to a single book only; omit them or organize one book at a time."
    )


def _organize_inputs(input_path: Path, roots: list[Path]) -> list[Path]:
    if len(roots) == 1:
        return [input_path.resolve()]
    return sorted(roots, key=lambda p: str(p.resolve()))


def _book_root_for_input(book_input: Path) -> Path:
    if book_input.is_file():
        return book_input.resolve()
    return discover_book_root(book_input)


def _resolve_metadata_at_input(
    book_input: Path,
    *,
    overrides: MetadataOverrides | None,
    allow_guess: bool,
) -> tuple[ResolvedMetadata, Path]:
    book_root = _book_root_for_input(book_input)
    book_audio = collect_book_audio(book_root)
    track_files = [item.source for item in book_audio]
    sidecar_root_path = sidecar_root(book_input, book_root)
    copy_sidecars = list_copy_sidecars(sidecar_root_path)

    resolved = resolve_book_metadata(
        track_files, overrides=overrides, allow_guess=allow_guess
    )
    opf_metadata, reader_txt = _resolve_gap_fill_sources(copy_sidecars)
    resolved = apply_gap_fill(
        resolved,
        opf_metadata=opf_metadata,
        reader_txt=reader_txt,
        overrides=overrides,
    )
    return resolved, book_root


def _maybe_infer_folder_sequence(
    resolved: ResolvedMetadata,
    book_root: Path,
    *,
    on_log: Callable[[str], None] | None,
) -> MetadataOverrides | None:
    if resolved.metadata.sequence is not None:
        return None
    inferred = infer_sequence_from_folder_name(book_root.name)
    if inferred is None:
        return None
    if on_log is not None:
        on_log(
            f"Inferred sequence {inferred} from book-root folder name {book_root.name!r}"
        )
    return MetadataOverrides(sequence=inferred)


def _per_book_overrides(
    book_input: Path,
    *,
    cli_overrides: MetadataOverrides | None,
    multi_root: bool,
    allow_guess: bool,
    on_log: Callable[[str], None] | None,
) -> MetadataOverrides | None:
    resolve_overrides = None if multi_root else cli_overrides
    resolved, book_root = _resolve_metadata_at_input(
        book_input,
        overrides=resolve_overrides,
        allow_guess=allow_guess,
    )

    effective = MetadataOverrides()
    has_fields = False

    if multi_root and cli_overrides is not None:
        for field in _GAP_FILL_CLI_FIELDS:
            cli_value = getattr(cli_overrides, field)
            if cli_value is None:
                continue
            existing = getattr(resolved.metadata, field)
            if existing is not None and existing != "":
                continue
            effective = replace(effective, **{field: cli_value})
            has_fields = True
    elif cli_overrides is not None:
        effective = cli_overrides
        has_fields = any(
            getattr(cli_overrides, field) is not None
            for field in (
                "author",
                "title",
                "year",
                "series",
                "sequence",
                "narrator",
            )
        )

    inferred = _maybe_infer_folder_sequence(resolved, book_root, on_log=on_log)
    if inferred is not None:
        if effective.sequence is None:
            effective = replace(effective, sequence=inferred.sequence)
            has_fields = True

    return effective if has_fields else None


def organize_batch(
    input_path: Path,
    library_path: Path,
    *,
    overrides: MetadataOverrides | None = None,
    include_subtitle_in_folder: bool = False,
    dry_run: bool = False,
    move: bool = False,
    replace: bool = False,
    allow_guess: bool = False,
    continue_on_error: bool = False,
    on_log: Callable[[str], None] | None = None,
) -> BatchResult:
    """Organize every detected book root under *input_path*.

    Dry-run attempts all roots. Apply stops on the first failure unless
    *continue_on_error* is set.
    """
    input_path = input_path.resolve()
    library_path = library_path.resolve()

    _validate_input_path(input_path)
    _validate_library(library_path)

    roots = discover_book_roots(input_path)
    validate_batch_override_policy(roots, overrides)
    multi_root = len(roots) > 1
    book_inputs = _organize_inputs(input_path, roots)

    outcomes: list[BookOutcome] = []
    for book_input in book_inputs:
        try:
            per_book_overrides = _per_book_overrides(
                book_input,
                cli_overrides=overrides,
                multi_root=multi_root,
                allow_guess=allow_guess,
                on_log=on_log,
            )
            result, warnings = organize(
                book_input,
                library_path,
                overrides=per_book_overrides,
                include_subtitle_in_folder=include_subtitle_in_folder,
                dry_run=dry_run,
                move=move,
                replace=replace,
                allow_guess=allow_guess,
                on_log=on_log,
            )
        except OrganizeIOError as exc:
            outcomes.append(
                BookOutcome(
                    book_input=book_input,
                    ok=False,
                    result=None,
                    warnings=(),
                    error=str(exc),
                    io_error=True,
                )
            )
            if not dry_run and not continue_on_error:
                break
            continue
        except (ValidationError, MetadataError) as exc:
            outcomes.append(
                BookOutcome(
                    book_input=book_input,
                    ok=False,
                    result=None,
                    warnings=(),
                    error=str(exc),
                )
            )
            if not dry_run and not continue_on_error:
                break
            continue
        else:
            outcomes.append(
                BookOutcome(
                    book_input=book_input,
                    ok=True,
                    result=result,
                    warnings=warnings,
                    error=None,
                )
            )

    return BatchResult(outcomes=tuple(outcomes))
