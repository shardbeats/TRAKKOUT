"""Tests for animated artwork support (GIF/MP4 as cover). No Qt, no binaries."""
from __future__ import annotations

from pathlib import Path

from app.ffmpeg import probe as probe_mod
from app.ffmpeg.ffmpeg_service import FFmpegService
from app.models.models import OverlaySettings, VideoSettings
from app.utils.files import (
    is_animated_artwork,
    is_artwork_file,
    is_image_file,
    is_video_artwork,
)
from app.utils.validators import validate_artwork_path, validate_image_path


def test_artwork_predicates_cover_requested_formats():
    assert is_artwork_file("cover.mp4") is True
    assert is_artwork_file("cover.GIF") is True
    assert is_artwork_file("cover.jpg") is True
    assert is_artwork_file("cover.png") is True
    assert is_artwork_file("beat.mp3") is False
    assert is_artwork_file("notes.txt") is False


def test_video_and_animated_predicates():
    assert is_video_artwork("loop.mp4") is True
    assert is_video_artwork("loop.MOV") is True
    assert is_video_artwork("cover.jpg") is False
    assert is_video_artwork("anim.gif") is False
    assert is_animated_artwork("loop.mp4") is True
    assert is_animated_artwork("anim.gif") is True
    assert is_animated_artwork("anim.apng") is True
    assert is_animated_artwork("cover.jpg") is False


def test_still_images_still_count_as_images():
    # Backward compatibility: stills keep passing the legacy predicate.
    assert is_image_file("cover.JPG") is True
    assert is_image_file("cover.png") is True
    assert is_image_file("loop.mp4") is False


def test_validate_artwork_accepts_mp4_and_gif(tmp_path: Path):
    for name in ("cover.mp4", "anim.gif", "cover.jpg"):
        p = tmp_path / name
        p.write_bytes(b"fake-content")
        assert validate_artwork_path(str(p)).ok is True


def test_validate_artwork_rejects_unsupported(tmp_path: Path):
    bad = tmp_path / "notes.txt"
    bad.write_bytes(b"x")
    result = validate_artwork_path(str(bad))
    assert result.ok is False
    assert ".mp4" in result.message
    assert ".gif" in result.message


def test_validate_image_path_stays_backward_compatible(tmp_path: Path):
    mp4 = tmp_path / "loop.mp4"
    mp4.write_bytes(b"fake-content")
    assert validate_image_path(str(mp4)).ok is True
    txt = tmp_path / "notes.txt"
    txt.write_bytes(b"x")
    result = validate_image_path(str(txt))
    assert result.ok is False
    assert "Unsupported image format" in result.message


def _animated_probe(monkeypatch, path: Path, payload: dict):
    monkeypatch.setattr(probe_mod, "probe_data", lambda _exe, _p: payload)
    return probe_mod.image_info("ffprobe", path)


def test_probe_marks_gif_as_animated(tmp_path: Path, monkeypatch):
    p = tmp_path / "anim.gif"
    p.write_bytes(b"GIF89a")
    info = _animated_probe(monkeypatch, p, {
        "format": {},
        "streams": [{"codec_type": "video", "width": 640, "height": 480,
                     "codec_name": "gif", "nb_frames": "24",
                     "avg_frame_rate": "10/1"}],
    })
    assert info.is_animated is True
    assert (info.width, info.height) == (640, 480)


def test_probe_marks_mp4_as_animated(tmp_path: Path, monkeypatch):
    p = tmp_path / "loop.mp4"
    p.write_bytes(b"fake")
    info = _animated_probe(monkeypatch, p, {
        "format": {"duration": "5.000000"},
        "streams": [{"codec_type": "video", "width": 1280, "height": 720,
                     "codec_name": "h264", "avg_frame_rate": "30/1",
                     "duration": "5.000000"}],
    })
    assert info.is_animated is True
    assert info.duration == 5.0


def test_probe_keeps_still_image_not_animated(tmp_path: Path, monkeypatch):
    p = tmp_path / "cover.jpg"
    p.write_bytes(b"fake")
    info = _animated_probe(monkeypatch, p, {
        "format": {},
        "streams": [{"codec_type": "video", "width": 1920, "height": 1080,
                     "codec_name": "mjpeg", "avg_frame_rate": "25/1"}],
    })
    assert info.is_animated is False
    assert info.duration == 0.0


def _build(is_animated: bool) -> list[str]:
    svc = FFmpegService()
    return svc.build_command(Path("cover.mp4"), Path("beat.mp3"), Path("out.mp4"),
                             VideoSettings(), OverlaySettings(),
                             60.0, is_animated=is_animated)


def test_build_command_still_uses_single_image_loop():
    cmd = _build(False)
    assert "-loop" in cmd
    assert "1" in cmd[cmd.index("-loop") + 1]
    assert "-stream_loop" not in cmd


def test_build_command_animated_loops_input():
    cmd = _build(True)
    assert "-stream_loop" in cmd
    assert "-1" in cmd[cmd.index("-stream_loop") + 1]
    assert "-loop" not in cmd
    # Both flavours still cut at the audio clip length.
    assert "-shortest" in cmd
    assert "-t" in cmd
