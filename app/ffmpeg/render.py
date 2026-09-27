"""Construcción del comando ffmpeg + parseo de progreso (Fase 4)."""
from __future__ import annotations

import re
from pathlib import Path

from app.ffmpeg.filters import build_video_filter
from app.models.models import OverlaySettings, VideoSettings

AUDIO_CODEC_MAP = {
    "aac": (["-c:a", "aac", "-b:a"], "192k"),
    "mp3": (["-c:a", "libmp3lame", "-b:a"], "192k"),
    "opus": (["-c:a", "libopus", "-b:a"], "160k"),
    "wav": (["-c:a", "pcm_s16le"], None),
}

TIME_RE = re.compile(r"out_time_ms=(\d+)")


def parse_progress_line(line: str) -> float | None:
    """Segundos renderizados según la línea `-progress pipe:1`, o None."""
    m = TIME_RE.search(line or "")
    if not m:
        return None
    try:
        return int(m.group(1)) / 1_000_000.0
    except (ValueError, TypeError):
        return None


def build_command(
    ff_exe: str,
    image_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    vs: VideoSettings,
    ov: OverlaySettings,
    duration: float,
    start: float = 0.0,
) -> list[str]:
    vf = build_video_filter(vs, ov)
    audio_args, default_br = AUDIO_CODEC_MAP.get(vs.audio_format, AUDIO_CODEC_MAP["aac"])
    abr = vs.audio_bitrate or default_br
    cmd = [
        ff_exe, "-y", "-v", "warning", "-progress", "pipe:1", "-nostats",
        "-loop", "1", "-framerate", str(max(1, vs.fps)), "-i", str(image_path),
    ]
    if start > 0:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += [
        "-i", str(audio_path),
        "-filter_complex", vf,
        "-map", "[vout]", "-map", "1:a:0?",
        "-c:v", "libx264", "-preset", vs.preset or "medium",
        "-crf", "18", "-pix_fmt", "yuv420p",
        "-r", str(max(1, vs.fps)),
        "-shortest", "-t", f"{max(0.05, duration):.3f}",
        "-movflags", "+faststart",
    ]
    cmd += audio_args
    if abr and vs.audio_format in ("aac", "mp3", "opus"):
        cmd += [abr]
    if vs.audio_format in ("aac", "mp3", "opus"):
        cmd += ["-ar", "48000"]
    cmd += ["-max_interleave_delta", "200M", str(output_path)]
    return cmd
