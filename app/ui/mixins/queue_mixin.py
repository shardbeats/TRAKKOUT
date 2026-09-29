"""Cola batch (mixin). Extraído de queue_history (Fase 3)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox, QTableWidgetItem

from app.models.models import HistoryEntry, QueueItem
from app.ui.workers import BatchGenerateWorker, BatchUploadWorker, vars_for
from app.utils.scheduling import describe_rfc3339_in_tz
from app.utils.validators import validate_trim

if TYPE_CHECKING:
    from app.ui.mixins.protocol import MainWindowProtocol as _MixinBase
else:
    _MixinBase = object

log = logging.getLogger(__name__)


class QueueMixin(_MixinBase):  # type: ignore[misc]
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
        from app.ui.batch_coordinator import long_vertical_names, missing_files

        bad = missing_files(items)
        if bad:
            QMessageBox.warning(self, "Queue", "Missing files in:\n" + "\n".join(bad[:8]))
            return
        vs = self._collect_video_settings()
        ov = self._collect_overlay()
        self._persist_ui_to_settings()
        # Vertical videos over 3 min are not classified as Shorts (warn, don't block).
        if vs.is_vertical:
            from app.services.clip_policy import bulk_shorts_warning
            long_names = long_vertical_names(items, self.ffmpeg, vs)
            msg = bulk_shorts_warning(long_names)
            if msg:
                QMessageBox.information(self, "Vertical videos", msg)
        self._fresh_cover = False  # sesión establecida con este cover
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
        from app.ui.batch_coordinator import count_scheduled

        items = [i for i in self.queue.all() if i.status in ("Ready",) and i.video_path and Path(i.video_path).exists()]
        if not items:
            QMessageBox.information(self, "Queue", "No Ready videos to upload. Generate first.")
            return
        sched_n = count_scheduled(items)
        sched_txt = f"\n({sched_n} scheduled for future publishing)" if sched_n else ""
        ret = QMessageBox.question(
            self, "Upload All",
            f"You are about to PUBLISH {len(items)} video(s) to YouTube.{sched_txt}\nConfirm bulk upload?")
        if ret != QMessageBox.Yes:
            return
        if not self.yt.is_connected():
            QMessageBox.warning(self, "Queue", "Connect Google first.")
            return
        self._fresh_cover = False  # sesión establecida con este cover
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
