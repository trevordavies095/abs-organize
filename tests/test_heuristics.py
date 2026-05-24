"""Unit tests for folder-name heuristics."""

from __future__ import annotations

from abs_organize.heuristics import guess_from_name


def test_guess_author_title_hyphen():
    result = guess_from_name("Jane Author - Great Book")
    assert result is not None
    assert result.author == "Jane Author"
    assert result.title == "Great Book"
    assert result.year is None


def test_guess_author_title_en_dash():
    result = guess_from_name("Jane Author – Great Book")
    assert result is not None
    assert result.author == "Jane Author"
    assert result.title == "Great Book"


def test_guess_author_title_em_dash():
    result = guess_from_name("Jane Author — Great Book")
    assert result is not None
    assert result.author == "Jane Author"
    assert result.title == "Great Book"


def test_guess_title_with_internal_hyphen():
    result = guess_from_name("Jane Author - Great Book - Part Two")
    assert result is not None
    assert result.author == "Jane Author"
    assert result.title == "Great Book - Part Two"


def test_guess_trailing_year():
    result = guess_from_name("Jane Author - Great Book (2020)")
    assert result is not None
    assert result.author == "Jane Author"
    assert result.title == "Great Book"
    assert result.year == 2020


def test_guess_rejects_no_separator():
    assert guess_from_name("Great Book") is None


def test_guess_rejects_empty_author():
    assert guess_from_name(" - Great Book") is None


def test_guess_rejects_empty_title():
    assert guess_from_name("Jane Author - ") is None


def test_guess_rejects_year_only_title():
    assert guess_from_name("Jane Author - (2020)") is None


def test_guess_strips_whitespace():
    result = guess_from_name("  Jane Author  -  Great Book  ")
    assert result is not None
    assert result.author == "Jane Author"
    assert result.title == "Great Book"
