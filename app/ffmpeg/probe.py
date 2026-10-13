"""Sondeo y validación de medios (Fase 4). Sin GUI."""
from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

from app.ffmpeg.detect import _run_capture, resolve_tool
from app.ffmpeg.errors import FFmpegNotFoundError, MediaProbeError, VideoBuildError
from app.models.models import AudioInfo, ImageInfo

log = logging.getLogger(__name__)


def probe_data(ffprobe_exe: str, path: str | Path, timeout: float = 25.0) -> dict:
    cmd = [ffprobe_exe, "-v", "quiet", "-print_format", "json",
           "-show_format", "-show_streams", str(path)]
    try:
        r = _run_capture(cmd, timeout=timeout)
    except FileNotFoundError as exc:
        raise FFmpegNotFoundError(f"FFprobe not found ({ffprobe_exe}).") from exc
    except subprocess.TimeoutExpired as exc:
        raise MediaProbeError("FFprobe timed out reading the file.") from exc
    if r.returncode != 0:
        raise MediaProbeError(f"FFprobe could not read the file.\n{(r.stderr or '')[:800]}")
    try:
        return json.loads(r.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise MediaProbeError(f"Invalid FFprobe response: {exc}") from exc


def _to_int(value, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def audio_info(ffprobe_exe: str, path: str | Path) -> AudioInfo:
    p = Path(str(path))
    if not p.exists():
        raise MediaProbeError(f"Audio does not exist: {p}")
    data = probe_data(ffprobe_exe, p)
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    audio = next((s for s in streams if s.get("codec_type") == "audio"),
                 streams[0] if streams else {})
    try:
        duration = float(fmt.get("duration") or audio.get("duration") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    return AudioInfo(
        path=str(p),
        duration=duration,
        format_name=str(fmt.get("format_name") or ""),
        codec=str(audio.get("codec_name") or ""),
        sample_rate=_to_int(audio.get("sample_rate")),
        channels=_to_int(audio.get("channels")),
        bit_rate=_to_int(fmt.get("bit_rate") or audio.get("bit_rate")),
        size_bytes=p.stat().st_size,
    )


def image_info(ffprobe_exe: str, path: str | Path) -> ImageInfo:
    p = Path(str(path))
    if not p.exists():
        raise MediaProbeError(f"Image does not exist: {p}")
    data = probe_data(ffprobe_exe, p)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"),
                 streams[0] if streams else {})
    try:
        width = int(video.get("width") or 0)
    except (TypeError, ValueError):
        width = 0
    try:
        height = int(video.get("height") or 0)
    except (TypeError, ValueError):
        height = 0
    return ImageInfo(
        path=str(p),
        width=width,
        height=height,
        format_name=str(video.get("codec_name") or p.suffix.lstrip(".").lower()),
        size_bytes=p.stat().st_size,
    )


def validate_audio(ffprobe_exe: str, path: str | Path) -> AudioInfo:
    info = audio_info(ffprobe_exe, path)
    if info.duration <= 0:
        raise MediaProbeError("Audio looks corrupt or has no detectable duration (duration = 0).")
    return info


def validate_image(ffprobe_exe: str, path: str | Path) -> ImageInfo:
    info = image_info(ffprobe_exe, path)
    if not info.width or not info.height:
        raise MediaProbeError("Image looks corrupt (no detectable resolution).")
    return info


def waveform_peaks(ffmpeg_exe: str, audio_path: str | Path,
                   buckets: int = 800, timeout: float = 120.0,
                   cancel_event=None,
                   max_input_bytes: int = 250 * 1024 * 1024,
                   max_pcm_bytes: int = 150 * 1024 * 1024) -> list[float]:
    """Peak amplitudes 0..1 decodificando a PCM mono en memoria.

    Bounded: oversized inputs are rejected before decoding (RAM guard),
    the decode is time-bounded AND cancellable, and absurd PCM output
    (decompression bomb) aborts instead of filling RAM.
    """
    from app.ffmpeg.waveform import peaks_from_s16le

    try:
        buckets = int(buckets)
    except (TypeError, ValueError):
        buckets = 800
    buckets = max(8, min(int(buckets), 10000))
    try:
        if Path(str(audio_path)).stat().st_size > max_input_bytes:
            raise VideoBuildError("Audio too large for waveform preview.")
    except OSError as exc:
        raise MediaProbeError(f"Cannot read audio file: {exc}") from exc

    cmd = [ffmpeg_exe, "-v", "error", "-nostdin",
           "-i", str(audio_path),
           "-vn", "-ac", "1", "-ar", "4000", "-f", "s16le",
           "-acodec", "pcm_s16le", "-"]
    kwargs: dict = {"stdout": subprocess.PIPE, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except FileNotFoundError as exc:
        raise FFmpegNotFoundError(f"FFmpeg not found ({cmd[0]}).") from exc
    import time as _time
    deadline = _time.monotonic() + max(1.0, float(timeout))
    try:
        while proc.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
                raise VideoBuildError("Waveform analysis cancelled.")
            if _time.monotonic() > deadline:
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
                raise VideoBuildError("Waveform analysis timed out.")
            try:
                proc.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                continue
        try:
            out, _ = proc.communicate(timeout=10)
        except Exception as exc:
            raise VideoBuildError("Waveform analysis timed out.") from exc
    except (VideoBuildError, FFmpegNotFoundError, MediaProbeError):
        raise
    except Exception as exc:
        try:
            proc.kill()
        except Exception:
            pass
        raise MediaProbeError(f"Could not decode audio for the waveform: {exc}") from exc
    if proc.returncode != 0 or not out:
        raise MediaProbeError("Could not decode audio for the waveform.")
    if len(out) > max_pcm_bytes:
        raise VideoBuildError("Audio too long for waveform preview.")
    return peaks_from_s16le(bytes(out), buckets)
