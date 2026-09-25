"""Tests for the {{variable}} template engine."""
from __future__ import annotations

import pytest

from app.models.models import BeatMetadata
from app.templates.engine import TemplateEngine


def test_render_double_brace_and_unknown_stays():
    engine = TemplateEngine()
    out = engine.render("[FREE] {{title}} {{unknown}}", {"title": "Wolf"})
    assert out == "[FREE] Wolf {{unknown}}"


def test_render_legacy_single_brace():
    engine = TemplateEngine()
    assert engine.render("{title}!", {"title": "Wolf"}) == "Wolf!"


def test_render_legacy_unknown_stays_intact():
    engine = TemplateEngine()
    assert engine.render("{nope}", {"nope": "x"}) == "{nope}"


def test_render_alias_beat_name_resolves_to_title():
    engine = TemplateEngine()
    assert engine.render("{{beat_name}}", {"title": "Wolf"}) == "Wolf"


def test_render_registered_default_used_when_missing():
    engine = TemplateEngine()
    engine.register_variable("producer", default="@trakkout")
    assert engine.render("by {{producer}}", {}) == "by @trakkout"


def test_register_invalid_name_raises():
    engine = TemplateEngine()
    with pytest.raises(ValueError):
        engine.register_variable("not valid!")


def test_variable_names_sorted():
    engine = TemplateEngine()
    names = engine.variable_names()
    assert names == sorted(names)
    assert "title" in names


def test_extract_variables_unique_sorted_and_alias_resolved():
    engine = TemplateEngine()
    found = engine.extract_variables("{{title}} {title} {{beat_name}} {{title}}")
    assert found == ["title"]


def test_missing_variables_detects_only_valueless():
    engine = TemplateEngine()
    assert engine.missing_variables("{{title}} {{bpm}}", {"title": "Wolf"}) == ["bpm"]
    assert engine.missing_variables("", {}) == []


def test_context_from_beat_handles_list_and_string_tags():
    engine = TemplateEngine()
    ctx = engine.context_from_beat(BeatMetadata(title="Wolf", tags=["a", "b"]))
    assert ctx["title"] == "Wolf"
    assert ctx["tags"] == "a, b"
    assert ctx["date"]

    ctx2 = engine.context_from_beat(BeatMetadata(tags="a; b, c"))
    assert ctx2["tags"] == "a, b, c"


def test_context_extra_overrides():
    engine = TemplateEngine()
    ctx = engine.context_from_beat(BeatMetadata(), {"channel": "My Channel"})
    assert ctx["channel"] == "My Channel"
