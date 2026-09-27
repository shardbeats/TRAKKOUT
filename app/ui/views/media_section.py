"""Sección Beat/Media."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)

if TYPE_CHECKING:
    from app.ui.mixins.protocol import MainWindowProtocol


def build_media_section(win: MainWindowProtocol) -> None:
    from app.ui.sections import CollapsibleSection

    win.sec_media = CollapsibleSection("Beat / Media", icon="♪")  # type: ignore[attr-defined]
    win._sections["media"] = win.sec_media
    f = QGridLayout()
    f.addWidget(QLabel("Audio:"), 0, 0)
    win.ed_audio = QLineEdit()  # type: ignore[attr-defined]
    win.ed_audio.setPlaceholderText("Drag audio here or press Browse…")
    win.ed_audio.setAcceptDrops(True)
    f.addWidget(win.ed_audio, 0, 1)
    win.btn_audio = QPushButton("Browse")  # type: ignore[attr-defined]
    win.btn_audio.clicked.connect(win._pick_audio)  # type: ignore[attr-defined]
    f.addWidget(win.btn_audio, 0, 2)

    f.addWidget(QLabel("Artwork:"), 1, 0)
    win.ed_cover = QLineEdit()  # type: ignore[attr-defined]
    win.ed_cover.setPlaceholderText("Drag artwork here or press Browse…")
    win.ed_cover.setAcceptDrops(True)
    f.addWidget(win.ed_cover, 1, 1)
    win.btn_cover = QPushButton("Browse")  # type: ignore[attr-defined]
    win.btn_cover.clicked.connect(win._pick_cover)  # type: ignore[attr-defined]
    f.addWidget(win.btn_cover, 1, 2)

    win.lbl_media_info = QLabel("No media loaded.")  # type: ignore[attr-defined]
    win.lbl_media_info.setWordWrap(True)
    win.lbl_media_info.setStyleSheet("color:#92959A;")
    f.addWidget(win.lbl_media_info, 2, 0, 1, 3)
    win.lbl_source = QLabel("Source: manual (no linked URL)")  # type: ignore[attr-defined]
    win.lbl_source.setWordWrap(True)
    win.lbl_source.setStyleSheet("color:#92959A; font-style:italic;")
    f.addWidget(win.lbl_source, 3, 0, 1, 3)

    row = QHBoxLayout()
    win.btn_clear = QPushButton("Clear")  # type: ignore[attr-defined]
    win.btn_clear.clicked.connect(win._clear_media)  # type: ignore[attr-defined]
    win.lbl_cover_prev = QLabel()  # type: ignore[attr-defined]
    win.lbl_cover_prev.setFixedSize(120, 90)
    win.lbl_cover_prev.setAlignment(Qt.AlignCenter)
    win.lbl_cover_prev.setStyleSheet("border:1px solid #45474A;")
    row.addWidget(win.lbl_cover_prev)
    row.addStretch(1)
    row.addWidget(win.btn_clear)
    f.addLayout(row, 4, 0, 1, 3)
    win.sec_media.addLayout(f)
    win.sections_layout.addWidget(win.sec_media)
