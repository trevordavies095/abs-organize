"""Conservative folder-name heuristics for sparse metadata.

Supported patterns (v1):
- ``Author - Title`` (hyphen, en dash, or em dash surrounded by spaces)
- ``Author - Title (YYYY)`` for an optional trailing year

Filename parsing and additional patterns can be added in follow-up work.
"""

from __future__ import annotations

import re

from abs_organize.metadata import BookMetadata, parse_year

_SEPARATOR_RE = re.compile(r" [\-\u2013\u2014] ")
_YEAR_SUFFIX_RE = re.compile(r"\((\d{4})\)$")
# Leading volume number on book-root folder names: ``01 - Title``, ``12. Title``, ``3 Title``.
# Known false positive: ``1984 - Title`` is read as volume 1984, not a publication year.
_SEQUENCE_PREFIX_RE = re.compile(
    r"^(\d+)(?:\s*[-.\u2013\u2014]+\s+|\.\s+|\s+).+$"
)


def guess_from_name(name: str) -> BookMetadata | None:
    """Parse author and title from a folder or file stem name.

    Returns ``None`` when the name does not match a supported pattern.
    """
    text = name.strip()
    if not text:
        return None

    match = _SEPARATOR_RE.search(text)
    if match is None:
        return None

    author = text[: match.start()].strip()
    title_part = text[match.end() :].strip()
    if not author or not title_part:
        return None

    year = None
    year_match = _YEAR_SUFFIX_RE.search(title_part)
    if year_match is not None:
        year = parse_year(year_match.group(1))
        title_part = title_part[: year_match.start()].strip()
        if not title_part:
            return None

    return BookMetadata(author=author, title=title_part, year=year)


def infer_sequence_from_folder_name(name: str) -> int | float | None:
    """Infer series sequence / volume from a book-root directory name.

    Matches a leading integer followed by a separator (`` - ``, ``. ``, or space)
    before the rest of the name. Returns ``None`` when the pattern does not match.
    """
    text = name.strip()
    if not text:
        return None
    match = _SEQUENCE_PREFIX_RE.match(text)
    if match is None:
        return None
    return int(match.group(1))
