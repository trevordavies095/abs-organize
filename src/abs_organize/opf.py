"""Parse OPF sidecar metadata for gap-fill after audio majority vote."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from abs_organize.metadata import BookMetadata, normalize_narrator, parse_year

_NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "opf": "http://www.idpf.org/2007/opf",
}


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    text = element.text.strip()
    return text or None


def _find_meta(root: ET.Element, *names: str) -> str | None:
    lowered = {name.lower() for name in names}
    for meta in root.iter():
        if _local(meta.tag) != "meta":
            continue
        for attr in ("name", "property"):
            value = meta.get(attr)
            if value and value.lower() in lowered:
                content = meta.get("content") or _text(meta)
                if content:
                    return content.strip()
    return None


def _creator_role(element: ET.Element) -> str | None:
    for attr in ("role", "{http://www.idpf.org/2007/opf}role"):
        value = element.get(attr)
        if value:
            return value.lower().split(":")[-1]
    file_as = element.get("file-as")
    if file_as:
        return None
    return None


def _dc_elements(root: ET.Element, local_name: str) -> list[ET.Element]:
    return [el for el in root.iter() if _local(el.tag) == local_name]


def _parse_sequence(value: str | None) -> int | float | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return number


def parse_opf(path: Path) -> BookMetadata | None:
    """Parse bibliographic fields from an OPF file.

    Returns partial metadata (only fields found in OPF) or ``None`` on failure.
    """
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError):
        return None

    root = tree.getroot()

    title = None
    for el in _dc_elements(root, "title"):
        title = _text(el)
        if title:
            break

    author = None
    creators = _dc_elements(root, "creator")
    for role in ("aut", "author"):
        for el in creators:
            if _creator_role(el) == role:
                author = _text(el)
                if author:
                    break
        if author:
            break
    if not author and creators:
        author = _text(creators[0])

    series = _find_meta(
        root,
        "calibre:series",
        "series",
        "belongs-to-collection",
    )
    sequence = _parse_sequence(
        _find_meta(
            root,
            "calibre:series_index",
            "series_index",
            "group-position",
        )
    )

    year = None
    for el in _dc_elements(root, "date"):
        year = parse_year(_text(el))
        if year is not None:
            break

    narrator = None
    for el in _dc_elements(root, "contributor"):
        role = _creator_role(el)
        if role in {"nrt", "narr", "narrator", "reader"}:
            narrator = _text(el)
            if narrator:
                break
    if not narrator:
        narrator = _find_meta(root, "calibre:author_sort_narrator", "narrator")
    if narrator:
        narrator = normalize_narrator(narrator) or None

    if not any((title, author, series, sequence, year, narrator)):
        return None

    return BookMetadata(
        author=author or "",
        title=title or "",
        series=series,
        sequence=sequence,
        year=year,
        narrator=narrator,
    )


def read_reader_txt(path: Path) -> str | None:
    """Return stripped narrator text from ``reader.txt``."""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text:
        return None
    normalized = normalize_narrator(text)
    return normalized or None
