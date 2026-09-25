"""Batch queue and history (mixin)."""
from __future__ import annotations

import logging
import webbrowser
from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QTableWidgetItem

from app.models.models import HistoryEntry, QueueItem
from app.ui.workers import BatchGenerateWorker, BatchUploadWorker, vars_for
from app.utils.scheduling import describe_rfc3339_in_tz

log = logging.getLogger(__name__)



class QueueHistoryMixin:
    def _queue_add_current(self):
        audio = self.ed_audio.text().strip()
        cover = self.ed_cover.text().strip()
        if not audio or not cover:
            QMessageBox.warning(self, "Queue", "Select audio and artwork first.")
            return
        meta = self._collect_metadata()
        ch = self._selected_channel()
        _pub, _pub_err = self._collect_publish_at()
        if _pub_err:
            QMessageBox.warning(self, "Queue", f"Invalid schedule.\n{_pub_err}")
            return
        item = QueueItem(
            beat_name=self.ed_beat.text().strip() or Path(audio).stem,
            audio_path=audio, artwork_path=cover,
            title=meta.title or self.ed_beat.text().strip(),
            description=meta.description, tags=self.ed_tags.text(),
            category_id=str(self.cb_cat.currentData() or "10"),
            privacy=self.cb_privacy.currentText(),
            channel_id=ch.channel_id if ch else "",
            publish_at=_pub,
            status="Pending",
        )
        self.queue.add(item)
        self._refresh_queue_table()
        self._set_status(f"Added to queue: {item.beat_name}")

    def _refresh_queue_table(self):
        items = self.queue.all()
        self.tbl_queue.setRowCount(len(items))
        for r, it in enumerate(items):
            ch_title = it.channel_id
            for ch in self.channels:
                if ch.channel_id == it.channel_id:
                    ch_title = ch.title
                    break
            vals = [str(it.id), it.beat_name, it.title, ch_title, it.privacy,
                    describe_rfc3339_in_tz(it.publish_at, self.cb_tz.currentText()) if it.publish_at else "Now",
                    it.status, it.video_path]
            for c, v in enumerate(vals):
                self.tbl_queue.setItem(r, c, QTableWidgetItem(v))

    def _queue_remove_selected(self):
        rows = sorted({i.row() for i in self.tbl_queue.selectedItems()}, reverse=True)
        items = self.queue.all()
        for r in rows:
            if 0 <= r < len(items):
                self.queue.remove(items[r].id)
        self._refresh_queue_table()

    def _on_batch_generate(self):
        items = [i for i in self.queue.all() if i.status in ("Pending", "Failed")]
        if not items:
            QMessageBox.information(self, "Queue", "No pending items.")
            return
        self._start_batch_generate(items)

    def _on_batch_generate_selected(self):
        rows = {i.row() for i in self.tbl_queue.selectedItems()}
        if not rows:
            QMessageBox.information(self, "Queue", "Select at least one row first.")
            return
        all_items = self.queue.all()
        items = [all_items[r] for r in sorted(rows)
                 if 0 <= r < len(all_items) and all_items[r].status in ("Pending", "Failed")]
        if not items:
            QMessageBox.information(self, "Queue", "Selected rows are not pending.")
            return
        self._start_batch_generate(items)

    def _start_batch_generate(self, items: list):
        bad = [i.beat_name for i in items if not Path(i.audio_path).exists() or not Path(i.artwork_path).exists()]
        if bad:
            QMessageBox.warning(self, "Queue", "Missing files in:\n" + "\n".join(bad[:8]))
            return
        vs = self._collect_video_settings()
        ov = self._collect_overlay()
        self._persist_ui_to_settings()
        # Vertical videos over 3 min are not classified as Shorts (warn, don't block).
        if vs.is_vertical:
            from app.ui.mixins.collectors import SHORTS_MAX_SECONDS
            long_names = []
            for i in items:
                try:
                    if self.ffmpeg.get_audio_info(i.audio_path).duration > SHORTS_MAX_SECONDS:
                        long_names.append(i.beat_name)
                except Exception:
                    pass
            if long_names:
                QMessageBox.information(
                    self, "Vertical videos",
                    f"{len(long_names)} vertical video(s) exceed 3 minutes and will publish "
                    "as regular videos, not Shorts:\n" + "\n".join(long_names[:8]))
        self._set_busy(True)
        worker = BatchGenerateWorker(self.video_gen, [vars_for(i) for i in items], vs, ov,
                                     self.settings.output_dir, self)
        worker.item_started.connect(lambda iid: self.queue.set_status(iid, "Generating") or self._refresh_queue_table())
        worker.item_progress.connect(
            lambda iid, pct: (self._set_progress(pct, f"[{self.queue.get(iid).beat_name}] {pct:.0f}%"),
                              self._set_status(f"Generating {self.queue.get(iid).beat_name}… {pct:.0f}%")))
        worker.item_done.connect(self._on_batch_gen_done)
        worker.item_failed.connect(self._on_batch_gen_fail)
        worker.all_done.connect(lambda: (self._set_busy(False), self._refresh_queue_table(),
                                         self._set_status("Batch generated.")))
        self.batch_worker = worker
        worker.start()

    def _on_batch_gen_done(self, iid: int, path: str):
        self.queue.set_status(iid, "Ready", video_path=path)
        it = self.queue.get(iid)
        self._refresh_queue_table()
        self._log_history(HistoryEntry(
            beat_name=it.beat_name if it else "", video_path=path, status="Generated",
            title=it.title if it else "", description=it.description if it else "",
            tags=it.tags if it else "", category_id=it.category_id if it else "10",
            privacy=it.privacy if it else "private"))

    def _on_batch_gen_fail(self, iid: int, msg: str):
        log.error("Error generating video (item %s): %s", iid, msg)
        self.queue.set_status(iid, "Failed", error=msg)
        self._refresh_queue_table()

    def _on_batch_upload(self):
        items = [i for i in self.queue.all() if i.status in ("Ready",) and i.video_path and Path(i.video_path).exists()]
        if not items:
            QMessageBox.information(self, "Queue", "No Ready videos to upload. Generate first.")
            return
        sched_n = sum(1 for i in items if i.publish_at)
        sched_txt = f"\n({sched_n} scheduled for future publishing)" if sched_n else ""
        ret = QMessageBox.question(
            self, "Upload All",
            f"You are about to PUBLISH {len(items)} video(s) to YouTube.{sched_txt}\nConfirm bulk upload?")
        if ret != QMessageBox.Yes:
            return
        if not self.yt.is_connected():
            QMessageBox.warning(self, "Queue", "Connect Google first.")
            return
        self._set_busy(True)
        worker = BatchUploadWorker(self.yt, [vars_for(i) for i in items], self)
        worker.item_started.connect(lambda iid: self.queue.set_status(iid, "Uploading") or self._refresh_queue_table())
        worker.item_progress.connect(
            lambda iid, pct: (self._set_progress(pct, f"Uploading {self.queue.get(iid).beat_name} {pct:.0f}%"),
                              self._set_status(f"Uploading {pct:.0f}%…")))
        worker.item_done.connect(self._on_batch_up_done)
        worker.item_failed.connect(self._on_batch_up_fail)
        worker.all_done.connect(lambda: (self._set_busy(False), self._refresh_queue_table(),
                                         self._refresh_history_table(), self._set_status("Batch uploaded.")))
        self.batch_worker = worker
        worker.start()

    def _on_batch_up_done(self, iid: int, result: dict):
        it = self.queue.get(iid)
        scheduled = bool(it and it.publish_at)
        self.queue.set_status(iid, "Scheduled" if scheduled else "Uploaded")
        self._refresh_queue_table()
        self._log_history(HistoryEntry(
            beat_name=it.beat_name if it else "", video_path=it.video_path if it else "",
            channel_id=result.get("channel_id", ""), channel_title=result.get("channel_title", ""),
            video_id=result.get("video_id", ""), video_url=result.get("url", ""),
            status="Scheduled" if scheduled else "Uploaded",
            title=it.title if it else "", description=it.description if it else "",
            tags=it.tags if it else "", category_id=it.category_id if it else "10",
            privacy=it.privacy if it else "private"))

    def _on_batch_up_fail(self, iid: int, msg: str):
        self.queue.set_status(iid, "Failed", error=msg)
        self._refresh_queue_table()

    # ================= history =================

    _UPLOADED_STATUS = ("Uploaded", "Scheduled")

    def _refresh_history_table(self):
        from PySide6.QtGui import QColor
        try:
            entries = self.history.list(200)
        except Exception as exc:
            log.warning("History: %s", exc)
            return
        self.tbl_hist.setRowCount(len(entries))
        for r, e in enumerate(entries):
            status = f"✓ {e.status}" if e.status in self._UPLOADED_STATUS else (e.status or "")
            vals = [e.created_at, e.beat_name, e.channel_title or e.channel_id,
                    e.video_id, e.video_url, status]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v or ""))
                if e.status in self._UPLOADED_STATUS:
                    item.setBackground(QColor("#1e4d2b"))
                self.tbl_hist.setItem(r, c, item)

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
        e.beat_name = self.ed_beat.text().strip() or e.beat_name
        e.audio_path = self.ed_audio.text().strip() or e.audio_path
        if self.current_video and Path(self.current_video).exists():
            e.video_path = self.current_video
        e.title = self.ed_title.text().strip()
        e.description = self.ed_desc.toPlainText()
        e.tags = self.ed_tags.text().strip()
        e.category_id = str(self.cb_cat.currentData() or "10")
        e.privacy = self.cb_privacy.currentText()
        try:
            self.history.update(e)
        except Exception as exc:
            QMessageBox.warning(self, "History", f"Could not update entry.\n{exc}")
            return
        self._refresh_history_table()
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
        if e.video_path:
            self.current_video = e.video_path
        self._show_view(0)
        self._set_status(f"Loaded from history: {e.beat_name or e.title or e.video_path}")

    def _history_clear(self):
        ret = QMessageBox.question(self, "History", "Clear all local history?")
        if ret == QMessageBox.Yes:
            self.history.clear()
            self._refresh_history_table()
