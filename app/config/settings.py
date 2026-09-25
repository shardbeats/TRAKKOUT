"""Persistent configuration (JSON) + paths. No secrets in this file."""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.templates.presets import DEFAULT_TEMPLATE

log = logging.getLogger(__name__)


def app_data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "TRAKKOUT"
    return Path.home() / ".trakkout"


def legacy_data_dirs() -> list[Path]:
    """Pre-rebrand data locations (one-time migration source)."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return [Path(base) / "Beat2YouTube"]
    return [Path.home() / ".beat2youtube"]


def _migrate_legacy_data() -> None:
    """Copy settings/token/history from the old Beat2YouTube folder once."""
    new_dir = app_data_dir()
    if any((new_dir / f).exists() for f in ("settings.json", "token.json", "history.db")):
        return
    for old in legacy_data_dirs():
        if not old.is_dir():
            continue
        try:
            new_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            for f in ("settings.json", "token.json", "history.db"):
                src = old / f
                if src.exists() and not (new_dir / f).exists():
                    shutil.copy2(src, new_dir / f)
            log.info("Migrated data from %s", old)
        except OSError as exc:
            log.warning("Could not migrate legacy data: %s", exc)
        break


def default_output_dir() -> Path:
    return Path.home() / "Videos" / "TRAKKOUT"


@dataclass
class AppSettings:
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    output_dir: str = str(default_output_dir())
    resolution: str = "1920x1080"
    fit_mode: str = "cover"          # cover | fit | crop | letterbox
    blurred_background: bool = True
    background_color: str = "000000"
    fps: int = 30
    video_preset: str = "medium"
    audio_format: str = "aac"        # aac | mp3 | opus | wav
    audio_bitrate: str = "192k"
    overlay_enabled: bool = False
    overlay_text: str = "{{title}}\nProd. by {{producer}}"
    overlay_position: str = "bottom-center"
    overlay_font_size: int = 48
    overlay_opacity: float = 0.9
    overlay_margin: int = 60
    overlay_font: str = ""
    default_privacy: str = "private"
    default_category: str = "10"
    made_for_kids: bool = False
    last_channel_id: str = ""
    templates: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        clean = {k: v for k, v in (data or {}).items() if k in known}
        obj = cls(**clean)
        if not obj.templates:
            obj.templates = [dict(DEFAULT_TEMPLATE)]
        return obj


class SettingsStore:
    """Load/save settings.json in app_data_dir. Never store tokens here."""

    def __init__(self, config_path: Path | None = None) -> None:
        if config_path is None:
            _migrate_legacy_data()
        self.config_path = config_path or (app_data_dir() / "settings.json")
        self.settings = AppSettings()

    def load(self) -> AppSettings:
        try:
            if self.config_path.exists():
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                self.settings = AppSettings.from_dict(data)
        except Exception as exc:
            log.warning("Could not read configuration (%s). Using defaults.", exc)
            self.settings = AppSettings()
        if not self.settings.templates:
            self.settings.templates = [dict(DEFAULT_TEMPLATE)]
        return self.settings

    def save(self) -> None:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.config_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.settings.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.config_path)
        except Exception as exc:
            log.error("Could not save configuration: %s", exc)
            raise

    # Credential/token paths (kept separate from settings.json)
    def client_secrets_path(self) -> Path:
        return app_data_dir() / "client_secrets.json"

    def token_path(self) -> Path:
        return app_data_dir() / "token.json"

    def db_path(self) -> Path:
        return app_data_dir() / "history.db"
