"""File utilities (sizes, Windows paths, disk space)."""
from __future__ import annotations

import shutil
from pathlib import Path


AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".opus", ".aac", ".wma", ".aiff", ".aif", ".alac"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def human_size(num_bytes: int | float) -> str:
    n = float(num_bytes or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024.0
    return f"{n:.1f} PB"


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def has_space_for(path: str | Path, needed_bytes: int) -> bool:
    try:
        anchor = Path(path)
        if anchor.suffix or not anchor.exists():
            anchor = anchor.parent if anchor.suffix else anchor
        anchor.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(str(anchor)).free
        return free > needed_bytes
    except OSError:
        return False


def is_audio_file(path: str | Path) -> bool:
    return Path(str(path)).suffix.lower() in AUDIO_EXTS


def is_image_file(path: str | Path) -> bool:
    return Path(str(path)).suffix.lower() in IMAGE_EXTS


def safe_stem(name: str) -> str:
    bad = '<>:"/\\|?*'
    out = "".join(c if c not in bad else "_" for c in (name or "unnamed"))
    return out.strip().rstrip(".") or "unnamed"
