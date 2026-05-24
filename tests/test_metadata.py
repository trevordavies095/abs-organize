"""Unit tests for metadata resolution."""

from __future__ import annotations

import pytest

from abs_organize.metadata import (
    MetadataError,
    parse_year,
    resolve_metadata,
)


class _FakeTags(dict):
    """Dict-like tags container matching Mutagen easy interface."""


def test_resolve_prefers_albumartist_over_artist():
    tags = _FakeTags(
        albumartist=["Jane Author"],
        artist=["Wrong Author"],
        album=["Book Title"],
    )
    meta = resolve_metadata(tags)
    assert meta.author == "Jane Author"
    assert meta.title == "Book Title"


def test_resolve_falls_back_to_artist_and_title():
    tags = _FakeTags(artist=["Jane Author"], title=["Book Title"])
    meta = resolve_metadata(tags)
    assert meta.author == "Jane Author"
    assert meta.title == "Book Title"


def test_resolve_strips_whitespace():
    tags = _FakeTags(albumartist=["  Jane  "], album=["  Book  "])
    meta = resolve_metadata(tags)
    assert meta.author == "Jane"
    assert meta.title == "Book"


def test_resolve_optional_fields():
    tags = _FakeTags(
        albumartist=["Terry Goodkind"],
        album=["Wizards First Rule"],
        grouping=["Sword of Truth"],
        date=["1994"],
        composer=["Sam Tsoutsouvas"],
        subtitle=["Book One"],
    )
    meta = resolve_metadata(tags)
    assert meta.series == "Sword of Truth"
    assert meta.year == 1994
    assert meta.narrator == "Sam Tsoutsouvas"
    assert meta.subtitle == "Book One"
    assert meta.sequence is None


def test_resolve_strips_narrator_prefix_from_composer():
    tags = _FakeTags(
        albumartist=["Author"],
        album=["Beyond Reach"],
        composer=["Narrated by Joyce Bean"],
    )
    meta = resolve_metadata(tags)
    assert meta.narrator == "Joyce Bean"


def test_parse_year_from_iso_date():
    assert parse_year("1994-01-01") == 1994


def test_parse_year_invalid():
    assert parse_year("nineteen ninety-four") is None


def test_resolve_missing_author_raises():
    tags = _FakeTags(album=["Book Title"])
    with pytest.raises(MetadataError, match="author"):
        resolve_metadata(tags)


def test_resolve_missing_title_raises():
    tags = _FakeTags(albumartist=["Jane Author"])
    with pytest.raises(MetadataError, match="title"):
        resolve_metadata(tags)


def test_resolve_empty_tags_raises():
    with pytest.raises(MetadataError):
        resolve_metadata(_FakeTags())
