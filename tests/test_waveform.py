"""Tests for waveform data + geometry helpers (Qt-free)."""
from __future__ import annotations

import struct

from app.ffmpeg.waveform import (
    clamp_range,
    compute_peaks,
    peaks_from_s16le,
    time_to_x,
    x_to_time,
)


def test_compute_peaks_exact_values():
    # 4 samples, 2 buckets: max(|1000|,|-2000|)/32768, max(|3000|,|4000|)/32768.
    peaks = compute_peaks([1000, -2000, 3000, 4000], 2)
    assert peaks == [2000 / 32768.0, 4000 / 32768.0]


def test_compute_peaks_empty_and_edges():
    assert compute_peaks([], 5) == [0.0] * 5
    assert compute_peaks([100], 0) == []
    assert compute_peaks([-32768], 1) == [1.0]
    # More buckets than samples: every bucket still gets a sample.
    peaks = compute_peaks([1000, 2000], 5)
    assert len(peaks) == 5
    assert all(p > 0 for p in peaks)


def test_compute_peaks_clamps_to_unit_range():
    assert compute_peaks([99999], 1) == [1.0]


def test_peaks_from_s16le_roundtrip():
    raw = struct.pack("<4h", 0, 16384, -16384, 32767)
    peaks = peaks_from_s16le(raw, 2)
    assert peaks == [16384 / 32768.0, 32767 / 32768.0]


def test_peaks_from_s16le_empty_and_odd_bytes():
    assert peaks_from_s16le(b"", 3) == [0.0, 0.0, 0.0]
    # Trailing odd byte is dropped, not an error.
    assert peaks_from_s16le(b"\x01\x02\x03", 1) == [0x0201 / 32768.0]


def test_time_x_roundtrip():
    for t in (0.0, 30.0, 60.0, 200.0):
        x = time_to_x(t, 200.0, 600.0)
        assert x_to_time(x, 200.0, 600.0) == t


def test_time_x_clamps_outside():
    assert time_to_x(-5.0, 200.0, 600.0, 8.0) == 8.0
    assert time_to_x(999.0, 200.0, 600.0, 8.0) == 600.0 - 8.0
    assert x_to_time(-50.0, 200.0, 600.0, 8.0) == 0.0
    assert x_to_time(9999.0, 200.0, 600.0, 8.0) == 200.0


def test_clamp_range():
    assert clamp_range(30.0, 60.0, 200.0) == (30.0, 60.0)
    # Dragged past the other handle: collapse at the dragged position.
    assert clamp_range(80.0, 20.0, 200.0) == (80.0, 80.0)
    assert clamp_range(-5.0, 999.0, 200.0) == (0.0, 200.0)
    assert clamp_range(10.0, 20.0, 0.0) == (0.0, 0.0)
