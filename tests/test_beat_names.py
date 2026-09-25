"""Tests for filename auto-detection (title/BPM/key)."""
from __future__ import annotations

from app.utils.beat_names import parse_beat_filename


def test_bpm_and_minor_key_detected():
    info = parse_beat_filename("wolf Bm 95bpm")
    assert info.bpm == "95"
    assert info.key == "Bm"
    assert info.title == "wolf"


def test_sharp_key_and_uppercase_bpm():
    info = parse_beat_filename("DARK F#m 150 BPM")
    assert info.bpm == "150"
    assert info.key == "F#m"
    assert "DARK" in info.title


def test_flat_key():
    info = parse_beat_filename("love Eb 90bpm")
    assert info.bpm == "90"
    assert info.key == "Eb"
    assert info.title == "love"


def test_word_key_minor_and_major():
    assert parse_beat_filename("idea A minor").key == "Am"
    assert parse_beat_filename("idea C major").key == "C"


def test_bare_letter_is_not_a_key():
    info = parse_beat_filename("song A")
    assert info.key == ""
    assert info.title == "song A"


def test_out_of_range_bpm_ignored():
    info = parse_beat_filename("song 300bpm Bm")
    assert info.bpm == ""
    assert info.key == "Bm"


def test_separators_normalized():
    info = parse_beat_filename("trap_140bpm")
    assert info.bpm == "140"
    assert info.title == "trap"

    info = parse_beat_filename("my-beat (dark) [2026]")
    assert "(" not in info.title
    assert "[" not in info.title


def test_empty_stem_keeps_original():
    info = parse_beat_filename("   ")
    assert info.title == ""
    assert info.bpm == ""
    assert info.key == ""
