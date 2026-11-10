"""Bundled FFmpeg resolution.

The one-file portable extracts the binaries to ``sys._MEIPASS`` at launch,
while the installer/sidecar layout keeps them in an ``ffmpeg\\`` folder next
to the exe. ``detect`` must search both before falling back to PATH.
"""
from __future__ import annotations

import sys
from pathlib import Path

from app.ffmpeg import detect


def _exe_name() -> str:
    return "ffmpeg.exe" if detect.os.name == "nt" else "ffmpeg"


def test_not_frozen_has_no_bundled_dirs(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert detect._bundled_tool_dirs() == []


def test_meipass_is_searched_when_frozen(tmp_path, monkeypatch):
    mei = tmp_path / "_MEI123"
    mei.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(mei), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "TRAKKOUT.exe"))

    dirs = detect._bundled_tool_dirs()
    assert mei in dirs
    assert (tmp_path / "ffmpeg") in dirs  # installer/sidecar layout still wins


def test_resolve_tool_prefers_bundled_copy(tmp_path, monkeypatch):
    mei = tmp_path / "_MEI123"
    mei.mkdir()
    bundled = mei / _exe_name()
    bundled.write_bytes(b"stub")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(mei), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "TRAKKOUT.exe"))
    monkeypatch.setattr(detect.shutil, "which", lambda *a, **k: None)

    assert Path(detect.resolve_tool("ffmpeg", "", "")) == bundled


def test_explicit_settings_path_still_wins(tmp_path, monkeypatch):
    custom = tmp_path / "custom" / _exe_name()
    custom.parent.mkdir()
    custom.write_bytes(b"stub")
    monkeypatch.setattr(detect.shutil, "which", lambda *a, **k: None)

    assert Path(detect.resolve_tool("ffmpeg", str(custom), "")) == custom
