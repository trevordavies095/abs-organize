"""Copy tagged audio into the library layout."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from abs_organize.covers import resolve_cover, write_cover_jpg
from abs_organize.discovery import (
    BookAudio,
    collect_book_audio,
    discover_book_root,
    list_copy_sidecars,
    sidecar_root,
)
from abs_organize.metadata import (
    BookMetadata,
    MetadataOverrides,
    SUPPORTED_EXTENSIONS,
    ValidationError,
    apply_gap_fill,
    resolve_book_metadata,
)
from abs_organize.naming import book_destination_segments
from abs_organize.opf import parse_opf, read_reader_txt


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


def _collision_warnings(
    dest_dir: Path, *, replace: bool, dry_run: bool
) -> tuple[str, ...]:
    messages = [f"Destination title folder already exists: {dest_dir}"]
    if dry_run and replace:
        messages.append("Would delete existing title folder (--replace).")
    elif not replace:
        messages.append(
            "Re-run with --replace to delete the existing title folder and copy again."
        )
    return tuple(messages)


def _assert_replace_safe(dest_dir: Path, library_path: Path) -> None:
    dest_resolved = dest_dir.resolve()
    lib_resolved = library_path.resolve()
    if dest_resolved == lib_resolved:
        raise ValidationError(f"Refusing to delete library root: {lib_resolved}")
    if not dest_resolved.is_relative_to(lib_resolved):
        raise ValidationError(
            f"Refusing to delete destination outside library root: {dest_resolved}"
        )
    if len(dest_resolved.relative_to(lib_resolved).parts) < 2:
        raise ValidationError(
            "Refusing to delete destination that is not a title folder under "
            f"library: {dest_resolved}"
        )


def _copy_sidecars(sidecars: list[Path], dest_dir: Path) -> tuple[str, ...]:
    copied: list[str] = []
    for sidecar in sidecars:
        dest_file = dest_dir / sidecar.name
        try:
            shutil.copy2(sidecar, dest_file)
        except OSError as exc:
            raise OrganizeIOError(
                f"Failed to copy sidecar {sidecar.name}: {exc}"
            ) from exc
        copied.append(sidecar.name)
    return tuple(copied)


def _resolve_gap_fill_sources(
    sidecars: list[Path],
    *,
    on_log: Callable[[str], None] | None = None,
) -> tuple[BookMetadata | None, str | None]:
    opf_paths = [path for path in sidecars if path.suffix.lower() == ".opf"]
    opf_metadata = None
    if opf_paths:
        if len(opf_paths) > 1 and on_log is not None:
            on_log(
                "Multiple OPF files found; using "
                f"{opf_paths[0].name} for metadata gap-fill."
            )
        opf_metadata = parse_opf(opf_paths[0])

    reader_txt = None
    for sidecar in sidecars:
        if sidecar.name.lower() == "reader.txt":
            reader_txt = read_reader_txt(sidecar)
            break

    return opf_metadata, reader_txt


def _apply_supplemental_files(
    *,
    sidecar_root_path: Path,
    track_files: list[Path],
    sidecars: list[Path],
    dest_dir: Path,
    dry_run: bool,
    on_log: Callable[[str], None] | None = None,
) -> tuple[str, ...]:
    copied: list[str] = []

    cover = resolve_cover(sidecar_root_path, track_files)
    if cover is not None:
        if dry_run:
            copied.append("Cover.jpg")
            if on_log is not None:
                if cover.has_sidecar:
                    on_log(
                        f"Would copy cover from {cover.sidecar_path.name} as Cover.jpg"
                    )
                else:
                    on_log("Would extract embedded cover as Cover.jpg")
        else:
            copied.append(write_cover_jpg(dest_dir, cover))
            if on_log is not None:
                if cover.has_sidecar:
                    on_log(
                        f"Wrote Cover.jpg from sidecar {cover.sidecar_path.name}"
                    )
                else:
                    on_log("Wrote Cover.jpg from embedded audio art")

    if sidecars:
        if dry_run:
            copied.extend(sidecar.name for sidecar in sidecars)
            if on_log is not None:
                for sidecar in sidecars:
                    on_log(f"Would copy sidecar: {sidecar.name}")
        else:
            copied.extend(_copy_sidecars(sidecars, dest_dir))
            if on_log is not None:
                for sidecar in sidecars:
                    on_log(f"Copied sidecar: {sidecar.name}")

    return tuple(copied)


def _planned_filenames(audio: list[BookAudio]) -> tuple[str, ...]:
    return tuple(item.dest_relative.as_posix() for item in audio)


def _copy_files(audio: list[BookAudio], dest_dir: Path) -> tuple[str, ...]:
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OrganizeIOError(f"Failed to create destination directory: {exc}") from exc

    copied: list[str] = []
    for item in audio:
        dest_file = dest_dir / item.dest_relative
        try:
            dest_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OrganizeIOError(
                f"Failed to create directory for {item.dest_relative}: {exc}"
            ) from exc
        try:
            shutil.copy2(item.source, dest_file)
        except OSError as exc:
            raise OrganizeIOError(
                f"Failed to copy {item.dest_relative.as_posix()}: {exc}"
            ) from exc
        copied.append(item.dest_relative.as_posix())
    return tuple(copied)


def organize(
    input_path: Path,
    library_path: Path,
    *,
    overrides: MetadataOverrides | None = None,
    include_subtitle_in_folder: bool = False,
    dry_run: bool = False,
    replace: bool = False,
    on_log: Callable[[str], None] | None = None,
) -> tuple[OrganizeResult, tuple[str, ...]]:
    input_path = input_path.resolve()
    library_path = library_path.resolve()

    _validate_input_path(input_path)
    _validate_library(library_path)

    if input_path.is_file():
        book_root = input_path
        book_audio = collect_book_audio(input_path)
    else:
        book_root = discover_book_root(input_path)
        book_audio = collect_book_audio(book_root)

    sidecar_root_path = sidecar_root(input_path, book_root)
    copy_sidecars = list_copy_sidecars(sidecar_root_path)
    track_files = [item.source for item in book_audio]

    resolved = resolve_book_metadata(track_files, overrides=overrides)
    opf_metadata, reader_txt = _resolve_gap_fill_sources(
        copy_sidecars, on_log=on_log
    )
    resolved = apply_gap_fill(
        resolved,
        opf_metadata=opf_metadata,
        reader_txt=reader_txt,
        overrides=overrides,
    )

    dest_dir = _build_dest_dir(
        resolved.metadata,
        library_path,
        include_subtitle_in_folder=include_subtitle_in_folder,
        on_log=on_log,
    )

    extra_warnings: tuple[str, ...] = ()
    if dest_dir.exists():
        if dry_run:
            extra_warnings = _collision_warnings(
                dest_dir, replace=replace, dry_run=True
            )
        elif replace:
            _assert_replace_safe(dest_dir, library_path)
            try:
                shutil.rmtree(dest_dir)
            except OSError as exc:
                raise OrganizeIOError(
                    f"Failed to remove existing destination: {exc}"
                ) from exc
        else:
            raise ValidationError(
                f"Destination title folder already exists: {dest_dir}"
            )

    if dry_run:
        copied_files = list(_planned_filenames(book_audio))
    else:
        copied_files = list(_copy_files(book_audio, dest_dir))

    copied_files.extend(
        _apply_supplemental_files(
            sidecar_root_path=sidecar_root_path,
            track_files=track_files,
            sidecars=copy_sidecars,
            dest_dir=dest_dir,
            dry_run=dry_run,
            on_log=on_log,
        )
    )

    return (
        OrganizeResult(
            source=input_path,
            dest_dir=dest_dir,
            copied_files=tuple(copied_files),
        ),
        resolved.warnings + extra_warnings,
    )


def organize_file(
    input_path: Path,
    library_path: Path,
    *,
    include_subtitle_in_folder: bool = False,
    replace: bool = False,
    on_log: Callable[[str], None] | None = None,
) -> OrganizeResult:
    result, _warnings = organize(
        input_path,
        library_path,
        include_subtitle_in_folder=include_subtitle_in_folder,
        replace=replace,
        on_log=on_log,
    )
    return result
