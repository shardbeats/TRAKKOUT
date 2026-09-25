"""Shared window feedback and navigation (mixin)."""
from __future__ import annotations

import logging

from PySide6.QtWidgets import QDialog, QMessageBox

from app.ffmpeg.ffmpeg_service import FFmpegService
from app.services.video_generator import VideoGenerator
from app.ui.dialogs import SettingsDialog

log = logging.getLogger(__name__)



class FeedbackMixin:
    def _show_view(self, idx: int):
        """Switch between Main / Queue / History / Log."""
        if hasattr(self, "views"):
            self.views.setCurrentIndex(idx)
        for i, act in enumerate(getattr(self, "_view_actions", [])):
            act.setChecked(i == idx)

    def _goto_section(self, sid: str):
        """Sidebar navigation: show Main, expand and scroll to the section."""
        self._show_view(0)
        self.sidebar.set_active(sid)
        sec = self._sections.get(sid)
        if sec is None:
            return
        sec.setExpanded(True)
        self.scroll.ensureWidgetVisible(sec)

    # ================= feedback =================

    def _set_status(self, text: str):
        self.lbl_status.setText(text)
        self.statusBar().showMessage(text[:120])
        log.info(text)

    def _set_progress(self, pct: float, label: str = ""):
        self.progress.setValue(int(max(0, min(100, pct))))
        if label:
            self.lbl_times.setText(label)

    def _set_busy(self, busy: bool):
        for b in (self.btn_generate, self.btn_upload, self.btn_queue_add,
                  self.btn_connect, self.btn_refresh_ch, self.btn_q_gen, self.btn_q_sel,
                  self.btn_q_up):
            b.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)

    @staticmethod
    def _is_token_expired(text: str) -> bool:
        t = str(text or "").lower()
        return "invalid_grant" in t or "expired" in t

    def _show_token_expired(self, detail: str = ""):
        body = f"Google session expired.\n\n{detail}\n\n" if detail else \
            "Your Google session has expired.\n\n"
        QMessageBox.information(self, "Expired token",
                                f"{body}Press 'Connect account' to authorize again.")

    def _log_history(self, entry) -> None:
        try:
            self.history.add(entry)
            self._refresh_history_table()
        except Exception as exc:
            log.warning("Could not save history: %s", exc)

    def _open_settings(self):
        dlg = SettingsDialog(self.store, self)
        if dlg.exec() == QDialog.Accepted:
            dlg.apply()
            self.settings = self.store.settings
            self.ffmpeg = FFmpegService(self.settings.ffmpeg_path, self.settings.ffprobe_path)
            self.video_gen = VideoGenerator(self.ffmpeg)
            self._load_settings_to_ui()
            self._set_status("Settings saved.")
