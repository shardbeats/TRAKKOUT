"""Tests for tag parsing, compat API and preset storage."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.templates.compat import render_template, template_values
from app.templates.presets import PresetManager, ensure_default_presets
from app.templates.tags import parse_tags


def test_parse_tags_splits_and_dedupes():
    assert parse_tags("trap, drill; boombap\ntrap, #dark") == [
        "trap",
        "drill",
        "boombap",
        "dark",
    ]


def test_parse_tags_renders_variables_first():
    assert parse_tags("{{genre}}, type beat", {"genre": "Trap"}) == ["Trap", "type beat"]


def test_parse_tags_caps_at_30():
    tags = parse_tags(",".join(f"t{i}" for i in range(50)))
    assert len(tags) == 30


def test_compat_render_template_unknown_intact():
    assert render_template("{{title}} {{nope}}", {"title": "Wolf"}) == "Wolf {{nope}}"


def test_template_values_defaults_and_extra():
    vals = template_values(beat_name="Wolf", producer="DK", license_url="https://x", contact="ig")
    assert vals["title"] == "Wolf"
    assert vals["beat_name"] == "Wolf"
    assert vals["purchase_url"] == "https://x"
    assert vals["bpm"] == ""
    assert template_values(extra_key="v")["extra_key"] == "v"


def test_preset_manager_crud(tmp_path: Path):
    manager = PresetManager(tmp_path)
    path = manager.save_preset("My Preset", "T {{title}}", "D {{bpm}}", "trap, {{title}}")
    assert path.exists()

    loaded = manager.get_preset("My Preset")
    assert loaded["title"] == "T {{title}}"
    assert loaded["tags"] == "trap, {{title}}"
    assert manager.list_presets() == ["My Preset"]
    assert manager.delete_preset("My Preset") is True
    assert manager.delete_preset("My Preset") is False


def test_preset_manager_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        PresetManager(tmp_path).get_preset("missing")


def test_preset_list_skips_invalid_json(tmp_path: Path):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    assert PresetManager(tmp_path).list_presets() == []


def test_ensure_default_presets_creates_missing(tmp_path: Path):
    manager = PresetManager(tmp_path)
    ensure_default_presets(manager)
    assert "Free Standard" in manager.list_presets()
    # Second call must not fail or duplicate.
    ensure_default_presets(manager)
    assert "Free Standard" in manager.list_presets()
