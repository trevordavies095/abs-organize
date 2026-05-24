"""Shared test fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.mp4 import MP4

_FIXTURES = Path(__file__).parent / "fixtures"
_SILENT_MP3 = _FIXTURES / "silent.mp3"
_SILENT_M4B = _FIXTURES / "silent.m4b"


def _tag_mp3(path: Path, tags: dict[str, str]) -> Path:
    shutil.copy(_SILENT_MP3, path)
    easy = EasyID3(path)
    for key, value in tags.items():
        easy[key] = value
    easy.save()
    return path


def _tag_m4b(path: Path, tags: dict[str, str]) -> Path:
    shutil.copy(_SILENT_M4B, path)
    easy = EasyMP4(path)
    for key, value in tags.items():
        easy[key] = value
    easy.save()
    return path


def _set_mp4_movement(path: Path, *, name: str, index: int) -> Path:
    audio = MP4(path)
    audio.tags[_MP4_MOVEMENT_NAME] = [name]
    audio.tags[_MP4_MOVEMENT_INDEX] = [index]
    audio.save()
    return path


def _set_mp4_narrator(path: Path, narrator: str) -> Path:
    audio = MP4(path)
    audio.tags[_MP4_COMPOSER] = [narrator]
    audio.save()
    return path


_MP4_MOVEMENT_NAME = "\xa9mvn"
_MP4_MOVEMENT_INDEX = "\xa9mvi"
_MP4_COMPOSER = "\xa9wrt"


def _set_id3_subtitle(path: Path, subtitle: str) -> Path:
    from mutagen.id3 import ID3, TIT3

    id3 = ID3(path)
    id3.add(TIT3(encoding=3, text=subtitle))
    id3.save()
    return path


@pytest.fixture
def make_tagged_mp3(tmp_path):
    def _factory(name: str = "book.mp3", *, subtitle: str | None = None, **tags: str) -> Path:
        path = _tag_mp3(tmp_path / name, tags)
        if subtitle:
            path = _set_id3_subtitle(path, subtitle)
        return path

    return _factory


@pytest.fixture
def make_tagged_m4b(tmp_path):
    def _factory(name: str = "book.m4b", *, narrator: str | None = None, **tags: str) -> Path:
        path = _tag_m4b(tmp_path / name, tags)
        if narrator:
            path = _set_mp4_narrator(path, narrator)
        return path

    return _factory


@pytest.fixture
def make_tagged_m4b_with_movement(tmp_path):
    def _factory(
        name: str = "book.m4b",
        *,
        movement_name: str,
        movement_index: int,
        narrator: str | None = None,
        **tags: str,
    ) -> Path:
        path = _tag_m4b(tmp_path / name, tags)
        path = _set_mp4_movement(path, name=movement_name, index=movement_index)
        if narrator:
            path = _set_mp4_narrator(path, narrator)
        return path

    return _factory
