"""Legacy alias: the implementation lives in app.templates.engine."""
from app.templates.engine import *  # noqa: F401,F403
from app.templates.engine import (
    DOUBLE_RE,
    LEGACY_RE,
    TemplateEngine,
)
from app.templates.variables import BASE_VARIABLES, TemplateVariable

__all__ = [
    "BASE_VARIABLES",
    "DOUBLE_RE",
    "LEGACY_RE",
    "TemplateEngine",
    "TemplateVariable",
]
