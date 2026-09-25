"""{{...}} variables available in templates."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TemplateVariable:
    name: str
    description: str = ""
    default: str = ""
    aliases: tuple[str, ...] = ()


BASE_VARIABLES: tuple[TemplateVariable, ...] = (
    TemplateVariable("title", "Beat title", "", ("beat_name",)),
    TemplateVariable("artist", "Target artist of the type beat"),
    TemplateVariable("artist2", "Second artist of the type beat"),
    TemplateVariable("producer", "Producer name"),
    TemplateVariable("genre", "Genre (Trap, Drill, …)"),
    TemplateVariable("bpm", "Tempo in BPM"),
    TemplateVariable("key", "Key (e.g. F# min)"),
    TemplateVariable("purchase_url", "Purchase/license link", "", ("license_url",)),
    TemplateVariable("tags", "Comma-separated tags"),
    TemplateVariable("description", "Base beat description"),
    TemplateVariable("contact", "Contact"),
    TemplateVariable("date", "Current date (YYYY-MM-DD)"),
    TemplateVariable("channel", "Selected YouTube channel name"),
)
