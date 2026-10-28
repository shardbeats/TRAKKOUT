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


def vbv_caps(vs: VideoSettings) -> tuple[str, str]:
    """Peak bitrate ceiling (maxrate/bufsize) for the output resolution.

    CRF alone has no upper bound: noisy animated artwork (e.g. a dithered
    GIF upscaled to 1080p) can push x264 past 30 Mbps, turning a normal
    song into a ~1 GB file. The VBV cap only bites on those peaks;
    typical content keeps its CRF quality untouched. Tiers follow the
    YouTube upload recommendations for SDR (8 Mbps at 1080p30).
    """
    height = max(1, int(vs.height or 1080))
    if height >= 1080:
        maxrate, bufsize = ("20M", "40M") if vs.fps > 30 else ("12M", "24M")
    elif height >= 720:
        maxrate, bufsize = ("10M", "20M") if vs.fps > 30 else ("8M", "16M")
    else:
        maxrate, bufsize = ("6M", "12M") if vs.fps > 30 else ("5M", "10M")
    return maxrate, bufsize


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
    is_animated: bool = False,
) -> list[str]:
    """Build the ffmpeg command for a still or an animated artwork input.

    Still artwork is looped as a single image (``-loop 1``). Animated
    artwork (GIF/MP4) is looped at the input level (``-stream_loop -1``)
    so short loops stretch to the full audio length; ``-shortest`` cuts
    the output at the audio clip length either way.
    """
    vf = build_video_filter(vs, ov)
    audio_args, default_br = AUDIO_CODEC_MAP.get(vs.audio_format, AUDIO_CODEC_MAP["aac"])
    abr = vs.audio_bitrate or default_br
    maxrate, bufsize = vbv_caps(vs)
    cmd = [
        ff_exe, "-y", "-nostdin", "-v", "warning", "-progress", "pipe:1", "-nostats",
    ]
    if is_animated:
        cmd += ["-stream_loop", "-1", "-i", str(image_path)]
    else:
        cmd += ["-loop", "1", "-framerate", str(max(1, vs.fps)), "-i", str(image_path)]
    if start > 0:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += [
        "-i", str(audio_path),
        "-filter_complex", vf,
        "-map", "[vout]", "-map", "1:a:0?",
        "-c:v", "libx264", "-preset", vs.preset or "medium",
        "-crf", "18", "-maxrate", maxrate, "-bufsize", bufsize,
        "-pix_fmt", "yuv420p",
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
