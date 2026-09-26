"""File and metadata validation with clear user-facing messages."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .files import AUDIO_EXTS, IMAGE_EXTS


@dataclass
class ValidationResult:
    ok: bool
    message: str = ""


def validate_audio_path(path: str) -> ValidationResult:
    if not path:
        return ValidationResult(False, "No audio file selected.")
    p = Path(path)
    if not p.exists():
        return ValidationResult(False, f"Audio file does not exist:\n{p}")
    if not p.is_file():
        return ValidationResult(False, f"Audio path is not a file:\n{p}")
    if p.suffix.lower() not in AUDIO_EXTS:
        return ValidationResult(
            False,
            f"Unsupported audio format ({p.suffix or 'no extension'}). "
            f"Supported formats: {', '.join(sorted(AUDIO_EXTS))}.",
        )
    if p.stat().st_size == 0:
        return ValidationResult(False, "Audio file is empty (0 bytes).")
    return ValidationResult(True, "Valid audio.")


def validate_image_path(path: str) -> ValidationResult:
    if not path:
        return ValidationResult(False, "No artwork selected.")
    p = Path(path)
    if not p.exists():
        return ValidationResult(False, f"Image does not exist:\n{p}")
    if not p.is_file():
        return ValidationResult(False, f"Image path is not a file:\n{p}")
    if p.suffix.lower() not in IMAGE_EXTS:
        return ValidationResult(
            False,
            f"Unsupported image format ({p.suffix or 'no extension'}). "
            f"Supported formats: {', '.join(sorted(IMAGE_EXTS))}.",
        )
    if p.stat().st_size == 0:
        return ValidationResult(False, "Image is empty (0 bytes).")
    return ValidationResult(True, "Valid image.")


def validate_youtube_metadata(title: str, description: str = "", tags: list[str] | None = None) -> ValidationResult:
    if not (title or "").strip():
        return ValidationResult(False, "Video title is required.")
    if len(title) > 100:
        return ValidationResult(False, f"Title exceeds 100 characters ({len(title)}). Shorten it.")
    tags = tags or []
    if len(" ".join(tags)) > 500:
        return ValidationResult(False, "Tags exceed the total limit (~500 characters). Remove some.")
    return ValidationResult(True, "Valid metadata.")


#: Minimum clip length in seconds (matches the encoder floor in FFmpegService).
MIN_CLIP_SECONDS = 0.5


def validate_trim(start: float, end: float, duration: float) -> ValidationResult:
    """Validate a Short-clip selection. ``end`` <= 0 means "to the end".

    With an unknown duration (<= 0, file not probed) only the ordering
    is checked; range checks need the real length.
    """
    total = max(0.0, float(duration or 0.0))
    try:
        s = max(0.0, float(start or 0.0))
    except (TypeError, ValueError):
        return ValidationResult(False, "Invalid clip start.")
    try:
        e = float(end or 0.0)
    except (TypeError, ValueError):
        return ValidationResult(False, "Invalid clip end.")
    if e <= 0.0:
        e = total
    if total <= 0.0:
        if e > 0.0 and e <= s:
            return ValidationResult(False, "Clip end must be after clip start.")
        return ValidationResult(True, "Valid clip.")
    if s >= total:
        return ValidationResult(False, "Clip start is beyond the audio length.")
    if e <= s:
        return ValidationResult(False, "Clip end must be after clip start.")
    if e > total:
        return ValidationResult(
            False, f"Clip end ({e:.1f}s) exceeds the audio length ({total:.1f}s).")
    if e - s < MIN_CLIP_SECONDS:
        return ValidationResult(
            False, f"Clip is too short (minimum {MIN_CLIP_SECONDS:g} s).")
    return ValidationResult(True, "Valid clip.")
