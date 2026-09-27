"""Historial + autosave (mixin). Extraído de queue_history (Fase 3)."""
from __future__ import annotations

import logging
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox, QTableWidgetItem

if TYPE_CHECKING:
    from app.ui.mixins.protocol import MainWindowProtocol as _MixinBase
else:
    _MixinBase = object

log = logging.getLogger(__name__)

_UPLOADED_STATUS = ("Uploaded", "Scheduled")


def paint_history_row(win, row: int, entry, link_id: int | None) -> None:
    """Pinta una fila del historial (usado por refresh total y parcial)."""
    from PySide6.QtGui import QColor

    status = f"✓ {entry.status}" if entry.status in _UPLOADED_STATUS else (entry.status or "")
    vals = [entry.created_at, entry.beat_name, entry.channel_title or entry.channel_id,
            entry.video_id, entry.video_url, status]
    for c, v in enumerate(vals):
        item = QTableWidgetItem(str(v or ""))
        if entry.status in _UPLOADED_STATUS:
            item.setBackground(QColor("#33363B"))
        elif entry.id == link_id:
            item.setBackground(QColor("#3a2f1a"))
            item.setForeground(QColor("#F5A623"))
        win.tbl_hist.setItem(row, c, item)


class HistoryMixin(_MixinBase):  # type: ignore[misc]
    _UPLOADED_STATUS = _UPLOADED_STATUS

    # ================= history autosave (B+C) =================
    def _wire_history_autosave(self):
        for w in (self.ed_beat, self.ed_title, self.ed_tags):
            w.textChanged.connect(lambda _t: self._mark_history_dirty())
        self.ed_desc.textChanged.connect(lambda: self._mark_history_dirty())
        self.cb_cat.currentIndexChanged.connect(lambda _i: self._mark_history_dirty())
        self.cb_privacy.currentTextChanged.connect(lambda _t: self._mark_history_dirty())
        self.sp_trim_start.valueChanged.connect(lambda _v: self._mark_history_dirty())
        self.sp_trim_end.valueChanged.connect(lambda _v: self._mark_history_dirty())
        self.tbl_hist.itemSelectionChanged.connect(self._on_history_selection_changed)

    def _mark_history_dirty(self):
        if self._history_link_id is None:
            return
        self._history_dirty = True
        self._history_save_timer.start(800)

    def _set_history_link(self, entry_id: int | None) -> None:
        self._history_save_timer.stop()
        self._history_link_id = entry_id
        self._history_dirty = False
        self._refresh_history_table()
        if entry_id is not None:
            self._set_status(f"Editing history #{entry_id} (auto-save on).")

    def _flush_history_link(self) -> None:
        """Persist pending form edits to the linked entry (no-op when clean)."""
        if self._history_link_id is None or not self._history_dirty:
            return
        try:
            entries = self.history.list(200)
        except Exception as exc:
            log.warning("History autosave: %s", exc)
            return
        entry = next((e for e in entries if e.id == self._history_link_id), None)
        if entry is None:
            self._set_history_link(None)
            return
        self._write_form_to_history_entry(entry)
        try:
            self.history.update(entry)
        except Exception as exc:
            log.warning("History autosave: %s", exc)
            return
        self._history_dirty = False
        self._refresh_history_row(entry)
        self._set_status(f"History #{entry.id} saved.")

    def _rotate_history_link(self, new_id: int | None) -> None:
        current = self.ed_audio.text().strip()
        if current and current == (getattr(self, "_last_gen_audio", "") or ""):
            self._flush_history_link()
        self._set_history_link(new_id)

    def _write_form_to_history_entry(self, entry) -> None:
        entry.beat_name = self.ed_beat.text().strip() or entry.beat_name
        entry.audio_path = self.ed_audio.text().strip() or entry.audio_path
        if self.current_video and Path(self.current_video).exists():
            entry.video_path = self.current_video
        entry.title = self.ed_title.text().strip()
        entry.description = self.ed_desc.toPlainText()
        entry.tags = self.ed_tags.text().strip()
        entry.category_id = str(self.cb_cat.currentData() or "10")
        entry.privacy = self.cb_privacy.currentText()
        entry.trim_start = float(self.sp_trim_start.value())
        entry.trim_end = float(self.sp_trim_end.value())

    def _refresh_history_row(self, entry) -> None:
        """Update one row in place (no full rebuild, selection preserved)."""
        try:
            entries = self.history.list(200)
        except Exception:
            return
        rows = {e.id: r for r, e in enumerate(entries)}
        r = rows.get(entry.id)
        if r is None or r >= self.tbl_hist.rowCount():
            self._refresh_history_table()
            return
        paint_history_row(self, r, entry, self._history_link_id)

    def _on_history_selection_changed(self):
        if self._history_link_id is not None and self._history_dirty:
            self._flush_history_link()

    # ================= history table =================
    def _refresh_history_table(self):
        try:
            entries = self.history.list(200)
        except Exception as exc:
            log.warning("History: %s", exc)
            return
        self.tbl_hist.setRowCount(len(entries))
        for r, e in enumerate(entries):
            paint_history_row(self, r, e, self._history_link_id)

    def _history_open_selected(self):
        rows = {i.row() for i in self.tbl_hist.selectedItems()}
        if not rows:
            return
        r = sorted(rows)[0]
        item = self.tbl_hist.item(r, 4)
        url = item.text().strip() if item else ""
        if url:
            webbrowser.open(url)

    def _history_update_selected(self):
        """Overwrite the selected entry with the current form values."""
        rows = {i.row() for i in self.tbl_hist.selectedItems()}
        if not rows:
            QMessageBox.information(self, "History", "Select a history row first.")
            return
        try:
            entries = self.history.list(200)
        except Exception as exc:
            QMessageBox.warning(self, "History", f"Could not read history.\n{exc}")
            return
        r = sorted(rows)[0]
        if not 0 <= r < len(entries):
            return
        e = entries[r]
        self._write_form_to_history_entry(e)
        try:
            self.history.update(e)
        except Exception as exc:
            QMessageBox.warning(self, "History", f"Could not update entry.\n{exc}")
            return
        self._history_dirty = False
        self._set_history_link(e.id)
        self._set_status(f"History entry updated: {e.beat_name or e.title}")

    def _history_load_selected(self):
        """Restore a history entry into the form, ready to upload."""
        rows = {i.row() for i in self.tbl_hist.selectedItems()}
        if not rows:
            QMessageBox.information(self, "History", "Select a history row first.")
            return
        try:
            entries = self.history.list(200)
        except Exception as exc:
            QMessageBox.warning(self, "History", f"Could not read history.\n{exc}")
            return
        r = sorted(rows)[0]
        if not 0 <= r < len(entries):
            return
        e = entries[r]
        if e.video_path and not Path(e.video_path).exists():
            QMessageBox.warning(self, "History",
                                f"Video file no longer exists:\n{e.video_path}")
            return
        if e.beat_name:
            self.ed_beat.setText(e.beat_name)
        self.ed_title.setText(e.title or "")
        self.ed_desc.setPlainText(e.description or "")
        self.ed_tags.setText(e.tags or "")
        if e.category_id:
            idx = self.cb_cat.findData(e.category_id)
            if idx >= 0:
                self.cb_cat.setCurrentIndex(idx)
        if e.privacy in ("private", "unlisted", "public") and not self.ck_schedule.isChecked():
            self.cb_privacy.setCurrentText(e.privacy)
        self.sp_trim_start.setValue(float(e.trim_start or 0.0))
        self.sp_trim_end.setValue(float(e.trim_end or 0.0))
        self._update_trim_range()
        if e.video_path:
            self.current_video = e.video_path
        self._set_history_link(e.id)
        self._show_view(0)
        self._set_status(f"Loaded from history: {e.beat_name or e.title or e.video_path}")

    def _history_clear(self):
        ret = QMessageBox.question(self, "History", "Clear all local history?")
        if ret == QMessageBox.Yes:
            self.history.clear()
            self._set_history_link(None)
