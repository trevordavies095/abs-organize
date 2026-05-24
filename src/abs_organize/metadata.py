"""Read audio metadata and resolve author/title for simple naming."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mutagen import File as MutagenFile

SUPPORTED_EXTENSIONS = {".mp3", ".m4b", ".m4a"}

AUTHOR_KEYS = ("albumartist", "artist")
TITLE_KEYS = ("album", "title")


class MetadataError(Exception):
    """Author or title could not be resolved from tags."""


class ValidationError(Exception):
    """Input path or library path is invalid."""


@dataclass(frozen=True)
class BookMetadata:
    author: str
    title: str


def _tag_value(tags: object, key: str) -> str | None:
    if tags is None:
        return None
    raw = tags.get(key)
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        if not raw:
            return None
        raw = raw[0]
    text = str(raw).strip()
    return text or None


def _first_tag(tags: object, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _tag_value(tags, key)
        if value:
            return value
    return None


def read_tags(path: Path) -> object:
    audio = MutagenFile(path, easy=True)
    if audio is None:
        raise MetadataError(f"Could not read audio metadata from {path}")
    return audio.tags


def resolve_metadata(tags: object) -> BookMetadata:
    author = _first_tag(tags, AUTHOR_KEYS)
    title = _first_tag(tags, TITLE_KEYS)

    missing: list[str] = []
    if not author:
        missing.append(f"author ({' or '.join(AUTHOR_KEYS)})")
    if not title:
        missing.append(f"title ({' or '.join(TITLE_KEYS)})")

    if missing:
        raise MetadataError(
            "Missing required metadata: "
            + ", ".join(missing)
            + ". Set tags on the file or use a tagged source."
        )

    return BookMetadata(author=author, title=title)


def read_book_metadata(path: Path) -> BookMetadata:
    tags = read_tags(path)
    return resolve_metadata(tags)
