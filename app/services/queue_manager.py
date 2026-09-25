"""Beat queue (batch processing), persisted in SQLite for crash recovery.

Every mutation is saved immediately, so an accidental close or crash loses
nothing. On load, in-flight states go back to Pending (clean retry),
finished Uploaded/Scheduled items are dropped (history keeps the record),
and Ready items whose video file is gone become Failed.
"""
from __future__ import annotations

import itertools
import logging
import sqlite3
from dataclasses import asdict
from pathlib import Path

from app.models.models import QueueItem

log = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY,
    beat_name TEXT DEFAULT '',
    audio_path TEXT DEFAULT '',
    artwork_path TEXT DEFAULT '',
    title TEXT DEFAULT '',
    description TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    category_id TEXT DEFAULT '10',
    privacy TEXT DEFAULT 'private',
    channel_id TEXT DEFAULT '',
    publish_at TEXT DEFAULT '',
    video_path TEXT DEFAULT '',
    status TEXT DEFAULT 'Pending',
    error TEXT DEFAULT ''
);
"""

_COLUMNS = ("id", "beat_name", "audio_path", "artwork_path", "title",
            "description", "tags", "category_id", "privacy", "channel_id",
            "publish_at", "video_path", "status", "error")

# Terminal states live in history; the queue only keeps actionable items.
_DROP_ON_LOAD = ("Uploaded", "Scheduled")
# In-flight states cannot resume after a restart: clean retry.
_RETRY_ON_LOAD = ("Generating", "Uploading")


class QueueManager:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self._items: list[QueueItem] = []
        self._ids = itertools.count(1)
        self._db = Path(db_path) if db_path else None
        if self._db is not None:
            self.load()

    # ---------- persistence ----------
    def _connect(self) -> sqlite3.Connection:
        assert self._db is not None
        self._db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db))
        conn.row_factory = sqlite3.Row
        return conn

    def _save(self) -> None:
        if self._db is None:
            return
        try:
            with self._connect() as conn:
                conn.execute(_SCHEMA)
                conn.execute("DELETE FROM queue")
                for it in self._items:
                    conn.execute(
                        "INSERT INTO queue (id, beat_name, audio_path, artwork_path, title,"
                        " description, tags, category_id, privacy, channel_id, publish_at,"
                        " video_path, status, error) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        tuple(getattr(it, c) or "" if c != "id" else it.id for c in _COLUMNS),
                    )
                conn.commit()
        except Exception as exc:
            log.warning("Could not persist queue: %s", exc)

    def load(self) -> list[QueueItem]:
        """Load persisted items, normalizing states after a restart."""
        if self._db is None:
            return []
        try:
            with self._connect() as conn:
                conn.execute(_SCHEMA)
                rows = conn.execute("SELECT * FROM queue ORDER BY id").fetchall()
        except Exception as exc:
            log.warning("Could not load queue: %s", exc)
            return []
        items: list[QueueItem] = []
        for r in rows:
            d = dict(r)
            try:
                item = QueueItem(**{c: d.get(c, "") for c in _COLUMNS})
            except TypeError:
                continue
            if item.status in _DROP_ON_LOAD:
                continue
            if item.status in _RETRY_ON_LOAD:
                item.status = "Pending"  # type: ignore[assignment]
                item.error = ""
            if item.status == "Ready" and not Path(item.video_path or "").exists():
                item.status = "Failed"  # type: ignore[assignment]
                item.error = "Video file missing after restart."
            items.append(item)
        self._items = items
        if items:
            self._ids = itertools.count(max(i.id for i in items) + 1)
        self._save()  # persist the normalized states
        return list(items)

    # ---------- queue ops (every mutation persists) ----------
    def add(self, item: QueueItem) -> QueueItem:
        if not item.id:
            item.id = next(self._ids)
        self._items.append(item)
        self._save()
        return item

    def remove(self, item_id: int) -> None:
        self._items = [i for i in self._items if i.id != item_id]
        self._save()

    def clear(self) -> None:
        self._items.clear()
        self._save()

    def all(self) -> list[QueueItem]:
        return list(self._items)

    def get(self, item_id: int) -> QueueItem | None:
        for i in self._items:
            if i.id == item_id:
                return i
        return None

    def set_status(self, item_id: int, status: str, error: str = "", video_path: str = "") -> None:
        it = self.get(item_id)
        if it is None:
            return
        it.status = status  # type: ignore[assignment]
        if error:
            it.error = error
        if video_path:
            it.video_path = video_path
        self._save()
