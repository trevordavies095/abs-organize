"""CLI tests for --json success output and exit codes."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest


def test_cli_json_success(tmp_path, make_tagged_mp3, capsys):
    from abs_organize.cli import main

    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(library), "--json"])

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert set(payload) == {"destination", "files", "warnings"}
    assert payload["files"] == ["book.mp3"]
    assert payload["warnings"] == []
    dest = library / "Jane Author" / "Book Title"
    assert payload["destination"] == f"{dest.resolve()}/"
    assert (dest / "book.mp3").is_file()


def test_cli_json_includes_warnings(tmp_path, make_tagged_mp3, capsys):
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
        main([str(tracks_dir), "--library", str(library), "--json"])

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["warnings"]
    assert any("title tag conflict" in w for w in payload["warnings"])
    assert "Library:" not in captured.out


def test_cli_json_failure_no_stdout_json(make_tagged_mp3, tmp_path, capsys):
    from abs_organize.cli import main

    source = make_tagged_mp3()
    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(library), "--json"])

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Missing required metadata" in captured.err
    assert captured.out.strip() == ""


def test_cli_json_collision_exits_1(tmp_path, make_tagged_mp3, capsys):
    from abs_organize.cli import main

    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(library), "--json"])
    assert exc.value.code == 0
    capsys.readouterr()

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(library), "--json"])

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "already exists" in captured.err
    assert captured.out.strip() == ""


def test_cli_io_failure_exits_2(tmp_path, make_tagged_mp3, capsys):
    from abs_organize.cli import main

    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()

    with patch("abs_organize.organize.shutil.copy2", side_effect=OSError("disk full")):
        with pytest.raises(SystemExit) as exc:
            main([str(source), "--library", str(library)])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "disk full" in captured.err or "Failed to copy" in captured.err
    assert captured.out.strip() == ""


def test_cli_move_io_failure_exits_2(tmp_path, make_tagged_mp3, capsys):
    from abs_organize.cli import main

    source = make_tagged_mp3(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()

    with patch("abs_organize.organize.shutil.move", side_effect=OSError("disk full")):
        with pytest.raises(SystemExit) as exc:
            main([str(source), "--library", str(library), "--move"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "disk full" in captured.err or "Failed to move" in captured.err
    assert captured.out.strip() == ""
