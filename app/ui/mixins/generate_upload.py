"""Single video generation and upload + preview (mixin)."""
from __future__ import annotations

import logging
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from app.models.models import HistoryEntry
from app.ui.dialogs import PreviewDialog
from app.ui.workers import FFmpegWorker, UploadWorker
from app.utils.files import ensure_dir, human_size, safe_stem
from app.utils.formatting import fmt_hms
from app.utils.scheduling import describe_rfc3339_in_tz
from app.utils.validators import (
    validate_audio_path, validate_image_path, validate_youtube_metadata,
)

log = logging.getLogger(__name__)



class GenerateUploadMixin:
    def _default_output(self) -> Path:
        ensure_dir(self.settings.output_dir)
        stem = safe_stem(self.ed_beat.text().strip() or Path(self.ed_audio.text()).stem
                         if self.ed_audio.text() else "beat")
        return Path(self.settings.output_dir) / f"{stem}.mp4"

    def _on_generate(self):
        audio = self.ed_audio.text().strip()
        cover = self.ed_cover.text().strip()
        va = validate_audio_path(audio)
        if not va.ok:
            QMessageBox.warning(self, "Generate video", va.message); return
        vi = validate_image_path(cover)
        if not vi.ok:
            QMessageBox.warning(self, "Generate video", vi.message); return
        try:
            self.ffmpeg.require_tools()
            self.audio_info = self.ffmpeg.get_audio_info(audio)
            self.image_info = self.ffmpeg.get_image_info(cover)
            self._refresh_media_info()
        except Exception as exc:
            QMessageBox.warning(self, "Generate video", f"Invalid files.\n{exc}")
            return

        vs = self._collect_video_settings()
        ov = self._collect_overlay()
        out = self._default_output()
        # If it exists, add a suffix
        if out.exists():
            out = out.with_name(f"{out.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        # Vertical videos over 3 min are not classified as Shorts.
        from app.ui.mixins.collectors import SHORTS_MAX_SECONDS
        if vs.is_vertical and (self.audio_info.duration or 0) > SHORTS_MAX_SECONDS:
            QMessageBox.warning(
                self, "Vertical video",
                "This video is vertical but longer than 3 minutes, so YouTube will "
                "treat it as a regular video, not a Short.\n\nGeneration continues anyway.")

        self._persist_ui_to_settings()
        self._set_busy(True)
        self._op_start = time.time()
        self._op_total = self.audio_info.duration or 0
        self._set_status(f"Generating video… -> {out.name}")
        self.ffmpeg_worker = FFmpegWorker(self.video_gen, cover, audio, str(out), vs, ov, self)
        self.ffmpeg_worker.progress.connect(self._on_ff_progress)
        self.ffmpeg_worker.finished_ok.connect(self._on_ff_done)
        self.ffmpeg_worker.failed.connect(self._on_ff_fail)
        self.ffmpeg_worker.start()

    def _on_ff_progress(self, out_s: float, total: float, pct: float):
        el = time.time() - self._op_start
        self._set_progress(pct, f"{fmt_hms(out_s)} / {fmt_hms(total)}   "
                                f"elapsed {fmt_hms(el)}")
        self._set_status(f"Generating video… {pct:.1f}%  ({fmt_hms(out_s)} / {fmt_hms(total)})")

    def _on_ff_done(self, path: str):
        self._set_busy(False)
        self.current_video = path
        el = time.time() - self._op_start
        self._set_progress(100, f"Done in {fmt_hms(el)}")
        self._set_status("Video generated successfully.")
        QMessageBox.information(self, "Video", f"Video generated successfully.\n{path}")
        self._log_history(HistoryEntry(
            beat_name=self.ed_beat.text().strip() or Path(path).stem,
            audio_path=self.ed_audio.text().strip(), video_path=path,
            channel_id="", channel_title="", status="Generated",
            title=self.ed_title.text().strip(), description=self.ed_desc.toPlainText(),
            tags=self.ed_tags.text().strip(),
            category_id=str(self.cb_cat.currentData() or "10"),
            privacy=self.cb_privacy.currentText()))

    def _on_ff_fail(self, msg: str):
        self._set_busy(False)
        self._set_progress(0, "")
        self._set_status("Error generating the video.")
        log.error("Error generating the video: %s", msg)
        QMessageBox.critical(self, "Generate video", f"Could not generate the video.\n{msg}")
        self._log_history(HistoryEntry(
            beat_name=self.ed_beat.text().strip(), audio_path=self.ed_audio.text().strip(),
            status="Failed", error=msg[:500]))

    # ================= preview =================

    def _on_preview(self):
        ch = self._selected_channel()
        meta = self._collect_metadata()
        beat = self._collect_beat_metadata()
        dur = self.audio_info.duration if self.audio_info else 0.0
        vs = self._collect_video_settings()
        sched = describe_rfc3339_in_tz(meta.publish_at, self.cb_tz.currentText()) if meta.publish_at else "Now"
        summary = (
            f"Beat: {beat.title or '-'} | Artist: {beat.artist or '-'}{(' x ' + beat.artist2) if beat.artist2 else ''} | Prod: {beat.producer or '-'}\n"
            f"Genre: {beat.genre or '-'}  BPM: {beat.bpm or '-'}  Key: {beat.key or '-'}\n"
            f"Purchase: {beat.purchase_url or '-'}\n"
            f"Title: {meta.title or '(untitled)'}\n"
            f"Description: {(meta.description or '')[:600]}\n"
            f"Tags: {', '.join(meta.tags)}\n"
            f"Category: {meta.category_id}  Privacy: {meta.privacy}  Kids: {meta.made_for_kids}\n"
            f"Publish: {sched}\n"
            f"Channel: {ch.display if ch else '(none selected)'}\n"
            f"Audio length: {fmt_hms(dur)}\n"
            f"Resolution: {vs.resolution}  Fit: {vs.fit_mode}  FPS: {vs.fps}  Audio: {vs.audio_format} {vs.audio_bitrate}\n"
            f"Current video: {self.current_video or '(not generated yet)'}\n"
            f"Audio: {self.ed_audio.text()}\nArtwork: {self.ed_cover.text()}"
        )
        dlg = PreviewDialog(summary, self.ed_cover.text().strip(), self)
        dlg.exec()
        if self.current_video and Path(self.current_video).exists():
            ret = QMessageBox.question(self, "Play", "Open the generated MP4 with the system player?")
            if ret == QMessageBox.Yes:
                self._open_path(self.current_video)

    def _open_path(self, path: str):
        try:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception:
            webbrowser.open(path)

    # ================= upload =================

    def _on_upload(self):
        if not self.current_video or not Path(self.current_video).exists():
            QMessageBox.warning(self, "Upload", "Generate the video first (Generate Video).")
            return
        if not self.yt.is_connected():
            QMessageBox.warning(self, "Upload", "Connect your Google account first.")
            return
        ch = self._selected_channel()
        if ch is None:
            QMessageBox.warning(self, "Upload", "Select a YouTube channel (Refresh Channels if empty).")
            return
        meta = self._collect_metadata()
        v = validate_youtube_metadata(meta.title, meta.description, meta.tags)
        if not v.ok:
            QMessageBox.warning(self, "Upload", v.message)
            return
        _pub_check, _pub_err = self._collect_publish_at()
        if _pub_err:
            QMessageBox.warning(self, "Upload", f"Invalid schedule.\n{_pub_err}")
            return
        sched_line = (f"\nScheduled publishing: "
                      f"{describe_rfc3339_in_tz(meta.publish_at, self.cb_tz.currentText())}"
                      if meta.publish_at else "")
        ret = QMessageBox.question(
            self, "Confirm upload",
            f"You are about to publish:\n“{meta.title}”\nChannel: {ch.title} ({ch.channel_id})\n"
            f"Privacy: {meta.privacy}{sched_line}\nContinue?")
        if ret != QMessageBox.Yes:
            return
        self._last_publish_at = meta.publish_at
        self._persist_ui_to_settings()
        self._set_busy(True)
        self._op_start = time.time()
        self._set_status(f"Uploading to YouTube… channel {ch.title}")
        self.upload_worker = UploadWorker(self.yt, self.current_video, meta,
                                          channel_id=ch.channel_id,
                                          playlist_id=meta.playlist_id, parent=self)
        self.upload_worker.progress.connect(self._on_up_progress)
        self.upload_worker.finished_ok.connect(self._on_up_done)
        self.upload_worker.failed.connect(self._on_up_fail)
        self.upload_worker.start()

    def _on_up_progress(self, sent: int, total: int, pct: float):
        el = time.time() - self._op_start
        eta = (el / pct * (100 - pct)) if pct > 1 else 0
        self._set_progress(pct, f"{human_size(sent)} / {human_size(total)}   "
                                f"elapsed {fmt_hms(el)}  remaining ~{fmt_hms(eta)}")
        self._set_status(f"Uploading to YouTube… {pct:.1f}%")

    def _on_up_done(self, result: dict):
        self._set_busy(False)
        self._set_progress(100, "Upload completed.")
        vid = result.get("video_id", "")
        url = result.get("url", "")
        cht = result.get("channel_title", "")
        scheduled = bool(getattr(self, "_last_publish_at", ""))
        self._set_status("Upload completed (scheduled)." if scheduled else "Upload completed.")
        self._log_history(HistoryEntry(
            beat_name=self.ed_beat.text().strip(), audio_path=self.ed_audio.text().strip(),
            video_path=self.current_video, channel_id=result.get("channel_id", ""),
            channel_title=cht, video_id=vid, video_url=url,
            privacy=self.cb_privacy.currentText(),
            status="Scheduled" if scheduled else "Uploaded",
            title=self.ed_title.text().strip(), description=self.ed_desc.toPlainText(),
            tags=self.ed_tags.text().strip(),
            category_id=str(self.cb_cat.currentData() or "10")))
        box = QMessageBox(self)
        box.setWindowTitle("Upload complete")
        extra = (f"\nScheduled: {describe_rfc3339_in_tz(self._last_publish_at, self.cb_tz.currentText())}"
                 if scheduled else "")
        box.setText(f"Upload completed.\nVideo ID: {vid}\nChannel: {cht}\n{url}{extra}")
        box.addButton("Open in browser", QMessageBox.AcceptRole)
        box.addButton("Close", QMessageBox.RejectRole)
        if box.exec() == 0 and url:
            webbrowser.open(url)

    def _on_up_fail(self, msg: str):
        self._set_busy(False)
        self._set_status("Upload error.")
        QMessageBox.critical(self, "Upload to YouTube", f"Could not upload the video.\n{msg}")
        self._log_history(HistoryEntry(
            beat_name=self.ed_beat.text().strip(), video_path=self.current_video,
            status="Failed", error=str(msg)[:500]))

    def _on_cancel(self):
        if self.ffmpeg_worker and self.ffmpeg_worker.isRunning():
            self.ffmpeg_worker.cancel()
            self._set_status("Cancelling generation…")
        if self.upload_worker and self.upload_worker.isRunning():
            self.upload_worker.cancel()
            self._set_status("Cancelling upload…")
        if self.batch_worker and self.batch_worker.isRunning():
            try:
                self.batch_worker.cancel()  # type: ignore[attr-defined]
            except Exception:
                pass
            self._set_status("Cancelling batch…")
