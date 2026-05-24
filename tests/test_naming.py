"""Unit tests for folder name sanitization and ABS maximal naming."""

from __future__ import annotations

import pytest

from abs_organize.metadata import BookMetadata
from abs_organize.naming import (
    _sanitize_segment,
    author_folder,
    book_destination_segments,
    build_title_folder,
)


def test_sanitize_replaces_illegal_chars():
    assert author_folder("Author/Name: Test") == "Author-Name- Test"


def test_sanitize_collapses_whitespace():
    assert build_title_folder(BookMetadata(author="A", title="  Book   Title  ")) == (
        "Book Title"
    )


def test_sanitize_strips_trailing_dots_and_spaces():
    assert _sanitize_segment("Title...  ") == "Title"


def test_sanitize_truncates_long_segments():
    long_name = "A" * 200
    result = _sanitize_segment(long_name)
    assert len(result) == 180


def test_sanitize_verbose_logs_substitutions():
    messages: list[str] = []
    _sanitize_segment("bad/name", on_log=messages.append)
    assert any("illegal" in message.lower() for message in messages)


def test_sanitize_replaces_null_byte():
    assert _sanitize_segment("a\x00b") == "a-b"


@pytest.mark.parametrize("year", [1994, 1990, 2001, 2021])
def test_build_title_folder_preserves_year_digits(year: int):
    meta = BookMetadata(
        author="Andy Weir",
        title="Project Hail Mary",
        year=year,
        narrator="Ray Porter",
    )
    assert build_title_folder(meta) == (
        f"{year} - Project Hail Mary {{Ray Porter}}"
    )


def test_golden_terry_goodkind_series_layout():
    meta = BookMetadata(
        author="Terry Goodkind",
        title="Wizards First Rule",
        series="Sword of Truth",
        sequence=1,
        year=1994,
        narrator="Sam Tsoutsouvas",
    )
    assert book_destination_segments(meta) == (
        "Terry Goodkind",
        "Sword of Truth",
        "Vol 1 - 1994 - Wizards First Rule {Sam Tsoutsouvas}",
    )


def test_golden_standalone_with_narrator():
    meta = BookMetadata(
        author="Steven Levy",
        title="Hackers - Heroes of the Computer Revolution",
        narrator="Mike Chamberlain",
    )
    assert book_destination_segments(meta) == (
        "Steven Levy",
        None,
        "Hackers - Heroes of the Computer Revolution {Mike Chamberlain}",
    )


def test_subtitle_included_when_config_enabled():
    meta = BookMetadata(
        author="Terry Goodkind",
        title="Wizards First Rule",
        series="Sword of Truth",
        sequence=1,
        year=1994,
        narrator="Sam Tsoutsouvas",
        subtitle="Book One",
    )
    title = build_title_folder(meta, include_subtitle_in_folder=True)
    assert title == (
        "Vol 1 - 1994 - Wizards First Rule - Book One {Sam Tsoutsouvas}"
    )


def test_subtitle_omitted_by_default():
    meta = BookMetadata(
        author="A",
        title="Title",
        subtitle="Sub",
        narrator="N",
    )
    title = build_title_folder(meta, include_subtitle_in_folder=False)
    assert title == "Title {N}"


def test_minimal_metadata_title_only():
    meta = BookMetadata(author="Jane Author", title="Book Title")
    assert book_destination_segments(meta) == ("Jane Author", None, "Book Title")
