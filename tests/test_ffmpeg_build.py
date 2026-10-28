"""Tests for ffmpeg command construction with clip seeking (no binaries run)."""
from __future__ import annotations

from pathlib import Path

from app.ffmpeg.ffmpeg_service import FFmpegService
from app.ffmpeg.render import vbv_caps
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


def test_build_command_caps_peak_bitrate():
    cmd = _cmd()
    assert "-maxrate" in cmd
    assert "-bufsize" in cmd
    # Buffers are sized at 2x maxrate so peaks stay smooth.
    maxrate = cmd[cmd.index("-maxrate") + 1]
    bufsize = cmd[cmd.index("-bufsize") + 1]
    assert int(maxrate.rstrip("M")) * 2 == int(bufsize.rstrip("M"))


def test_vbv_caps_follow_resolution_tiers():
    assert vbv_caps(VideoSettings(width=1920, height=1080, fps=30)) == ("12M", "24M")
    assert vbv_caps(VideoSettings(width=1920, height=1080, fps=60)) == ("20M", "40M")
    assert vbv_caps(VideoSettings(width=1280, height=720, fps=30)) == ("8M", "16M")
    assert vbv_caps(VideoSettings(width=854, height=480, fps=30)) == ("5M", "10M")
