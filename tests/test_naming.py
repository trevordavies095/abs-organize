"""Unit tests for folder name sanitization."""

from __future__ import annotations

from abs_organize.metadata import BookMetadata
from abs_organize.naming import author_folder, book_destination_dirs, title_folder


def test_sanitize_replaces_illegal_chars():
    assert author_folder("Author/Name: Test") == "Author-Name- Test"


def test_sanitize_collapses_whitespace():
    assert title_folder("  Book   Title  ") == "Book Title"


def test_book_destination_dirs():
    meta = BookMetadata(author="Jane Author", title="Book Title")
    assert book_destination_dirs(meta) == ("Jane Author", "Book Title")
