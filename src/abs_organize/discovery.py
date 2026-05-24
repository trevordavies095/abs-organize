"""Discover audio tracks and sidecars in a book root directory."""

from __future__ import annotations

from pathlib import Path

from abs_organize.metadata import SUPPORTED_EXTENSIONS, ValidationError

_SIDECAR_NAMES = frozenset(
    {
        "cover.jpg",
        "folder.jpg",
        "Cover.jpg",
        "desc.txt",
        "reader.txt",
    }
)


def find_track_files(book_root: Path) -> list[Path]:
    """Return supported audio files directly under book_root, sorted by name."""
    book_root = book_root.resolve()
    tracks = [
        child
        for child in book_root.iterdir()
        if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if not tracks:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValidationError(
            f"No audio files found in {book_root}; supported extensions: {supported}"
        )
    return sorted(tracks, key=lambda p: p.name.lower())


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
