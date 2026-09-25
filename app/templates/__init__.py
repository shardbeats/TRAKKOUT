"""Sistema de plantillas {{variable}}: motor, tags, presets y compatibilidad."""
from app.templates.compat import render_template, template_values
from app.templates.engine import TemplateEngine
from app.templates.presets import (
    DEFAULT_PRESETS,
    DEFAULT_TEMPLATE,
    PresetManager,
    TemplatePresetsManager,
    create_default_presets,
    ensure_default_presets,
)
from app.templates.tags import parse_tags
from app.templates.variables import BASE_VARIABLES, TemplateVariable

__all__ = [
    "BASE_VARIABLES",
    "DEFAULT_PRESETS",
    "DEFAULT_TEMPLATE",
    "PresetManager",
    "TemplateEngine",
    "TemplatePresetsManager",
    "TemplateVariable",
    "create_default_presets",
    "ensure_default_presets",
    "parse_tags",
    "render_template",
    "template_values",
]
