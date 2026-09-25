"""Legacy alias: the implementation lives in app.templates."""
from app.templates.compat import render_template, template_values
from app.templates.tags import parse_tags

__all__ = ["parse_tags", "render_template", "template_values"]
