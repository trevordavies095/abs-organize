"""Shared test fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4

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


@pytest.fixture
def make_tagged_mp3(tmp_path):
    def _factory(name: str = "book.mp3", **tags: str) -> Path:
        return _tag_mp3(tmp_path / name, tags)

    return _factory


@pytest.fixture
def make_tagged_m4b(tmp_path):
    def _factory(name: str = "book.m4b", **tags: str) -> Path:
        return _tag_m4b(tmp_path / name, tags)

    return _factory
