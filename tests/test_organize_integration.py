"""Integration tests for organize (single file and multi-track folder)."""

from __future__ import annotations

from pathlib import Path

import pytest

from abs_organize.batch import organize_batch, validate_batch_override_policy
from abs_organize.metadata import MetadataOverrides, ValidationError
from abs_organize.metadata import MetadataError, MetadataOverrides, ValidationError
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


def test_organize_year_with_zero_in_title_folder(tmp_path, make_tagged_m4b):
    source = make_tagged_m4b(
        artist="Andy Weir",
        title="Project Hail Mary",
        date="2021",
        narrator="Ray Porter",
    )
    library = tmp_path / "library"
    library.mkdir()

    organize_file(source, library)

    dest = (
        library
        / "Andy Weir"
        / "2021 - Project Hail Mary {Ray Porter}"
        / "book.m4b"
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


def _make_untagged_book_folder(tmp_path, make_tagged_mp3, folder_name: str) -> Path:
    book = tmp_path / folder_name
    book.mkdir()
    path = make_tagged_mp3(name="01.mp3")
    path.rename(book / "01.mp3")
    return book


def test_organize_untagged_folder_fails_without_allow_guess(
    tmp_path, make_tagged_mp3
):
    source = _make_untagged_book_folder(
        tmp_path, make_tagged_mp3, "Jane Author - Great Book"
    )
    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(MetadataError, match="Missing required metadata"):
        organize(source, library)

    assert not list(library.iterdir())


def test_organize_untagged_folder_succeeds_with_allow_guess(
    tmp_path, make_tagged_mp3
):
    source = _make_untagged_book_folder(
        tmp_path, make_tagged_mp3, "Jane Author - Great Book"
    )
    library = tmp_path / "library"
    library.mkdir()

    result, warnings = organize(source, library, allow_guess=True)

    dest = library / "Jane Author" / "Great Book" / "01.mp3"
    assert dest.is_file()
    assert result.dest_dir == dest.parent
    assert any("Guessed author" in warning for warning in warnings)
    assert any("Guessed title" in warning for warning in warnings)


def test_organize_allow_guess_dry_run_plans_without_writing(
    tmp_path, make_tagged_mp3
):
    source = _make_untagged_book_folder(
        tmp_path, make_tagged_mp3, "Jane Author - Great Book"
    )
    library = tmp_path / "library"
    library.mkdir()

    result, warnings = organize(source, library, dry_run=True, allow_guess=True)

    assert result.dest_dir == library / "Jane Author" / "Great Book"
    assert result.copied_files == ("01.mp3",)
    assert any("Guessed author" in warning for warning in warnings)
    assert not list(library.iterdir())


def test_cli_allow_guess_organizes_untagged_folder(
    tmp_path, make_tagged_mp3, capsys
):
    from abs_organize.cli import main

    source = _make_untagged_book_folder(
        tmp_path, make_tagged_mp3, "Jane Author - Great Book"
    )
    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(library), "--allow-guess"])

    assert exc.value.code == 0
    err = capsys.readouterr().err
    assert "Guessed author" in err
    assert (library / "Jane Author" / "Great Book" / "01.mp3").is_file()


def test_organize_allow_guess_title_override_beats_folder(
    tmp_path, make_tagged_mp3
):
    source = _make_untagged_book_folder(
        tmp_path, make_tagged_mp3, "Jane Author - Great Book"
    )
    library = tmp_path / "library"
    library.mkdir()

    result, warnings = organize(
        source,
        library,
        allow_guess=True,
        overrides=MetadataOverrides(title="Override Title"),
    )

    dest = library / "Jane Author" / "Override Title" / "01.mp3"
    assert dest.is_file()
    assert result.dest_dir == dest.parent
    assert any("Guessed author" in warning for warning in warnings)
    assert not any("Guessed title" in warning for warning in warnings)


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

    library_direct = tmp_path / "library_direct"
    library_wrapper = tmp_path / "library_wrapper"
    library_direct.mkdir()
    library_wrapper.mkdir()

    direct_result, direct_warnings = organize(book_in_wrapper, library_direct)
    wrapper_result, wrapper_warnings = organize(wrapper, library_wrapper)

    dest = library_direct / "Jane Author" / "Book Title"
    dest_wrapper = library_wrapper / "Jane Author" / "Book Title"
    assert direct_result.dest_dir == dest
    assert wrapper_result.dest_dir == dest_wrapper
    assert direct_result.copied_files == ("01.mp3", "02.mp3")
    assert wrapper_result.copied_files == direct_result.copied_files
    assert direct_warnings == wrapper_warnings == ()
    for lib_dest in (dest, dest_wrapper):
        assert (lib_dest / "01.mp3").is_file()
        assert (lib_dest / "02.mp3").is_file()


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
    assert "--batch" in err
    assert not list(library.iterdir())


def _two_book_subfolder_inbox(tmp_path, make_tagged_mp3) -> tuple[Path, Path]:
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
    return inbox, library


def test_organize_batch_dry_run_two_subfolders(tmp_path, make_tagged_mp3):
    inbox, library = _two_book_subfolder_inbox(tmp_path, make_tagged_mp3)

    batch = organize_batch(inbox, library, dry_run=True)

    assert batch.ok_count == 2
    assert batch.failed_count == 0
    assert len(batch.outcomes) == 2
    destinations = {outcome.result.dest_dir.name for outcome in batch.outcomes}
    assert destinations == {"Alpha", "Beta"}
    assert not list(library.iterdir())


def test_organize_batch_apply_two_subfolders(tmp_path, make_tagged_mp3):
    inbox, library = _two_book_subfolder_inbox(tmp_path, make_tagged_mp3)

    batch = organize_batch(inbox, library)

    assert batch.ok_count == 2
    assert batch.failed_count == 0
    author_dir = library / "Jane Author"
    assert (author_dir / "Alpha" / "01.mp3").is_file()
    assert (author_dir / "Beta" / "01.mp3").is_file()


def test_organize_batch_apply_stops_on_first_failure(tmp_path, make_tagged_mp3):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for folder, album in (("bookA", "Alpha"), ("bookB", "Beta"), ("bookC", "Gamma")):
        book_dir = inbox / folder
        book_dir.mkdir()
        path = make_tagged_mp3(
            name="01.mp3", albumartist="Jane Author", album=album
        )
        path.rename(book_dir / path.name)

    library = tmp_path / "library"
    library.mkdir()
    organize_file(inbox / "bookB" / "01.mp3", library)

    batch = organize_batch(inbox, library)

    assert batch.ok_count == 1
    assert batch.failed_count == 1
    assert len(batch.outcomes) == 2
    assert batch.outcomes[0].ok
    assert not batch.outcomes[1].ok
    assert "already exists" in (batch.outcomes[1].error or "")
    assert not (library / "Jane Author" / "Gamma").exists()


def test_organize_batch_single_root_matches_wrapper_organize(
    tmp_path, make_tagged_mp3
):
    book = tmp_path / "BookName"
    book.mkdir()
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    for i in range(1, 3):
        path = make_tagged_mp3(name=f"{i:02d}.mp3", **tags)
        path.rename(book / path.name)

    wrapper = tmp_path / "wrapper"
    wrapper.mkdir()
    book.rename(wrapper / book.name)

    library = tmp_path / "library"
    library.mkdir()

    single, _ = organize(wrapper, library, dry_run=True)
    batch = organize_batch(wrapper, library, dry_run=True)

    assert batch.ok_count == 1
    assert batch.outcomes[0].result is not None
    assert batch.outcomes[0].result.source == wrapper.resolve()
    assert batch.outcomes[0].result.dest_dir == single.dest_dir
    assert batch.outcomes[0].result.copied_files == single.copied_files


def test_cli_batch_dry_run_two_subfolders(tmp_path, make_tagged_mp3, capsys):
    from abs_organize.cli import main

    inbox, library = _two_book_subfolder_inbox(tmp_path, make_tagged_mp3)

    with pytest.raises(SystemExit) as exc:
        main([str(inbox), "--library", str(library), "--batch", "--dry-run"])

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "Alpha" in captured.out
    assert "Beta" in captured.out
    assert "Batch complete: 2 ok, 0 failed" in captured.err


def test_cli_batch_apply_two_subfolders(tmp_path, make_tagged_mp3, capsys):
    from abs_organize.cli import main

    inbox, library = _two_book_subfolder_inbox(tmp_path, make_tagged_mp3)

    with pytest.raises(SystemExit) as exc:
        main([str(inbox), "--library", str(library), "--batch"])

    assert exc.value.code == 0
    assert (library / "Jane Author" / "Alpha" / "01.mp3").is_file()
    assert (library / "Jane Author" / "Beta" / "01.mp3").is_file()
    err = capsys.readouterr().err
    assert "Batch complete: 2 ok, 0 failed" in err


def test_organize_batch_infers_volume_from_numbered_folders(
    tmp_path, make_tagged_mp3
):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for folder, album in (("01 - Alpha", "Alpha"), ("02 - Beta", "Beta")):
        book_dir = inbox / folder
        book_dir.mkdir()
        path = make_tagged_mp3(
            name="01.mp3", albumartist="Jane Author", album=album
        )
        path.rename(book_dir / path.name)
    library = tmp_path / "library"
    library.mkdir()

    batch = organize_batch(inbox, library, dry_run=True)

    assert batch.ok_count == 2
    names = {outcome.result.dest_dir.name for outcome in batch.outcomes}
    assert names == {"Vol 1 - Alpha", "Vol 2 - Beta"}


def test_organize_batch_folder_sequence_not_from_wrapper_name(
    tmp_path, make_tagged_mp3
):
    wrapper = tmp_path / "99 - Box Set"
    wrapper.mkdir()
    book_dir = wrapper / "01 - Alpha"
    book_dir.mkdir()
    path = make_tagged_mp3(
        name="01.mp3", albumartist="Jane Author", album="Alpha"
    )
    path.rename(book_dir / path.name)
    library = tmp_path / "library"
    library.mkdir()

    batch = organize_batch(wrapper, library, dry_run=True)

    assert batch.outcomes[0].result is not None
    assert batch.outcomes[0].result.dest_dir.name == "Vol 1 - Alpha"


def test_organize_batch_folder_sequence_does_not_override_tags(
    tmp_path, make_tagged_m4b_with_movement
):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    book_dir = inbox / "01 - Alpha"
    book_dir.mkdir()
    path = make_tagged_m4b_with_movement(
        name="book.m4b",
        albumartist="Jane Author",
        album="Alpha",
        movement_name="Series",
        movement_index=5,
    )
    path.rename(book_dir / path.name)
    library = tmp_path / "library"
    library.mkdir()

    batch = organize_batch(inbox, library, dry_run=True)

    assert batch.outcomes[0].result is not None
    assert batch.outcomes[0].result.dest_dir.name == "Vol 5 - Alpha"


def test_organize_batch_multi_root_series_gap_fill(tmp_path, make_tagged_mp3):
    inbox, library = _two_book_subfolder_inbox(tmp_path, make_tagged_mp3)

    batch = organize_batch(
        inbox,
        library,
        overrides=MetadataOverrides(series="Shared Series"),
        dry_run=True,
    )

    assert batch.ok_count == 2
    for outcome in batch.outcomes:
        assert outcome.result is not None
        assert outcome.result.dest_dir.parent.name == "Shared Series"


def test_organize_batch_multi_root_series_gap_fill_skips_tagged_series(
    tmp_path, make_tagged_mp3
):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for folder, album, series in (
        ("bookA", "Alpha", "Tagged Series"),
        ("bookB", "Beta", None),
    ):
        book_dir = inbox / folder
        book_dir.mkdir()
        tags = {"albumartist": "Jane Author", "album": album}
        if series:
            tags["grouping"] = series
        path = make_tagged_mp3(name="01.mp3", **tags)
        path.rename(book_dir / path.name)
    library = tmp_path / "library"
    library.mkdir()

    batch = organize_batch(
        inbox,
        library,
        overrides=MetadataOverrides(series="Shared Series"),
        dry_run=True,
    )

    series_dirs = {outcome.result.dest_dir.parent.name for outcome in batch.outcomes}
    assert series_dirs == {"Tagged Series", "Shared Series"}


def test_organize_batch_single_root_series_cli_override(tmp_path, make_tagged_mp3):
    book = tmp_path / "single"
    book.mkdir()
    path = make_tagged_mp3(
        name="01.mp3", albumartist="Jane Author", album="Book Title"
    )
    path.rename(book / path.name)
    library = tmp_path / "library"
    library.mkdir()

    batch = organize_batch(
        book,
        library,
        overrides=MetadataOverrides(series="CLI Series"),
        dry_run=True,
    )

    assert batch.outcomes[0].result is not None
    assert batch.outcomes[0].result.dest_dir.parent.name == "CLI Series"


def test_organize_batch_forbidden_author_multi_root(tmp_path, make_tagged_mp3):
    inbox, _library = _two_book_subfolder_inbox(tmp_path, make_tagged_mp3)
    roots = [inbox / "bookA", inbox / "bookB"]

    with pytest.raises(ValidationError, match="--author"):
        validate_batch_override_policy(
            roots, MetadataOverrides(author="One Author")
        )


def test_organize_batch_apply_continue_on_error(tmp_path, make_tagged_mp3):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for folder, album in (("bookA", "Alpha"), ("bookB", "Beta"), ("bookC", "Gamma")):
        book_dir = inbox / folder
        book_dir.mkdir()
        path = make_tagged_mp3(
            name="01.mp3", albumartist="Jane Author", album=album
        )
        path.rename(book_dir / path.name)

    library = tmp_path / "library"
    library.mkdir()
    organize_file(inbox / "bookB" / "01.mp3", library)

    batch = organize_batch(
        inbox, library, continue_on_error=True
    )

    assert batch.ok_count == 2
    assert batch.failed_count == 1
    assert len(batch.outcomes) == 3
    assert (library / "Jane Author" / "Gamma").exists()


def test_organize_collision_aborts_without_replace(tmp_path, make_tagged_mp3):
    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()

    organize_file(source, library)
    dest_file = library / "Jane Author" / "Book Title" / "book.mp3"
    assert dest_file.is_file()
    mtime_before = dest_file.stat().st_mtime

    with pytest.raises(ValidationError, match="already exists"):
        organize_file(source, library)

    assert dest_file.is_file()
    assert dest_file.stat().st_mtime == mtime_before
    assert source.is_file()


def test_cli_collision_exits_1(tmp_path, make_tagged_mp3, capsys):
    from abs_organize.cli import main

    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(library)])

    assert exc.value.code == 0

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(library)])

    assert exc.value.code == 1
    err = capsys.readouterr().err
    dest = library / "Jane Author" / "Book Title"
    assert str(dest.resolve()) in err
    assert "already exists" in err


def test_organize_replace_removes_old_tree(tmp_path, make_tagged_mp3):
    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()
    dest_dir = library / "Jane Author" / "Book Title"
    dest_dir.mkdir(parents=True)
    stale = dest_dir / "old.mp3"
    stale.write_bytes(b"stale")

    result = organize_file(source, library, replace=True)

    assert result.copied_files == ("book.mp3",)
    assert not stale.exists()
    assert (dest_dir / "book.mp3").is_file()


def test_organize_replace_multi_disc(tmp_path, make_tagged_mp3):
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
    dest_dir = library / "Jane Author" / "Book Title"
    dest_dir.mkdir(parents=True)
    wrong_disc = dest_dir / "Wrong Disc"
    wrong_disc.mkdir()
    (wrong_disc / "stale.mp3").write_bytes(b"stale")

    result, _ = organize(book, library, replace=True)

    assert not wrong_disc.exists()
    assert result.copied_files == (
        "Disc 1/01.mp3",
        "Disc 1/02.mp3",
        "Disc 2/01.mp3",
        "Disc 2/02.mp3",
    )
    for rel in result.copied_files:
        assert (dest_dir / rel).is_file()


def test_organize_dry_run_collision_warns_no_delete(tmp_path, make_tagged_mp3):
    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()
    dest_dir = library / "Jane Author" / "Book Title"
    dest_dir.mkdir(parents=True)

    result, warnings = organize(source, library, dry_run=True)

    assert result.copied_files == ("book.mp3",)
    assert not (dest_dir / "book.mp3").exists()
    assert any("already exists" in w for w in warnings)
    assert any("--replace" in w for w in warnings)


def test_cli_dry_run_collision(tmp_path, make_tagged_mp3, capsys):
    from abs_organize.cli import main

    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()
    dest_dir = library / "Jane Author" / "Book Title"
    dest_dir.mkdir(parents=True)

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(library), "--dry-run"])

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "already exists" in captured.err
    assert not (dest_dir / "book.mp3").exists()


def test_replace_refuses_dest_outside_library(tmp_path):
    from abs_organize.organize import _assert_replace_safe

    library = tmp_path / "library"
    library.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "book"
    marker.mkdir()

    with pytest.raises(ValidationError, match="outside library root"):
        _assert_replace_safe(marker, library)


def test_replace_refuses_library_root(tmp_path):
    from abs_organize.organize import _assert_replace_safe

    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(ValidationError, match="library root"):
        _assert_replace_safe(library, library)


def test_organize_move_removes_source_single_file(tmp_path, make_tagged_mp3):
    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()

    result = organize_file(source, library, move=True)

    dest = library / "Jane Author" / "Book Title" / "book.mp3"
    assert dest.is_file()
    assert result.dest_dir == dest.parent
    assert result.copied_files == ("book.mp3",)
    assert not source.is_file()


def test_organize_move_multi_disc(tmp_path, make_tagged_mp3):
    book = tmp_path / "BookName"
    book.mkdir()
    tags = {"albumartist": "Jane Author", "album": "Book Title"}
    track_paths: list[Path] = []
    for disc_name, tracks in (
        ("Disc 1", ("01.mp3", "02.mp3")),
        ("Disc 2", ("01.mp3", "02.mp3")),
    ):
        disc = book / disc_name
        disc.mkdir()
        for name in tracks:
            path = make_tagged_mp3(name=name, **tags)
            path.rename(disc / name)
            track_paths.append(disc / name)

    library = tmp_path / "library"
    library.mkdir()

    result, _ = organize(book, library, move=True)

    dest_dir = library / "Jane Author" / "Book Title"
    assert result.copied_files == (
        "Disc 1/01.mp3",
        "Disc 1/02.mp3",
        "Disc 2/01.mp3",
        "Disc 2/02.mp3",
    )
    for rel in result.copied_files:
        assert (dest_dir / rel).is_file()
    for path in track_paths:
        assert not path.is_file()


def test_organize_move_collision_aborts_without_replace(tmp_path, make_tagged_mp3):
    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()

    organize_file(source, library)
    dest_file = library / "Jane Author" / "Book Title" / "book.mp3"
    assert dest_file.is_file()

    with pytest.raises(ValidationError, match="already exists"):
        organize_file(source, library, move=True)

    assert source.is_file()
    assert dest_file.is_file()


def test_organize_move_with_replace(tmp_path, make_tagged_mp3):
    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()
    dest_dir = library / "Jane Author" / "Book Title"
    dest_dir.mkdir(parents=True)
    stale = dest_dir / "old.mp3"
    stale.write_bytes(b"stale")

    result = organize_file(source, library, move=True, replace=True)

    assert result.copied_files == ("book.mp3",)
    assert not stale.exists()
    assert (dest_dir / "book.mp3").is_file()
    assert not source.is_file()


def test_organize_move_sidecar_and_cover(tmp_path, make_tagged_mp3, minimal_jpeg):
    book = tmp_path / "download"
    book.mkdir()
    track = make_tagged_mp3(albumartist="Jane Author", album="Book Title")
    track_path = book / track.name
    track.rename(track_path)
    cover_path = book / "cover.jpg"
    cover_path.write_bytes(minimal_jpeg)
    desc_path = book / "desc.txt"
    desc_path.write_text("A great book.", encoding="utf-8")

    library = tmp_path / "library"
    library.mkdir()

    result = organize_file(book, library, move=True)

    assert not track_path.is_file()
    assert not cover_path.is_file()
    assert not desc_path.is_file()
    assert (result.dest_dir / "Cover.jpg").is_file()
    assert (result.dest_dir / "desc.txt").read_text(encoding="utf-8") == "A great book."
    assert "Cover.jpg" in result.copied_files
    assert "desc.txt" in result.copied_files


def test_cli_move_success(tmp_path, make_tagged_mp3, capsys):
    from abs_organize.cli import main

    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(library), "--move"])

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "Moved:" in captured.out
    assert not source.is_file()
    assert (
        library / "Jane Author" / "Book Title" / "book.mp3"
    ).is_file()


def test_organize_sidecar_cover_copied_as_cover_jpg(
    tmp_path, make_tagged_mp3, minimal_jpeg
):
    book = tmp_path / "download"
    book.mkdir()
    track = make_tagged_mp3(albumartist="Jane Author", album="Book Title")
    track.rename(book / track.name)
    (book / "cover.jpg").write_bytes(minimal_jpeg)

    library = tmp_path / "library"
    library.mkdir()

    result = organize_file(book, library)

    assert (result.dest_dir / "Cover.jpg").is_file()
    assert "Cover.jpg" in result.copied_files


def test_organize_embedded_cover_extracted(tmp_path, make_mp3_with_cover):
    source = make_mp3_with_cover(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()

    result = organize_file(source, library)

    assert (result.dest_dir / "Cover.jpg").is_file()
    assert "Cover.jpg" in result.copied_files


def test_organize_copies_text_and_opf_sidecars(tmp_path, make_tagged_mp3, write_opf):
    book = tmp_path / "download"
    book.mkdir()
    track = make_tagged_mp3(albumartist="Jane Author", album="Book Title")
    track.rename(book / track.name)
    (book / "desc.txt").write_text("A great book.", encoding="utf-8")
    (book / "reader.txt").write_text("Sam Tsoutsouvas", encoding="utf-8")
    write_opf(book / "metadata.opf", series="Ignored Series")

    library = tmp_path / "library"
    library.mkdir()

    result = organize_file(book, library)

    assert (result.dest_dir / "desc.txt").read_text(encoding="utf-8") == "A great book."
    assert (result.dest_dir / "reader.txt").read_text(encoding="utf-8") == "Sam Tsoutsouvas"
    assert (result.dest_dir / "metadata.opf").is_file()
    assert "desc.txt" in result.copied_files
    assert "reader.txt" in result.copied_files
    assert "metadata.opf" in result.copied_files


def test_organize_opf_series_gap_fill_creates_series_folder(
    tmp_path, make_tagged_mp3, write_opf
):
    book = tmp_path / "download"
    book.mkdir()
    track = make_tagged_mp3(albumartist="Terry Goodkind", album="Wizards First Rule")
    track.rename(book / track.name)
    write_opf(book / "metadata.opf", series="Sword of Truth", sequence="1")

    library = tmp_path / "library"
    library.mkdir()

    result = organize_file(book, library)

    dest = (
        library
        / "Terry Goodkind"
        / "Sword of Truth"
        / "Vol 1 - Wizards First Rule"
        / track.name
    )
    assert dest.is_file()
    assert result.dest_dir == dest.parent


def test_organize_reader_txt_fills_narrator_in_title_folder(tmp_path, make_tagged_mp3):
    book = tmp_path / "download"
    book.mkdir()
    track = make_tagged_mp3(albumartist="Jane Author", album="Book Title")
    track.rename(book / track.name)
    (book / "reader.txt").write_text("Sam Tsoutsouvas", encoding="utf-8")

    library = tmp_path / "library"
    library.mkdir()

    result = organize_file(book, library)

    assert result.dest_dir.name == "Book Title {Sam Tsoutsouvas}"
    assert (result.dest_dir / "reader.txt").is_file()


def test_organize_strips_narrator_prefix_in_title_folder(tmp_path, make_tagged_mp3):
    book = tmp_path / "download"
    book.mkdir()
    track = make_tagged_mp3(
        albumartist="Author",
        album="Beyond Reach",
        date="2007",
        composer="Narrated by Joyce Bean",
    )
    track.rename(book / track.name)

    library = tmp_path / "library"
    library.mkdir()

    result = organize_file(book, library)

    assert result.dest_dir.name == "2007 - Beyond Reach {Joyce Bean}"


def test_organize_splits_album_narrator_suffix_in_title_folder(
    tmp_path, make_tagged_mp3
):
    book = tmp_path / "download"
    book.mkdir()
    track = make_tagged_mp3(
        albumartist="George R. R. Martin",
        album="A Game of Thrones (read by Roy Dotrice)",
        date="1996",
    )
    track.rename(book / track.name)

    library = tmp_path / "library"
    library.mkdir()

    result = organize_file(book, library)

    assert result.dest_dir.name == "1996 - A Game of Thrones {Roy Dotrice}"


def test_organize_cli_title_override_strips_narrator_suffix(
    tmp_path, make_tagged_mp3
):
    from abs_organize.cli import main

    book = tmp_path / "download"
    book.mkdir()
    track = make_tagged_mp3(
        albumartist="George R. R. Martin",
        album="Generic Album Title",
        date="1996",
    )
    track.rename(book / track.name)

    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main(
            [
                str(book),
                "--library",
                str(library),
                "--title",
                "A Game of Thrones (read by Roy Dotrice)",
            ]
        )
    assert exc.value.code == 0

    dest = library / "George R. R. Martin" / "1996 - A Game of Thrones {Roy Dotrice}"
    assert dest.is_dir()
