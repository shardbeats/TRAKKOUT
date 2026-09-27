"""BatchCoordinator: lógica de lote fuera de la UI (Fase 3).

Los mixins solo muestran diálogos y actualizan tablas; las decisiones
(faltan ficheros, verticales largos, contadores) viven aquí y son
testeables sin Qt.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from app.ffmpeg.ffmpeg_service import FFmpegService
    from app.models.models import VideoSettings


def missing_files(items: Iterable) -> list[str]:
    """Nombres de items cuyo audio/artwork no existe en disco."""
    bad: list[str] = []
    for i in items:
        audio = getattr(i, "audio_path", "")
        art = getattr(i, "artwork_path", "")
        if not audio or not art or not Path(audio).exists() or not Path(art).exists():
            bad.append(getattr(i, "beat_name", "?"))
    return bad


def long_vertical_names(items: Iterable, ffmpeg: FFmpegService,
                        vs: VideoSettings, limit_seconds: float | None = None) -> list[str]:
    """Items verticales cuyo clip supera el límite de Shorts."""
    from app.models.models import resolve_clip_range
    from app.services.clip_policy import SHORTS_MAX_SECONDS

    if not getattr(vs, "is_vertical", False):
        return []
    limit = SHORTS_MAX_SECONDS if limit_seconds is None else limit_seconds
    out: list[str] = []
    for i in items:
        try:
            dur = ffmpeg.get_audio_info(i.audio_path).duration
        except Exception:
            continue
        _s, _e = resolve_clip_range(
            getattr(i, "trim_start", 0.0), getattr(i, "trim_end", 0.0), dur)
        if _e - _s > limit:
            out.append(i.beat_name)
    return out


def count_scheduled(items: Iterable) -> int:
    return sum(1 for i in items if getattr(i, "publish_at", ""))
