"""Copy tagged audio into the library layout."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from abs_organize.discovery import (
    collect_track_files,
    discover_book_root,
    list_sidecars,
)
from abs_organize.metadata import (
    BookMetadata,
    MetadataError,
    MetadataOverrides,
    SUPPORTED_EXTENSIONS,
    ValidationError,
    resolve_book_metadata,
)
from abs_organize.naming import book_destination_segments


class OrganizeIOError(Exception):
    """Filesystem operation failed during organize."""


@dataclass(frozen=True)
class OrganizeResult:
    source: Path
    dest_dir: Path
    copied_files: tuple[str, ...]


def _validate_input_path(path: Path) -> None:
    if not path.exists():
        raise ValidationError(f"Input does not exist: {path}")
    if path.is_file():
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValidationError(
                f"Unsupported file type {path.suffix!r}; supported: {supported}"
            )
    elif not path.is_dir():
        raise ValidationError(f"Input must be a file or directory: {path}")


def _validate_library(library: Path) -> None:
    if not library.exists():
        raise ValidationError(f"Library path does not exist: {library}")
    if not library.is_dir():
        raise ValidationError(f"Library path must be a directory: {library}")


def _build_dest_dir(
    metadata: BookMetadata,
    library_path: Path,
    *,
    include_subtitle_in_folder: bool = False,
    on_log: Callable[[str], None] | None = None,
) -> Path:
    author_seg, series_seg, title_seg = book_destination_segments(
        metadata,
        include_subtitle_in_folder=include_subtitle_in_folder,
        on_log=on_log,
    )
    dest_dir = library_path / author_seg
    if series_seg:
        dest_dir /= series_seg
    dest_dir /= title_seg
    return dest_dir


def _planned_filenames(sources: list[Path]) -> tuple[str, ...]:
    return tuple(source.name for source in sources)


def _copy_files(sources: list[Path], dest_dir: Path) -> tuple[str, ...]:
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OrganizeIOError(f"Failed to create destination directory: {exc}") from exc

    copied: list[str] = []
    for source in sources:
        dest_file = dest_dir / source.name
        try:
            shutil.copy2(source, dest_file)
        except OSError as exc:
            raise OrganizeIOError(f"Failed to copy {source.name}: {exc}") from exc
        copied.append(source.name)
    return tuple(copied)


def organize(
    input_path: Path,
    library_path: Path,
    *,
    overrides: MetadataOverrides | None = None,
    include_subtitle_in_folder: bool = False,
    dry_run: bool = False,
    on_log: Callable[[str], None] | None = None,
) -> tuple[OrganizeResult, tuple[str, ...]]:
    input_path = input_path.resolve()
    library_path = library_path.resolve()

    _validate_input_path(input_path)
    _validate_library(library_path)

    if input_path.is_file():
        track_files = [input_path]
    else:
        book_root = discover_book_root(input_path)
        track_files = collect_track_files(book_root)
        if on_log is not None:
            for sidecar in list_sidecars(book_root):
                on_log(f"Sidecar found (not copied): {sidecar.name}")

    try:
        resolved = resolve_book_metadata(track_files, overrides=overrides)
    except MetadataError:
        raise

    dest_dir = _build_dest_dir(
        resolved.metadata,
        library_path,
        include_subtitle_in_folder=include_subtitle_in_folder,
        on_log=on_log,
    )
    if dry_run:
        copied_files = _planned_filenames(track_files)
    else:
        copied_files = _copy_files(track_files, dest_dir)

    return (
        OrganizeResult(
            source=input_path,
            dest_dir=dest_dir,
            copied_files=copied_files,
        ),
        resolved.warnings,
    )


def organize_file(
    input_path: Path,
    library_path: Path,
    *,
    include_subtitle_in_folder: bool = False,
    on_log: Callable[[str], None] | None = None,
) -> OrganizeResult:
    result, _warnings = organize(
        input_path,
        library_path,
        include_subtitle_in_folder=include_subtitle_in_folder,
        on_log=on_log,
    )
    return result
