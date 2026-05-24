"""Unit tests for album/title narrator suffix parsing."""

from __future__ import annotations

import pytest

from abs_organize.metadata import split_title_and_narrator


@pytest.mark.parametrize(
    ("title", "expected_title", "expected_narrator"),
    [
        (
            "A Game of Thrones (read by Roy Dotrice)",
            "A Game of Thrones",
            "Roy Dotrice",
        ),
        (
            "Beyond Reach (narrated by Joyce Bean)",
            "Beyond Reach",
            "Joyce Bean",
        ),
        (
            "The Book (performed by Sam Tsoutsouvas)",
            "The Book",
            "Sam Tsoutsouvas",
        ),
        (
            "The Book [read by Ray Porter]",
            "The Book",
            "Ray Porter",
        ),
        (
            "The Book (Read By Ray Porter)",
            "The Book",
            "Ray Porter",
        ),
        (
            "The Book (READ BY Ray Porter)",
            "The Book",
            "Ray Porter",
        ),
    ],
)
def test_split_title_and_narrator_matches_suffix(
    title: str, expected_title: str, expected_narrator: str
) -> None:
    clean, narrator = split_title_and_narrator(title)
    assert clean == expected_title
    assert narrator == expected_narrator


@pytest.mark.parametrize(
    "title",
    [
        "A Game of Thrones",
        "Part 2 - read by committee",
        "Title (read by)",
        "(read by Roy Dotrice)",
        "Title (read by X) (Unabridged)",
        "Title(read by X)",
    ],
)
def test_split_title_and_narrator_no_op(title: str) -> None:
    clean, narrator = split_title_and_narrator(title)
    assert clean == title
    assert narrator is None
