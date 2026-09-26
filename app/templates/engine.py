"""{{variable}} template engine (with legacy {variable} compatibility).

Unknown or valueless variables are left intact so text never breaks.
"""
from __future__ import annotations

import re
from typing import Mapping

from app.templates.variables import BASE_VARIABLES, TemplateVariable

DOUBLE_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
# Legacy {var}, without touching {{...}} leftovers (lookaround).
LEGACY_RE = re.compile(r"(?<!\{)\{([a-zA-Z0-9_]+)\}(?!\})")
_VALID_NAME_RE = re.compile(r"[a-zA-Z0-9_]+")


class TemplateEngine:
    """Standalone, extensible engine. No GUI or network dependencies."""

    def __init__(self, extra: Mapping[str, str] | None = None) -> None:
        self._vars: dict[str, TemplateVariable] = {v.name: v for v in BASE_VARIABLES}
        self._aliases: dict[str, str] = {
            alias: var.name for var in BASE_VARIABLES for alias in var.aliases
        }
        self._extra_defaults: dict[str, str] = dict(extra or {})

    # ---- registry ----
    def register_variable(self, name: str, description: str = "", default: str = "",
                          aliases: tuple[str, ...] = ()) -> None:
        """Add (or replace) a variable available in templates."""
        if not _VALID_NAME_RE.fullmatch(name or ""):
            raise ValueError(f"Invalid variable name: {name!r} (use letters, numbers and _).")
        self._vars[name] = TemplateVariable(name, description, default, tuple(aliases or ()))
        for alias in aliases or ():
            self._aliases[alias] = name

    def variable_names(self) -> list[str]:
        return sorted(self._vars)

    # ---- render ----
    def _lookup(self, key: str, context: Mapping) -> tuple[bool, str]:
        canon = self._aliases.get(key, key)
        var = self._vars.get(canon)
        names = [key] if key == canon else [key, canon]
        if var:
            names += [a for a in var.aliases if a not in names]
        for name in names:
            if name in context and context[name] is not None:
                return True, str(context[name])
        if var and var.default:
            return True, str(var.default)
        if canon in self._extra_defaults:
            return True, str(self._extra_defaults[canon])
        return False, ""

    def render(self, text: str, context: Mapping | None = None) -> str:
        """Replace {{var}} and {var} (legacy). Unknown stays intact."""
        if not text:
            return ""
        ctx = context or {}

        def _rep(m: re.Match) -> str:
            found, val = self._lookup(m.group(1), ctx)
            return val if found else m.group(0)

        out = DOUBLE_RE.sub(_rep, text)

        def _rep_legacy(m: re.Match) -> str:
            key = m.group(1)
            if self._aliases.get(key, key) not in self._vars:
                return m.group(0)
            found, val = self._lookup(key, ctx)
            return val if found else m.group(0)

        return LEGACY_RE.sub(_rep_legacy, out)

    def extract_variables(self, text: str) -> list[str]:
        """Canonical variables used in the text (aliases resolved)."""
        found: list[str] = []
        for rx in (DOUBLE_RE, LEGACY_RE):
            for m in rx.finditer(text or ""):
                canon = self._aliases.get(m.group(1), m.group(1))
                if canon not in found:
                    found.append(canon)
        return sorted(found)

    def missing_variables(self, text: str, context: Mapping | None = None) -> list[str]:
        """Variables in the text with no available value (neither context nor default)."""
        ctx = context or {}
        return sorted(n for n in self.extract_variables(text)
                      if not self._lookup(n, ctx)[0])

    # ---- context from BeatMetadata ----
    def context_from_beat(self, beat, extra: Mapping | None = None) -> dict[str, str]:
        """Build the {{var}} context from a BeatMetadata (duck-typing)."""
        from datetime import date as _date
        raw_tags = getattr(beat, "tags", "")
        if isinstance(raw_tags, (list, tuple)):
            tags = list(raw_tags)
        else:
            tags = [t.strip() for t in str(raw_tags or "").replace(";", ",").split(",") if t.strip()]
        ctx = {
            "title": getattr(beat, "title", "") or "",
            "artist": getattr(beat, "artist", "") or "",
            "artist2": getattr(beat, "artist2", "") or "",
            "producer": getattr(beat, "producer", "") or "",
            "genre": getattr(beat, "genre", "") or "",
            "bpm": str(getattr(beat, "bpm", "") or ""),
            "key": getattr(beat, "key", "") or "",
            "purchase_url": getattr(beat, "purchase_url", "") or "",
            "tags": ", ".join(tags),
            "description": getattr(beat, "description", "") or "",
            "date": _date.today().isoformat(),
            "channel": "",
        }
        if extra:
            ctx.update({k: str(v) for k, v in extra.items()})
        return ctx
