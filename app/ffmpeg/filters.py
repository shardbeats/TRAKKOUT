"""Construcción de filtros drawtext/scale/pad (Fase 4). Sin GUI ni procesos."""
from __future__ import annotations

import os
from pathlib import Path

from app.models.models import OverlaySettings, VideoSettings


def find_system_font() -> str:
    candidates = []
    if os.name == "nt":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        candidates += [
            str(Path(windir) / "Fonts" / "arial.ttf"),
            str(Path(windir) / "Fonts" / "DejaVuSans.ttf"),
            str(Path(windir) / "Fonts" / "calibri.ttf"),
        ]
    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return ""


def escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'\"'\\'")
        .replace("\n", "\\n")
        .replace("%", "\\%")
    )


def overlay_xy(position: str, margin: int) -> tuple[str, str]:
    m = max(0, int(margin))
    pos = (position or "bottom-center").lower()
    mapping = {
        "top-left": (f"{m}", f"{m}"),
        "top-center": ("(w-text_w)/2", f"{m}"),
        "top-right": (f"w-text_w-{m}", f"{m}"),
        "center": ("(w-text_w)/2", "(h-text_h)/2"),
        "bottom-left": (f"{m}", f"h-text_h-{m}"),
        "bottom-center": ("(w-text_w)/2", f"h-text_h-{m}"),
        "bottom-right": (f"w-text_w-{m}", f"h-text_h-{m}"),
    }
    return mapping.get(pos, mapping["bottom-center"])


def build_video_filter(vs: VideoSettings, ov: OverlaySettings) -> str:
    """filter_complex con entrada [0:v] y salida [vout]."""
    W, H = vs.width, vs.height
    bg = (vs.background_color or "000000").lstrip("#")
    if len(bg) != 6:
        bg = "000000"

    square = "crop='min(iw,ih)':'min(iw,ih)'"

    if vs.blurred_background:
        chain = (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},gblur=sigma=40[bg];"
            f"[0:v]{square},scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p"
        )
    elif vs.fit_mode in ("cover", "crop"):
        chain = (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},setsar=1,format=yuv420p"
        )
    elif vs.fit_mode in ("fit", "letterbox"):
        chain = (
            f"[0:v]{square},scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#{bg},setsar=1,format=yuv420p"
        )
    else:
        chain = f"[0:v]scale={W}:{H},setsar=1,format=yuv420p"

    if ov and ov.enabled and (ov.text or "").strip():
        font = ov.font_path or find_system_font()
        x, y = overlay_xy(ov.position, ov.margin)
        alpha = max(0.0, min(1.0, ov.opacity))
        safe = escape_drawtext(ov.text.strip())
        dt = (
            f"drawtext=text='{safe}':fontsize={max(12, ov.font_size)}"
            f":fontcolor=white@{alpha:.2f}:borderw=2:bordercolor=black@{min(1.0, alpha + 0.1):.2f}"
            f":x={x}:y={y}:line_spacing=8"
        )
        if font:
            f_esc = font.replace("\\", "/").replace(":", "\\:")
            dt += f":fontfile='{f_esc}'"
        chain += "," + dt
    chain += f",fps={max(1, vs.fps)}[vout]"
    return chain
