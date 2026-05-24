"""Unit tests for metadata resolution."""

from __future__ import annotations

import pytest

from abs_organize.metadata import MetadataError, resolve_metadata


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
