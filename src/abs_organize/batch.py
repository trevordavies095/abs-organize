"""Batch orchestration: organize multiple book roots from one INPUT."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from abs_organize.discovery import discover_book_roots
from abs_organize.metadata import MetadataError, MetadataOverrides, ValidationError
from abs_organize.organize import OrganizeIOError, OrganizeResult, organize
from abs_organize.organize import _validate_input_path, _validate_library


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


def _organize_inputs(input_path: Path, roots: list[Path]) -> list[Path]:
    if len(roots) == 1:
        return [input_path.resolve()]
    return sorted(roots, key=lambda p: str(p.resolve()))


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
    on_log: Callable[[str], None] | None = None,
) -> BatchResult:
    """Organize every detected book root under *input_path*.

    Dry-run attempts all roots. Apply stops on the first failure.
    """
    input_path = input_path.resolve()
    library_path = library_path.resolve()

    _validate_input_path(input_path)
    _validate_library(library_path)

    roots = discover_book_roots(input_path)
    book_inputs = _organize_inputs(input_path, roots)

    outcomes: list[BookOutcome] = []
    for book_input in book_inputs:
        try:
            result, warnings = organize(
                book_input,
                library_path,
                overrides=overrides,
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
            if not dry_run:
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
            if not dry_run:
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
