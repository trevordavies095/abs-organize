"""Build simple author/title folder names from metadata."""

from __future__ import annotations

import re

from abs_organize.metadata import BookMetadata

_ILLEGAL_CHARS = re.compile(r"[/:\0]")
_WHITESPACE = re.compile(r"\s+")


def _sanitize_segment(value: str) -> str:
    cleaned = _ILLEGAL_CHARS.sub("-", value)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    return cleaned


def author_folder(author: str) -> str:
    segment = _sanitize_segment(author)
    if not segment:
        raise ValueError("Author folder name is empty after sanitization")
    return segment


def title_folder(title: str) -> str:
    segment = _sanitize_segment(title)
    if not segment:
        raise ValueError("Title folder name is empty after sanitization")
    return segment


def book_destination_dirs(metadata: BookMetadata) -> tuple[str, str]:
    return author_folder(metadata.author), title_folder(metadata.title)
