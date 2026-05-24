"""Shared test fixtures."""

from __future__ import annotations

import io
import shutil
from pathlib import Path

import pytest
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.id3 import APIC, ID3, TIT3
from mutagen.mp4 import MP4
from PIL import Image

_FIXTURES = Path(__file__).parent / "fixtures"
_SILENT_MP3 = _FIXTURES / "silent.mp3"
_SILENT_M4B = _FIXTURES / "silent.m4b"


def minimal_jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1), color="red").save(buffer, format="JPEG")
    return buffer.getvalue()


def write_minimal_opf(
    path: Path,
    *,
    series: str | None = None,
    sequence: str | None = None,
    title: str | None = None,
    author: str | None = None,
    narrator: str | None = None,
    year: str | None = None,
) -> Path:
    metadata_lines: list[str] = []
    if title:
        metadata_lines.append(f'    <dc:title>{title}</dc:title>')
    if author:
        metadata_lines.append(
            f'    <dc:creator opf:role="aut">{author}</dc:creator>'
        )
    if year:
        metadata_lines.append(f"    <dc:date>{year}</dc:date>")
    if series:
        metadata_lines.append(
            f'    <meta name="calibre:series" content="{series}"/>'
        )
    if sequence:
        metadata_lines.append(
            f'    <meta name="calibre:series_index" content="{sequence}"/>'
        )
    if narrator:
        metadata_lines.append(
            f'    <dc:contributor opf:role="nrt">{narrator}</dc:contributor>'
        )

    body = "\n".join(metadata_lines)
    content = f"""<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
{body}
  </metadata>
</package>
"""
    path.write_text(content, encoding="utf-8")
    return path


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
    id3 = ID3(path)
    id3.add(TIT3(encoding=3, text=subtitle))
    id3.save()
    return path


def _set_id3_cover(path: Path, image_data: bytes | None = None) -> Path:
    data = image_data if image_data is not None else minimal_jpeg_bytes()
    id3 = ID3(path)
    id3.add(
        APIC(
            encoding=3,
            mime="image/jpeg",
            type=3,
            desc="Cover",
            data=data,
        )
    )
    id3.save()
    return path


@pytest.fixture
def minimal_jpeg():
    return minimal_jpeg_bytes()


@pytest.fixture
def make_tagged_mp3(tmp_path):
    def _factory(
        name: str = "book.mp3",
        *,
        subtitle: str | None = None,
        with_cover: bool = False,
        **tags: str,
    ) -> Path:
        path = _tag_mp3(tmp_path / name, tags)
        if subtitle:
            path = _set_id3_subtitle(path, subtitle)
        if with_cover:
            path = _set_id3_cover(path)
        return path

    return _factory


@pytest.fixture
def make_mp3_with_cover(tmp_path):
    def _factory(name: str = "book.mp3", **tags: str) -> Path:
        path = _tag_mp3(tmp_path / name, tags)
        return _set_id3_cover(path)

    return _factory


@pytest.fixture
def write_opf(tmp_path):
    def _factory(
        path: Path | None = None,
        *,
        name: str = "metadata.opf",
        **fields: str,
    ) -> Path:
        return write_minimal_opf(path or (tmp_path / name), **fields)

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
