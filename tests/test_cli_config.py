"""CLI integration tests for config-driven library resolution."""

from __future__ import annotations

import textwrap

import pytest

from abs_organize.cli import main


def _write_user_config(home: Path, body: str) -> None:
    config_dir = home / ".config" / "abs-organize"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.toml"
    config_path.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
    return config_path


def test_cli_organize_without_library_flag(monkeypatch, tmp_path, make_tagged_mp3, capsys):
    home = tmp_path / "home"
    home.mkdir()
    library = tmp_path / "library"
    library.mkdir()
    monkeypatch.setenv("HOME", str(home))

    _write_user_config(
        home,
        f"""
        [libraries.default]
        path = "{library}"
        """,
    )

    source = make_tagged_mp3(albumartist="Jane Author", album="Book Title")

    with pytest.raises(SystemExit) as exc:
        main([str(source)])

    assert exc.value.code == 0
    dest = library / "Jane Author" / "Book Title" / "book.mp3"
    assert dest.is_file()
    assert "Destination:" in capsys.readouterr().out


def test_cli_organize_with_profile(monkeypatch, tmp_path, make_tagged_mp3):
    home = tmp_path / "home"
    home.mkdir()
    default_lib = tmp_path / "default-lib"
    fiction_lib = tmp_path / "fiction-lib"
    default_lib.mkdir()
    fiction_lib.mkdir()
    monkeypatch.setenv("HOME", str(home))

    _write_user_config(
        home,
        f"""
        [libraries.default]
        path = "{default_lib}"

        [libraries.fiction]
        path = "{fiction_lib}"
        """,
    )

    source = make_tagged_mp3(albumartist="A", album="B")

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--profile", "fiction"])

    assert exc.value.code == 0
    assert (fiction_lib / "A" / "B" / "book.mp3").is_file()
    assert not list(default_lib.iterdir())


def test_cli_library_flag_overrides_config(monkeypatch, tmp_path, make_tagged_mp3):
    home = tmp_path / "home"
    home.mkdir()
    config_lib = tmp_path / "config-lib"
    override_lib = tmp_path / "override-lib"
    config_lib.mkdir()
    override_lib.mkdir()
    monkeypatch.setenv("HOME", str(home))

    _write_user_config(
        home,
        f"""
        [libraries.default]
        path = "{config_lib}"
        """,
    )

    source = make_tagged_mp3(albumartist="A", album="B")

    with pytest.raises(SystemExit) as exc:
        main([str(source), "--library", str(override_lib)])

    assert exc.value.code == 0
    assert (override_lib / "A" / "B" / "book.mp3").is_file()
    assert not list(config_lib.iterdir())


def test_cli_include_subtitle_in_folder(
    monkeypatch, tmp_path, make_tagged_mp3, capsys
):
    home = tmp_path / "home"
    home.mkdir()
    library = tmp_path / "library"
    library.mkdir()
    monkeypatch.setenv("HOME", str(home))

    _write_user_config(
        home,
        f"""
        include_subtitle_in_folder = true

        [libraries.default]
        path = "{library}"
        """,
    )

    source = make_tagged_mp3(
        albumartist="Terry Goodkind",
        album="Wizards First Rule",
        grouping="Sword of Truth",
        date="1994",
        composer="Sam Tsoutsouvas",
        subtitle="Book One",
    )

    with pytest.raises(SystemExit) as exc:
        main([str(source)])

    assert exc.value.code == 0
    dest = (
        library
        / "Terry Goodkind"
        / "Sword of Truth"
        / "1994 - Wizards First Rule - Book One {Sam Tsoutsouvas}"
        / "book.mp3"
    )
    assert dest.is_file()


def test_cli_missing_config_exits_1(monkeypatch, tmp_path, make_tagged_mp3, capsys):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    source = make_tagged_mp3(albumartist="A", album="B")

    with pytest.raises(SystemExit) as exc:
        main([str(source)])

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Config file not found" in err
    assert ".config/abs-organize/config.toml" in err
