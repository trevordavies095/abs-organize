"""CLI tests for --batch, --continue-on-error, and batch JSON output."""

from __future__ import annotations

import json

import pytest


def test_cli_batch_forbidden_author_exits_1_no_writes(
    tmp_path, make_tagged_mp3, capsys
):
    from abs_organize.cli import main

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for folder in ("bookA", "bookB"):
        book_dir = inbox / folder
        book_dir.mkdir()
        path = make_tagged_mp3(
            name="01.mp3", albumartist="Jane Author", album=folder
        )
        path.rename(book_dir / path.name)
    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main(
            [
                str(inbox),
                "--library",
                str(library),
                "--batch",
                "--author",
                "Stamped Author",
            ]
        )

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "--author" in captured.err
    assert not list(library.iterdir())
    assert captured.out.strip() == ""


def test_cli_batch_json_single_m4b(tmp_path, make_tagged_m4b, capsys):
    from abs_organize.cli import main

    source = make_tagged_m4b(
        albumartist="Jane Author",
        album="Book Title",
    )
    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main(
            [
                str(source),
                "--library",
                str(library),
                "--batch",
                "--json",
            ]
        )

    assert exc.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"books", "summary"}
    assert payload["summary"] == {"ok": 1, "failed": 0}
    assert len(payload["books"]) == 1
    book = payload["books"][0]
    assert book["ok"] is True
    assert book["files"] == ["book.m4b"]
    assert "destination" in book


def test_cli_json_without_batch_flat_shape(tmp_path, make_tagged_mp3, capsys):
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
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"destination", "files", "warnings"}


def test_cli_batch_continue_on_error_summary(tmp_path, make_tagged_mp3, capsys):
    from abs_organize.cli import main
    from abs_organize.organize import organize_file

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

    with pytest.raises(SystemExit) as exc:
        main(
            [
                str(inbox),
                "--library",
                str(library),
                "--batch",
                "--continue-on-error",
                "--json",
            ]
        )

    assert exc.value.code == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["summary"] == {"ok": 2, "failed": 1}
    assert len(payload["books"]) == 3
    assert (library / "Jane Author" / "Gamma").exists()


def test_cli_batch_dry_run_json_lists_all_roots_on_failure(
    tmp_path, make_tagged_mp3, capsys
):
    from abs_organize.cli import main

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    good = inbox / "good"
    good.mkdir()
    path = make_tagged_mp3(
        name="01.mp3", albumartist="Jane Author", album="Good"
    )
    path.rename(good / path.name)
    bad = inbox / "bad"
    bad.mkdir()
    untagged = make_tagged_mp3(name="01.mp3")
    untagged.rename(bad / "01.mp3")
    # Strip tags so metadata resolution fails during organize.
    from mutagen.easyid3 import EasyID3

    easy = EasyID3(bad / "01.mp3")
    easy.delete()
    easy.save()

    library = tmp_path / "library"
    library.mkdir()

    with pytest.raises(SystemExit) as exc:
        main(
            [
                str(inbox),
                "--library",
                str(library),
                "--batch",
                "--dry-run",
                "--json",
            ]
        )

    assert exc.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["books"]) == 2
    assert payload["summary"]["failed"] >= 1
