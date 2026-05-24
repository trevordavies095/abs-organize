"""Unit tests for folder-name metadata guessing."""

from __future__ import annotations

from abs_organize.metadata import (
    BookMetadata,
    MetadataOverrides,
    ResolvedMetadata,
    apply_folder_guess,
)


def test_apply_folder_guess_fills_missing_fields():
    resolved = ResolvedMetadata(
        metadata=BookMetadata(author="", title=""),
        warnings=(),
    )

    result = apply_folder_guess(
        resolved, name="Jane Author - Great Book", overrides=None
    )

    assert result.metadata.author == "Jane Author"
    assert result.metadata.title == "Great Book"
    assert any("Guessed author" in warning for warning in result.warnings)
    assert any("Guessed title" in warning for warning in result.warnings)


def test_apply_folder_guess_respects_title_override():
    resolved = ResolvedMetadata(
        metadata=BookMetadata(author="", title=""),
        warnings=(),
    )

    result = apply_folder_guess(
        resolved,
        name="Jane Author - Great Book",
        overrides=MetadataOverrides(title="Override Title"),
    )

    assert result.metadata.author == "Jane Author"
    assert result.metadata.title == "Override Title"
    assert any("Guessed author" in warning for warning in result.warnings)
    assert not any("Guessed title" in warning for warning in result.warnings)


def test_apply_folder_guess_noop_when_metadata_complete():
    resolved = ResolvedMetadata(
        metadata=BookMetadata(author="Tagged Author", title="Tagged Title"),
        warnings=("existing",),
    )

    result = apply_folder_guess(
        resolved, name="Jane Author - Great Book", overrides=None
    )

    assert result.metadata.author == "Tagged Author"
    assert result.metadata.title == "Tagged Title"
    assert result.warnings == ("existing",)
