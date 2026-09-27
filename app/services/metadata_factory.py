"""Construcción de BeatMetadata/YouTubeMetadata desde campos planos (Fase 5).

Los mixins siguen leyendo los widgets (collectors), pero la fusión
 Campos + beat vinculado + canal vive aquí y es testeable sin Qt.
"""
from __future__ import annotations

from pathlib import Path


def beat_title_or_stem(explicit_title: str, audio_path: str, fallback: str = "") -> str:
    title = (explicit_title or "").strip()
    if title:
        return title
    if (audio_path or "").strip():
        return Path(audio_path.strip()).stem
    return fallback


def split_tags(raw: str) -> list[str]:
    return [t.strip() for t in (raw or "").replace(";", ",").split(",") if t.strip()]


def build_beat_kwargs(fields: dict, linked_beat=None) -> dict:
    """Fusión campos del formulario + beat vinculado. No importa Qt."""
    lb = linked_beat
    title = beat_title_or_stem(
        fields.get("title", ""), fields.get("audio_path", ""),
        getattr(lb, "title", "") if lb else "")
    return {
        "title": title or (getattr(lb, "title", "") if lb else ""),
        "producer": fields.get("producer", "") or (getattr(lb, "producer", "") if lb else ""),
        "artist": fields.get("artist", ""),
        "artist2": fields.get("artist2", ""),
        "genre": fields.get("genre", ""),
        "bpm": fields.get("bpm", ""),
        "key": fields.get("key", ""),
        "purchase_url": fields.get("purchase_url", ""),
        "tags": split_tags(fields.get("tags", "")),
        "description": fields.get("description", ""),
        "artwork_url": getattr(lb, "artwork_url", "") if lb else "",
        "artwork_path": fields.get("artwork_path", ""),
        "audio_path": fields.get("audio_path", ""),
        "preview_audio_url": "",
        "source": getattr(lb, "source", "manual") if lb else "manual",
        "fetched_at": getattr(lb, "fetched_at", "") if lb else "",
    }
