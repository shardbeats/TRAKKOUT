"""Application dialogs (settings and preview)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from app.config.settings import SettingsStore


class SettingsDialog(QDialog):
    def __init__(self, store: SettingsStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        s = store.settings
        layout = QFormLayout(self)

        self.ed_ffmpeg = QLineEdit(s.ffmpeg_path)
        self.ed_ffprobe = QLineEdit(s.ffprobe_path)
        self.ed_out = QLineEdit(s.output_dir)
        row1 = QHBoxLayout(); row1.addWidget(self.ed_ffmpeg)
        b1 = QPushButton("…"); b1.clicked.connect(lambda: self._pick(self.ed_ffmpeg)); row1.addWidget(b1)
        row2 = QHBoxLayout(); row2.addWidget(self.ed_ffprobe)
        b2 = QPushButton("…"); b2.clicked.connect(lambda: self._pick(self.ed_ffprobe)); row2.addWidget(b2)
        row3 = QHBoxLayout(); row3.addWidget(self.ed_out)
        b3 = QPushButton("…"); b3.clicked.connect(lambda: self._pick_dir(self.ed_out)); row3.addWidget(b3)
        w1, w2, w3 = QWidget(), QWidget(), QWidget()
        w1.setLayout(row1); w2.setLayout(row2); w3.setLayout(row3)
        layout.addRow("FFmpeg:", w1)
        layout.addRow("FFprobe:", w2)
        layout.addRow("Videos folder:", w3)

        self.cb_res = QComboBox(); self.cb_res.addItems(["1920x1080", "1280x720", "854x480"])
        self.cb_res.setCurrentText(s.resolution)
        self.cb_afmt = QComboBox(); self.cb_afmt.addItems(["aac", "mp3", "opus", "wav"])
        self.cb_afmt.setCurrentText(s.audio_format)
        self.cb_abr = QComboBox(); self.cb_abr.addItems(["128k", "160k", "192k", "256k", "320k"])
        self.cb_abr.setCurrentText(s.audio_bitrate)
        layout.addRow("Resolution:", self.cb_res)
        layout.addRow("Audio:", self.cb_afmt)
        layout.addRow("Bitrate:", self.cb_abr)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _pick(self, edit: QLineEdit):
        f, _ = QFileDialog.getOpenFileName(self, "Select executable", "", "EXE (*.exe);;All (*)")
        if f:
            edit.setText(f)

    def _pick_dir(self, edit: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, "Output folder")
        if d:
            edit.setText(d)

    def apply(self):
        s = self.store.settings
        s.ffmpeg_path = self.ed_ffmpeg.text().strip() or "ffmpeg"
        s.ffprobe_path = self.ed_ffprobe.text().strip() or "ffprobe"
        s.output_dir = self.ed_out.text().strip() or str(Path.home() / "Videos" / "TRAKKOUT")
        s.resolution = self.cb_res.currentText()
        s.audio_format = self.cb_afmt.currentText()
        s.audio_bitrate = self.cb_abr.currentText()
        self.store.save()


class PreviewDialog(QDialog):
    def __init__(self, summary: str, cover_path: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preview")
        self.setMinimumSize(560, 480)
        layout = QVBoxLayout(self)
        if cover_path and Path(cover_path).exists():
            lbl = QLabel()
            pm = QPixmap(cover_path)
            if not pm.isNull():
                lbl.setPixmap(pm.scaled(480, 270, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                lbl.setAlignment(Qt.AlignCenter)
                layout.addWidget(lbl)
        txt = QPlainTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(summary)
        layout.addWidget(txt)
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)
