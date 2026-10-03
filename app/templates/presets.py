"""Template presets stored as JSON in app/templates/../resources.

Preset format: {name, title, description, tags, ...}.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"))


def _bundled_templates_dir() -> Path:
    """Read-only dir with the presets shipped inside the exe/source tree."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "app" / "resources" / "templates"
    return Path(__file__).resolve().parent.parent / "resources" / "templates"


def _default_dir() -> Path:
    # Frozen: presets must live in a writable folder (APPDATA), never in
    # _MEIPASS (temp, read-only, deleted on exit). Seed it once from the
    # bundled defaults so a fresh install keeps working offline.
    if _is_frozen():
        if os.name == "nt":
            base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
            d = Path(base) / "TRAKKOUT" / "presets"
        else:
            d = Path.home() / ".trakkout" / "presets"
        try:
            d.mkdir(parents=True, exist_ok=True)
            bundled = _bundled_templates_dir()
            if bundled.is_dir() and not any(d.glob("*.json")):
                import shutil

                for src in bundled.glob("*.json"):
                    try:
                        shutil.copy2(src, d / src.name)
                    except OSError:
                        pass
        except OSError:
            pass
        return d
    d = Path(__file__).resolve().parent.parent / "resources" / "templates"
    d.mkdir(parents=True, exist_ok=True)
    return d


DEFAULT_PRESETS: dict[str, dict[str, str]] = {
    "Free Standard": {
        "name": "Free Standard",
        "title_template": "[FREE] {{artist}} x {{artist2}} {{genre}} Type Beat - \"{{title}}\" | BoomBap",
        "description_template": """💰📥 Compra/Descarga este beat:
{{purchase_url}}

❌ PROHIBIDO distribuir/comercializar la obra hecha con este beat sin comprar una licencia. 🎹 Beats nuevos todas las semanas

🎚️ BPM: {{bpm}}
🎵 Key: {{key}}

INSTRUMENTAL DE USO LIBRE PARA FINES NO LUCRATIVOS, NO MONETIZAR NI REGISTRAR EN PLATAFORMAS DIGITALES, SI USAS ESTA PISTA FAVOR DE DAR CRÉDITOS EN LA DESCRIPCIÓN O TITULO DE TU VIDEO.

👤 IG: @{{producer}}""",
        "tags_template": "{{genre}}, {{title}}, {{artist}}, type beat, boombap, instrumental, free beat, @{{producer}}",
    },
}

#: Default template for settings.json when none is stored.
DEFAULT_TEMPLATE: dict[str, str] = {
    "name": "FREE Beat",
    "title": "[FREE] {{title}}",
    "description": (
        "FREE FOR NON PROFIT ONLY\n\n"
        "📥 Purchase Link: {{purchase_url}}\n\n"
        "🎚️ BPM: {{bpm}}\n"
        "🎵 Key: {{key}}\n\n"
        "👤 IG: @producer"
    ),
    "tags": "{{genre}}, type beat, {{artist}} type beat, {{key}}, {{bpm}} bpm",
    "category": "10",
    "privacy": "private",
}


def _sanitize_preset_name(preset_name: str) -> str:
    """Reject names that could escape the presets dir (../, separators...).

    Only the local user could type these into their own dialog (self-attack),
    but rejecting them costs nothing and keeps list/get/save/delete coherent.
    """
    name = (preset_name or "").strip()
    if not name or name in (".", ".."):
        raise ValueError("Preset name is required.")
    if any(sep in preset_name for sep in ("/", "\\", ":", "*", "?", '"', "<", ">", "|")):
        raise ValueError(f"Invalid preset name: {preset_name!r}")
    if preset_name != name or preset_name.startswith("."):
        raise ValueError(f"Invalid preset name: {preset_name!r}")
    return name


class PresetManager:
    """CRUD for template presets in JSON files."""

    def __init__(self, presets_dir: str | Path | None = None) -> None:
        self._dir = Path(presets_dir) if presets_dir else _default_dir()

    def preset_path(self, preset_name: str) -> Path:
        return self._dir / f"{_sanitize_preset_name(preset_name)}.json"

    def _read_json(self, path: Path) -> dict[str, Any]:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_preset(self, preset_name: str, title_template: str,
                    description_template: str, tags_template: str = "") -> Path:
        """Save (or overwrite) a preset. Return its path."""
        path = self.preset_path(preset_name)
        self._write_json(path, {
            "name": preset_name,
            "title": title_template,
            "description": description_template,
            "tags": tags_template,
        })
        return path

    # Legacy alias.
    save_preset_to_file = save_preset

    def get_preset(self, preset_name: str) -> dict[str, Any]:
        """Load a preset. Raise FileNotFoundError when missing."""
        path = self.preset_path(preset_name)
        if not path.exists():
            raise FileNotFoundError(f"Preset not found: {preset_name}")
        return self._read_json(path)

    def list_presets(self) -> list[str]:
        """Names of presets with valid JSON, sorted."""
        out: list[str] = []
        for path in self._dir.glob("*.json"):
            try:
                out.append(self._read_json(path).get("name", path.stem))
            except (json.JSONDecodeError, OSError):
                continue
        return sorted(out)

    def delete_preset(self, preset_name: str) -> bool:
        path = self.preset_path(preset_name)
        if path.exists():
            path.unlink()
            return True
        return False

    # Legacy alias.
    load_presets_from_file = _read_json


# Legacy class alias.
TemplatePresetsManager = PresetManager


def ensure_default_presets(manager: PresetManager | None = None) -> None:
    """Create any missing default presets on disk."""
    manager = manager or PresetManager()
    for preset_key, preset_data in DEFAULT_PRESETS.items():
        if not manager.preset_path(preset_key).exists():
            log.info("Creating preset: %s", preset_data["name"])
            manager.save_preset(
                preset_data["name"],
                preset_data["title_template"],
                preset_data["description_template"],
                preset_data.get("tags_template", ""),
            )


# Legacy alias.
create_default_presets = ensure_default_presets


if __name__ == "__main__":
    ensure_default_presets()
