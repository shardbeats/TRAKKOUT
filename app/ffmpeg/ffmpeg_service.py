"""FFmpeg/FFprobe service: fachada delegante (Fase 4).

API pública sin cambios. La implementación vive en:
- errors.py  (excepciones)
- detect.py  (binarios, ToolStatus)
- probe.py   (sondeo, validación, waveform)
- filters.py (filter_complex, drawtext)
- render.py  (build_command, progreso)

Este módulo conserva los nombres importados por tests y UI.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

from app.ffmpeg import detect as _detect
from app.ffmpeg import filters as _filters
from app.ffmpeg import probe as _probe
from app.ffmpeg import render as _render
from app.ffmpeg.detect import ToolStatus, _popen, _run_capture
from app.ffmpeg.errors import (
    FFmpegNotFoundError,
    MediaProbeError,
    VideoBuildError,
)
from app.ffmpeg.filters import escape_drawtext, find_system_font
from app.models.models import AudioInfo, ImageInfo, OverlaySettings, VideoSettings
from app.utils.files import human_size

log = logging.getLogger(__name__)

ProgressCallback = Callable[[float, float, float], None]  # (out_seconds, total, pct)

# Re-exports de compatibilidad (tests / código externo).
_AUDIO_CODEC_MAP = _render.AUDIO_CODEC_MAP
_TIME_RE = _render.TIME_RE

__all__ = [
    "FFmpegService",
    "FFmpegNotFoundError",
    "MediaProbeError",
    "VideoBuildError",
    "ToolStatus",
    "ProgressCallback",
    "find_system_font",
    "escape_drawtext",
]


class FFmpegService:
    """All media operations. No GUI dependencies."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"
        self.ffprobe_path = ffprobe_path or "ffprobe"
        self._proc = None
        self._cancel = threading.Event()
        self._lock = threading.Lock()

    # ---------- detection ----------
    def resolve(self, name: str) -> str:
        return _detect.resolve_tool(name, self.ffmpeg_path, self.ffprobe_path)

    def status(self) -> ToolStatus:
        return _detect.query_status(self.ffmpeg_path, self.ffprobe_path)

    def _check_tool(self, exe: str, args: list[str]) -> bool:
        return _detect.check_tool(exe, args)

    def require_tools(self) -> ToolStatus:
        return _detect.require_tools(self.ffmpeg_path, self.ffprobe_path)

    # ---------- probe ----------
    def probe(self, path: str | Path) -> dict:
        return _probe.probe_data(self.resolve("ffprobe"), path)

    def get_audio_info(self, path: str | Path) -> AudioInfo:
        return _probe.audio_info(self.resolve("ffprobe"), path)

    def get_image_info(self, path: str | Path) -> ImageInfo:
        return _probe.image_info(self.resolve("ffprobe"), path)

    def validate_audio(self, path: str | Path) -> AudioInfo:
        return _probe.validate_audio(self.resolve("ffprobe"), path)

    def validate_image(self, path: str | Path) -> ImageInfo:
        return _probe.validate_image(self.resolve("ffprobe"), path)

    def get_waveform(self, audio_path: str | Path, buckets: int = 800) -> list[float]:
        return _probe.waveform_peaks(self.resolve("ffmpeg"), audio_path, buckets)

    # ---------- filter construction ----------
    def build_video_filter(self, vs: VideoSettings, ov: OverlaySettings) -> str:
        return _filters.build_video_filter(vs, ov)

    @staticmethod
    def _overlay_xy(position: str, margin: int) -> tuple[str, str]:
        return _filters.overlay_xy(position, margin)

    def build_command(
        self,
        image_path: str | Path,
        audio_path: str | Path,
        output_path: str | Path,
        vs: VideoSettings,
        ov: OverlaySettings,
        duration: float,
        start: float = 0.0,
    ) -> list[str]:
        return _render.build_command(
            self.resolve("ffmpeg"), image_path, audio_path,
            output_path, vs, ov, duration, start=start)

    # ---------- generation ----------
    def generate_video(
        self,
        image_path: str | Path,
        audio_path: str | Path,
        output_path: str | Path,
        vs: VideoSettings,
        ov: OverlaySettings,
        on_progress: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Path:
        self.require_tools()
        audio = self.validate_audio(audio_path)
        self.validate_image(image_path)
        total = audio.duration
        if total <= 0:
            raise VideoBuildError("Invalid audio duration (0 s).")

        clip_start, clip_end = vs.clip_range(total)
        if clip_end <= clip_start:
            raise VideoBuildError(
                f"Invalid clip selection ({clip_start:.1f}s – {clip_end:.1f}s).")
        total = clip_end - clip_start

        out = Path(str(output_path))
        out.parent.mkdir(parents=True, exist_ok=True)
        need = int(total * 1.5 * 1024 * 1024) + 20 * 1024 * 1024
        from app.utils.files import has_space_for
        if not has_space_for(out.parent, need):
            raise VideoBuildError("Not enough disk space in the output folder.")

        cmd = self.build_command(image_path, audio_path, out, vs, ov, total,
                                 start=clip_start)
        log.info("FFmpeg: %s", " ".join(cmd))
        self._cancel.clear()
        if cancel_event is None:
            cancel_event = self._cancel
        with self._lock:
            self._proc = _popen(cmd)
            proc = self._proc
        try:
            assert proc.stdout is not None
            from collections import deque
            tail: deque[str] = deque(maxlen=25)
            for line in proc.stdout:
                if cancel_event.is_set():
                    self._terminate(proc)
                    raise VideoBuildError("Generation cancelled by the user.")
                tail.append(line or "")
                out_s = _render.parse_progress_line(line or "")
                if out_s is not None and on_progress:
                    try:
                        pct = max(0.0, min(100.0, out_s / total * 100.0)) if total else 0.0
                        on_progress(out_s, total, pct)
                    except (ValueError, ZeroDivisionError):
                        pass
            rc = proc.wait()
            if cancel_event.is_set():
                raise VideoBuildError("Generation cancelled by the user.")
            if rc != 0:
                detail = "".join(tail)[-1200:].strip()
                log.error("FFmpeg failed (rc=%s). Tail:\n%s", rc, detail)
                hint = f"\nDetalle FFmpeg:\n{detail}" if detail else ""
                raise VideoBuildError(f"FFmpeg exited with code {rc}. Check logs/app.log.{hint}")
            if not out.exists() or out.stat().st_size == 0:
                raise VideoBuildError("FFmpeg did not produce the output file.")
            try:
                probe_out = self.probe(out)
                dur = float(probe_out.get("format", {}).get("duration") or 0)
                if dur and abs(dur - total) > 1.0:
                    log.warning("Output duration %.2f differs from audio %.2f", dur, total)
            except Exception as exc:
                log.warning("Could not verify output duration: %s", exc)
            if on_progress:
                on_progress(total, total, 100.0)
            log.info("Video rendered: %s (%s)", out, human_size(out.stat().st_size))
            return out
        finally:
            with self._lock:
                self._proc = None

    def cancel(self) -> None:
        self._cancel.set()
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._terminate(self._proc)

    def _terminate(self, proc) -> None:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        except Exception as exc:
            log.warning("Error terminating FFmpeg: %s", exc)
