"""Unit tests for OPF sidecar parsing."""

from __future__ import annotations

from abs_organize.opf import parse_opf

from conftest import write_minimal_opf


def test_parse_opf_splits_title_suffix_into_narrator(tmp_path):
    opf_path = write_minimal_opf(
        tmp_path / "metadata.opf",
        title="A Game of Thrones (read by Roy Dotrice)",
    )

    metadata = parse_opf(opf_path)

    assert metadata is not None
    assert metadata.title == "A Game of Thrones"
    assert metadata.narrator == "Roy Dotrice"


def test_parse_opf_contributor_narrator_wins_over_title_suffix(tmp_path):
    opf_path = write_minimal_opf(
        tmp_path / "metadata.opf",
        title="A Game of Thrones (read by Other Narrator)",
        narrator="Roy Dotrice",
    )

    metadata = parse_opf(opf_path)

    assert metadata is not None
    assert metadata.title == "A Game of Thrones"
    assert metadata.narrator == "Roy Dotrice"
