"""Beat filename auto-detection: title, BPM and key from the file name.

Typical producer convention: "wolf Bm 95bpm", "DARK F#m 150 BPM",
"love Eb 90bpm". Pure function (no Qt) so it can be tested.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# BPM with explicit suffix: 95bpm, 95 bpm, 150 BPM. Musical range 50-220.
_BPM_RE = re.compile(r"(?<![\d.])([5-9]\d|1\d\d|2[0-2]\d)\s?bpm\b", re.IGNORECASE)

# Key with explicit words (case-insensitive): "A minor", "C major".
_KEY_WORDS_RE = re.compile(
    r"\b([A-G])\s*(#|b)?\s*(minor|major|min|maj)\b", re.IGNORECASE)

# Keys with attached accidental or mode. UPPERCASE root on purpose:
# "Am"/"Bm"/"Bb" are detected but not the verbs "am"/"em" or "bb".
# - sharps: F#, F#m, F#min (# never appears in plain words,
#   so a lowercase root is fine: f#m)
_KEY_SHARP_RE = re.compile(r"\b([A-Ga-g])#\s?(m|min)?\b")
# - flats: Bb, Bbm, Eb, Ebmin
_KEY_FLAT_RE = re.compile(r"\b([A-G])b\s?(m|min)?\b")
# - natural minors: Bm, Am, Amin
_KEY_MINOR_RE = re.compile(r"\b([A-G])\s?(m|min)\b")

_SEP_RE = re.compile(r"\s{2,}")


@dataclass
class BeatNameInfo:
    title: str = ""
    bpm: str = ""
    key: str = ""


def _norm_key(root: str, acc: str = "", mode: str = "") -> str:
    key = root.upper() + (acc or "")
    if (mode or "").lower().startswith("maj"):
        return key  # major is written bare: "C", "F#"
    if mode:
        return key + "m"  # minor/min -> "m": "Bm", "Ebm"
    return key


def parse_beat_filename(stem: str) -> BeatNameInfo:
    """Extract (title, bpm, key) from the file name (no extension).

    Rules:
    - BPM: number 50-220 followed by "bpm". Out of range is ignored.
    - Key: always when it carries #/b/m/min (Bm, F#m, Bb, Ebm, Amin) or the
      words minor/major ("A minor", "C major"). A bare letter (A, C, …)
      only counts with explicit minor/major.
    - Title: remainder after removing BPM/key, with separators normalized.
    """
    text = (stem or "").strip()
    # _ and . act as separators (trap_140bpm -> "trap 140bpm").
    text = re.sub(r"[_\.]+", " ", text)
    text = _SEP_RE.sub(" ", text).strip()
    bpm = ""
    key = ""

    m = _BPM_RE.search(text)
    if m:
        bpm = m.group(1)
        text = (text[:m.start()] + " " + text[m.end():])

    m = _KEY_WORDS_RE.search(text)
    if m:
        key = _norm_key(m.group(1), m.group(2) or "", m.group(3))
        text = (text[:m.start()] + " " + text[m.end():])
    else:
        for rx, kind in ((_KEY_SHARP_RE, "sharp"),
                         (_KEY_FLAT_RE, "flat"),
                         (_KEY_MINOR_RE, "minor")):
            m = rx.search(text)
            if m:
                if kind == "sharp":
                    key = _norm_key(m.group(1), "#", m.group(2) or "")
                elif kind == "flat":
                    key = _norm_key(m.group(1), "b", m.group(2) or "")
                else:
                    key = _norm_key(m.group(1), "", m.group(2) or "")
                text = (text[:m.start()] + " " + text[m.end():])
                break

    # Normalize separators: _ . () [] and bare dashes -> space.
    text = re.sub(r"[_\.\(\)\[\]]+", " ", text)
    text = re.sub(r"\s+-\s+", " ", text)
    text = _SEP_RE.sub(" ", text).strip(" \t-_")
    title = _SEP_RE.sub(" ", text).strip()
    if not title:
        title = (stem or "").strip()
    return BeatNameInfo(title=title, bpm=bpm, key=key)
