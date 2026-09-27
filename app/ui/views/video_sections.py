"""Secciones Video + Short Clip + Text/Overlay."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox,
)

if TYPE_CHECKING:
    from app.ui.mixins.protocol import MainWindowProtocol


def build_video_section(win: MainWindowProtocol) -> None:
    from app.ui.sections import CollapsibleSection

    win.sec_video = CollapsibleSection("Video", icon="▣")  # type: ignore[attr-defined]
    win._sections["video"] = win.sec_video
    vf = QGridLayout()
    vf.addWidget(QLabel("Format:"), 0, 0)
    win.cb_format = QComboBox()  # type: ignore[attr-defined]
    win.cb_format.addItems(["16:9 — Standard", "9:16 — Short"])
    win.cb_format.currentIndexChanged.connect(win._on_format_changed)  # type: ignore[attr-defined]
    vf.addWidget(win.cb_format, 0, 1)
    vf.addWidget(QLabel("Resolution:"), 0, 2)
    win.cb_res = QComboBox()  # type: ignore[attr-defined]
    win.cb_res.setEditable(True)
    win.cb_res.addItems(["1920x1080", "1280x720", "854x480", "1080x1920", "720x1280"])
    win.cb_res.currentTextChanged.connect(win._on_resolution_changed)  # type: ignore[attr-defined]
    vf.addWidget(win.cb_res, 0, 3)
    vf.addWidget(QLabel("Aspect:"), 1, 0)
    win.cb_fit = QComboBox()  # type: ignore[attr-defined]
    win.cb_fit.addItems(["cover", "fit", "crop", "letterbox"])
    vf.addWidget(win.cb_fit, 1, 1)
    win.ck_blur = QCheckBox("Blurred background")  # type: ignore[attr-defined]
    vf.addWidget(win.ck_blur, 1, 2, 1, 2)
    vf.addWidget(QLabel("FPS:"), 2, 0)
    win.sp_fps = QSpinBox()  # type: ignore[attr-defined]
    win.sp_fps.setRange(15, 60)
    win.sp_fps.setValue(30)
    vf.addWidget(win.sp_fps, 2, 1)
    vf.addWidget(QLabel("Preset:"), 2, 2)
    win.cb_preset = QComboBox()  # type: ignore[attr-defined]
    win.cb_preset.addItems(["ultrafast", "veryfast", "fast", "medium", "slow"])
    vf.addWidget(win.cb_preset, 2, 3)
    vf.addWidget(QLabel("Audio:"), 3, 0)
    win.cb_afmt = QComboBox()  # type: ignore[attr-defined]
    win.cb_afmt.addItems(["aac", "mp3", "opus", "wav"])
    vf.addWidget(win.cb_afmt, 3, 1)
    win.cb_abr = QComboBox()  # type: ignore[attr-defined]
    win.cb_abr.addItems(["128k", "160k", "192k", "256k", "320k"])
    vf.addWidget(win.cb_abr, 3, 2)
    vf.addWidget(QLabel("Background:"), 3, 3)
    win.ed_bg = QLineEdit("000000")  # type: ignore[attr-defined]
    win.ed_bg.setPlaceholderText("000000")
    vf.addWidget(win.ed_bg, 3, 4)
    win.sec_video.addLayout(vf)
    win.sections_layout.addWidget(win.sec_video)


def build_clip_section(win: MainWindowProtocol) -> None:
    from app.ui.sections import CollapsibleSection
    from app.ui.waveform import WaveformWidget

    win.sec_clip = CollapsibleSection("Short Clip", icon="✂")  # type: ignore[attr-defined]
    win._sections["clip"] = win.sec_clip
    cf = QGridLayout()
    win.wave = WaveformWidget()  # type: ignore[attr-defined]
    win.wave.rangeChanged.connect(win._on_wave_range_changed)  # type: ignore[attr-defined]
    cf.addWidget(win.wave, 0, 0, 1, 5)
    cf.addWidget(QLabel("Start (s):"), 1, 0)
    win.sp_trim_start = QDoubleSpinBox()  # type: ignore[attr-defined]
    win.sp_trim_start.setDecimals(1)
    win.sp_trim_start.setRange(0.0, 3600.0)
    win.sp_trim_start.setSingleStep(1.0)
    win.sp_trim_start.setSuffix(" s")
    win.sp_trim_start.valueChanged.connect(lambda _v: win._on_trim_spin_changed())  # type: ignore[attr-defined]
    cf.addWidget(win.sp_trim_start, 1, 1)
    cf.addWidget(QLabel("End (s):"), 1, 2)
    win.sp_trim_end = QDoubleSpinBox()  # type: ignore[attr-defined]
    win.sp_trim_end.setDecimals(1)
    win.sp_trim_end.setRange(0.0, 3600.0)
    win.sp_trim_end.setSingleStep(1.0)
    win.sp_trim_end.setSuffix(" s")
    win.sp_trim_end.setSpecialValueText("End")
    win.sp_trim_end.valueChanged.connect(lambda _v: win._on_trim_spin_changed())  # type: ignore[attr-defined]
    cf.addWidget(win.sp_trim_end, 1, 3)
    win.btn_clip_full = QPushButton("Full")  # type: ignore[attr-defined]
    win.btn_clip_full.setToolTip("Reset to the full audio")
    win.btn_clip_full.clicked.connect(win._reset_clip)  # type: ignore[attr-defined]
    cf.addWidget(win.btn_clip_full, 1, 4)
    win.lbl_clip_info = QLabel("Load an audio file to enable clipping.")  # type: ignore[attr-defined]
    win.lbl_clip_info.setStyleSheet("color:#92959A;")
    win.lbl_clip_info.setWordWrap(True)
    cf.addWidget(win.lbl_clip_info, 2, 0, 1, 5)
    win.sec_clip.addLayout(cf)
    win.sections_layout.addWidget(win.sec_clip)


def build_overlay_section(win: MainWindowProtocol) -> None:
    from app.ui.sections import CollapsibleSection

    win.sec_texto = CollapsibleSection("Text / Overlay", icon="T")  # type: ignore[attr-defined]
    win._sections["texto"] = win.sec_texto
    of = QGridLayout()
    win.ck_overlay = QCheckBox("Show text over the artwork")  # type: ignore[attr-defined]
    of.addWidget(win.ck_overlay, 0, 0, 1, 2)
    of.addWidget(QLabel("Text:"), 1, 0)
    win.ed_overlay = QLineEdit("{beat_name} — Prod. by {producer}")  # type: ignore[attr-defined]
    of.addWidget(win.ed_overlay, 1, 1)
    of.addWidget(QLabel("Position:"), 2, 0)
    win.cb_ov_pos = QComboBox()  # type: ignore[attr-defined]
    win.cb_ov_pos.addItems(["top-left", "top-center", "top-right", "center",
                            "bottom-left", "bottom-center", "bottom-right"])
    of.addWidget(win.cb_ov_pos, 2, 1)
    of.addWidget(QLabel("Size:"), 3, 0)
    win.sp_ov_size = QSpinBox()  # type: ignore[attr-defined]
    win.sp_ov_size.setRange(12, 160)
    win.sp_ov_size.setValue(48)
    of.addWidget(win.sp_ov_size, 3, 1)
    of.addWidget(QLabel("Opacity:"), 4, 0)
    win.sp_ov_op = QDoubleSpinBox()  # type: ignore[attr-defined]
    win.sp_ov_op.setRange(0.1, 1.0)
    win.sp_ov_op.setSingleStep(0.05)
    win.sp_ov_op.setValue(0.9)
    of.addWidget(win.sp_ov_op, 4, 1)
    of.addWidget(QLabel("Margin:"), 5, 0)
    win.sp_ov_margin = QSpinBox()  # type: ignore[attr-defined]
    win.sp_ov_margin.setRange(0, 300)
    win.sp_ov_margin.setValue(60)
    of.addWidget(win.sp_ov_margin, 5, 1)
    win.sec_texto.addLayout(of)
    win.sections_layout.addWidget(win.sec_texto)
