"""Load TOML config and resolve the active library root path."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ENV_LIBRARY = "ABS_ORGANIZE_LIBRARY"


class ConfigError(Exception):
    """Config file is missing, invalid, or does not define the requested profile."""


@dataclass(frozen=True)
class AppConfig:
    libraries: dict[str, Path]
    include_subtitle_in_folder: bool = False


def default_config_path() -> Path:
    return Path.home() / ".config" / "abs-organize" / "config.toml"


def _parse_libraries(raw: object, config_path: Path) -> dict[str, Path]:
    if not isinstance(raw, dict):
        raise ConfigError(
            f"Invalid config {config_path}: [libraries] must be a table"
        )

    libraries: dict[str, Path] = {}
    for name, entry in raw.items():
        if not isinstance(name, str):
            raise ConfigError(
                f"Invalid config {config_path}: library profile names must be strings"
            )
        if not isinstance(entry, dict):
            raise ConfigError(
                f"Invalid config {config_path}: [libraries.{name}] must be a table"
            )
        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            raise ConfigError(
                f"Invalid config {config_path}: "
                f"[libraries.{name}] requires a non-empty path = \"...\""
            )
        libraries[name] = Path(path_value.strip()).expanduser()

    if "default" not in libraries:
        raise ConfigError(
            f"Invalid config {config_path}: [libraries.default] is required"
        )

    return libraries


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path if path is not None else default_config_path()

    if not config_path.is_file():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        with config_path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid config {config_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Invalid config {config_path}: root must be a table")

    subtitle = data.get("include_subtitle_in_folder", False)
    if not isinstance(subtitle, bool):
        raise ConfigError(
            f"Invalid config {config_path}: include_subtitle_in_folder must be a boolean"
        )

    if "libraries" not in data:
        raise ConfigError(
            f"Invalid config {config_path}: [libraries] table is required"
        )

    libraries = _parse_libraries(data["libraries"], config_path)

    return AppConfig(
        libraries=libraries,
        include_subtitle_in_folder=subtitle,
    )


def resolve_library_path(
    *,
    library_flag: Path | None,
    profile: str | None,
    config_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    if library_flag is not None:
        return library_flag

    env = os.environ if environ is None else environ

    if profile is None:
        env_path = env.get(ENV_LIBRARY)
        if env_path:
            return Path(env_path.strip()).expanduser()

    path = config_path if config_path is not None else default_config_path()
    config = load_config(path)

    profile_name = profile if profile is not None else "default"
    if profile_name not in config.libraries:
        if profile is None:
            raise ConfigError(
                f"Invalid config {path}: [libraries.default] is required"
            )
        raise ConfigError(
            f"Unknown library profile {profile_name!r} in config {path}. "
            f"Available profiles: {', '.join(sorted(config.libraries))}"
        )

    return config.libraries[profile_name]
