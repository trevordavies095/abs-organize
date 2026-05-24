"""Resolve cover art and write ``Cover.jpg`` into the title folder.

Priority:
1. Sidecar image at book root (``cover.*`` / ``folder.*`` — see ``discovery``).
2. Embedded art from audio — first track in ``collect_book_audio`` order that has art.
"""

from __future__ import annotations

import io
import shutil
from dataclasses import dataclass
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC
from mutagen.mp4 import MP4Cover
from PIL import Image

from abs_organize.discovery import find_cover_sidecar

COVER_FILENAME = "Cover.jpg"
_JPEG_EXTENSIONS = frozenset({".jpg", ".jpeg"})


@dataclass(frozen=True)
class CoverSource:
    """Resolved cover bytes or sidecar path."""

    sidecar_path: Path | None = None
    image_data: bytes | None = None
    mime: str | None = None

    @property
    def has_sidecar(self) -> bool:
        return self.sidecar_path is not None


def _embedded_from_mp3(path: Path) -> tuple[bytes, str] | None:
    audio = MutagenFile(path)
    if audio is None or audio.tags is None:
        return None
    for frame in audio.tags.getall("APIC"):
        if isinstance(frame, APIC) and frame.data:
            mime = frame.mime or "image/jpeg"
            return frame.data, mime
    return None


def _embedded_from_mp4(path: Path) -> tuple[bytes, str] | None:
    audio = MutagenFile(path)
    if audio is None or audio.tags is None:
        return None
    covers = audio.tags.get("covr")
    if not covers:
        return None
    cover = covers[0]
    if isinstance(cover, MP4Cover):
        if cover.imageformat == MP4Cover.FORMAT_JPEG:
            return bytes(cover), "image/jpeg"
        if cover.imageformat == MP4Cover.FORMAT_PNG:
            return bytes(cover), "image/png"
    if isinstance(cover, (bytes, bytearray)):
        return bytes(cover), "image/jpeg"
    return None


def _embedded_from_flac(path: Path) -> tuple[bytes, str] | None:
    audio = MutagenFile(path)
    if not isinstance(audio, FLAC):
        return None
    pictures: list[Picture] = audio.pictures
    if not pictures:
        return None
    picture = pictures[0]
    mime = picture.mime or "image/jpeg"
    return picture.data, mime


def extract_embedded_cover(path: Path) -> tuple[bytes, str] | None:
    """Return embedded cover bytes and MIME type, if present."""
    suffix = path.suffix.lower()
    if suffix == ".mp3":
        return _embedded_from_mp3(path)
    if suffix in {".m4b", ".m4a"}:
        return _embedded_from_mp4(path)
    if suffix == ".flac":
        return _embedded_from_flac(path)
    return None


def resolve_cover(
    sidecar_root: Path,
    track_paths: list[Path],
) -> CoverSource | None:
    """Resolve cover from sidecar image or embedded audio art."""
    sidecar = find_cover_sidecar(sidecar_root)
    if sidecar is not None:
        return CoverSource(sidecar_path=sidecar)

    for track in track_paths:
        embedded = extract_embedded_cover(track)
        if embedded is not None:
            data, mime = embedded
            return CoverSource(image_data=data, mime=mime)
    return None


def _write_jpeg_bytes(dest: Path, data: bytes, *, mime: str | None) -> None:
    if mime == "image/jpeg" or (mime is None and data[:3] == b"\xff\xd8\xff"):
        dest.write_bytes(data)
        return
    image = Image.open(io.BytesIO(data))
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image.save(dest, format="JPEG", quality=90)


def write_cover_jpg(dest_dir: Path, source: CoverSource, *, move: bool = False) -> str:
    """Write ``Cover.jpg`` under *dest_dir*. Returns relative filename."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / COVER_FILENAME

    if source.sidecar_path is not None:
        sidecar = source.sidecar_path
        if sidecar.suffix.lower() in _JPEG_EXTENSIONS:
            if move:
                shutil.move(sidecar, dest)
            else:
                shutil.copy2(sidecar, dest)
        else:
            image = Image.open(sidecar)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            image.save(dest, format="JPEG", quality=90)
            if move:
                sidecar.unlink()
    elif source.image_data is not None:
        _write_jpeg_bytes(dest, source.image_data, mime=source.mime)
    else:
        raise ValueError("CoverSource has no sidecar or embedded image data")

    return COVER_FILENAME
