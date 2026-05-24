"""Unit tests for book-root discovery."""

from __future__ import annotations

import pytest

from abs_organize.discovery import (
    collect_book_audio,
    collect_track_files,
    discover_book_root,
    discover_book_roots,
    find_cover_sidecar,
    is_disc_folder_name,
    list_copy_sidecars,
    sidecar_root,
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
    assert "--batch" in message


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
    assert "--batch" in message


def test_discover_book_roots_two_book_subfolders(tmp_path, make_tagged_mp3):
    root = tmp_path / "inbox"
    root.mkdir()
    for folder, album in (("bookA", "Alpha"), ("bookB", "Beta")):
        book_dir = root / folder
        book_dir.mkdir()
        path = make_tagged_mp3(
            name="01.mp3", albumartist="Jane Author", album=album
        )
        path.rename(book_dir / path.name)

    roots = discover_book_roots(root)
    assert roots == [
        (root / "bookA").resolve(),
        (root / "bookB").resolve(),
    ]


def test_discover_book_roots_multi_disc(tmp_path, make_tagged_mp3):
    book = tmp_path / "Book"
    book.mkdir()
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    for disc_name in ("Disc 1", "Disc 2"):
        disc = book / disc_name
        disc.mkdir()
        path = make_tagged_mp3(name="01.mp3", **tags)
        path.rename(disc / path.name)

    assert discover_book_roots(book) == [book.resolve()]


def test_discover_book_roots_mixed_container_and_mp3(
    tmp_path, make_tagged_m4b, make_tagged_mp3
):
    root = tmp_path / "inbox"
    root.mkdir()
    m4b = make_tagged_m4b(name="book.m4b", artist="A", title="T")
    mp3 = make_tagged_mp3(name="01.mp3", albumartist="A", album="T")
    m4b.rename(root / "book.m4b")
    mp3.rename(root / "01.mp3")

    with pytest.raises(ValidationError, match="Multiple books detected"):
        discover_book_roots(root)


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


@pytest.mark.parametrize(
    "name",
    [
        "Disc 1",
        "disc 1",
        "Disc1",
        "CD 2",
        "cd2",
        "DISK 004",
        "Disk  3",
    ],
)
def test_is_disc_folder_name_positive(name: str) -> None:
    assert is_disc_folder_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "tracks",
        "bookA",
        "Disc",
        "Disc A",
        "Disc A 1",
        "Volume 1",
    ],
)
def test_is_disc_folder_name_negative(name: str) -> None:
    assert not is_disc_folder_name(name)


def test_discover_book_root_multi_disc(tmp_path, make_tagged_mp3):
    book = tmp_path / "BookName"
    book.mkdir()
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    for disc_name, tracks in (("Disc 1", ("01.mp3", "02.mp3")), ("Disc 2", ("01.mp3",))):
        disc = book / disc_name
        disc.mkdir()
        for name in tracks:
            path = make_tagged_mp3(name=name, **tags)
            path.rename(disc / name)

    assert discover_book_root(book) == book.resolve()


def test_collect_book_audio_multi_disc_paths_and_order(tmp_path, make_tagged_mp3):
    book = tmp_path / "BookName"
    book.mkdir()
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    for disc_name, tracks in (("Disc 2", ("01.mp3",)), ("Disc 1", ("01.mp3", "02.mp3"))):
        disc = book / disc_name
        disc.mkdir()
        for name in tracks:
            path = make_tagged_mp3(name=name, **tags)
            path.rename(disc / name)

    audio = collect_book_audio(book)

    assert [a.dest_relative.as_posix() for a in audio] == [
        "Disc 1/01.mp3",
        "Disc 1/02.mp3",
        "Disc 2/01.mp3",
    ]
    assert collect_track_files(book) == [a.source for a in audio]


def test_discover_book_root_wrapper_with_multi_disc(tmp_path, make_tagged_mp3):
    book = tmp_path / "BookName"
    for disc_name in ("Disc 1", "Disc 2"):
        disc = book / disc_name
        disc.mkdir(parents=True)
        path = make_tagged_mp3(
            name="01.mp3", albumartist="Jane Author", album="Book Title"
        )
        path.rename(disc / path.name)

    wrapper = tmp_path / "wrapper"
    wrapper.mkdir()
    book.rename(wrapper / book.name)

    assert discover_book_root(wrapper) == (wrapper / "BookName").resolve()
    audio = collect_book_audio(wrapper / "BookName")
    assert [a.dest_relative.as_posix() for a in audio] == [
        "Disc 1/01.mp3",
        "Disc 2/01.mp3",
    ]


def test_find_cover_sidecar_case_insensitive(tmp_path, minimal_jpeg):
    (tmp_path / "Cover.JPG").write_bytes(minimal_jpeg)
    assert find_cover_sidecar(tmp_path) == tmp_path / "Cover.JPG"


def test_find_cover_sidecar_prefers_cover_over_folder(tmp_path, minimal_jpeg):
    (tmp_path / "folder.jpg").write_bytes(minimal_jpeg)
    cover = tmp_path / "cover.jpg"
    cover.write_bytes(minimal_jpeg)
    assert find_cover_sidecar(tmp_path) == cover


def test_list_copy_sidecars_includes_text_and_opf(tmp_path):
    (tmp_path / "desc.txt").write_text("description", encoding="utf-8")
    (tmp_path / "reader.txt").write_text("Narrator Name", encoding="utf-8")
    (tmp_path / "book.opf").write_text("<package/>", encoding="utf-8")

    sidecars = list_copy_sidecars(tmp_path)

    assert [path.name for path in sidecars] == ["book.opf", "desc.txt", "reader.txt"]


def test_sidecar_root_for_file_input(tmp_path, make_tagged_mp3):
    source = make_tagged_mp3(name="book.mp3")
    book_dir = tmp_path / "download"
    book_dir.mkdir()
    source.rename(book_dir / source.name)

    assert sidecar_root(book_dir / "book.mp3", book_dir / "book.mp3") == book_dir
