"""Integration tests for single-file organize."""

from __future__ import annotations

import pytest

from abs_organize.metadata import MetadataError, ValidationError
from abs_organize.organize import organize_file


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
