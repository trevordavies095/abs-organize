"""Unit tests for book-root discovery."""

from __future__ import annotations

import pytest

from abs_organize.discovery import (
    collect_track_files,
    discover_book_root,
)
from abs_organize.metadata import ValidationError


def test_discover_book_root_single_file(make_tagged_mp3):
    source = make_tagged_mp3(albumartist="A", album="B")
    assert discover_book_root(source) == source.resolve()


def test_discover_book_root_flat_track_folder(tmp_path, make_tagged_mp3):
    book = tmp_path / "Book"
    book.mkdir()
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    for i in range(1, 3):
        path = make_tagged_mp3(name=f"{i:02d}.mp3", **tags)
        path.rename(book / path.name)

    assert discover_book_root(book) == book.resolve()


def test_discover_book_root_wrapper_one_level(tmp_path, make_tagged_mp3):
    book = tmp_path / "BookName"
    book.mkdir()
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    for i in range(1, 3):
        path = make_tagged_mp3(name=f"{i:02d}.mp3", **tags)
        path.rename(book / path.name)

    wrapper = tmp_path / "wrapper"
    wrapper.mkdir()
    book.rename(wrapper / book.name)

    assert discover_book_root(wrapper) == (wrapper / "BookName").resolve()


def test_collect_track_files_nested_tracks_subdir(tmp_path, make_tagged_mp3):
    book = tmp_path / "BookName"
    tracks = book / "tracks"
    tracks.mkdir(parents=True)
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    for i in range(1, 3):
        path = make_tagged_mp3(name=f"{i:02d}.mp3", **tags)
        path.rename(tracks / path.name)

    root = discover_book_root(book)
    files = collect_track_files(root)

    assert root == tracks.resolve()
    assert [p.name for p in files] == ["01.mp3", "02.mp3"]


def test_discover_book_root_wrapper_with_tracks_subdir(tmp_path, make_tagged_mp3):
    book = tmp_path / "BookName"
    tracks = book / "tracks"
    tracks.mkdir(parents=True)
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    path = make_tagged_mp3(name="01.mp3", **tags)
    path.rename(tracks / path.name)

    wrapper = tmp_path / "wrapper"
    wrapper.mkdir()
    book.rename(wrapper / book.name)

    root = discover_book_root(wrapper)
    assert root == (wrapper / "BookName" / "tracks").resolve()
    assert collect_track_files(root)[0].name == "01.mp3"


def test_discover_book_root_two_sibling_m4b(tmp_path, make_tagged_m4b):
    root = tmp_path / "inbox"
    root.mkdir()
    a = make_tagged_m4b(name="a.m4b", artist="A1", title="T1")
    b = make_tagged_m4b(name="b.m4b", artist="A2", title="T2")
    a.rename(root / "a.m4b")
    b.rename(root / "b.m4b")

    with pytest.raises(ValidationError, match="Multiple books detected") as exc:
        discover_book_root(root)

    message = str(exc.value)
    assert str((root / "a.m4b").resolve()) in message
    assert str((root / "b.m4b").resolve()) in message


def test_discover_book_root_two_book_subfolders(tmp_path, make_tagged_mp3):
    root = tmp_path / "inbox"
    root.mkdir()
    for folder, album in (("bookA", "Alpha"), ("bookB", "Beta")):
        book_dir = root / folder
        book_dir.mkdir()
        path = make_tagged_mp3(
            name="01.mp3", albumartist="Jane Author", album=album
        )
        path.rename(book_dir / path.name)

    with pytest.raises(ValidationError, match="Multiple books detected") as exc:
        discover_book_root(root)

    message = str(exc.value)
    assert str((root / "bookA").resolve()) in message
    assert str((root / "bookB").resolve()) in message


def test_discover_book_root_mixed_container_and_mp3(tmp_path, make_tagged_m4b, make_tagged_mp3):
    root = tmp_path / "inbox"
    root.mkdir()
    m4b = make_tagged_m4b(name="book.m4b", artist="A", title="T")
    mp3 = make_tagged_mp3(name="01.mp3", albumartist="A", album="T")
    m4b.rename(root / "book.m4b")
    mp3.rename(root / "01.mp3")

    with pytest.raises(ValidationError, match="Multiple books detected") as exc:
        discover_book_root(root)

    message = str(exc.value)
    assert str((root / "book.m4b").resolve()) in message
    assert str(root.resolve()) in message


def test_discover_book_root_no_audio(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(ValidationError, match="No audio files found"):
        discover_book_root(empty)
