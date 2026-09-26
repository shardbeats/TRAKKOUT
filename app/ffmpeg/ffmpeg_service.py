"""FFmpeg/FFprobe service: detection, probing, validation and video rendering."""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from app.models.models import AudioInfo, ImageInfo, OverlaySettings, VideoSettings
from app.utils.files import human_size

log = logging.getLogger(__name__)

ProgressCallback = Callable[[float, float, float], None]  # (out_seconds, total, pct)

_AUDIO_CODEC_MAP = {
    "aac": (["-c:a", "aac", "-b:a"], "192k"),
    "mp3": (["-c:a", "libmp3lame", "-b:a"], "192k"),
    "opus": (["-c:a", "libopus", "-b:a"], "160k"),
    "wav": (["-c:a", "pcm_s16le"], None),
}

_TIME_RE = re.compile(r"out_time_ms=(\d+)")


class FFmpegNotFoundError(RuntimeError):
    pass


class MediaProbeError(RuntimeError):
    pass


class VideoBuildError(RuntimeError):
    pass


@dataclass
class ToolStatus:
    ffmpeg: str
    ffprobe: str
    ffmpeg_ok: bool
    ffprobe_ok: bool
    ffmpeg_version: str = ""


def _run_capture(cmd: list[str]) -> subprocess.CompletedProcess:
    kwargs: dict = {"capture_output": True, "text": True}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(cmd, **kwargs)


def _popen(cmd: list[str]) -> subprocess.Popen:
    kwargs: dict = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT,
                    "text": True, "bufsize": 1, "universal_newlines": True}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(cmd, **kwargs)


def _bundled_bin(name: str) -> str | None:
    """ffmpeg/ffprobe shipped inside the PyInstaller exe (extracted to sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return None
    candidate = Path(base) / f"{name}.exe"
    return str(candidate) if candidate.exists() else None


def ffmpeg_bin() -> str:
    """Preferred ffmpeg binary: bundled in exe builds, else PATH."""
    return _bundled_bin("ffmpeg") or "ffmpeg"


def ffprobe_bin() -> str:
    """Preferred ffprobe binary: bundled in exe builds, else PATH."""
    return _bundled_bin("ffprobe") or "ffprobe"


def find_system_font() -> str:
    candidates = []
    if os.name == "nt":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        candidates += [
            str(Path(windir) / "Fonts" / "arial.ttf"),
            str(Path(windir) / "Fonts" / "DejaVuSans.ttf"),
            str(Path(windir) / "Fonts" / "calibri.ttf"),
        ]
    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return ""


def escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'\"'\\'")
        .replace("\n", "\\n")
        .replace("%", "\\%")
    )


class FFmpegService:
    """All media operations. No GUI dependencies."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"
        self.ffprobe_path = ffprobe_path or "ffprobe"
        self._proc: Optional[subprocess.Popen] = None
        self._cancel = threading.Event()
        self._lock = threading.Lock()

    # ---------- detection ----------
    def resolve(self, name: str) -> str:
        p = self.ffmpeg_path if name == "ffmpeg" else self.ffprobe_path
        if Path(p).exists():
            return str(Path(p))
        if getattr(sys, "frozen", False):
            # Inside the exe: prefer the bundled binary over anything on PATH
            # (version-matched with the release).
            bundled = _bundled_bin(name)
            if bundled:
                return bundled
        found = shutil.which(p) or shutil.which(name)
        return found or p

    def status(self) -> ToolStatus:
        ff = self.resolve("ffmpeg")
        fp = self.resolve("ffprobe")
        ff_ok = self._check_tool(ff, ["-version"])
        fp_ok = self._check_tool(fp, ["-version"])
        ver = ""
        if ff_ok:
            try:
                r = _run_capture([ff, "-version"])
                ver = (r.stdout or "").splitlines()[0][:120] if r.stdout else ""
            except Exception:
                ver = ""
        return ToolStatus(ffmpeg=ff, ffprobe=fp, ffmpeg_ok=ff_ok, ffprobe_ok=fp_ok, ffmpeg_version=ver)

    def _check_tool(self, exe: str, args: list[str]) -> bool:
        try:
            r = _run_capture([exe, *args])
            return r.returncode == 0
        except FileNotFoundError:
            return False
        except Exception as exc:
            log.warning("Error checking %s: %s", exe, exc)
            return False

    def require_tools(self) -> ToolStatus:
        st = self.status()
        if not st.ffmpeg_ok and not st.ffprobe_ok:
            raise FFmpegNotFoundError(
                "FFmpeg and FFprobe were not found.\n"
                "Install FFmpeg https://www.gyan.dev/ffmpeg/builds/ or 'winget install Gyan.FFmpeg') "
                "and make sure they are on the PATH, or set the path in Settings."
            )
        if not st.ffmpeg_ok:
            raise FFmpegNotFoundError("FFmpeg not found. Check the path in Settings.")
        if not st.ffprobe_ok:
            raise FFmpegNotFoundError("FFprobe not found (it ships with FFmpeg). Check the path in Settings.")
        return st

    # ---------- probe ----------
    def probe(self, path: str | Path) -> dict:
        fp = self.resolve("ffprobe")
        cmd = [fp, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)]
        try:
            r = _run_capture(cmd)
        except FileNotFoundError as exc:
            raise FFmpegNotFoundError(f"FFprobe not found ({fp}).") from exc
        if r.returncode != 0:
            raise MediaProbeError(f"FFprobe could not read the file.\n{(r.stderr or '')[:800]}")
        try:
            return json.loads(r.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise MediaProbeError(f"Invalid FFprobe response: {exc}") from exc

    def get_audio_info(self, path: str | Path) -> AudioInfo:
        p = Path(str(path))
        if not p.exists():
            raise MediaProbeError(f"Audio does not exist: {p}")
        data = self.probe(p)
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        audio = next((s for s in streams if s.get("codec_type") == "audio"), streams[0] if streams else {})
        try:
            duration = float(fmt.get("duration") or audio.get("duration") or 0.0)
        except (TypeError, ValueError):
            duration = 0.0
        try:
            sr = int(audio.get("sample_rate") or 0)
        except (TypeError, ValueError):
            sr = 0
        try:
            br = int((fmt.get("bit_rate") or audio.get("bit_rate") or 0))
        except (TypeError, ValueError):
            br = 0
        try:
            ch = int(audio.get("channels") or 0)
        except (TypeError, ValueError):
            ch = 0
        return AudioInfo(
            path=str(p),
            duration=duration,
            format_name=str(fmt.get("format_name") or ""),
            codec=str(audio.get("codec_name") or ""),
            sample_rate=sr,
            channels=ch,
            bit_rate=br,
            size_bytes=p.stat().st_size,
        )

    def get_image_info(self, path: str | Path) -> ImageInfo:
        p = Path(str(path))
        if not p.exists():
            raise MediaProbeError(f"Image does not exist: {p}")
        data = self.probe(p)
        streams = data.get("streams", [])
        video = next((s for s in streams if s.get("codec_type") == "video"), streams[0] if streams else {})
        return ImageInfo(
            path=str(p),
            width=int(video.get("width") or 0),
            height=int(video.get("height") or 0),
            format_name=str(video.get("codec_name") or p.suffix.lstrip(".").lower()),
            size_bytes=p.stat().st_size,
        )

    def validate_audio(self, path: str | Path) -> AudioInfo:
        info = self.get_audio_info(path)
        if info.duration <= 0:
            raise MediaProbeError("Audio looks corrupt or has no detectable duration (duration = 0).")
        return info

    def validate_image(self, path: str | Path) -> ImageInfo:
        info = self.get_image_info(path)
        if not info.width or not info.height:
            raise MediaProbeError("Image looks corrupt (no detectable resolution).")
        return info

    # ---------- filter construction ----------
    def build_video_filter(self, vs: VideoSettings, ov: OverlaySettings) -> str:
        """Return a filter_complex with input [0:v] and output [vout].

        The artwork (fg) is always center-cropped to a 1:1 square before
        scaling: ``crop='min(iw,ih)':'min(iw,ih)'`` (x/y default to center).
        The blurred background uses the full image to fill 16:9.
        """
        W, H = vs.width, vs.height
        bg = (vs.background_color or "000000").lstrip("#")
        if len(bg) != 6:
            bg = "000000"

        # Centered square crop (center is ffmpeg's crop default).
        square = "crop='min(iw,ih)':'min(iw,ih)'"

        if vs.blurred_background:
            # Full-screen blurred background + centered square artwork.
            chain = (
                f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},gblur=sigma=40[bg];"
                f"[0:v]{square},scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p"
            )
        elif vs.fit_mode in ("cover", "crop"):
            chain = (
                f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},setsar=1,format=yuv420p"
            )
        elif vs.fit_mode in ("fit", "letterbox"):
            chain = (
                f"[0:v]{square},scale={W}:{H}:force_original_aspect_ratio=decrease,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#{bg},setsar=1,format=yuv420p"
            )
        else:
            chain = f"[0:v]scale={W}:{H},setsar=1,format=yuv420p"

        if ov and ov.enabled and (ov.text or "").strip():
            font = ov.font_path or find_system_font()
            x, y = self._overlay_xy(ov.position, ov.margin)
            alpha = max(0.0, min(1.0, ov.opacity))
            safe = escape_drawtext(ov.text.strip())
            dt = (
                f"drawtext=text='{safe}':fontsize={max(12, ov.font_size)}"
                f":fontcolor=white@{alpha:.2f}:borderw=2:bordercolor=black@{min(1.0, alpha + 0.1):.2f}"
                f":x={x}:y={y}:line_spacing=8"
            )
            if font:
                # Windows path with \: -> escape for ffmpeg.
                f_esc = font.replace("\\", "/").replace(":", "\\:")
                dt += f":fontfile='{f_esc}'"
            chain += "," + dt
        # fps at the end, then the output label
        chain += f",fps={max(1, vs.fps)}[vout]"
        return chain

    @staticmethod
    def _overlay_xy(position: str, margin: int) -> tuple[str, str]:
        m = max(0, int(margin))
        pos = (position or "bottom-center").lower()
        mapping = {
            "top-left": (f"{m}", f"{m}"),
            "top-center": ("(w-text_w)/2", f"{m}"),
            "top-right": (f"w-text_w-{m}", f"{m}"),
            "center": ("(w-text_w)/2", "(h-text_h)/2"),
            "bottom-left": (f"{m}", f"h-text_h-{m}"),
            "bottom-center": ("(w-text_w)/2", f"h-text_h-{m}"),
            "bottom-right": (f"w-text_w-{m}", f"h-text_h-{m}"),
        }
        return mapping.get(pos, mapping["bottom-center"])

    def build_command(
        self,
        image_path: str | Path,
        audio_path: str | Path,
        output_path: str | Path,
        vs: VideoSettings,
        ov: OverlaySettings,
        duration: float,
    ) -> list[str]:
        ff = self.resolve("ffmpeg")
        vf = self.build_video_filter(vs, ov)
        audio_args, default_br = _AUDIO_CODEC_MAP.get(vs.audio_format, _AUDIO_CODEC_MAP["aac"])
        abr = vs.audio_bitrate or default_br
        cmd = [
            ff, "-y", "-v", "warning", "-progress", "pipe:1", "-nostats",
            "-loop", "1", "-framerate", str(max(1, vs.fps)), "-i", str(image_path),
            "-i", str(audio_path),
            "-filter_complex", vf,
            "-map", "[vout]", "-map", "1:a:0?",
            "-c:v", "libx264", "-preset", vs.preset or "medium",
            "-crf", "18", "-pix_fmt", "yuv420p",
            "-r", str(max(1, vs.fps)),
            "-shortest", "-t", f"{max(0.5, duration):.3f}",
            "-movflags", "+faststart",
        ]
        cmd += audio_args
        # Bitrate only applies to compressed codecs (not PCM/WAV).
        if abr and vs.audio_format in ("aac", "mp3", "opus"):
            cmd += [abr]
        if vs.audio_format in ("aac", "mp3", "opus"):
            cmd += ["-ar", "48000"]
        cmd += ["-max_interleave_delta", "200M", str(output_path)]
        return cmd

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

        out = Path(str(output_path))
        out.parent.mkdir(parents=True, exist_ok=True)
        # Rough free-space check: duration * 1.5 MB/s + 20 MB margin.
        need = int(total * 1.5 * 1024 * 1024) + 20 * 1024 * 1024
        from app.utils.files import has_space_for
        if not has_space_for(out.parent, need):
            raise VideoBuildError("Not enough disk space in the output folder.")

        cmd = self.build_command(image_path, audio_path, out, vs, ov, total)
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
                m = _TIME_RE.search(line or "")
                if m and on_progress:
                    try:
                        out_s = int(m.group(1)) / 1_000_000.0
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
            # Verify final duration (container tolerance).
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

    def _terminate(self, proc: subprocess.Popen) -> None:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception as exc:
            log.warning("Error terminating FFmpeg: %s", exc)
