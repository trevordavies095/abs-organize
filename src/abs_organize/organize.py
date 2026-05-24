"""Copy a single tagged audio file into the library layout."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from abs_organize.metadata import (
    MetadataError,
    SUPPORTED_EXTENSIONS,
    ValidationError,
    read_book_metadata,
)
from abs_organize.naming import book_destination_segments


class OrganizeIOError(Exception):
    """Filesystem operation failed during organize."""


@dataclass(frozen=True)
class OrganizeResult:
    source: Path
    dest_dir: Path
    copied_files: tuple[str, ...]


def _validate_input(path: Path) -> None:
    if not path.exists():
        raise ValidationError(f"Input does not exist: {path}")
    if not path.is_file():
        raise ValidationError(f"Input must be a file: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValidationError(
            f"Unsupported file type {path.suffix!r}; supported: {supported}"
        )


def _validate_library(library: Path) -> None:
    if not library.exists():
        raise ValidationError(f"Library path does not exist: {library}")
    if not library.is_dir():
        raise ValidationError(f"Library path must be a directory: {library}")


def organize_file(
    input_path: Path,
    library_path: Path,
    *,
    include_subtitle_in_folder: bool = False,
    on_log: Callable[[str], None] | None = None,
) -> OrganizeResult:
    input_path = input_path.resolve()
    library_path = library_path.resolve()

    _validate_input(input_path)
    _validate_library(library_path)

    try:
        metadata = read_book_metadata(input_path)
    except MetadataError:
        raise

    author_seg, series_seg, title_seg = book_destination_segments(
        metadata,
        include_subtitle_in_folder=include_subtitle_in_folder,
        on_log=on_log,
    )
    dest_dir = library_path / author_seg
    if series_seg:
        dest_dir /= series_seg
    dest_dir /= title_seg
    dest_file = dest_dir / input_path.name

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_path, dest_file)
    except OSError as exc:
        raise OrganizeIOError(f"Failed to copy {input_path.name}: {exc}") from exc

    return OrganizeResult(
        source=input_path,
        dest_dir=dest_dir,
        copied_files=(input_path.name,),
    )
