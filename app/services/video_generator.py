"""VideoGenerator: builds the YouTube-ready MP4 from audio + artwork.

Thin, standalone layer over FFmpegService (dependency injection):
the GUI and the queue talk to VideoGenerator, never to FFmpeg directly.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from app.ffmpeg.ffmpeg_service import FFmpegService, ProgressCallback
from app.models.models import OverlaySettings, VideoSettings
from app.utils.files import ensure_dir, safe_stem


class VideoGenerator:
    """Input: audio + artwork + VideoSettings/OverlaySettings. Output: MP4."""

    def __init__(self, ffmpeg_service: FFmpegService) -> None:
        self.ffmpeg = ffmpeg_service

    # ---- main pipeline ----
    def generate(
        self,
        audio_path: str | Path,
        artwork_path: str | Path,
        output_path: str | Path,
        video_settings: VideoSettings,
        overlay_settings: OverlaySettings,
        on_progress: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Path:
        """Generate the video. Raises exceptions with clear messages (no tracebacks)."""
        audio = str(audio_path or "").strip()
        art = str(artwork_path or "").strip()
        if not audio or not Path(audio).exists():
            from app.ffmpeg.ffmpeg_service import VideoBuildError
            raise VideoBuildError(f"Audio file does not exist:\n{audio or '(empty)'}")
        if not art or not Path(art).exists():
            from app.ffmpeg.ffmpeg_service import VideoBuildError
            raise VideoBuildError(f"Artwork does not exist:\n{art or '(empty)'}")
        return self.ffmpeg.generate_video(
            art, audio, output_path, video_settings, overlay_settings,
            on_progress=on_progress, cancel_event=cancel_event)

    def cancel(self) -> None:
        self.ffmpeg.cancel()

    # ---- helpers ----
    @staticmethod
    def default_output_path(output_dir: str | Path, beat_title: str) -> Path:
        ensure_dir(output_dir)
        return Path(output_dir) / f"{safe_stem(beat_title or 'beat')}.mp4"

    def probe_inputs(self, audio_path: str | Path, artwork_path: str | Path) -> dict:
        """Return {'audio': AudioInfo, 'image': ImageInfo} or raise a clear error."""
        return {
            "audio": self.ffmpeg.get_audio_info(audio_path),
            "image": self.ffmpeg.get_image_info(artwork_path),
        }
