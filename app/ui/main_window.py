"""TRAKKOUT main window (PySide6).

Thin shell: __init__ + _build_ui (delegado a app/ui/views/*).
Logic lives in app/ui/mixins/*.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QMainWindow

if TYPE_CHECKING:
    from app.ui.workers import FFmpegWorker, UploadWorker

from app.config.settings import SettingsStore
from app.ffmpeg.ffmpeg_service import FFmpegService
from app.models.models import BeatMetadata, ChannelInfo
from app.services.video_generator import VideoGenerator
from app.services.history_store import HistoryStore
from app.services.queue_manager import QueueManager
from app.templates import PresetManager, TemplateEngine
from app.ui.mixins import (
    CollectorsMixin, FeedbackMixin, GenerateUploadMixin, MediaMixin,
    QueueHistoryMixin, SessionMixin, TemplatesMixin, YouTubeAuthMixin,
)
from app.ui.views.youtube_section import YOUTUBE_CATEGORIES
from app.youtube.auth import GoogleAuth
from app.youtube.youtube_service import YouTubeService

__all__ = ["MainWindow", "YOUTUBE_CATEGORIES"]


# ---------------------------------------------------------------- main window


class MainWindow(MediaMixin, CollectorsMixin, TemplatesMixin, YouTubeAuthMixin,
                   GenerateUploadMixin, QueueHistoryMixin, SessionMixin, FeedbackMixin, QMainWindow):
    def __init__(self, project_root: Path, store: SettingsStore) -> None:
        super().__init__()
        self.project_root = project_root
        self.store = store
        self.settings = store.settings
        self.ffmpeg = FFmpegService(store.settings.ffmpeg_path, store.settings.ffprobe_path)
        self.video_gen = VideoGenerator(self.ffmpeg)
        self.engine = TemplateEngine()
        self.presets = PresetManager()
        self.auth = GoogleAuth(store.client_secrets_path(), store.token_path())
        self.yt = YouTubeService(self.auth)
        self.history = HistoryStore(store.db_path())
        self.queue = QueueManager(store.db_path())
        self.beat = BeatMetadata()
        self.channels: list[ChannelInfo] = []
        self.current_video: str = ""
        self._last_publish_at: str = ""
        self.audio_info = None
        self.image_info = None

        self.ffmpeg_worker: FFmpegWorker | None = None
        self.upload_worker: UploadWorker | None = None
        self.batch_worker: QThread | None = None
        self.waveform_worker: QThread | None = None
        self._op_start = 0.0
        self._op_total = 0.0
        self._last_trim: tuple[float, float] = (0.0, 0.0)
        self._trim_audio_path = ""
        self._wave_audio_path = ""
        self._last_gen_audio = ""
        # Beat session: el audio define la sesión (ver SessionMixin).
        self._session_audio = ""
        self._fresh_cover = False
        # History autosave (B+C): link = entry being edited, dirty = pending
        # keystrokes, timer = debounce before flushing to SQLite.
        self._history_link_id: int | None = None
        self._history_dirty = False
        self._history_save_timer = QTimer(self)
        self._history_save_timer.setSingleShot(True)
        self._history_save_timer.setInterval(800)
        self._history_save_timer.timeout.connect(self._flush_history_link)

        self.setWindowTitle("TRAKKOUT")
        self.resize(1180, 820)
        self.setMinimumSize(1000, 700)
        self.setAcceptDrops(True)
        self._build_ui()
        self.lbl_cover_prev.setAcceptDrops(True)
        self._load_settings_to_ui()
        self._refresh_history_table()
        restored = [i for i in self.queue.all() if i.status in ("Pending", "Failed", "Ready")]
        self._refresh_queue_table()
        if restored:
            # After _startup_checks overwrites the status line.
            QTimer.singleShot(600, lambda n=len(restored): self._set_status(
                f"Queue restored: {n} item(s) recovered."))
        QTimer.singleShot(400, self._startup_checks)

    # ================= UI =================

    def _build_ui(self):
        from app.ui.views import build_all
        build_all(self)

    def closeEvent(self, event):  # noqa: N802
        try:
            self._flush_history_link()
        except Exception:
            pass
        self._persist_ui_to_settings()
        try:
            if self.ffmpeg_worker and self.ffmpeg_worker.isRunning():
                self.ffmpeg_worker.cancel()
                self.ffmpeg_worker.wait(3000)
        except Exception:
            pass
        try:
            if self.waveform_worker and self.waveform_worker.isRunning():
                self.waveform_worker.wait(3000)
        except Exception:
            pass
        super().closeEvent(event)
