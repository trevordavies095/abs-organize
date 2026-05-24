"""Integration tests for organize (single file and multi-track folder)."""

from __future__ import annotations

import pytest

from abs_organize.metadata import MetadataError, ValidationError
from abs_organize.organize import organize, organize_file


def test_organize_mp3_with_albumartist_and_album(tmp_path, make_tagged_mp3):
    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()

    result = organize_file(source, library)

    dest = library / "Jane Author" / "Book Title" / "book.mp3"
    assert dest.is_file()
    assert result.dest_dir == dest.parent
    assert result.copied_files == ("book.mp3",)
    assert source.is_file()
    assert list(library.iterdir()) == [library / "Jane Author"]


def test_organize_m4b_with_artist_and_title(tmp_path, make_tagged_m4b):
    source = make_tagged_m4b(
        name="audiobook.m4b",
        artist="Steven Levy",
        title="Hackers - Heroes of the Computer Revolution",
        narrator="Mike Chamberlain",
    )
    library = tmp_path / "library"
    library.mkdir()

    organize_file(source, library)

    dest = (
        library
        / "Steven Levy"
        / "Hackers - Heroes of the Computer Revolution {Mike Chamberlain}"
        / "audiobook.m4b"
    )
    assert dest.is_file()


def test_organize_maximal_series_layout(tmp_path, make_tagged_m4b_with_movement):
    source = make_tagged_m4b_with_movement(
        albumartist="Terry Goodkind",
        album="Wizards First Rule",
        grouping="Sword of Truth",
        date="1994",
        movement_name="Sword of Truth",
        movement_index=1,
        narrator="Sam Tsoutsouvas",
    )
    library = tmp_path / "library"
    library.mkdir()

    result = organize_file(source, library)

    dest = (
        library
        / "Terry Goodkind"
        / "Sword of Truth"
        / "Vol 1 - 1994 - Wizards First Rule {Sam Tsoutsouvas}"
        / "book.m4b"
    )
    assert dest.is_file()
    assert result.dest_dir == dest.parent


def test_organize_missing_metadata_exits_with_metadata_error(make_tagged_mp3, tmp_path):
    source = make_tagged_mp3()
    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(MetadataError, match="Missing required metadata"):
        organize_file(source, library)


def test_organize_invalid_library(make_tagged_mp3, tmp_path):
    source = make_tagged_mp3(albumartist="A", album="B")
    with pytest.raises(ValidationError, match="Library path does not exist"):
        organize_file(source, tmp_path / "missing")


def test_cli_missing_metadata_exits_1(make_tagged_mp3, tmp_path, capsys):
    from abs_organize.cli import main

    source = make_tagged_mp3()
    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(library)])

    assert exc.value.code == 1
    assert "Missing required metadata" in capsys.readouterr().err


def test_organize_multi_disc_folder(tmp_path, make_tagged_mp3):
    book = tmp_path / "BookName"
    book.mkdir()
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    for disc_name, tracks in (
        ("Disc 1", ("01.mp3", "02.mp3")),
        ("Disc 2", ("01.mp3", "02.mp3")),
    ):
        disc = book / disc_name
        disc.mkdir()
        for name in tracks:
            path = make_tagged_mp3(name=name, **tags)
            path.rename(disc / name)

    library = tmp_path / "library"
    library.mkdir()

    result, warnings = organize(book, library)

    dest_dir = library / "Jane Author" / "Book Title"
    assert result.dest_dir == dest_dir
    assert result.copied_files == (
        "Disc 1/01.mp3",
        "Disc 1/02.mp3",
        "Disc 2/01.mp3",
        "Disc 2/02.mp3",
    )
    assert warnings == ()
    for rel in result.copied_files:
        assert (dest_dir / rel).is_file()
        assert (book / rel).is_file()


def test_organize_multi_disc_preserves_source_folder_spelling(tmp_path, make_tagged_mp3):
    book = tmp_path / "BookName"
    book.mkdir()
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    for disc_name in ("disc 1", "CD 2"):
        disc = book / disc_name
        disc.mkdir()
        path = make_tagged_mp3(name="01.mp3", **tags)
        path.rename(disc / path.name)

    library = tmp_path / "library"
    library.mkdir()

    result, _ = organize(book, library)

    dest_dir = library / "Jane Author" / "Book Title"
    assert (dest_dir / "disc 1" / "01.mp3").is_file()
    assert (dest_dir / "CD 2" / "01.mp3").is_file()
    assert result.copied_files == ("disc 1/01.mp3", "CD 2/01.mp3")


def test_organize_multi_track_folder(tmp_path, make_tagged_mp3):
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    for i in range(1, 4):
        name = f"{i:02d}.mp3"
        path = make_tagged_mp3(name=name, **tags)
        path.rename(tracks_dir / name)

    library = tmp_path / "library"
    library.mkdir()

    result, warnings = organize(tracks_dir, library)

    dest_dir = library / "Jane Author" / "Book Title"
    assert result.dest_dir == dest_dir
    assert result.copied_files == ("01.mp3", "02.mp3", "03.mp3")
    assert warnings == ()
    for name in ("01.mp3", "02.mp3", "03.mp3"):
        assert (dest_dir / name).is_file()
        assert (tracks_dir / name).is_file()


def test_organize_multi_track_tag_conflict_warns(tmp_path, make_tagged_mp3):
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    for name, album in (
        ("01.mp3", "Book One"),
        ("02.mp3", "Book One"),
        ("03.mp3", "Book Two"),
    ):
        path = make_tagged_mp3(
            name=name, albumartist="Jane Author", album=album
        )
        path.rename(tracks_dir / name)

    library = tmp_path / "library"
    library.mkdir()

    result, warnings = organize(tracks_dir, library)

    assert result.dest_dir == library / "Jane Author" / "Book One"
    assert any("title tag conflict" in w for w in warnings)
    assert (result.dest_dir / "01.mp3").is_file()
    assert (result.dest_dir / "03.mp3").is_file()


def test_organize_no_majority_title_copies_nothing(tmp_path, make_tagged_mp3):
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    for name, album in (("01.mp3", "Alpha"), ("02.mp3", "Beta")):
        path = make_tagged_mp3(
            name=name, albumartist="Jane Author", album=album
        )
        path.rename(tracks_dir / name)

    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(MetadataError, match="No majority for required field 'title'"):
        organize(tracks_dir, library)

    assert not (library / "Jane Author").exists()


def test_organize_dry_run_single_file(tmp_path, make_tagged_mp3):
    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()
    library_mtime_before = library.stat().st_mtime

    result, warnings = organize(source, library, dry_run=True)

    assert warnings == ()
    assert result.dest_dir == library / "Jane Author" / "Book Title"
    assert result.copied_files == ("book.mp3",)
    assert not (library / "Jane Author").exists()
    assert library.stat().st_mtime == library_mtime_before
    assert source.is_file()


def test_cli_dry_run_prints_plan_and_leaves_library_empty(
    tmp_path, make_tagged_mp3, capsys
):
    from abs_organize.cli import main

    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()
    library_mtime_before = library.stat().st_mtime

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(library), "--dry-run"])

    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert f"Library: {library}" in out
    assert "Destination:" in out
    assert "Planned:" in out
    assert "book.mp3 → Jane Author/Book Title/book.mp3" in out
    assert "Copied:" not in out
    assert not (library / "Jane Author").exists()
    assert library.stat().st_mtime == library_mtime_before


def test_cli_dry_run_missing_metadata_exits_1(make_tagged_mp3, tmp_path, capsys):
    from abs_organize.cli import main

    source = make_tagged_mp3()
    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(library), "--dry-run"])

    assert exc.value.code == 1
    assert "Missing required metadata" in capsys.readouterr().err
    assert not list(library.iterdir())


def test_organize_dry_run_multi_track_folder(tmp_path, make_tagged_mp3, capsys):
    from abs_organize.cli import main

    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    for i in range(1, 4):
        name = f"{i:02d}.mp3"
        path = make_tagged_mp3(name=name, **tags)
        path.rename(tracks_dir / name)

    library = tmp_path / "library"
    library.mkdir()

    result, warnings = organize(tracks_dir, library, dry_run=True)

    assert warnings == ()
    assert result.dest_dir == library / "Jane Author" / "Book Title"
    assert result.copied_files == ("01.mp3", "02.mp3", "03.mp3")
    assert not (library / "Jane Author").exists()

    with pytest.raises(SystemExit) as exc:
        main([str(tracks_dir), "--library", str(library), "--dry-run"])

    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "01.mp3 → Jane Author/Book Title/01.mp3" in out
    assert "03.mp3 → Jane Author/Book Title/03.mp3" in out


def test_cli_dry_run_multi_track_tag_conflict_warns(
    tmp_path, make_tagged_mp3, capsys
):
    from abs_organize.cli import main

    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    for name, album in (
        ("01.mp3", "Book One"),
        ("02.mp3", "Book One"),
        ("03.mp3", "Book Two"),
    ):
        path = make_tagged_mp3(
            name=name, albumartist="Jane Author", album=album
        )
        path.rename(tracks_dir / name)

    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main([str(tracks_dir), "--library", str(library), "--dry-run"])

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert any("title tag conflict" in w for w in captured.err.splitlines())
    assert "Planned:" in captured.out
    assert not (library / "Jane Author").exists()


def test_organize_cli_overrides_fix_bad_rip(
    tmp_path, make_tagged_mp3, capsys
):
    from abs_organize.cli import main

    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    for name, album in (("01.mp3", "One"), ("02.mp3", "Two")):
        path = make_tagged_mp3(name=name, albumartist="Bad", album=album)
        path.rename(tracks_dir / name)

    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main(
            [
                str(tracks_dir),
                "--library",
                str(library),
                "--author",
                "Good Author",
                "--title",
                "Good Title",
            ]
        )

    assert exc.value.code == 0
    dest = library / "Good Author" / "Good Title"
    assert (dest / "01.mp3").is_file()
    assert (dest / "02.mp3").is_file()
    err = capsys.readouterr().err
    assert "author tag conflict" not in err
    assert "title tag conflict" not in err


def _make_flat_book_dir(tmp_path, make_tagged_mp3, *, parent: Path, name: str = "BookName"):
    book = parent / name
    book.mkdir()
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    for i in range(1, 3):
        path = make_tagged_mp3(name=f"{i:02d}.mp3", **tags)
        path.rename(book / path.name)
    return book


def test_organize_wrapper_matches_book_dir(tmp_path, make_tagged_mp3):
    book = _make_flat_book_dir(tmp_path, make_tagged_mp3, parent=tmp_path)
    wrapper = tmp_path / "wrapper"
    wrapper.mkdir()
    book_in_wrapper = wrapper / book.name
    book.rename(book_in_wrapper)

    library = tmp_path / "library"
    library.mkdir()

    direct_result, direct_warnings = organize(book_in_wrapper, library)
    wrapper_result, wrapper_warnings = organize(wrapper, library)

    dest = library / "Jane Author" / "Book Title"
    assert direct_result.dest_dir == dest
    assert wrapper_result.dest_dir == dest
    assert direct_result.copied_files == ("01.mp3", "02.mp3")
    assert wrapper_result.copied_files == direct_result.copied_files
    assert direct_warnings == wrapper_warnings == ()
    assert (dest / "01.mp3").is_file()
    assert (dest / "02.mp3").is_file()


def test_organize_wrapper_dry_run_matches_book_dir(tmp_path, make_tagged_mp3):
    book = _make_flat_book_dir(tmp_path, make_tagged_mp3, parent=tmp_path)
    wrapper = tmp_path / "wrapper"
    wrapper.mkdir()
    book_in_wrapper = wrapper / book.name
    book.rename(book_in_wrapper)

    library = tmp_path / "library"
    library.mkdir()

    direct_result, _ = organize(book_in_wrapper, library, dry_run=True)
    wrapper_result, _ = organize(wrapper, library, dry_run=True)

    assert direct_result.dest_dir == wrapper_result.dest_dir
    assert direct_result.copied_files == wrapper_result.copied_files
    assert not (library / "Jane Author").exists()


def test_organize_two_sibling_m4b_fails(tmp_path, make_tagged_m4b):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    a = make_tagged_m4b(name="a.m4b", artist="A1", title="T1")
    b = make_tagged_m4b(name="b.m4b", artist="A2", title="T2")
    a.rename(inbox / "a.m4b")
    b.rename(inbox / "b.m4b")

    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(ValidationError, match="Multiple books detected") as exc:
        organize(inbox, library)

    message = str(exc.value)
    assert str((inbox / "a.m4b").resolve()) in message
    assert str((inbox / "b.m4b").resolve()) in message
    assert not list(library.iterdir())


def test_organize_two_book_subfolders_fails(tmp_path, make_tagged_mp3):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for folder, album in (("bookA", "Alpha"), ("bookB", "Beta")):
        book_dir = inbox / folder
        book_dir.mkdir()
        path = make_tagged_mp3(
            name="01.mp3", albumartist="Jane Author", album=album
        )
        path.rename(book_dir / path.name)

    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(ValidationError, match="Multiple books detected") as exc:
        organize(inbox, library)

    message = str(exc.value)
    assert str((inbox / "bookA").resolve()) in message
    assert str((inbox / "bookB").resolve()) in message
    assert not list(library.iterdir())


def test_cli_multiple_books_exits_1(tmp_path, make_tagged_m4b, capsys):
    from abs_organize.cli import main

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    a = make_tagged_m4b(name="a.m4b", artist="A1", title="T1")
    b = make_tagged_m4b(name="b.m4b", artist="A2", title="T2")
    a.rename(inbox / "a.m4b")
    b.rename(inbox / "b.m4b")

    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main([str(inbox), "--library", str(library)])

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Multiple books detected" in err
    assert str((inbox / "a.m4b").resolve()) in err
    assert str((inbox / "b.m4b").resolve()) in err
    assert not list(library.iterdir())
