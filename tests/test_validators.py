"""Tests for app.utils.validators (no Qt, no network)."""
from __future__ import annotations

from pathlib import Path

from app.utils.validators import (
    validate_audio_path,
    validate_image_path,
    validate_youtube_metadata,
)


def test_validate_audio_path_empty():
    result = validate_audio_path("")
    assert result.ok is False
    assert "No audio" in result.message


def test_validate_audio_path_missing(tmp_path: Path):
    result = validate_audio_path(str(tmp_path / "missing.mp3"))
    assert result.ok is False
    assert "does not exist" in result.message


def test_validate_audio_path_directory(tmp_path: Path):
    result = validate_audio_path(str(tmp_path))
    assert result.ok is False
    assert "not a file" in result.message


def test_validate_audio_path_bad_extension(tmp_audio: Path):
    bad = tmp_audio.with_suffix(".txt")
    bad.write_bytes(b"x")
    result = validate_audio_path(str(bad))
    assert result.ok is False
    assert "Unsupported audio format" in result.message


def test_validate_audio_path_empty_file(tmp_path: Path):
    empty = tmp_path / "empty.mp3"
    empty.write_bytes(b"")
    result = validate_audio_path(str(empty))
    assert result.ok is False
    assert "empty" in result.message.lower()


def test_validate_audio_path_ok(tmp_audio: Path):
    result = validate_audio_path(str(tmp_audio))
    assert result.ok is True


def test_validate_image_path_ok(tmp_image: Path):
    result = validate_image_path(str(tmp_image))
    assert result.ok is True


def test_validate_image_path_bad_extension(tmp_audio: Path):
    result = validate_image_path(str(tmp_audio))
    assert result.ok is False
    assert "Unsupported image format" in result.message


def test_validate_youtube_metadata_requires_title():
    assert validate_youtube_metadata("").ok is False
    assert validate_youtube_metadata("   ").ok is False
    assert validate_youtube_metadata("My beat").ok is True


def test_validate_youtube_metadata_title_limit():
    result = validate_youtube_metadata("A" * 101)
    assert result.ok is False
    assert "100" in result.message
    assert validate_youtube_metadata("A" * 100).ok is True


def test_validate_youtube_metadata_tags_limit():
    result = validate_youtube_metadata("Title", tags=["x" * 501])
    assert result.ok is False
    assert "500" in result.message
