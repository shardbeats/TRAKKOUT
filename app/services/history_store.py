"""Local history in SQLite (auto-migrates old databases)."""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from app.models.models import HistoryEntry

log = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    beat_name TEXT DEFAULT '',
    audio_path TEXT DEFAULT '',
    video_path TEXT DEFAULT '',
    channel_id TEXT DEFAULT '',
    channel_title TEXT DEFAULT '',
    video_id TEXT DEFAULT '',
    video_url TEXT DEFAULT '',
    privacy TEXT DEFAULT '',
    status TEXT DEFAULT '',
    error TEXT DEFAULT '',
    title TEXT DEFAULT '',
    description TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    category_id TEXT DEFAULT '10'
);
"""


class HistoryStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(_SCHEMA)
            cols = {r[1] for r in conn.execute("PRAGMA table_info(history)").fetchall()}
            for col, default in (("title", "''"), ("description", "''"),
                                 ("tags", "''"), ("category_id", "'10'")):
                if col not in cols:
                    conn.execute(f"ALTER TABLE history ADD COLUMN {col} TEXT DEFAULT {default}")
            conn.commit()

    def add(self, entry: HistoryEntry) -> int:
        entry.created_at = entry.created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO history (created_at, beat_name, audio_path, video_path, "
                "channel_id, channel_title, video_id, video_url, privacy, status, error,"
                " title, description, tags, category_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (entry.created_at, entry.beat_name, entry.audio_path, entry.video_path,
                 entry.channel_id, entry.channel_title, entry.video_id, entry.video_url,
                 entry.privacy, entry.status, entry.error,
                 entry.title, entry.description, entry.tags, entry.category_id),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list(self, limit: int = 200) -> list[HistoryEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM history ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        return [HistoryEntry(**dict(r)) for r in rows]

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM history")
            conn.commit()

    def update(self, entry: HistoryEntry) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE history SET beat_name=?, audio_path=?, video_path=?,"
                " channel_id=?, channel_title=?, video_id=?, video_url=?, privacy=?,"
                " status=?, error=?, title=?, description=?, tags=?, category_id=?"
                " WHERE id=?",
                (entry.beat_name, entry.audio_path, entry.video_path,
                 entry.channel_id, entry.channel_title, entry.video_id, entry.video_url,
                 entry.privacy, entry.status, entry.error,
                 entry.title, entry.description, entry.tags, entry.category_id,
                 entry.id),
            )
            conn.commit()
