"""Tests for SQLite stores and settings (tmp databases only)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config.settings import AppSettings, SettingsStore
from app.models.models import HistoryEntry, QueueItem
from app.services.history_store import HistoryStore
from app.services.queue_manager import QueueManager


def test_history_add_list_update_clear(tmp_path: Path):
    store = HistoryStore(tmp_path / "history.db")
    row_id = store.add(HistoryEntry(beat_name="Wolf", status="Uploaded", video_id="abc"))
    assert row_id > 0

    items = store.list()
    assert len(items) == 1
    assert items[0].beat_name == "Wolf"
    assert items[0].video_id == "abc"

    items[0].status = "Scheduled"
    store.update(items[0])
    assert store.list()[0].status == "Scheduled"

    store.clear()
    assert store.list() == []


def test_history_migrates_old_schema(tmp_path: Path):
    db = tmp_path / "old.db"
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            "CREATE TABLE history (id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " created_at TEXT NOT NULL, beat_name TEXT DEFAULT '')"
        )
        conn.execute("INSERT INTO history (created_at, beat_name) VALUES ('2026-01-01', 'Old')")
        conn.commit()

    store = HistoryStore(db)
    items = store.list()
    assert len(items) == 1
    assert items[0].beat_name == "Old"
    # New columns exist with defaults.
    assert items[0].title == ""
    assert items[0].category_id == "10"


def test_queue_memory_crud():
    queue = QueueManager()
    item = queue.add(QueueItem(beat_name="Wolf"))
    assert item.id == 1
    assert queue.get(1) is not None

    queue.set_status(1, "Ready", video_path="v.mp4")
    assert queue.get(1).status == "Ready"

    queue.remove(1)
    assert queue.all() == []

    queue.add(QueueItem(beat_name="A"))
    queue.clear()
    assert queue.all() == []


def test_queue_persistence_normalizes_states(tmp_path: Path):
    db = tmp_path / "queue.db"
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x")

    queue = QueueManager(db)
    queue.add(QueueItem(beat_name="inflight", status="Generating"))
    queue.add(QueueItem(beat_name="done", status="Uploaded"))
    queue.add(QueueItem(beat_name="ready-ok", status="Ready", video_path=str(video)))
    queue.add(QueueItem(beat_name="ready-missing", status="Ready", video_path=str(tmp_path / "gone.mp4")))

    reloaded = QueueManager(db)
    by_name = {item.beat_name: item for item in reloaded.all()}

    assert "done" not in by_name  # terminal states are dropped
    assert by_name["inflight"].status == "Pending"
    assert by_name["ready-ok"].status == "Ready"
    assert by_name["ready-missing"].status == "Failed"


def test_settings_roundtrip_and_unknown_keys_ignored(tmp_path: Path):
    config = tmp_path / "settings.json"
    store = SettingsStore(config_path=config)
    settings = store.load()
    assert settings.ffmpeg_path == "ffmpeg"
    assert settings.templates

    settings.ffmpeg_path = "C:\\ffmpeg\\bin\\ffmpeg.exe"
    store.settings = settings
    store.save()

    reloaded = SettingsStore(config_path=config).load()
    assert reloaded.ffmpeg_path == "C:\\ffmpeg\\bin\\ffmpeg.exe"


def test_app_settings_from_dict_filters_unknown():
    settings = AppSettings.from_dict({"ffmpeg_path": "ff", "unknown_key": 123})
    assert settings.ffmpeg_path == "ff"
    assert not hasattr(settings, "unknown_key")
    assert AppSettings.from_dict({}).templates
