"""Local file provider (always available, no network).

Links a local file (audio or artwork) to a BeatMetadata. It is the main
route for audio: the user provides their legitimate download/license.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.models.models import BeatMetadata
from .base import MediaProvider
from app.utils.files import is_audio_file, is_image_file


class LocalFileProvider(MediaProvider):
    name = "local"
    label = "Local file"

    def can_handle(self, url_or_path: str) -> bool:
        p = Path(str(url_or_path or ""))
        return p.exists() and (is_audio_file(p) or is_image_file(p))

    def fetch_info(self, url_or_path: str) -> BeatMetadata:
        p = Path(str(url_or_path))
        beat = BeatMetadata(
            source="local",
            fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        if is_audio_file(p):
            beat.title = p.stem
            beat.audio_path = str(p)
        elif is_image_file(p):
            beat.artwork_path = str(p)
        return beat
