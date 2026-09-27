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


def probe_data(ffprobe_exe: str, path: str | Path) -> dict:
    cmd = [ffprobe_exe, "-v", "quiet", "-print_format", "json",
           "-show_format", "-show_streams", str(path)]
    try:
        r = _run_capture(cmd)
    except FileNotFoundError as exc:
        raise FFmpegNotFoundError(f"FFprobe not found ({ffprobe_exe}).") from exc
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
    return ImageInfo(
        path=str(p),
        width=int(video.get("width") or 0),
        height=int(video.get("height") or 0),
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
                   buckets: int = 800) -> list[float]:
    """Peak amplitudes 0..1 decodificando a PCM mono en memoria."""
    from app.ffmpeg.waveform import peaks_from_s16le

    cmd = [ffmpeg_exe, "-v", "error", "-i", str(audio_path),
           "-ac", "1", "-ar", "4000", "-f", "s16le",
           "-acodec", "pcm_s16le", "-"]
    kwargs: dict = {"capture_output": True}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(cmd, timeout=120, **kwargs)
    except FileNotFoundError as exc:
        raise FFmpegNotFoundError(f"FFmpeg not found ({cmd[0]}).") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoBuildError("Waveform analysis timed out.") from exc
    if result.returncode != 0 or not result.stdout:
        raise MediaProbeError("Could not decode audio for the waveform.")
    return peaks_from_s16le(bytes(result.stdout), buckets)
