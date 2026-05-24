"""Read audio metadata and resolve fields for ABS naming.

Majority vote rules:
- Required fields (author, title): strict majority (count > n/2) or MetadataError.
- Optional fields: highest count among non-empty values; lexicographic tie-break.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile

SUPPORTED_EXTENSIONS = {".mp3", ".m4b", ".m4a", ".flac", ".ogg"}

AUTHOR_KEYS = ("albumartist", "artist")
TITLE_KEYS = ("album", "title")
NARRATOR_KEYS = ("composer",)
YEAR_KEYS = ("date",)
SUBTITLE_KEYS = ("subtitle",)
SERIES_KEYS = ("grouping",)

_MP4_MOVEMENT_NAME = "\xa9mvn"
_MP4_MOVEMENT_INDEX = "\xa9mvi"
_MP4_COMPOSER = "\xa9wrt"
_YEAR_PATTERN = re.compile(r"^(\d{4})")


class MetadataError(Exception):
    """Author or title could not be resolved from tags."""


class ValidationError(Exception):
    """Input path or library path is invalid."""


@dataclass(frozen=True)
class BookMetadata:
    author: str
    title: str
    series: str | None = None
    sequence: int | float | None = None
    year: int | None = None
    narrator: str | None = None
    subtitle: str | None = None


@dataclass(frozen=True)
class MetadataOverrides:
    author: str | None = None
    title: str | None = None
    year: int | None = None
    series: str | None = None
    sequence: int | float | None = None
    narrator: str | None = None


@dataclass(frozen=True)
class ResolvedMetadata:
    metadata: BookMetadata
    warnings: tuple[str, ...]


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


def parse_year(value: str | None) -> int | None:
    if not value:
        return None
    match = _YEAR_PATTERN.match(value.strip())
    if match is None:
        return None
    return int(match.group(1))


def _mp4_atom_text(tags: object, key: str) -> str | None:
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


def _mp4_atom_number(tags: object, key: str) -> int | float | None:
    if tags is None:
        return None
    raw = tags.get(key)
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        if not raw:
            return None
        raw = raw[0]
    if isinstance(raw, (int, float)):
        return raw
    text = str(raw).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return number


def _read_mp4_movement(path: Path) -> tuple[str | None, int | float | None]:
    audio = MutagenFile(path)
    if audio is None or audio.tags is None:
        return None, None
    series = _mp4_atom_text(audio.tags, _MP4_MOVEMENT_NAME)
    sequence = _mp4_atom_number(audio.tags, _MP4_MOVEMENT_INDEX)
    return series, sequence


def _read_mp4_narrator(path: Path) -> str | None:
    audio = MutagenFile(path)
    if audio is None or audio.tags is None:
        return None
    return _mp4_atom_text(audio.tags, _MP4_COMPOSER)


def _read_id3_subtitle(path: Path) -> str | None:
    audio = MutagenFile(path)
    if audio is None or audio.tags is None:
        return None
    for frame in audio.tags.getall("TIT3"):
        if frame.text:
            text = str(frame.text[0]).strip()
            if text:
                return text
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

    return BookMetadata(
        author=author,
        title=title,
        series=_first_tag(tags, SERIES_KEYS),
        year=parse_year(_first_tag(tags, YEAR_KEYS)),
        narrator=_first_tag(tags, NARRATOR_KEYS),
        subtitle=_first_tag(tags, SUBTITLE_KEYS),
    )


def read_book_metadata(path: Path) -> BookMetadata:
    tags = read_tags(path)
    metadata = resolve_metadata(tags)

    suffix = path.suffix.lower()
    updates: dict[str, object] = {}

    if suffix == ".mp3":
        if metadata.subtitle is None:
            subtitle = _read_id3_subtitle(path)
            if subtitle:
                updates["subtitle"] = subtitle
    elif suffix in {".m4b", ".m4a"}:
        mp4_series, mp4_sequence = _read_mp4_movement(path)
        if metadata.series is None and mp4_series:
            updates["series"] = mp4_series
        if metadata.sequence is None and mp4_sequence is not None:
            updates["sequence"] = mp4_sequence
        if metadata.narrator is None:
            narrator = _read_mp4_narrator(path)
            if narrator:
                updates["narrator"] = narrator

    if updates:
        return replace(metadata, **updates)
    return metadata


def _strict_majority_winner(
    values: list[str], field_name: str
) -> str:
    if not values:
        raise MetadataError(
            f"No majority for required field {field_name!r} across audio files."
        )
    counts = Counter(values)
    top_count = max(counts.values())
    winners = sorted(v for v, c in counts.items() if c == top_count)
    if top_count <= len(values) / 2:
        raise MetadataError(
            f"No majority for required field {field_name!r} across audio files "
            f"({len(winners)} tied at {top_count}/{len(values)})."
        )
    return winners[0]


def _optional_majority_winner(values: list[Any]) -> Any | None:
    if not values:
        return None
    counts = Counter(values)
    top_count = max(counts.values())
    winners = sorted(v for v, c in counts.items() if c == top_count)
    return winners[0]


def _format_conflict_value(value: Any) -> str:
    return repr(value)


def _vote_field(
    per_file: list[BookMetadata],
    *,
    field_name: str,
    getter: Callable[[BookMetadata], Any],
    required: bool,
) -> tuple[Any, str | None]:
    values = [getter(m) for m in per_file]
    non_empty = [v for v in values if v is not None and v != ""]
    if not non_empty:
        if required:
            raise MetadataError(
                f"No majority for required field {field_name!r} across audio files."
            )
        return None, None

    if required:
        str_values = [str(v) for v in non_empty]
        winner = _strict_majority_winner(str_values, field_name)
        warning = None
        distinct = set(str_values)
        if len(distinct) > 1:
            parts = ", ".join(
                f"{_format_conflict_value(v)} ({str_values.count(v)})"
                for v in sorted(distinct)
            )
            warning = (
                f"{field_name} tag conflict: {parts} — using {_format_conflict_value(winner)}"
            )
        return winner, warning

    winner = _optional_majority_winner(non_empty)
    warning = None
    distinct = set(non_empty)
    if len(distinct) > 1:
        str_distinct = sorted(distinct, key=lambda v: str(v))
        parts = ", ".join(
            f"{_format_conflict_value(v)} ({non_empty.count(v)})" for v in str_distinct
        )
        warning = (
            f"{field_name} tag conflict: {parts} — using {_format_conflict_value(winner)}"
        )
    return winner, warning


def resolve_majority(
    per_file: list[BookMetadata],
    *,
    overrides: MetadataOverrides | None = None,
) -> ResolvedMetadata:
    if not per_file:
        raise MetadataError("No audio files to resolve metadata from.")

    overrides = overrides or MetadataOverrides()
    warnings: list[str] = []
    fields: dict[str, Any] = {}

    field_specs: list[tuple[str, Callable[[BookMetadata], Any], bool]] = [
        ("author", lambda m: m.author, True),
        ("title", lambda m: m.title, True),
        ("series", lambda m: m.series, False),
        ("year", lambda m: m.year, False),
        ("narrator", lambda m: m.narrator, False),
        ("sequence", lambda m: m.sequence, False),
        ("subtitle", lambda m: m.subtitle, False),
    ]
    override_fields = {
        "author": overrides.author,
        "title": overrides.title,
        "year": overrides.year,
        "series": overrides.series,
        "sequence": overrides.sequence,
        "narrator": overrides.narrator,
    }

    for field_name, getter, required in field_specs:
        if field_name in override_fields and override_fields[field_name] is not None:
            fields[field_name] = override_fields[field_name]
            continue
        value, warning = _vote_field(
            per_file, field_name=field_name, getter=getter, required=required
        )
        fields[field_name] = value
        if warning:
            warnings.append(warning)

    metadata = BookMetadata(
        author=fields["author"],
        title=fields["title"],
        series=fields["series"],
        year=fields["year"],
        narrator=fields["narrator"],
        sequence=fields["sequence"],
        subtitle=fields["subtitle"],
    )
    return ResolvedMetadata(metadata=metadata, warnings=tuple(warnings))


def resolve_book_metadata(
    paths: list[Path],
    *,
    overrides: MetadataOverrides | None = None,
) -> ResolvedMetadata:
    per_file = [read_book_metadata(path) for path in paths]
    return resolve_majority(per_file, overrides=overrides)


_GAP_FILL_FIELDS = ("series", "sequence", "year", "narrator", "subtitle")


def apply_gap_fill(
    resolved: ResolvedMetadata,
    *,
    opf_metadata: BookMetadata | None = None,
    reader_txt: str | None = None,
    overrides: MetadataOverrides | None = None,
) -> ResolvedMetadata:
    """Fill empty optional metadata from OPF and reader.txt after audio majority."""
    overrides = overrides or MetadataOverrides()
    override_map = {
        "series": overrides.series,
        "sequence": overrides.sequence,
        "year": overrides.year,
        "narrator": overrides.narrator,
    }

    current = resolved.metadata
    updates: dict[str, object] = {}

    if opf_metadata is not None:
        for field in _GAP_FILL_FIELDS:
            if override_map.get(field) is not None:
                continue
            existing = getattr(current, field)
            if existing is not None and existing != "":
                continue
            incoming = getattr(opf_metadata, field)
            if incoming is not None and incoming != "":
                updates[field] = incoming

    if reader_txt and override_map.get("narrator") is None:
        narrator = updates.get("narrator", current.narrator)
        if narrator is None or narrator == "":
            updates["narrator"] = reader_txt

    if not updates:
        return resolved

    metadata = replace(current, **updates)
    return ResolvedMetadata(metadata=metadata, warnings=resolved.warnings)
