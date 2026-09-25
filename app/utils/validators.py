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
