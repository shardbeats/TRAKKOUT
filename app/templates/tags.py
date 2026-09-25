"""Comma-separated tag parsing (with prior variable rendering)."""
from __future__ import annotations

import re


def parse_tags(tags_str: str, values: dict | None = None) -> list[str]:
    from app.templates.compat import render_template
    raw = render_template(tags_str or "", values or {})
    out: list[str] = []
    for part in re.split(r"[,;\n]+", raw):
        tag = part.strip().strip("#")
        if tag and tag not in out:
            out.append(tag)
    return out[:30]
