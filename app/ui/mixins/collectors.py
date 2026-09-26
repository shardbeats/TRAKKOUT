"""Widget-to-model/settings readers (mixin)."""
from __future__ import annotations

import logging
from pathlib import Path

from app.ffmpeg.ffmpeg_service import FFmpegService
from app.models.models import BeatMetadata, OverlaySettings, VideoSettings, YouTubeMetadata
from app.services.video_generator import VideoGenerator
from app.templates import parse_tags
from app.utils.scheduling import local_to_utc_rfc3339

log = logging.getLogger(__name__)

#: Shorts auto-classification limit: vertical/square videos up to 3 min.
SHORTS_MAX_SECONDS = 180
_HORIZONTAL_RES = ("1920x1080", "1280x720", "854x480")
_VERTICAL_RES = ("1080x1920", "720x1280")



class CollectorsMixin:
    def _load_settings_to_ui(self):
        s = self.settings
        self.ffmpeg = FFmpegService(s.ffmpeg_path, s.ffprobe_path)
        self.video_gen = VideoGenerator(self.ffmpeg)
        self.cb_res.setCurrentText(s.resolution if s.resolution in ("1920x1080", "1280x720", "854x480", "1080x1920", "720x1280") else "1920x1080")
        self.cb_fit.setCurrentText(s.fit_mode if s.fit_mode in ("cover", "fit", "crop", "letterbox") else "cover")
        self.ck_blur.setChecked(bool(s.blurred_background))
        self.ed_bg.setText(s.background_color or "000000")
        self.cb_afmt.setCurrentText(s.audio_format if s.audio_format in ("aac", "mp3", "opus", "wav") else "aac")
        self.cb_abr.setCurrentText(s.audio_bitrate if s.audio_bitrate in ("128k", "160k", "192k", "256k", "320k") else "192k")
        self.cb_preset.setCurrentText(s.video_preset if s.video_preset else "medium")
        self.ck_overlay.setChecked(bool(s.overlay_enabled))
        self.ed_overlay.setText(s.overlay_text or "")
        self.cb_ov_pos.setCurrentText(s.overlay_position or "bottom-center")
        self.sp_ov_size.setValue(int(s.overlay_font_size or 48))
        self.sp_ov_op.setValue(float(s.overlay_opacity or 0.9))
        self.sp_ov_margin.setValue(int(s.overlay_margin or 60))
        self.cb_privacy.setCurrentText(s.default_privacy if s.default_privacy in ("private", "unlisted", "public") else "private")
        idx = self.cb_cat.findData(s.default_category or "10")
        if idx >= 0:
            self.cb_cat.setCurrentIndex(idx)
        self.ck_kids.setChecked(bool(s.made_for_kids))
        self._sync_format_to_resolution()

        # Load presets stored in settings, if any
        self._reload_templates()

        # Also load templates stored in settings
        # (without duplicating the ones already loaded from preset files).
        if s.templates:
            existing = {self.cb_template.itemText(i) for i in range(self.cb_template.count())}
            for t in s.templates:
                display_name = t.get("name", "template")
                if display_name in existing:
                    continue
                existing.add(display_name)
                self.cb_template.addItem(display_name, t)
                log.info(f"[Templates] Loaded settings preset: {display_name}")

        self._update_yt_status()

    def _sync_format_to_resolution(self):
        """Point the Format combo at the current resolution preset."""
        t = self.cb_res.currentText().strip()
        self.cb_format.blockSignals(True)
        self.cb_format.setCurrentIndex(1 if t in _VERTICAL_RES else 0)
        self.cb_format.blockSignals(False)
        self._update_clip_visibility()

    def _on_format_changed(self, idx: int):
        res = "1080x1920" if idx == 1 else "1920x1080"
        self.cb_res.blockSignals(True)
        self.cb_res.setCurrentText(res)
        self.cb_res.blockSignals(False)
        self._update_clip_visibility()

    def _on_resolution_changed(self, _text: str = ""):
        self._sync_format_to_resolution()

    # ---------- Short clip (phase 1: numeric selection) ----------

    def _update_clip_visibility(self):
        """The Short Clip section only exists for 9:16 output."""
        self.sec_clip.setVisible(self.cb_format.currentIndex() == 1)

    def _clip_duration_known(self) -> float:
        if self.audio_info is not None:
            return max(0.0, self.audio_info.duration or 0.0)
        return 0.0

    def _reset_clip(self):
        self.sp_trim_start.setValue(0.0)
        self.sp_trim_end.setValue(self._clip_duration_known())
        self._update_clip_info()

    def _on_trim_spin_changed(self):
        """Spinbox edit → move widget handles (silent) + refresh label."""
        self.wave.set_range(float(self.sp_trim_start.value()),
                            float(self.sp_trim_end.value()))
        self._update_clip_info()

    def _on_wave_range_changed(self, start: float, end: float):
        """Widget drag → set spinboxes (signals blocked: no loop)."""
        self.sp_trim_start.blockSignals(True)
        self.sp_trim_end.blockSignals(True)
        self.sp_trim_start.setValue(start)
        self.sp_trim_end.setValue(end)
        self.sp_trim_start.blockSignals(False)
        self.sp_trim_end.blockSignals(False)
        self._update_clip_info()

    def _update_trim_range(self):
        """Sync spinbox maximums with the loaded audio (call after probing).

        Never wipes an existing selection: only a NEW audio file resets the
        clip to full (note: generate re-probes the same file every time).
        """
        dur = self._clip_duration_known()
        audio_path = self.ed_audio.text().strip()
        for sp in (self.sp_trim_start, self.sp_trim_end):
            sp.blockSignals(True)
            sp.setMaximum(max(dur, 0.0))
            sp.blockSignals(False)
        if audio_path != self._trim_audio_path:
            self._trim_audio_path = audio_path
            self.sp_trim_start.blockSignals(True)
            self.sp_trim_end.blockSignals(True)
            self.sp_trim_start.setValue(0.0)
            self.sp_trim_end.setValue(dur)
            self.sp_trim_start.blockSignals(False)
            self.sp_trim_end.blockSignals(False)
        else:
            if self.sp_trim_end.value() == 0.0 and dur > 0:
                self.sp_trim_end.setValue(dur)
            if self.sp_trim_start.value() > dur:
                self.sp_trim_start.setValue(0.0)
            if self.sp_trim_end.value() > dur:
                self.sp_trim_end.setValue(dur)
        self.wave.set_duration(dur)
        self.wave.set_range(float(self.sp_trim_start.value()),
                            float(self.sp_trim_end.value()))
        self._update_clip_info()

    def _update_clip_info(self):
        from app.models.models import resolve_clip_range
        from app.utils.formatting import fmt_hms
        dur = self._clip_duration_known()
        if dur <= 0:
            self.lbl_clip_info.setText("Load an audio file to enable clipping.")
            return
        s, e = resolve_clip_range(self.sp_trim_start.value(),
                                  self.sp_trim_end.value(), dur)
        if e - s >= dur - 1e-6:
            self.lbl_clip_info.setText(f"Full audio · {fmt_hms(dur)}")
        else:
            self.lbl_clip_info.setText(
                f"Clip {fmt_hms(s)} – {fmt_hms(e)}  ({fmt_hms(e - s)} of {fmt_hms(dur)})")

    def _collect_video_settings(self) -> VideoSettings:
        res = self.cb_res.currentText()
        try:
            w, h = res.lower().split("x")
            width, height = int(w), int(h)
        except Exception:
            width, height = 1920, 1080
        vs = VideoSettings(
            width=width, height=height,
            fit_mode=self.cb_fit.currentText(),  # type: ignore[arg-type]
            blurred_background=self.ck_blur.isChecked(),
            background_color=(self.ed_bg.text().strip() or "000000").lstrip("#"),
            fps=int(self.sp_fps.value()),
            preset=self.cb_preset.currentText(),
            audio_format=self.cb_afmt.currentText(),  # type: ignore[arg-type]
            audio_bitrate=self.cb_abr.currentText(),
        )
        # Short-clip selection only applies to vertical (Short) output.
        # In 16:9 the spinboxes are hidden and ignored (full audio).
        if vs.is_vertical:
            vs.trim_start = float(self.sp_trim_start.value())
            vs.trim_end = float(self.sp_trim_end.value())
        return vs

    def _collect_overlay(self) -> OverlaySettings:
        vals = self._template_vals()
        text = self.engine.render(self.ed_overlay.text(), vals)
        return OverlaySettings(
            enabled=self.ck_overlay.isChecked(),
            text=text,
            position=self.cb_ov_pos.currentText(),
            font_size=int(self.sp_ov_size.value()),
            opacity=float(self.sp_ov_op.value()),
            margin=int(self.sp_ov_margin.value()),
            font_path=self.settings.overlay_font or "",
        )

    def _collect_beat_metadata(self) -> BeatMetadata:
        """BeatMetadata from confirmed fields + linked local files.

        Flow: the user links local audio/artwork (their legitimate license or
        download) and fills in the fields → TemplateEngine → YouTubeMetadata
        → VideoGenerator.
        """
        title = self.ed_beat.text().strip()
        if not title and self.ed_audio.text().strip():
            title = Path(self.ed_audio.text().strip()).stem
        return BeatMetadata(
            title=title or self.beat.title,
            producer=self.ed_producer.text().strip() or self.beat.producer,
            artist=self.ed_artist.text().strip(),
            artist2=self.ed_artist2.text().strip(),
            genre=self.ed_genre.text().strip(),
            bpm=self.ed_bpm.text().strip(),
            key=self.ed_key.text().strip(),
            purchase_url=self.ed_purchase.text().strip(),
            tags=[t.strip() for t in self.ed_tags.text().replace(";", ",").split(",") if t.strip()],
            description=self.ed_desc.toPlainText(),
            artwork_url=self.beat.artwork_url,
            artwork_path=self.ed_cover.text().strip(),
            audio_path=self.ed_audio.text().strip(),
            preview_audio_url="",
            source=self.beat.source,
            fetched_at=self.beat.fetched_at,
        )

    def _collect_publish_at(self) -> tuple[str, str]:
        """Return (publish_at_utc, error). '' = publish immediately."""
        if not self.ck_schedule.isChecked():
            return "", ""
        try:
            naive = self.dt_schedule.dateTime().toPython()
            value = local_to_utc_rfc3339(naive, self.cb_tz.currentText())
        except Exception as exc:
            return "", str(exc)
        from app.utils.scheduling import ScheduleError, ensure_future_publish_at
        try:
            return ensure_future_publish_at(value), ""
        except ScheduleError as exc:
            return "", str(exc)

    def _collect_metadata(self) -> YouTubeMetadata:
        beat = self._collect_beat_metadata()
        ch = self._selected_channel()
        vals = self.engine.context_from_beat(
            beat, {"channel": ch.title if ch else ""})
        tags = parse_tags(self.ed_tags.text(), vals)
        publish_at, _err = self._collect_publish_at()
        return YouTubeMetadata(
            title=self.ed_title.text().strip(),
            description=self.ed_desc.toPlainText(),
            tags=tags,
            category_id=str(self.cb_cat.currentData() or "10"),
            privacy=self.cb_privacy.currentText(),  # type: ignore[arg-type]
            playlist_id=self.ed_playlist.text().strip(),
            made_for_kids=self.ck_kids.isChecked(),
            publish_at=publish_at,
        )

    def _template_vals(self) -> dict:
        beat = self._collect_beat_metadata()
        ch = self._selected_channel()
        return self.engine.context_from_beat(
            beat, {"channel": ch.title if ch else ""})

    def _on_schedule_toggled(self, checked: bool) -> None:
        self.dt_schedule.setEnabled(checked)
        self.cb_tz.setEnabled(checked)
        if checked:
            # The API requires private privacy for scheduling.
            if self.cb_privacy.currentText() != "private":
                self.cb_privacy.setCurrentText("private")
                self._set_status("Scheduling on: privacy set to 'private' (YouTube requirement).")
            self.cb_privacy.setEnabled(False)
        else:
            self.cb_privacy.setEnabled(True)
