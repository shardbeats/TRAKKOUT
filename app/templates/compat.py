"""Compatibility with the old template API ({var}).

The real implementation lives in app.templates.engine ({{var}} syntax).
"""
from __future__ import annotations

from app.templates.engine import TemplateEngine

_engine = TemplateEngine()


def render_template(text: str, values: dict) -> str:
    """Replace {{var}} and {var}; unknown stays intact."""
    return _engine.render(text or "", values or {})


def template_values(beat_name="", producer="", genre="", license_url="", contact="", **extra) -> dict:
    from datetime import date
    vals = {
        "title": beat_name or "",
        "beat_name": beat_name or "",
        "producer": producer or "",
        "genre": genre or "",
        "purchase_url": license_url or "",
        "license_url": license_url or "",
        "contact": contact or "",
        "date": date.today().isoformat(),
        "artist": "", "artist2": "", "bpm": "", "key": "",
        "tags": "", "description": "", "channel": "",
    }
    vals.update(extra or {})
    return vals
