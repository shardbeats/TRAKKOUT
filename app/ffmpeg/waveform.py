"""Waveform data + geometry helpers (Qt-free, fully testable).

The widget (app/ui/waveform.py) renders from these; the service
(FFmpegService.get_waveform) produces the peaks from real audio.
"""
from __future__ import annotations

import array
import struct
import sys


def compute_peaks(samples: list[int] | array.array, buckets: int) -> list[float]:
    """Peak amplitude per bucket, normalized to 0..1 (int16 full scale).

    Empty input → flat zeros. Pure function: feed it synthetic data in tests.
    """
    n = max(0, int(buckets or 0))
    if n == 0:
        return []
    data = list(samples or [])
    if not data:
        return [0.0] * n
    out: list[float] = []
    total = len(data)
    for i in range(n):
        lo = (i * total) // n
        hi = ((i + 1) * total) // n
        chunk = data[lo:hi] or data[lo:lo + 1]
        peak = 0
        for s in chunk:
            a = abs(int(s))
            if a > peak:
                peak = a
        out.append(min(1.0, peak / 32768.0))
    return out


def peaks_from_s16le(raw: bytes, buckets: int) -> list[float]:
    """Decode little-endian int16 mono PCM bytes into normalized peaks."""
    blob = bytes(raw or b"")
    if len(blob) % 2:
        blob = blob[:-1]
    if not blob:
        return compute_peaks([], buckets)
    try:
        samples = array.array("h", blob)
    except Exception:
        # Fallback for exotic platforms: manual unpack.
        count = len(blob) // 2
        samples = array.array("h", struct.pack(f"<{count}h", *struct.unpack(f"<{count}h", blob)))
    if sys.byteorder != "little":
        samples.byteswap()
    return compute_peaks(samples, buckets)


def clamp_range(start: float, end: float, duration: float) -> tuple[float, float]:
    """Clamp a selection to [0, duration] keeping start <= end."""
    total = max(0.0, float(duration or 0.0))
    try:
        s = min(max(0.0, float(start or 0.0)), total)
    except (TypeError, ValueError):
        s = 0.0
    try:
        e = min(max(0.0, float(end or 0.0)), total)
    except (TypeError, ValueError):
        e = total
    if e < s:
        e = s
    return s, e


def time_to_x(t: float, duration: float, width: float, pad: float = 6.0) -> float:
    """Time in seconds → widget x coordinate."""
    total = max(1e-6, float(duration or 0.0))
    span = max(1.0, float(width) - 2.0 * pad)
    frac = min(1.0, max(0.0, float(t or 0.0) / total))
    return pad + frac * span


def x_to_time(x: float, duration: float, width: float, pad: float = 6.0) -> float:
    """Widget x coordinate → time in seconds."""
    total = max(0.0, float(duration or 0.0))
    span = max(1.0, float(width) - 2.0 * pad)
    frac = min(1.0, max(0.0, (float(x or 0.0) - pad) / span))
    return frac * total
