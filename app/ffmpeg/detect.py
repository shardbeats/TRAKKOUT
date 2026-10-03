"""Detección de binarios ffmpeg/ffprobe (Fase 4). Sin GUI."""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


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


def _bundled_tool_dirs() -> list[Path]:
    """Dirs searched BEFORE PATH when frozen (installer puts FFmpeg here).

    Layout created by installer/installer.iss:
        TRAKKOUT.exe
        ffmpeg\\ffmpeg.exe + ffprobe.exe
    Also accepts the tools directly next to the exe or in bin\\.
    """
    if not (getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")):
        return []
    try:
        exe_dir = Path(sys.executable).resolve().parent
    except Exception:
        return []
    return [exe_dir, exe_dir / "ffmpeg", exe_dir / "bin"]


def resolve_tool(name: str, ffmpeg_path: str, ffprobe_path: str) -> str:
    p = ffmpeg_path if name == "ffmpeg" else ffprobe_path
    if p and Path(p).exists():
        return str(Path(p))
    # Frozen portable/installer: prefer the FFmpeg shipped with the app so
    # inexpert users need nothing on PATH and no Settings tweak.
    exe_name = name + (".exe" if os.name == "nt" else "")
    for d in _bundled_tool_dirs():
        candidate = d / exe_name
        try:
            if candidate.is_file():
                return str(candidate)
        except OSError:
            continue
    found = shutil.which(p) or shutil.which(name)
    return found or p


def check_tool(exe: str, args: list[str]) -> bool:
    try:
        r = _run_capture([exe, *args])
        return r.returncode == 0
    except FileNotFoundError:
        return False
    except Exception as exc:
        log.warning("Error checking %s: %s", exe, exc)
        return False


def query_status(ffmpeg_path: str, ffprobe_path: str) -> ToolStatus:
    ff = resolve_tool("ffmpeg", ffmpeg_path, ffprobe_path)
    fp = resolve_tool("ffprobe", ffmpeg_path, ffprobe_path)
    ff_ok = check_tool(ff, ["-version"])
    fp_ok = check_tool(fp, ["-version"])
    ver = ""
    if ff_ok:
        try:
            r = _run_capture([ff, "-version"])
            ver = (r.stdout or "").splitlines()[0][:120] if r.stdout else ""
        except Exception:
            ver = ""
    return ToolStatus(ffmpeg=ff, ffprobe=fp, ffmpeg_ok=ff_ok,
                      ffprobe_ok=fp_ok, ffmpeg_version=ver)


def require_tools(ffmpeg_path: str, ffprobe_path: str) -> ToolStatus:
    from app.ffmpeg.errors import FFmpegNotFoundError

    st = query_status(ffmpeg_path, ffprobe_path)
    frozen = bool(getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"))
    hint = ("Reinstala TRAKKOUT con el instalador oficial (incluye FFmpeg)."
            if frozen else
            "Install FFmpeg https://www.gyan.dev/ffmpeg/builds/ or 'winget install Gyan.FFmpeg') "
            "and make sure they are on the PATH, or set the path in Settings.")
    if not st.ffmpeg_ok and not st.ffprobe_ok:
        raise FFmpegNotFoundError(
            "FFmpeg and FFprobe were not found.\n" + hint
        )
    if not st.ffmpeg_ok:
        raise FFmpegNotFoundError("FFmpeg not found. Check the path in Settings.")
    if not st.ffprobe_ok:
        raise FFmpegNotFoundError("FFprobe not found (it ships with FFmpeg). Check the path in Settings.")
    return st
