"""Batch queue and history (mixin)."""
from __future__ import annotations

import logging
import webbrowser
from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QTableWidgetItem

from app.models.models import HistoryEntry, QueueItem, resolve_clip_range
from app.ui.workers import BatchGenerateWorker, BatchUploadWorker, vars_for
from app.utils.scheduling import describe_rfc3339_in_tz
from app.utils.validators import validate_trim

log = logging.getLogger(__name__)



class QueueHistoryMixin:
    # ================= history autosave (B+C) =================
    # Link = entry being edited (visible highlight). Dirty = pending
    # keystrokes flushed after a debounce, on selection change, or on close.

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
        """Point the autosave link at a freshly created entry.

        Pending edits are flushed to the previous link first, but only when
        the form still shows the audio they belong to.
        """
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
        from PySide6.QtGui import QColor
        try:
            entries = self.history.list(200)
        except Exception:
            return
        rows = {e.id: r for r, e in enumerate(entries)}
        r = rows.get(entry.id)
        if r is None or r >= self.tbl_hist.rowCount():
            self._refresh_history_table()
            return
        status = f"✓ {entry.status}" if entry.status in self._UPLOADED_STATUS else (entry.status or "")
        vals = [entry.created_at, entry.beat_name, entry.channel_title or entry.channel_id,
                entry.video_id, entry.video_url, status]
        for c, v in enumerate(vals):
            item = QTableWidgetItem(str(v or ""))
            if entry.status in self._UPLOADED_STATUS:
                item.setBackground(QColor("#33363B"))
            elif entry.id == self._history_link_id:
                item.setBackground(QColor("#3a2f1a"))
                item.setForeground(QColor("#F5A623"))
            self.tbl_hist.setItem(r, c, item)

    def _on_history_selection_changed(self):
        # Viewing other rows must not lose pending edits: flush first.
        # The link stays (viewing is not editing).
        if self._history_link_id is not None and self._history_dirty:
            self._flush_history_link()

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
        vs = self._collect_video_settings()
        dur = 0.0
        if self.audio_info is not None and self.audio_info.path == audio:
            dur = self.audio_info.duration or 0.0
        else:
            try:
                dur = self.ffmpeg.get_audio_info(audio).duration or 0.0
            except Exception:
                dur = 0.0
        vt = validate_trim(vs.trim_start, vs.trim_end, dur)
        if not vt.ok:
            QMessageBox.warning(self, "Queue", vt.message)
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
            trim_start=vs.trim_start, trim_end=vs.trim_end,
            status="Pending",
        )
        self.queue.add(item)
        self._refresh_queue_table()
        if vs.has_trim:
            clip_s, clip_e = vs.clip_range(dur)
            self._set_status(f"Added to queue: {item.beat_name} "
                             f"(clip {clip_s:.1f}s–{clip_e:.1f}s)")
        else:
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
                    dur = self.ffmpeg.get_audio_info(i.audio_path).duration
                except Exception:
                    continue
                _s, _e = resolve_clip_range(i.trim_start, i.trim_end, dur)
                if _e - _s > SHORTS_MAX_SECONDS:
                    long_names.append(i.beat_name)
            if long_names:
                QMessageBox.information(
                    self, "Vertical videos",
                    f"{len(long_names)} vertical video(s) exceed 3 minutes and will publish "
                    "as regular videos, not Shorts:\n" + "\n".join(long_names[:8]))
        self._flush_history_link()
        self._set_history_link(None)
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
            privacy=it.privacy if it else "private",
            trim_start=it.trim_start if it else 0.0,
            trim_end=it.trim_end if it else 0.0))

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
        self._flush_history_link()
        self._set_history_link(None)
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
            privacy=it.privacy if it else "private",
            trim_start=it.trim_start if it else 0.0,
            trim_end=it.trim_end if it else 0.0))

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
                    item.setBackground(QColor("#33363B"))
                elif e.id == self._history_link_id:
                    item.setBackground(QColor("#3a2f1a"))
                    item.setForeground(QColor("#F5A623"))
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
