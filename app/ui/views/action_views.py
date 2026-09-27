"""Barra inferior Generate/Preview/Upload + vistas Queue/History/Log."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QLabel, QProgressBar,
    QPushButton, QPlainTextEdit, QTableWidget, QVBoxLayout, QWidget,
)

if TYPE_CHECKING:
    from app.ui.mixins.protocol import MainWindowProtocol


def build_bottom_bar(win: MainWindowProtocol) -> None:
    gen_bar = QFrame()
    gen_bar.setObjectName("generateBar")
    af = QVBoxLayout(gen_bar)
    af.setContentsMargins(0, 0, 0, 0)
    af.setSpacing(4)
    win.lbl_status = QLabel("Ready")  # type: ignore[attr-defined]
    win.lbl_status.setWordWrap(True)
    af.addWidget(win.lbl_status)
    win.progress = QProgressBar()  # type: ignore[attr-defined]
    win.progress.setRange(0, 100)
    win.progress.setValue(0)
    af.addWidget(win.progress)
    win.lbl_times = QLabel("")  # type: ignore[attr-defined]
    af.addWidget(win.lbl_times)
    brow = QHBoxLayout()
    win.btn_queue_add = QPushButton("Queue +")  # type: ignore[attr-defined]
    win.btn_queue_add.clicked.connect(win._queue_add_current)  # type: ignore[attr-defined]
    win.btn_generate = QPushButton("Generate Video")  # type: ignore[attr-defined]
    win.btn_generate.setObjectName("accentButton")
    win.btn_generate.clicked.connect(win._on_generate)  # type: ignore[attr-defined]
    win.btn_preview = QPushButton("Preview")  # type: ignore[attr-defined]
    win.btn_preview.clicked.connect(win._on_preview)  # type: ignore[attr-defined]
    win.btn_upload = QPushButton("Upload to YouTube")  # type: ignore[attr-defined]
    win.btn_upload.setObjectName("accentButton")
    win.btn_upload.clicked.connect(win._on_upload)  # type: ignore[attr-defined]
    win.btn_cancel = QPushButton("Cancel")  # type: ignore[attr-defined]
    win.btn_cancel.clicked.connect(win._on_cancel)  # type: ignore[attr-defined]
    win.btn_cancel.setEnabled(False)
    for b in (win.btn_queue_add, win.btn_generate, win.btn_preview,
              win.btn_upload, win.btn_cancel):
        brow.addWidget(b)
    af.addLayout(brow)
    win._page_main_layout.addWidget(gen_bar)  # type: ignore[attr-defined]


def build_queue_view(win: MainWindowProtocol) -> None:
    qtab = QWidget()
    ql = QVBoxLayout(qtab)
    win.tbl_queue = QTableWidget(0, 8)  # type: ignore[attr-defined]
    win.tbl_queue.setHorizontalHeaderLabels(
        ["ID", "Beat", "Title", "Channel", "Privacy", "Publish", "Status", "Video"])
    win.tbl_queue.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    win.tbl_queue.setSelectionBehavior(QTableWidget.SelectRows)
    win.tbl_queue.setSelectionMode(QTableWidget.ExtendedSelection)
    win.tbl_queue.setEditTriggers(QTableWidget.NoEditTriggers)
    win.tbl_queue.setAlternatingRowColors(True)
    ql.addWidget(win.tbl_queue)
    qbtns = QHBoxLayout()
    win.btn_q_gen = QPushButton("Generate All")  # type: ignore[attr-defined]
    win.btn_q_gen.clicked.connect(win._on_batch_generate)  # type: ignore[attr-defined]
    win.btn_q_sel = QPushButton("Generate Selected")  # type: ignore[attr-defined]
    win.btn_q_sel.setToolTip("Generate only the selected rows")
    win.btn_q_sel.clicked.connect(win._on_batch_generate_selected)  # type: ignore[attr-defined]
    win.btn_q_up = QPushButton("Upload All")  # type: ignore[attr-defined]
    win.btn_q_up.clicked.connect(win._on_batch_upload)  # type: ignore[attr-defined]
    win.btn_q_del = QPushButton("Remove")  # type: ignore[attr-defined]
    win.btn_q_del.clicked.connect(win._queue_remove_selected)  # type: ignore[attr-defined]
    win.btn_q_clear = QPushButton("Clear queue")  # type: ignore[attr-defined]
    win.btn_q_clear.clicked.connect(
        lambda: (win.queue.clear(), win._refresh_queue_table()))  # type: ignore[attr-defined]
    for b in (win.btn_q_gen, win.btn_q_sel, win.btn_q_up,
              win.btn_q_del, win.btn_q_clear):
        qbtns.addWidget(b)
    qbtns.addStretch(1)
    ql.addLayout(qbtns)
    win.views.addWidget(qtab)


def build_history_view(win: MainWindowProtocol) -> None:
    htab = QWidget()
    hl = QVBoxLayout(htab)
    win.tbl_hist = QTableWidget(0, 6)  # type: ignore[attr-defined]
    win.tbl_hist.setHorizontalHeaderLabels(
        ["Date", "Beat", "Channel", "Video ID", "URL", "Status"])
    win.tbl_hist.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    win.tbl_hist.setEditTriggers(QTableWidget.NoEditTriggers)
    win.tbl_hist.setAlternatingRowColors(True)
    hl.addWidget(win.tbl_hist)
    hb2 = QHBoxLayout()
    win.btn_h_refresh = QPushButton("Refresh")  # type: ignore[attr-defined]
    win.btn_h_refresh.clicked.connect(win._refresh_history_table)  # type: ignore[attr-defined]
    win.btn_h_open = QPushButton("Open video")  # type: ignore[attr-defined]
    win.btn_h_open.clicked.connect(win._history_open_selected)  # type: ignore[attr-defined]
    win.btn_h_load = QPushButton("Load to uploader")  # type: ignore[attr-defined]
    win.btn_h_load.setToolTip("Restore this video and its metadata into the form, ready to upload")
    win.btn_h_load.clicked.connect(win._history_load_selected)  # type: ignore[attr-defined]
    win.btn_h_update = QPushButton("Update from form")  # type: ignore[attr-defined]
    win.btn_h_update.setToolTip("Overwrite the selected entry with the current form values")
    win.btn_h_update.clicked.connect(win._history_update_selected)  # type: ignore[attr-defined]
    win.btn_h_clear = QPushButton("Clear history")  # type: ignore[attr-defined]
    win.btn_h_clear.clicked.connect(win._history_clear)  # type: ignore[attr-defined]
    for b in (win.btn_h_refresh, win.btn_h_open, win.btn_h_load,
              win.btn_h_update, win.btn_h_clear):
        hb2.addWidget(b)
    hb2.addStretch(1)
    hl.addLayout(hb2)
    win.views.addWidget(htab)
    win._wire_history_autosave()  # type: ignore[attr-defined]


def build_log_view(win: MainWindowProtocol) -> None:
    from PySide6.QtWidgets import QStatusBar

    ltab = QWidget()
    ll = QVBoxLayout(ltab)
    win.txt_log = QPlainTextEdit()  # type: ignore[attr-defined]
    win.txt_log.setReadOnly(True)
    win.txt_log.setMaximumBlockCount(2000)
    ll.addWidget(win.txt_log)
    win.views.addWidget(ltab)

    win.setStatusBar(QStatusBar())
    win.statusBar().showMessage("Ready")


def build_all(win: MainWindowProtocol) -> None:
    """Orquesta la construcción completa (mismo orden que el _build_ui original)."""
    from app.ui.views.media_section import build_media_section
    from app.ui.views.shell import build_shell
    from app.ui.views.video_sections import (
        build_clip_section, build_overlay_section, build_video_section,
    )
    from app.ui.views.youtube_section import build_youtube_section

    build_shell(win)
    build_media_section(win)
    build_video_section(win)
    build_clip_section(win)
    build_overlay_section(win)
    build_youtube_section(win)
    build_bottom_bar(win)
    build_queue_view(win)
    build_history_view(win)
    build_log_view(win)
