"""Discover audio tracks, book roots, and sidecars.

Book-root heuristic (see issue #6):
- **Container** files (``.m4b``, ``.m4a``): each direct sibling is its own book.
- **Track-style** files (``.mp3``, ``.flac``, ``.ogg``): all direct siblings in one folder are one book.
- **No direct audio**: recurse into child directories (max depth ``MAX_DISCOVERY_DEPTH``).
- **Mixed** container + track-style at the same level: multiple candidates → fail.
"""

from __future__ import annotations

from pathlib import Path

from abs_organize.metadata import SUPPORTED_EXTENSIONS, ValidationError

MAX_DISCOVERY_DEPTH = 5

_CONTAINER_EXTENSIONS = frozenset({".m4b", ".m4a"})

_SIDECAR_NAMES = frozenset(
    {
        "cover.jpg",
        "folder.jpg",
        "Cover.jpg",
        "desc.txt",
        "reader.txt",
    }
)

_MULTIPLE_BOOKS_PREFIX = (
    "Multiple books detected in INPUT. Re-run on one book at a time:"
)


def _is_audio_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def _direct_audio_files(directory: Path) -> list[Path]:
    return sorted(
        (child for child in directory.iterdir() if _is_audio_file(child)),
        key=lambda p: p.name.lower(),
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

    return _subdir_audio_roots(directory, depth_remaining=depth_remaining)


def _format_multiple_books(candidates: list[Path]) -> str:
    lines = "\n".join(f"  {path}" for path in sorted(candidates, key=str))
    return f"{_MULTIPLE_BOOKS_PREFIX}\n{lines}"


def discover_book_root(
    input_path: Path, *, max_depth: int = MAX_DISCOVERY_DEPTH
) -> Path:
    """Resolve a single book root under *input_path*.

    For a file path, returns the resolved file. For a directory, locates the
    unique book root using container vs track-style rules and optional wrapper
    descent. Raises ``ValidationError`` when no book is found or when multiple
    disjoint roots are detected (candidate paths are listed in the message).
    """
    input_path = input_path.resolve()

    if input_path.is_file():
        return input_path

    if not input_path.is_dir():
        raise ValidationError(f"Input must be a file or directory: {input_path}")

    roots = _book_roots_at(input_path, depth_remaining=max_depth)

    if not roots:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValidationError(
            f"No audio files found in {input_path}; supported extensions: {supported}"
        )

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


def collect_track_files(book_root: Path) -> list[Path]:
    """Return audio tracks for a resolved book root.

    Uses direct children of *book_root* when present; otherwise, if exactly one
    immediate subdirectory contains audio, uses that subdirectory (e.g.
    ``BookName/tracks/*.mp3``).
    """
    book_root = book_root.resolve()

    if book_root.is_file():
        if not _is_audio_file(book_root):
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValidationError(
                f"Unsupported file type {book_root.suffix!r}; supported: {supported}"
            )
        return [book_root]

    try:
        return find_track_files(book_root)
    except ValidationError:
        audio_subdirs = _subdirs_with_direct_audio(book_root)
        if len(audio_subdirs) == 1:
            return find_track_files(audio_subdirs[0])
        raise


def list_sidecars(book_root: Path) -> list[Path]:
    """Return recognized sidecar files at book root (not copied in this slice)."""
    book_root = book_root.resolve()
    sidecars: list[Path] = []
    for child in book_root.iterdir():
        if not child.is_file():
            continue
        name = child.name
        if name in _SIDECAR_NAMES or name.lower().endswith(".opf"):
            sidecars.append(child)
    return sorted(sidecars, key=lambda p: p.name.lower())
