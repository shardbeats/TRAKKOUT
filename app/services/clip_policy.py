"""Política de Shorts en un solo lugar (Fase 5).

Antes el límite de 3 min y los mensajes de aviso estaban duplicados
en generate_upload (single) y queue/batch (bulk). Aquí vive la regla;
los mixins solo muestran el diálogo.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.models import VideoSettings

#: Shorts auto-classification limit: vertical videos up to 3 min.
SHORTS_MAX_SECONDS = 180


def exceeds_shorts_limit(clip_seconds: float,
                         limit: float = SHORTS_MAX_SECONDS) -> bool:
    return (clip_seconds or 0.0) > limit


def vertical_exceeds_shorts(vs: VideoSettings, clip_seconds: float) -> bool:
    """True si es vertical y supera el límite (se publicará como normal)."""
    return bool(getattr(vs, "is_vertical", False)) and exceeds_shorts_limit(clip_seconds)


def single_shorts_warning(clip_seconds: float) -> str | None:
    """Mensaje para generación individual, o None si no aplica."""
    if exceeds_shorts_limit(clip_seconds):
        return (
            "This video is vertical but longer than 3 minutes, so YouTube will "
            "treat it as a regular video, not a Short.\n\nGeneration continues anyway."
        )
    return None


def bulk_shorts_warning(names: list[str]) -> str | None:
    """Mensaje para lote, o None si no hay excedidos."""
    if not names:
        return None
    shown = "\n".join(names[:8])
    return (
        f"{len(names)} vertical video(s) exceed 3 minutes and will publish "
        f"as regular videos, not Shorts:\n{shown}"
    )
