"""Tests for bundled vs PATH ffmpeg/ffprobe resolution (no real binaries needed)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from app.ffmpeg.ffmpeg_service import (
    FFmpegService,
    _bundled_bin,
    ffmpeg_bin,
    ffprobe_bin,
)


def test_bins_fall_back_to_names(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert ffmpeg_bin() == "ffmpeg"
    assert ffprobe_bin() == "ffprobe"
    assert _bundled_bin("ffmpeg") is None


def test_bins_use_bundled_dir(tmp_path: Path, monkeypatch):
    (tmp_path / "ffmpeg.exe").write_bytes(b"x")
    (tmp_path / "ffprobe.exe").write_bytes(b"x")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert ffmpeg_bin() == str(tmp_path / "ffmpeg.exe")
    assert ffprobe_bin() == str(tmp_path / "ffprobe.exe")


def test_bins_ignore_empty_bundle_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert ffmpeg_bin() == "ffmpeg"
    assert _bundled_bin("ffmpeg") is None


def test_resolve_prefers_explicit_settings_path(tmp_path: Path, monkeypatch):
    custom = tmp_path / "my-ffmpeg.exe"
    custom.write_bytes(b"x")
    (tmp_path / "ffmpeg.exe").write_bytes(b"x")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    svc = FFmpegService(ffmpeg_path=str(custom), ffprobe_path="ffprobe")
    assert svc.resolve("ffmpeg") == str(custom)


def test_resolve_uses_bundled_when_frozen(tmp_path: Path, monkeypatch):
    (tmp_path / "ffmpeg.exe").write_bytes(b"x")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(shutil, "which", lambda *a, **k: None)
    svc = FFmpegService()
    assert svc.resolve("ffmpeg") == str(tmp_path / "ffmpeg.exe")


def test_resolve_falls_back_to_name_without_bundle(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(shutil, "which", lambda *a, **k: None)
    svc = FFmpegService()
    assert svc.resolve("ffmpeg") == "ffmpeg"
    assert svc.resolve("ffprobe") == "ffprobe"
