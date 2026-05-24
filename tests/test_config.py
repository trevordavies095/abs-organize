"""Unit tests for config loading and library path resolution."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from abs_organize.config import (
    ENV_LIBRARY,
    AppConfig,
    ConfigError,
    load_config,
    resolve_library_path,
)


def _write_config(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "config.toml"

    def _factory(body: str) -> Path:
        _write_config(path, body)
        return path

    return _factory


def test_load_config_minimal(config_file):
    path = config_file(
        """
        [libraries.default]
        path = "/tmp/audiobooks"
        """
    )

    config = load_config(path)

    assert config == AppConfig(
        libraries={"default": Path("/tmp/audiobooks")},
        include_subtitle_in_folder=False,
    )


def test_load_config_with_profiles_and_subtitle_flag(config_file):
    path = config_file(
        """
        include_subtitle_in_folder = true

        [libraries.default]
        path = "~/Audiobooks"

        [libraries.fiction]
        path = "/Volumes/Books/Fiction"
        """
    )

    config = load_config(path)

    assert config.include_subtitle_in_folder is True
    assert config.libraries["default"] == Path("~/Audiobooks").expanduser()
    assert config.libraries["fiction"] == Path("/Volumes/Books/Fiction")


def test_load_config_missing_file(tmp_path):
    path = tmp_path / "missing.toml"

    with pytest.raises(ConfigError, match="Config file not found"):
        load_config(path)


def test_load_config_invalid_toml(config_file):
    path = config_file("not valid toml [[[")

    with pytest.raises(ConfigError, match="Invalid config"):
        load_config(path)


def test_load_config_missing_libraries_table(config_file):
    path = config_file("include_subtitle_in_folder = false\n")

    with pytest.raises(ConfigError, match="\\[libraries\\] table is required"):
        load_config(path)


def test_load_config_missing_default_profile(config_file):
    path = config_file(
        """
        [libraries.fiction]
        path = "/tmp/fiction"
        """
    )

    with pytest.raises(ConfigError, match="\\[libraries\\.default\\] is required"):
        load_config(path)


def test_load_config_profile_without_path(config_file):
    path = config_file(
        """
        [libraries.default]
        path = "/tmp/default"

        [libraries.fiction]
        """
    )

    with pytest.raises(ConfigError, match="\\[libraries\\.fiction\\].*path"):
        load_config(path)


def test_resolve_library_path_flag_wins(config_file, tmp_path):
    path = config_file(
        """
        [libraries.default]
        path = "/from/config"
        """
    )
    override = tmp_path / "flag-library"
    env = {ENV_LIBRARY: str(tmp_path / "env-library")}

    resolved = resolve_library_path(
        library_flag=override,
        profile=None,
        config_path=path,
        environ=env,
    )

    assert resolved == override


def test_resolve_library_path_env_overrides_default(config_file, tmp_path):
    path = config_file(
        """
        [libraries.default]
        path = "/from/config"
        """
    )
    env_library = tmp_path / "env-library"

    resolved = resolve_library_path(
        library_flag=None,
        profile=None,
        config_path=path,
        environ={ENV_LIBRARY: str(env_library)},
    )

    assert resolved == env_library


def test_resolve_library_path_profile_ignores_env(config_file, tmp_path):
    path = config_file(
        """
        [libraries.default]
        path = "/default"

        [libraries.fiction]
        path = "/fiction"
        """
    )

    resolved = resolve_library_path(
        library_flag=None,
        profile="fiction",
        config_path=path,
        environ={ENV_LIBRARY: str(tmp_path / "env-library")},
    )

    assert resolved == Path("/fiction")


def test_resolve_library_path_default_from_config(config_file):
    path = config_file(
        """
        [libraries.default]
        path = "/my/library"
        """
    )

    resolved = resolve_library_path(
        library_flag=None,
        profile=None,
        config_path=path,
        environ={},
    )

    assert resolved == Path("/my/library")


def test_resolve_library_path_unknown_profile(config_file):
    path = config_file(
        """
        [libraries.default]
        path = "/default"
        """
    )

    with pytest.raises(ConfigError, match="Unknown library profile 'nonfiction'"):
        resolve_library_path(
            library_flag=None,
            profile="nonfiction",
            config_path=path,
            environ={},
        )


def test_resolve_library_path_requires_config_when_unset(config_file, tmp_path):
    missing = tmp_path / "missing.toml"

    with pytest.raises(ConfigError, match="Config file not found"):
        resolve_library_path(
            library_flag=None,
            profile=None,
            config_path=missing,
            environ={},
        )
