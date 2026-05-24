"""Discover audio tracks, book roots, and sidecars.

Book-root heuristic (see issue #6):
- **Container** files (``.m4b``, ``.m4a``): each direct sibling is its own book.
- **Track-style** files (``.mp3``, ``.flac``, ``.ogg``): all direct siblings in one folder are one book.
- **No direct audio**: recurse into child directories (max depth ``MAX_DISCOVERY_DEPTH``).
- **Multiple disc subfolders** (``Disc`` / ``CD`` / ``Disk``): one book at the parent (issue #7).
- **Mixed** container + track-style at the same level: multiple candidates → fail.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from abs_organize.metadata import SUPPORTED_EXTENSIONS, ValidationError

MAX_DISCOVERY_DEPTH = 5

_CONTAINER_EXTENSIONS = frozenset({".m4b", ".m4a"})

_DISC_FOLDER_RE = re.compile(r"^(disc|cd|disk)\s*0*(\d+)$", re.IGNORECASE)

_COPY_SIDECAR_NAMES = frozenset({"desc.txt", "reader.txt"})

_COVER_BASENAMES = ("cover", "folder")
_COVER_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})

_MULTIPLE_BOOKS_PREFIX = (
    "Multiple books detected in INPUT. Re-run on one book at a time:"
)

_BATCH_HINT = "Or re-run with --batch to organize all detected books."


def is_disc_folder_name(name: str) -> bool:
    """Return True if *name* matches Audiobookshelf disc subfolder naming."""
    return _DISC_FOLDER_RE.match(name) is not None


def disc_folder_sort_key(name: str) -> tuple[int, str]:
    """Sort key for disc subfolders: numeric index, then original spelling."""
    match = _DISC_FOLDER_RE.match(name)
    if not match:
        return (0, name.lower())
    return (int(match.group(2)), name.lower())


@dataclass(frozen=True)
class BookAudio:
    """One audio file to copy, with path relative to the title folder."""

    source: Path
    dest_relative: Path


def _is_audio_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def _direct_audio_files(directory: Path) -> list[Path]:
    return sorted(
        (child for child in directory.iterdir() if _is_audio_file(child)),
        key=lambda p: p.name.lower(),
    )


def _is_disc_layout(audio_subdirs: list[Path]) -> bool:
    return bool(audio_subdirs) and all(
        is_disc_folder_name(subdir.name) for subdir in audio_subdirs
    )


def _subdir_audio_roots(directory: Path, *, depth_remaining: int) -> list[Path]:
    if depth_remaining <= 0:
        return []

    roots: list[Path] = []
    for child in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        roots.extend(_book_roots_at(child, depth_remaining=depth_remaining - 1))
    return roots


def _book_roots_at(directory: Path, *, depth_remaining: int) -> list[Path]:
    """Return zero or more book roots found under *directory* (not above it)."""
    directory = directory.resolve()
    direct_audio = _direct_audio_files(directory)

    if direct_audio:
        containers = [
            f for f in direct_audio if f.suffix.lower() in _CONTAINER_EXTENSIONS
        ]
        track_style = [
            f for f in direct_audio if f.suffix.lower() not in _CONTAINER_EXTENSIONS
        ]

        if len(containers) >= 2:
            return containers

        if containers and track_style:
            return containers + [directory]

        return [directory]

    audio_subdirs = _subdirs_with_direct_audio(directory)
    if len(audio_subdirs) >= 2 and _is_disc_layout(audio_subdirs):
        return [directory]

    return _subdir_audio_roots(directory, depth_remaining=depth_remaining)


def _format_multiple_books(candidates: list[Path]) -> str:
    lines = "\n".join(f"  {path}" for path in sorted(candidates, key=str))
    return f"{_MULTIPLE_BOOKS_PREFIX}\n{lines}\n{_BATCH_HINT}"


def _is_ambiguous_mixed_layout(roots: list[Path]) -> bool:
    """True when any root directory has container and track-style siblings."""
    for root in roots:
        if not root.is_dir():
            continue
        direct_audio = _direct_audio_files(root)
        if not direct_audio:
            continue
        containers = [
            f for f in direct_audio if f.suffix.lower() in _CONTAINER_EXTENSIONS
        ]
        track_style = [
            f for f in direct_audio if f.suffix.lower() not in _CONTAINER_EXTENSIONS
        ]
        if containers and track_style:
            return True
    return False


def _unique_sorted_roots(roots: list[Path]) -> list[Path]:
    by_key: dict[str, Path] = {}
    for path in roots:
        resolved = path.resolve()
        by_key[str(resolved)] = resolved
    return [by_key[key] for key in sorted(by_key)]


def discover_book_roots(
    input_path: Path, *, max_depth: int = MAX_DISCOVERY_DEPTH
) -> list[Path]:
    """Return all book roots under *input_path* (sorted, unique).

    For a file path, returns a one-element list. For a directory, enumerates
    roots using the same rules as ``discover_book_root``. Raises
    ``ValidationError`` when no book is found or when an ambiguous mixed
    container + track-style layout is detected.
    """
    input_path = input_path.resolve()

    if input_path.is_file():
        return [input_path]

    if not input_path.is_dir():
        raise ValidationError(f"Input must be a file or directory: {input_path}")

    roots = _book_roots_at(input_path, depth_remaining=max_depth)

    if not roots:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValidationError(
            f"No audio files found in {input_path}; supported extensions: {supported}"
        )

    unique_roots = _unique_sorted_roots(roots)

    if len(unique_roots) > 1 and _is_ambiguous_mixed_layout(unique_roots):
        raise ValidationError(_format_multiple_books(unique_roots))

    return unique_roots


def discover_book_root(
    input_path: Path, *, max_depth: int = MAX_DISCOVERY_DEPTH
) -> Path:
    """Resolve a single book root under *input_path*.

    For a file path, returns the resolved file. For a directory, locates the
    unique book root using container vs track-style rules and optional wrapper
    descent. Raises ``ValidationError`` when no book is found or when multiple
    disjoint roots are detected (candidate paths are listed in the message).
    """
    roots = discover_book_roots(input_path, max_depth=max_depth)
    if len(roots) > 1:
        raise ValidationError(_format_multiple_books(roots))
    return roots[0]


def find_track_files(book_root: Path) -> list[Path]:
    """Return supported audio files directly under book_root, sorted by name."""
    book_root = book_root.resolve()
    tracks = _direct_audio_files(book_root)
    if not tracks:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValidationError(
            f"No audio files found in {book_root}; supported extensions: {supported}"
        )
    return tracks


def _subdirs_with_direct_audio(book_root: Path) -> list[Path]:
    return sorted(
        (
            child
            for child in book_root.iterdir()
            if child.is_dir() and _direct_audio_files(child)
        ),
        key=lambda p: p.name.lower(),
    )


def _collect_from_disc_subdirs(book_root: Path, disc_subdirs: list[Path]) -> list[BookAudio]:
    ordered = sorted(disc_subdirs, key=lambda p: disc_folder_sort_key(p.name))
    audio: list[BookAudio] = []
    for disc_dir in ordered:
        for track in find_track_files(disc_dir):
            audio.append(
                BookAudio(
                    source=track,
                    dest_relative=Path(disc_dir.name) / track.name,
                )
            )
    return audio


def collect_book_audio(book_root: Path) -> list[BookAudio]:
    """Return audio files with destination paths relative to the title folder."""
    book_root = book_root.resolve()

    if book_root.is_file():
        if not _is_audio_file(book_root):
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValidationError(
                f"Unsupported file type {book_root.suffix!r}; supported: {supported}"
            )
        return [BookAudio(source=book_root, dest_relative=Path(book_root.name))]

    try:
        tracks = find_track_files(book_root)
    except ValidationError:
        audio_subdirs = _subdirs_with_direct_audio(book_root)
        if len(audio_subdirs) >= 2 and _is_disc_layout(audio_subdirs):
            return _collect_from_disc_subdirs(book_root, audio_subdirs)
        if len(audio_subdirs) == 1:
            tracks = find_track_files(audio_subdirs[0])
            return [
                BookAudio(source=track, dest_relative=Path(track.name))
                for track in tracks
            ]
        raise
    else:
        return [
            BookAudio(source=track, dest_relative=Path(track.name))
            for track in tracks
        ]


def collect_track_files(book_root: Path) -> list[Path]:
    """Return audio tracks for a resolved book root."""
    return [audio.source for audio in collect_book_audio(book_root)]


def sidecar_root(input_path: Path, book_root: Path) -> Path:
    """Return the directory to search for sidecars and cover images."""
    input_path = input_path.resolve()
    book_root = book_root.resolve()
    if input_path.is_file():
        return input_path.parent
    return book_root


def _is_cover_sidecar(path: Path) -> bool:
    stem = path.stem.lower()
    suffix = path.suffix.lower()
    return stem in _COVER_BASENAMES and suffix in _COVER_EXTENSIONS


def find_cover_sidecar(sidecar_root: Path) -> Path | None:
    """Return the highest-priority cover image at *sidecar_root*, if any."""
    sidecar_root = sidecar_root.resolve()
    if not sidecar_root.is_dir():
        return None

    by_key: dict[tuple[str, str], Path] = {}
    for child in sidecar_root.iterdir():
        if child.is_file() and _is_cover_sidecar(child):
            by_key[(child.stem.lower(), child.suffix.lower())] = child

    for basename in _COVER_BASENAMES:
        for ext in (".jpg", ".jpeg", ".png"):
            match = by_key.get((basename, ext))
            if match is not None:
                return match
    return None


def list_copy_sidecars(sidecar_root: Path) -> list[Path]:
    """Return text and OPF sidecars to copy into the title folder."""
    sidecar_root = sidecar_root.resolve()
    sidecars: list[Path] = []
    for child in sidecar_root.iterdir():
        if not child.is_file():
            continue
        name_lower = child.name.lower()
        if name_lower in _COPY_SIDECAR_NAMES or name_lower.endswith(".opf"):
            sidecars.append(child)
    return sorted(sidecars, key=lambda p: p.name.lower())


def list_sidecars(sidecar_root: Path) -> list[Path]:
    """Return all recognized sidecar files at *sidecar_root*."""
    sidecar_root = sidecar_root.resolve()
    sidecars: list[Path] = []
    cover = find_cover_sidecar(sidecar_root)
    if cover is not None:
        sidecars.append(cover)
    sidecars.extend(list_copy_sidecars(sidecar_root))
    return sorted(sidecars, key=lambda p: p.name.lower())
