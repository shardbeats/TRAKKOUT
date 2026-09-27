"""Errores de FFmpeg (Fase 4). Punto único de definición."""
from __future__ import annotations


class FFmpegNotFoundError(RuntimeError):
    pass


class MediaProbeError(RuntimeError):
    pass


class VideoBuildError(RuntimeError):
    pass
