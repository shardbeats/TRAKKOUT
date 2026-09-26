"""Tests for ffmpeg command construction with clip seeking (no binaries run)."""
from __future__ import annotations

from pathlib import Path

from app.ffmpeg.ffmpeg_service import FFmpegService
from app.models.models import OverlaySettings, VideoSettings


def _cmd(**kwargs) -> list[str]:
    svc = FFmpegService()
    vs = VideoSettings()
    ov = OverlaySettings()
    return svc.build_command(Path("cover.jpg"), Path("beat.mp3"),
                             Path("out.mp4"), vs, ov, kwargs.pop("duration", 120.0),
                             **kwargs)


def test_build_command_no_seek_by_default():
    cmd = _cmd()
    assert "-ss" not in cmd
    assert "-t" in cmd
    assert cmd[cmd.index("-t") + 1] == "120.000"


def test_build_command_seeks_before_audio_input():
    cmd = _cmd(start=12.5)
    assert "-ss" in cmd
    assert cmd[cmd.index("-ss") + 1] == "12.500"
    # Seek applies to the audio input: it must come after the image input
    # and before the audio input.
    image_idx = cmd.index("cover.jpg")
    audio_idx = cmd.index("beat.mp3")
    assert image_idx < cmd.index("-ss") < audio_idx


def test_build_command_zero_start_omits_seek():
    assert "-ss" not in _cmd(start=0.0)
    assert "-ss" not in _cmd(start=-3.0)
