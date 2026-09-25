"""Tests for app.utils.files (pure functions, no Qt, no ffmpeg)."""
from __future__ import annotations

from pathlib import Path

from app.utils.files import (
    AUDIO_EXTS,
    IMAGE_EXTS,
    ensure_dir,
    has_space_for,
    human_size,
    is_audio_file,
    is_image_file,
    safe_stem,
)


def test_human_size_bytes_and_units():
    assert human_size(0) == "0 B"
    assert human_size(512) == "512 B"
    assert human_size(1024) == "1.0 KB"
    assert human_size(1536) == "1.5 KB"
    assert human_size(1024 * 1024) == "1.0 MB"
    assert human_size(1024**3) == "1.0 GB"


def test_ensure_dir_creates_nested(tmp_path: Path):
    target = tmp_path / "a" / "b" / "c"
    result = ensure_dir(target)
    assert result == target
    assert target.is_dir()
    # Idempotent.
    assert ensure_dir(target) == target


def test_has_space_for_small_file(tmp_path: Path):
    target = tmp_path / "out"
    assert has_space_for(target, 1024) is True
    assert target.is_dir()


def test_has_space_for_invalid_path_returns_false():
    # NUL is invalid on Windows and raises OSError inside disk_usage/mkdir.
    assert has_space_for("nul:///:::invalid", 1024) is False


def test_is_audio_file_case_insensitive():
    assert is_audio_file("beat.MP3") is True
    assert is_audio_file("beat.wav") is True
    assert is_audio_file("beat.opus") is True
    assert is_audio_file("cover.jpg") is False
    assert is_audio_file("no-extension") is False


def test_is_image_file_case_insensitive():
    assert is_image_file("cover.JPG") is True
    assert is_image_file("cover.png") is True
    assert is_image_file("cover.webp") is True
    assert is_image_file("beat.mp3") is False


def test_audio_and_image_extension_sets():
    assert ".mp3" in AUDIO_EXTS
    assert ".wav" in AUDIO_EXTS
    assert ".jpg" in IMAGE_EXTS
    assert ".png" in IMAGE_EXTS


def test_safe_stem_replaces_windows_forbidden_chars():
    assert safe_stem('a<b>:"/\\|?*c') == "a_b________c"
    assert safe_stem("  spaced  ") == "spaced"


def test_safe_stem_empty_and_dots():
    assert safe_stem("") == "unnamed"
    assert safe_stem("...") == "unnamed"
    assert safe_stem("trailing.") == "trailing"
