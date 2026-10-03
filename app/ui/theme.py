"""Application theme (external QSS so it can be tweaked without touching code)."""
from __future__ import annotations

import sys
from pathlib import Path


def _candidate_paths() -> list[Path]:
    here = Path(__file__).with_name("style.qss")
    cands: list[Path] = [here]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cands.append(Path(meipass) / "app" / "ui" / "style.qss")
        cands.append(Path(meipass) / "app_ui" / "style.qss")
    try:
        cands.append(Path(sys.executable).resolve().parent / "app" / "ui" / "style.qss")
    except Exception:
        pass
    return cands


def load_stylesheet() -> str:
    """Read style.qss next to this module (or from _MEIPASS when frozen)."""
    for qss in _candidate_paths():
        try:
            if qss.is_file():
                return qss.read_text(encoding="utf-8")
        except OSError:
            continue
    return ""


def apply_theme(app) -> None:
    css = load_stylesheet()
    if css:
        app.setStyleSheet(css)
