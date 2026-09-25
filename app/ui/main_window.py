"""TRAKKOUT main window (PySide6).

Thin shell: __init__ + _build_ui. Logic lives in app/ui/mixins/*.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, QDateTime
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateTimeEdit, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPlainTextEdit, QProgressBar, QPushButton,
    QScrollArea, QSpinBox, QStackedWidget, QStatusBar, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QDoubleSpinBox, QHeaderView,
)

from app.config.settings import SettingsStore
from app.ffmpeg.ffmpeg_service import FFmpegService
from app.models.models import BeatMetadata, ChannelInfo
from app.services.video_generator import VideoGenerator
from app.services.history_store import HistoryStore
from app.services.queue_manager import QueueManager
from app.templates import PresetManager, TemplateEngine
from app.ui.mixins import (
    CollectorsMixin, FeedbackMixin, GenerateUploadMixin, MediaMixin,
    QueueHistoryMixin, TemplatesMixin, YouTubeAuthMixin,
)
from app.ui.sections import CollapsibleSection, Sidebar
from app.utils.scheduling import COMMON_TIMEZONES
from app.youtube.auth import GoogleAuth
from app.youtube.youtube_service import YouTubeService

log = logging.getLogger(__name__)

YOUTUBE_CATEGORIES = {
    "1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music",
    "15": "Pets & Animals", "17": "Sports", "19": "Travel & Events",
    "20": "Gaming", "22": "People & Blogs", "23": "Comedy",
    "24": "Entertainment", "25": "News & Politics", "26": "Howto & Style",
    "27": "Education", "28": "Science & Technology", "29": "Nonprofits & Activism",
}


# ---------------------------------------------------------------- main window


class MainWindow(MediaMixin, CollectorsMixin, TemplatesMixin, YouTubeAuthMixin,
                   GenerateUploadMixin, QueueHistoryMixin, FeedbackMixin, QMainWindow):
    def __init__(self, project_root: Path, store: SettingsStore) -> None:
        super().__init__()
        self.project_root = project_root
        self.store = store
        self.settings = store.settings
        self.ffmpeg = FFmpegService(store.settings.ffmpeg_path, store.settings.ffprobe_path)
        self.video_gen = VideoGenerator(self.ffmpeg)
        self.engine = TemplateEngine()
        self.presets = PresetManager()
        self.auth = GoogleAuth(store.client_secrets_path(), store.token_path())
        self.yt = YouTubeService(self.auth)
        self.history = HistoryStore(store.db_path())
        self.queue = QueueManager(store.db_path())
        self.beat = BeatMetadata()
        self.channels: list[ChannelInfo] = []
        self.current_video: str = ""
        self._last_publish_at: str = ""
        self.audio_info = None
        self.image_info = None

        self.ffmpeg_worker: FFmpegWorker | None = None
        self.upload_worker: UploadWorker | None = None
        self.batch_worker: QThread | None = None
        self._op_start = 0.0
        self._op_total = 0.0

        self.setWindowTitle("TRAKKOUT")
        self.resize(1180, 820)
        self.setMinimumSize(1000, 700)
        self.setAcceptDrops(True)
        self._build_ui()
        self.lbl_cover_prev.setAcceptDrops(True)
        self._load_settings_to_ui()
        self._refresh_history_table()
        restored = [i for i in self.queue.all() if i.status in ("Pending", "Failed", "Ready")]
        self._refresh_queue_table()
        if restored:
            # After _startup_checks overwrites the status line.
            QTimer.singleShot(600, lambda n=len(restored): self._set_status(
                f"Queue restored: {n} item(s) recovered."))
        QTimer.singleShot(400, self._startup_checks)

    # ================= UI =================


    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        # Menu
        menubar = self.menuBar()
        m_file = menubar.addMenu("&File")
        act_settings = QAction("Settings…", self)
        act_settings.triggered.connect(self._open_settings)
        m_file.addAction(act_settings)
        act_oauth_help = QAction("How to set up Google OAuth…", self)
        act_oauth_help.triggered.connect(self._show_oauth_help)
        m_file.addAction(act_oauth_help)
        act_quit = QAction("Exit", self)
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)

        # Main / Queue / History / Log views (one at a time)
        m_view = menubar.addMenu("&View")
        self._view_group = QActionGroup(self)
        self._view_group.setExclusive(True)
        self._view_actions: list = []
        for i, (label, shortcut) in enumerate(
                [("Main", "Ctrl+1"), ("Queue", "Ctrl+2"),
                 ("History", "Ctrl+3"), ("Log", "Ctrl+4")]):
            act = QAction(label, self, checkable=True)
            act.setShortcut(shortcut)
            act.triggered.connect(lambda checked=False, idx=i: self._show_view(idx))
            m_view.addAction(act)
            self._view_group.addAction(act)
            self._view_actions.append(act)
        self._view_actions[0].setChecked(True)

        # ---- root layout: sidebar + views ----
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(124)
        self.sidebar.navigated.connect(self._goto_section)
        root.addWidget(self.sidebar)
        self.views = QStackedWidget()
        root.addWidget(self.views, 1)

        page_main = QWidget()
        page_main_layout = QVBoxLayout(page_main)
        page_main_layout.setContentsMargins(0, 0, 0, 0)
        page_main_layout.setSpacing(8)
        self.views.addWidget(page_main)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        scroll_inner = QWidget()
        self.sections_layout = QVBoxLayout(scroll_inner)
        self.sections_layout.setContentsMargins(0, 0, 2, 0)
        self.sections_layout.setSpacing(8)
        self.scroll.setWidget(scroll_inner)
        page_main_layout.addWidget(self.scroll, 1)

        self._sections: dict[str, CollapsibleSection] = {}

        # ---- Media ----
        self.sec_media = CollapsibleSection("Beat / Media", icon="♪")
        self._sections["media"] = self.sec_media
        f = QGridLayout()
        f.addWidget(QLabel("Audio:"), 0, 0)
        self.ed_audio = QLineEdit()
        self.ed_audio.setPlaceholderText("Drag audio here or press Browse…")
        self.ed_audio.setAcceptDrops(True)
        f.addWidget(self.ed_audio, 0, 1)
        self.btn_audio = QPushButton("Browse")
        self.btn_audio.clicked.connect(self._pick_audio)
        f.addWidget(self.btn_audio, 0, 2)

        f.addWidget(QLabel("Artwork:"), 1, 0)
        self.ed_cover = QLineEdit()
        self.ed_cover.setPlaceholderText("Drag artwork here or press Browse…")
        self.ed_cover.setAcceptDrops(True)
        f.addWidget(self.ed_cover, 1, 1)
        self.btn_cover = QPushButton("Browse")
        self.btn_cover.clicked.connect(self._pick_cover)
        f.addWidget(self.btn_cover, 1, 2)

        self.lbl_media_info = QLabel("No media loaded.")
        self.lbl_media_info.setWordWrap(True)
        self.lbl_media_info.setStyleSheet("color:#777;")
        f.addWidget(self.lbl_media_info, 2, 0, 1, 3)
        self.lbl_source = QLabel("Source: manual (no linked URL)")
        self.lbl_source.setWordWrap(True)
        self.lbl_source.setStyleSheet("color:#777; font-style:italic;")
        f.addWidget(self.lbl_source, 3, 0, 1, 3)

        row = QHBoxLayout()
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self._clear_media)
        self.lbl_cover_prev = QLabel()
        self.lbl_cover_prev.setFixedSize(120, 90)
        self.lbl_cover_prev.setAlignment(Qt.AlignCenter)
        self.lbl_cover_prev.setStyleSheet("border:1px solid #555;")
        row.addWidget(self.lbl_cover_prev)
        row.addStretch(1)
        row.addWidget(self.btn_clear)
        f.addLayout(row, 4, 0, 1, 3)
        self.sec_media.addLayout(f)
        self.sections_layout.addWidget(self.sec_media)

        # ---- Video ----
        self.sec_video = CollapsibleSection("Video", icon="▣")
        self._sections["video"] = self.sec_video
        vf = QGridLayout()
        vf.addWidget(QLabel("Format:"), 0, 0)
        self.cb_format = QComboBox()
        self.cb_format.addItems(["16:9 — Standard", "9:16 — Short"])
        self.cb_format.currentIndexChanged.connect(self._on_format_changed)
        vf.addWidget(self.cb_format, 0, 1)
        vf.addWidget(QLabel("Resolution:"), 0, 2)
        self.cb_res = QComboBox()
        self.cb_res.setEditable(True)
        self.cb_res.addItems(["1920x1080", "1280x720", "854x480", "1080x1920", "720x1280"])
        self.cb_res.currentTextChanged.connect(self._on_resolution_changed)
        vf.addWidget(self.cb_res, 0, 3)
        vf.addWidget(QLabel("Aspect:"), 1, 0)
        self.cb_fit = QComboBox()
        self.cb_fit.addItems(["cover", "fit", "crop", "letterbox"])
        vf.addWidget(self.cb_fit, 1, 1)
        self.ck_blur = QCheckBox("Blurred background")
        vf.addWidget(self.ck_blur, 1, 2, 1, 2)
        vf.addWidget(QLabel("FPS:"), 2, 0)
        self.sp_fps = QSpinBox(); self.sp_fps.setRange(15, 60); self.sp_fps.setValue(30)
        vf.addWidget(self.sp_fps, 2, 1)
        vf.addWidget(QLabel("Preset:"), 2, 2)
        self.cb_preset = QComboBox()
        self.cb_preset.addItems(["ultrafast", "veryfast", "fast", "medium", "slow"])
        vf.addWidget(self.cb_preset, 2, 3)
        vf.addWidget(QLabel("Audio:"), 3, 0)
        self.cb_afmt = QComboBox(); self.cb_afmt.addItems(["aac", "mp3", "opus", "wav"])
        vf.addWidget(self.cb_afmt, 3, 1)
        self.cb_abr = QComboBox(); self.cb_abr.addItems(["128k", "160k", "192k", "256k", "320k"])
        vf.addWidget(self.cb_abr, 3, 2)
        vf.addWidget(QLabel("Background:"), 3, 3)
        self.ed_bg = QLineEdit("000000")
        self.ed_bg.setPlaceholderText("000000")
        vf.addWidget(self.ed_bg, 3, 4)
        self.sec_video.addLayout(vf)
        self.sections_layout.addWidget(self.sec_video)

        # ---- Texto / Overlay ----
        self.sec_texto = CollapsibleSection("Text / Overlay", icon="T")
        self._sections["texto"] = self.sec_texto
        of = QGridLayout()
        self.ck_overlay = QCheckBox("Show text over the artwork")
        of.addWidget(self.ck_overlay, 0, 0, 1, 2)
        of.addWidget(QLabel("Text:"), 1, 0)
        self.ed_overlay = QLineEdit("{beat_name} — Prod. by {producer}")
        of.addWidget(self.ed_overlay, 1, 1)
        of.addWidget(QLabel("Position:"), 2, 0)
        self.cb_ov_pos = QComboBox()
        self.cb_ov_pos.addItems(["top-left", "top-center", "top-right", "center",
                                 "bottom-left", "bottom-center", "bottom-right"])
        of.addWidget(self.cb_ov_pos, 2, 1)
        of.addWidget(QLabel("Size:"), 3, 0)
        self.sp_ov_size = QSpinBox(); self.sp_ov_size.setRange(12, 160); self.sp_ov_size.setValue(48)
        of.addWidget(self.sp_ov_size, 3, 1)
        of.addWidget(QLabel("Opacity:"), 4, 0)
        self.sp_ov_op = QDoubleSpinBox(); self.sp_ov_op.setRange(0.1, 1.0)
        self.sp_ov_op.setSingleStep(0.05); self.sp_ov_op.setValue(0.9)
        of.addWidget(self.sp_ov_op, 4, 1)
        of.addWidget(QLabel("Margin:"), 5, 0)
        self.sp_ov_margin = QSpinBox(); self.sp_ov_margin.setRange(0, 300); self.sp_ov_margin.setValue(60)
        of.addWidget(self.sp_ov_margin, 5, 1)
        self.sec_texto.addLayout(of)
        self.sections_layout.addWidget(self.sec_texto)

        # ---- YouTube ----
        self.sec_youtube = CollapsibleSection("YouTube", icon="▶")
        self._sections["youtube"] = self.sec_youtube
        # Account (always visible inside the section)
        yf = QGridLayout()
        self.lbl_yt_status = QLabel("Disconnected")
        yf.addWidget(QLabel("Status:"), 0, 0)
        yf.addWidget(self.lbl_yt_status, 0, 1)
        yf.addWidget(QLabel("Channel:"), 1, 0)
        self.cb_channel = QComboBox()
        self.cb_channel.setMinimumWidth(260)
        self.cb_channel.currentIndexChanged.connect(self._on_channel_changed)
        yf.addWidget(self.cb_channel, 1, 1, 1, 2)
        btns_yt = QHBoxLayout()
        self.btn_connect = QPushButton("Connect Google Account")
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_refresh_ch = QPushButton("Refresh Channels")
        self.btn_refresh_ch.clicked.connect(self._on_refresh_channels)
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        btns_yt.addWidget(self.btn_connect)
        btns_yt.addWidget(self.btn_refresh_ch)
        btns_yt.addWidget(self.btn_disconnect)
        yf.addLayout(btns_yt, 2, 0, 1, 3)
        self.sec_youtube.addLayout(yf)

        # Template (always visible inside the section)
        tf = QGridLayout()
        tf.addWidget(QLabel("Template:"), 0, 0)
        self.cb_template = QComboBox()
        self.cb_template.setMinimumWidth(220)
        tf.addWidget(self.cb_template, 0, 1)
        self.btn_apply_tpl = QPushButton("Apply")
        self.btn_apply_tpl.clicked.connect(self._apply_template)
        tf.addWidget(self.btn_apply_tpl, 0, 2)
        tpl_btns = QHBoxLayout()
        self.btn_tpl_new = QPushButton("New")
        self.btn_tpl_new.clicked.connect(self._on_tpl_new)
        self.btn_tpl_edit = QPushButton("Edit")
        self.btn_tpl_edit.clicked.connect(self._on_tpl_edit)
        self.btn_tpl_del = QPushButton("Delete")
        self.btn_tpl_del.clicked.connect(self._on_tpl_delete)
        for b in (self.btn_tpl_new, self.btn_tpl_edit, self.btn_tpl_del):
            tpl_btns.addWidget(b)
        tpl_btns.addStretch(1)
        tf.addLayout(tpl_btns, 1, 1, 1, 2)
        self.sec_youtube.addLayout(tf)

        # Metadata (collapsible)
        self.sub_metadata = CollapsibleSection("Metadata", expanded=False)
        mf = QGridLayout()
        mf.addWidget(QLabel("Title:"), 1, 0)
        self.ed_title = QLineEdit()
        mf.addWidget(self.ed_title, 1, 1, 1, 2)
        mf.addWidget(QLabel("Description:"), 2, 0)
        self.ed_desc = QTextEdit()
        self.ed_desc.setFixedHeight(90)
        mf.addWidget(self.ed_desc, 2, 1, 1, 2)
        mf.addWidget(QLabel("Tags:"), 3, 0)
        self.ed_tags = QLineEdit()
        self.ed_tags.setPlaceholderText("comma, separated")
        mf.addWidget(self.ed_tags, 3, 1, 1, 2)
        mf.addWidget(QLabel("Category:"), 4, 0)
        self.cb_cat = QComboBox()
        for cid, name in YOUTUBE_CATEGORIES.items():
            self.cb_cat.addItem(f"{name}", cid)
        mf.addWidget(self.cb_cat, 4, 1)
        mf.addWidget(QLabel("Privacy:"), 4, 2)
        mf.addWidget(QLabel(""), 4, 3)
        self.cb_privacy = QComboBox()
        self.cb_privacy.addItems(["private", "unlisted", "public"])
        mf.addWidget(self.cb_privacy, 5, 1)
        self.ck_kids = QCheckBox("Made for Kids")
        mf.addWidget(self.ck_kids, 5, 2)
        mf.addWidget(QLabel("Playlist ID:"), 6, 0)
        self.ed_playlist = QLineEdit()
        self.ed_playlist.setPlaceholderText("(optional)")
        mf.addWidget(self.ed_playlist, 6, 1, 1, 2)
        self.sub_metadata.addLayout(mf)
        self.sec_youtube.addWidget(self.sub_metadata)

        # Beat / Artist (collapsible)
        self.sub_beat = CollapsibleSection("Beat / Artist", expanded=False)
        mf = QGridLayout()
        mf.addWidget(QLabel("Beat:"), 0, 0)
        hb = QHBoxLayout()
        self.ed_beat = QLineEdit(); self.ed_beat.setPlaceholderText("Beat title ({{title}})")
        self.ed_artist = QLineEdit(); self.ed_artist.setPlaceholderText("Artist ({{artist}})")
        self.ed_artist2 = QLineEdit(); self.ed_artist2.setPlaceholderText("Artist 2 ({{artist2}})")
        hb.addWidget(self.ed_beat); hb.addWidget(self.ed_artist); hb.addWidget(self.ed_artist2)
        w = QWidget(); w.setLayout(hb)
        mf.addWidget(w, 0, 1, 1, 2)
        self.sub_beat.addLayout(mf)
        self.sec_youtube.addWidget(self.sub_beat)

        # Production (collapsible)
        self.sub_production = CollapsibleSection("Production", expanded=False)
        mf = QGridLayout()
        mf.addWidget(QLabel("Producer:"), 0, 0)
        self.ed_producer = QLineEdit(); self.ed_producer.setPlaceholderText("Producer")
        mf.addWidget(self.ed_producer, 0, 1)
        mf.addWidget(QLabel("Genre:"), 0, 2)
        self.ed_genre = QLineEdit(); self.ed_genre.setPlaceholderText("Genre")
        mf.addWidget(self.ed_genre, 0, 3)
        mf.addWidget(QLabel("BPM:"), 1, 0)
        self.ed_bpm = QLineEdit(); self.ed_bpm.setPlaceholderText("BPM")
        mf.addWidget(self.ed_bpm, 1, 1)
        mf.addWidget(QLabel("Key:"), 1, 2)
        self.ed_key = QLineEdit(); self.ed_key.setPlaceholderText("Key")
        mf.addWidget(self.ed_key, 1, 3)
        self.sub_production.addLayout(mf)
        self.sec_youtube.addWidget(self.sub_production)

        # Publishing (collapsible)
        self.sub_publishing = CollapsibleSection("Publishing", expanded=False)
        mf = QGridLayout()
        mf.addWidget(QLabel("Purchase URL:"), 0, 0)
        self.ed_purchase = QLineEdit()
        self.ed_purchase.setPlaceholderText("https://... ({{purchase_url}})")
        mf.addWidget(self.ed_purchase, 0, 1, 1, 2)
        # scheduling
        mf.addWidget(QLabel("Schedule:"), 1, 0)
        hs = QHBoxLayout()
        self.ck_schedule = QCheckBox("Publish later")
        self.ck_schedule.toggled.connect(self._on_schedule_toggled)
        self.dt_schedule = QDateTimeEdit()
        self.dt_schedule.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.dt_schedule.setCalendarPopup(True)
        self.dt_schedule.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.dt_schedule.setEnabled(False)
        self.cb_tz = QComboBox()
        self.cb_tz.addItems(COMMON_TIMEZONES)
        try:
            self.cb_tz.setCurrentText("Europe/Madrid")
        except Exception:
            pass
        self.cb_tz.setEnabled(False)
        hs.addWidget(self.ck_schedule); hs.addWidget(self.dt_schedule); hs.addWidget(self.cb_tz)
        w3 = QWidget(); w3.setLayout(hs)
        mf.addWidget(w3, 1, 1, 1, 2)
        self.sub_publishing.addLayout(mf)
        self.sec_youtube.addWidget(self.sub_publishing)
        self.sections_layout.addWidget(self.sec_youtube)
        self.sections_layout.addStretch(1)

        # ---- bottom bar: Generate / Publish (always visible) ----
        gen_bar = QFrame()
        gen_bar.setObjectName("generateBar")
        af = QVBoxLayout(gen_bar)
        af.setContentsMargins(0, 0, 0, 0)
        af.setSpacing(4)
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setWordWrap(True)
        af.addWidget(self.lbl_status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        af.addWidget(self.progress)
        self.lbl_times = QLabel("")
        af.addWidget(self.lbl_times)
        brow = QHBoxLayout()
        self.btn_queue_add = QPushButton("Queue +")
        self.btn_queue_add.clicked.connect(self._queue_add_current)
        self.btn_generate = QPushButton("Generate Video")
        self.btn_generate.setObjectName("accentButton")
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_upload = QPushButton("Upload to YouTube")
        self.btn_upload.setObjectName("accentButton")
        self.btn_upload.clicked.connect(self._on_upload)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.setEnabled(False)
        for b in (self.btn_queue_add, self.btn_generate, self.btn_preview, self.btn_upload, self.btn_cancel):
            brow.addWidget(b)
        af.addLayout(brow)
        page_main_layout.addWidget(gen_bar)

        # ---- Queue / History / Log views ----

        # Queue
        qtab = QWidget(); ql = QVBoxLayout(qtab)
        self.tbl_queue = QTableWidget(0, 8)
        self.tbl_queue.setHorizontalHeaderLabels(["ID", "Beat", "Title", "Channel", "Privacy", "Publish", "Status", "Video"])
        self.tbl_queue.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_queue.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_queue.setSelectionMode(QTableWidget.ExtendedSelection)
        self.tbl_queue.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_queue.setAlternatingRowColors(True)
        ql.addWidget(self.tbl_queue)
        qbtns = QHBoxLayout()
        self.btn_q_gen = QPushButton("Generate All")
        self.btn_q_gen.clicked.connect(self._on_batch_generate)
        self.btn_q_sel = QPushButton("Generate Selected")
        self.btn_q_sel.setToolTip("Generate only the selected rows")
        self.btn_q_sel.clicked.connect(self._on_batch_generate_selected)
        self.btn_q_up = QPushButton("Upload All")
        self.btn_q_up.clicked.connect(self._on_batch_upload)
        self.btn_q_del = QPushButton("Remove")
        self.btn_q_del.clicked.connect(self._queue_remove_selected)
        self.btn_q_clear = QPushButton("Clear queue")
        self.btn_q_clear.clicked.connect(lambda: (self.queue.clear(), self._refresh_queue_table()))
        for b in (self.btn_q_gen, self.btn_q_sel, self.btn_q_up, self.btn_q_del, self.btn_q_clear):
            qbtns.addWidget(b)
        qbtns.addStretch(1)
        ql.addLayout(qbtns)
        self.views.addWidget(qtab)

        # History
        htab = QWidget(); hl = QVBoxLayout(htab)
        self.tbl_hist = QTableWidget(0, 6)
        self.tbl_hist.setHorizontalHeaderLabels(["Date", "Beat", "Channel", "Video ID", "URL", "Status"])
        self.tbl_hist.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_hist.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_hist.setAlternatingRowColors(True)
        hl.addWidget(self.tbl_hist)
        hb2 = QHBoxLayout()
        self.btn_h_refresh = QPushButton("Refresh")
        self.btn_h_refresh.clicked.connect(self._refresh_history_table)
        self.btn_h_open = QPushButton("Open video")
        self.btn_h_open.clicked.connect(self._history_open_selected)
        self.btn_h_load = QPushButton("Load to uploader")
        self.btn_h_load.setToolTip("Restore this video and its metadata into the form, ready to upload")
        self.btn_h_load.clicked.connect(self._history_load_selected)
        self.btn_h_update = QPushButton("Update from form")
        self.btn_h_update.setToolTip("Overwrite the selected entry with the current form values")
        self.btn_h_update.clicked.connect(self._history_update_selected)
        self.btn_h_clear = QPushButton("Clear history")
        self.btn_h_clear.clicked.connect(self._history_clear)
        for b in (self.btn_h_refresh, self.btn_h_open, self.btn_h_load, self.btn_h_update, self.btn_h_clear):
            hb2.addWidget(b)
        hb2.addStretch(1)
        hl.addLayout(hb2)
        self.views.addWidget(htab)

        # Log
        ltab = QWidget(); ll = QVBoxLayout(ltab)
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(2000)
        ll.addWidget(self.txt_log)
        self.views.addWidget(ltab)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")


    def closeEvent(self, event):  # noqa: N802
        self._persist_ui_to_settings()
        try:
            if self.ffmpeg_worker and self.ffmpeg_worker.isRunning():
                self.ffmpeg_worker.cancel()
                self.ffmpeg_worker.wait(3000)
        except Exception:
            pass
        super().closeEvent(event)
