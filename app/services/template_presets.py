"""Legacy alias: the implementation lives in app.templates.presets."""
from app.templates.presets import (
    DEFAULT_PRESETS,
    PresetManager,
    TemplatePresetsManager,
    create_default_presets,
    ensure_default_presets,
)

__all__ = [
    "DEFAULT_PRESETS",
    "PresetManager",
    "TemplatePresetsManager",
    "create_default_presets",
    "ensure_default_presets",
]

if __name__ == "__main__":
    ensure_default_presets()
