"""Unit tests for narrator prefix normalization."""

from __future__ import annotations

import pytest

from abs_organize.metadata import normalize_narrator


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Narrated by Joyce Bean", "Joyce Bean"),
        ("narrated by Joyce Bean", "Joyce Bean"),
        ("NARRATED BY Joyce Bean", "Joyce Bean"),
        ("Read by Ray Porter", "Ray Porter"),
        ("read by Ray Porter", "Ray Porter"),
        ("Performed by Sam Tsoutsouvas", "Sam Tsoutsouvas"),
        ("Narrated by  Joyce   Bean", "Joyce Bean"),
        ("Ray Porter", "Ray Porter"),
        ("Sam Tsoutsouvas", "Sam Tsoutsouvas"),
        ("  Mike Chamberlain  ", "Mike Chamberlain"),
    ],
)
def test_normalize_narrator_strips_prefixes(raw: str, expected: str) -> None:
    assert normalize_narrator(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "Narrated by",
        "Read by",
        "Performed by",
        "   ",
        "",
    ],
)
def test_normalize_narrator_empty_after_strip(raw: str) -> None:
    assert normalize_narrator(raw) == ""
