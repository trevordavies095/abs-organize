"""Build ABS-style author, series, and title folder names from metadata."""

from __future__ import annotations

import re
from collections.abc import Callable

from abs_organize.metadata import BookMetadata

_ILLEGAL_CHARS = re.compile(r'[/:\\<>"|?*\x00]')
_WHITESPACE = re.compile(r"\s+")
_MAX_SEGMENT_LENGTH = 180


def _sanitize_segment(
    value: str,
    *,
    on_log: Callable[[str], None] | None = None,
) -> str:
    def log(message: str) -> None:
        if on_log is not None:
            on_log(message)

    cleaned = value
    if _ILLEGAL_CHARS.search(cleaned):
        cleaned = _ILLEGAL_CHARS.sub("-", cleaned)
        log(f"Replaced illegal path characters in {value!r}")

    collapsed = _WHITESPACE.sub(" ", cleaned).strip()
    if collapsed != cleaned.strip():
        log(f"Collapsed whitespace in {value!r}")

    trimmed = collapsed.rstrip(" .")
    if trimmed != collapsed:
        log(f"Trimmed trailing dots/spaces from {collapsed!r}")

    if len(trimmed) > _MAX_SEGMENT_LENGTH:
        log(
            f"Truncated segment from {len(trimmed)} to {_MAX_SEGMENT_LENGTH} characters"
        )
        trimmed = trimmed[:_MAX_SEGMENT_LENGTH].rstrip(" .")

    return trimmed


def _format_sequence(sequence: int | float) -> str:
    if isinstance(sequence, float) and sequence.is_integer():
        sequence = int(sequence)
    return str(sequence)


def author_folder(
    author: str,
    *,
    on_log: Callable[[str], None] | None = None,
) -> str:
    segment = _sanitize_segment(author, on_log=on_log)
    if not segment:
        raise ValueError("Author folder name is empty after sanitization")
    return segment


def series_folder(
    series: str,
    *,
    on_log: Callable[[str], None] | None = None,
) -> str | None:
    segment = _sanitize_segment(series, on_log=on_log)
    if not segment:
        return None
    return segment


def build_title_folder(
    metadata: BookMetadata,
    *,
    include_subtitle_in_folder: bool = False,
    on_log: Callable[[str], None] | None = None,
) -> str:
    parts: list[str] = []

    if metadata.sequence is not None:
        parts.append(f"Vol {_format_sequence(metadata.sequence)} - ")

    if metadata.year is not None:
        parts.append(f"{metadata.year} - ")

    parts.append(metadata.title)

    if include_subtitle_in_folder and metadata.subtitle:
        parts.append(f" - {metadata.subtitle}")

    if metadata.narrator:
        parts.append(f" {{{metadata.narrator}}}")

    raw = "".join(parts)
    segment = _sanitize_segment(raw, on_log=on_log)
    if not segment:
        raise ValueError("Title folder name is empty after sanitization")
    return segment


def book_destination_segments(
    metadata: BookMetadata,
    *,
    include_subtitle_in_folder: bool = False,
    on_log: Callable[[str], None] | None = None,
) -> tuple[str, str | None, str]:
    author = author_folder(metadata.author, on_log=on_log)
    series = (
        series_folder(metadata.series, on_log=on_log)
        if metadata.series
        else None
    )
    title = build_title_folder(
        metadata,
        include_subtitle_in_folder=include_subtitle_in_folder,
        on_log=on_log,
    )
    return author, series, title
