"""Unit tests for majority-vote metadata resolution."""

from __future__ import annotations

import pytest

from abs_organize.metadata import (
    BookMetadata,
    MetadataError,
    MetadataOverrides,
    resolve_majority,
)


def _meta(**kwargs: object) -> BookMetadata:
    defaults = {"author": "Author A", "title": "Title A"}
    defaults.update(kwargs)
    return BookMetadata(**defaults)  # type: ignore[arg-type]


def test_majority_picks_three_of_five():
    per_file = [
        _meta(author="Jane Author"),
        _meta(author="Jane Author"),
        _meta(author="Jane Author"),
        _meta(author="Other Author"),
        _meta(author="Other Author"),
    ]
    resolved = resolve_majority(per_file)
    assert resolved.metadata.author == "Jane Author"
    assert any("author tag conflict" in w for w in resolved.warnings)


def test_conflicting_title_emits_warning():
    per_file = [
        _meta(title="Book One"),
        _meta(title="Book One"),
        _meta(title="Book Two"),
    ]
    resolved = resolve_majority(per_file)
    assert resolved.metadata.title == "Book One"
    assert any("title tag conflict" in w for w in resolved.warnings)


def test_no_majority_author_raises():
    per_file = [
        _meta(author="Alice"),
        _meta(author="Bob"),
    ]
    with pytest.raises(MetadataError, match="No majority for required field 'author'"):
        resolve_majority(per_file)


def test_no_majority_title_raises():
    per_file = [
        _meta(title="Alpha"),
        _meta(title="Beta"),
        _meta(title="Gamma"),
    ]
    with pytest.raises(MetadataError, match="No majority for required field 'title'"):
        resolve_majority(per_file)


def test_optional_field_lexicographic_tie_break():
    per_file = [
        _meta(narrator="Zed"),
        _meta(narrator="Amy"),
    ]
    resolved = resolve_majority(per_file)
    assert resolved.metadata.narrator == "Amy"
    assert any("narrator tag conflict" in w for w in resolved.warnings)


def test_optional_field_all_empty_returns_none():
    per_file = [_meta(), _meta()]
    resolved = resolve_majority(per_file)
    assert resolved.metadata.series is None
    assert resolved.metadata.narrator is None


def test_resolve_book_metadata_applies_overrides(tmp_path, make_tagged_mp3):
    from abs_organize.metadata import resolve_book_metadata

    a = make_tagged_mp3(name="01.mp3", albumartist="A", album="One")
    b = make_tagged_mp3(name="02.mp3", albumartist="A", album="Two")
    resolved = resolve_book_metadata(
        [a, b],
        overrides=MetadataOverrides(author="Override Author", title="Override Title"),
    )
    assert resolved.metadata.author == "Override Author"
    assert resolved.metadata.title == "Override Title"
    assert not any("author tag conflict" in w for w in resolved.warnings)
    assert not any("title tag conflict" in w for w in resolved.warnings)
