"""Unit tests for OPF and reader.txt metadata gap-fill."""

from __future__ import annotations

from abs_organize.metadata import (
    BookMetadata,
    MetadataOverrides,
    ResolvedMetadata,
    apply_gap_fill,
    resolve_majority,
)


def _resolved(**kwargs: object) -> ResolvedMetadata:
    defaults = {"author": "Jane Author", "title": "Book Title"}
    defaults.update(kwargs)
    metadata = BookMetadata(**defaults)  # type: ignore[arg-type]
    return ResolvedMetadata(metadata=metadata, warnings=())


def test_opf_fills_empty_series():
    resolved = _resolved(series=None)
    opf = BookMetadata(author="", title="", series="Sword of Truth", sequence=1)

    filled = apply_gap_fill(resolved, opf_metadata=opf)

    assert filled.metadata.series == "Sword of Truth"
    assert filled.metadata.sequence == 1


def test_opf_does_not_override_existing_series():
    resolved = _resolved(series="Audio Series")
    opf = BookMetadata(author="", title="", series="OPF Series")

    filled = apply_gap_fill(resolved, opf_metadata=opf)

    assert filled.metadata.series == "Audio Series"


def test_opf_does_not_override_cli_override():
    resolved = _resolved(series="CLI Series")
    opf = BookMetadata(author="", title="", series="OPF Series")
    overrides = MetadataOverrides(series="CLI Series")

    filled = apply_gap_fill(resolved, opf_metadata=opf, overrides=overrides)

    assert filled.metadata.series == "CLI Series"


def test_reader_txt_fills_narrator_when_tags_missing():
    resolved = _resolved(narrator=None)

    filled = apply_gap_fill(resolved, reader_txt="Sam Tsoutsouvas")

    assert filled.metadata.narrator == "Sam Tsoutsouvas"


def test_reader_txt_does_not_override_opf_narrator():
    resolved = _resolved(narrator=None)
    opf = BookMetadata(author="", title="", narrator="OPF Narrator")

    filled = apply_gap_fill(
        resolved,
        opf_metadata=opf,
        reader_txt="Reader File Narrator",
    )

    assert filled.metadata.narrator == "OPF Narrator"


def test_reader_txt_does_not_override_existing_narrator():
    resolved = _resolved(narrator="Tag Narrator")

    filled = apply_gap_fill(resolved, reader_txt="Reader File Narrator")

    assert filled.metadata.narrator == "Tag Narrator"


def test_reader_txt_strips_narrator_prefix():
    resolved = _resolved(narrator=None)

    filled = apply_gap_fill(resolved, reader_txt="Read by Sam Tsoutsouvas")

    assert filled.metadata.narrator == "Sam Tsoutsouvas"


def test_opf_strips_narrator_prefix():
    resolved = _resolved(narrator=None)
    opf = BookMetadata(
        author="",
        title="",
        narrator="Narrated by Joyce Bean",
    )

    filled = apply_gap_fill(resolved, opf_metadata=opf)

    assert filled.metadata.narrator == "Joyce Bean"


def test_cli_narrator_override_strips_prefix():
    per_file = [
        BookMetadata(author="Author", title="Book", narrator="Ray Porter"),
    ]
    overrides = MetadataOverrides(narrator="Narrated by Joyce Bean")

    resolved = resolve_majority(per_file, overrides=overrides)

    assert resolved.metadata.narrator == "Joyce Bean"
