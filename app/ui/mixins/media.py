"""Audio/artwork, drag & drop and media probing (mixin)."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox

from app.models.models import BeatMetadata
from app.utils.files import human_size, is_audio_file, is_image_file
from app.utils.formatting import fmt_hms
from app.utils.validators import validate_audio_path, validate_image_path

log = logging.getLogger(__name__)



class MediaMixin:
    SOURCE_LABELS = {
        "manual": "manual",
        "local": "local file",
    }

    def _refresh_media_info(self):
        lines = []
        if self.audio_info is not None:
            a = self.audio_info
            lines.append(f"Audio: {a.file_name} | {fmt_hms(a.duration)} | {a.codec or a.format_name} | "
                         f"{a.sample_rate or '-'} Hz | {human_size(a.size_bytes)}")
        if self.image_info is not None:
            im = self.image_info
            lines.append(f"Artwork: {im.file_name} | {im.resolution} | {human_size(im.size_bytes)}")
        if self.beat.title or self.beat.producer:
            extra = []
            if self.beat.bpm:
                extra.append(f"BPM {self.beat.bpm}")
            if self.beat.key:
                extra.append(self.beat.key)
            if self.beat.genre:
                extra.append(self.beat.genre)
            suffix = f" ({', '.join(extra)})" if extra else ""
            lines.append(f"Beat: {self.beat.title or '-'} | Prod: {self.beat.producer or '-'}{suffix}")
        self.lbl_media_info.setText("\n".join(lines) if lines else "No media loaded.")
        src = self.SOURCE_LABELS.get(self.beat.source, self.beat.source or "manual")
        assoc = []
        if self.beat.audio_path:
            assoc.append(f"audio: {Path(self.beat.audio_path).name}")
        if self.beat.artwork_path:
            assoc.append(f"cover: {Path(self.beat.artwork_path).name}")
        link = f"  [linked: {' + '.join(assoc)}]" if assoc else "  [attach your local audio + cover]"
        self.lbl_source.setText(f"Source: {src}{link}")
        # thumbnail
        if self.image_info and Path(self.image_info.path).exists():
            pm = QPixmap(self.image_info.path)
            if not pm.isNull():
                self.lbl_cover_prev.setPixmap(pm.scaled(120, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    # ================= media =================

    def _set_audio_file(self, f: str) -> None:
        self.ed_audio.setText(f)
        self._probe_audio(f)

    def _set_cover_file(self, f: str) -> None:
        self.ed_cover.setText(f)
        self._probe_image(f)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            for u in event.mimeData().urls():
                p = u.toLocalFile()
                if p and (is_audio_file(p) or is_image_file(p)):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        paths = [p for p in paths if p and Path(p).is_file()]
        if not paths:
            event.ignore()
            return
        event.acceptProposedAction()
        # If dropped onto a specific field, force that target.
        target = None
        try:
            w = self.childAt(event.position().toPoint())
            while w is not None:
                if w is self.ed_audio:
                    target = "audio"
                    break
                if w is self.ed_cover or w is self.lbl_cover_prev:
                    target = "image"
                    break
                w = w.parentWidget()
        except Exception:
            target = None
        self._handle_dropped_files(paths, target)

    def _handle_dropped_files(self, paths: list[str], target: str | None = None) -> None:
        audios = [p for p in paths if is_audio_file(p)]
        images = [p for p in paths if is_image_file(p)]
        if target == "audio" and paths:
            # Dropped onto the audio field: accept the first file even if the
            # extension is not on the list (validation will warn).
            self._set_audio_file(paths[0])
            return
        if target == "image" and paths:
            self._set_cover_file(paths[0])
            return
        if audios:
            self._set_audio_file(audios[0])
        if images:
            self._set_cover_file(images[0])
        if not audios and not images:
            self._set_status("Unsupported file: drop an audio file or an image.")
        elif len(paths) > len(audios) + len(images):
            self._set_status("Some files were not audio/images and were skipped.")

    def _pick_audio(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Select audio", "",
            "Audio (*.mp3 *.wav *.m4a *.flac *.ogg *.opus *.aac *.wma *.aiff);;All (*)")
        if f:
            self._set_audio_file(f)

    def _pick_cover(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Select artwork", "",
            "Image (*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff);;All (*)")
        if f:
            self._set_cover_file(f)

    def _probe_audio(self, path: str):
        v = validate_audio_path(path)
        if not v.ok:
            QMessageBox.warning(self, "Audio", v.message)
            return
        try:
            self.audio_info = self.ffmpeg.get_audio_info(path)
            self.beat.audio_path = path
            # Auto-detect title/BPM/key from the filename (only fills blanks).
            from app.utils.beat_names import parse_beat_filename
            info = parse_beat_filename(Path(path).stem)
            if self.beat.source == "manual" and not self.beat.title:
                self.beat.title = info.title
            if not self.ed_beat.text().strip():
                self.ed_beat.setText(info.title)
            found = []
            if info.bpm and not self.ed_bpm.text().strip():
                self.ed_bpm.setText(info.bpm)
                self.beat.bpm = info.bpm
                found.append(f"BPM {info.bpm}")
            if info.key and not self.ed_key.text().strip():
                self.ed_key.setText(info.key)
                self.beat.key = info.key
                found.append(f"Key {info.key}")
            self._refresh_media_info()
            if found:
                self._set_status(f"Detected from filename: {', '.join(found)}.")
        except Exception as exc:
            QMessageBox.warning(self, "Audio", f"Could not read the audio.\n{exc}")

    def _probe_image(self, path: str):
        v = validate_image_path(path)
        if not v.ok:
            QMessageBox.warning(self, "Artwork", v.message)
            return
        try:
            self.image_info = self.ffmpeg.get_image_info(path)
            self.beat.artwork_path = path
            self._refresh_media_info()
        except Exception as exc:
            QMessageBox.warning(self, "Artwork", f"Could not read the image.\n{exc}")

    def _clear_media(self):
        self.ed_audio.clear(); self.ed_cover.clear()
        self.beat = BeatMetadata()
        self.audio_info = None; self.image_info = None
        self.lbl_cover_prev.clear()
        self._refresh_media_info()
