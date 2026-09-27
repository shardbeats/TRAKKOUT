"""Sección YouTube + sub-secciones colapsables."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateTimeEdit, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QWidget,
)

if TYPE_CHECKING:
    from app.ui.mixins.protocol import MainWindowProtocol

YOUTUBE_CATEGORIES = {
    "1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music",
    "15": "Pets & Animals", "17": "Sports", "19": "Travel & Events",
    "20": "Gaming", "22": "People & Blogs", "23": "Comedy",
    "24": "Entertainment", "25": "News & Politics", "26": "Howto & Style",
    "27": "Education", "28": "Science & Technology", "29": "Nonprofits & Activism",
}


def build_youtube_section(win: MainWindowProtocol) -> None:
    from app.ui.sections import CollapsibleSection
    from app.utils.scheduling import COMMON_TIMEZONES

    win.sec_youtube = CollapsibleSection("YouTube", icon="▶")  # type: ignore[attr-defined]
    win._sections["youtube"] = win.sec_youtube
    yf = QGridLayout()
    win.lbl_yt_status = QLabel("Disconnected")  # type: ignore[attr-defined]
    yf.addWidget(QLabel("Status:"), 0, 0)
    yf.addWidget(win.lbl_yt_status, 0, 1)
    yf.addWidget(QLabel("Channel:"), 1, 0)
    win.cb_channel = QComboBox()  # type: ignore[attr-defined]
    win.cb_channel.setMinimumWidth(260)
    win.cb_channel.currentIndexChanged.connect(win._on_channel_changed)  # type: ignore[attr-defined]
    yf.addWidget(win.cb_channel, 1, 1, 1, 2)
    btns_yt = QHBoxLayout()
    win.btn_connect = QPushButton("Connect Google Account")  # type: ignore[attr-defined]
    win.btn_connect.clicked.connect(win._on_connect)  # type: ignore[attr-defined]
    win.btn_refresh_ch = QPushButton("Refresh Channels")  # type: ignore[attr-defined]
    win.btn_refresh_ch.clicked.connect(win._on_refresh_channels)  # type: ignore[attr-defined]
    win.btn_disconnect = QPushButton("Disconnect")  # type: ignore[attr-defined]
    win.btn_disconnect.clicked.connect(win._on_disconnect)  # type: ignore[attr-defined]
    btns_yt.addWidget(win.btn_connect)
    btns_yt.addWidget(win.btn_refresh_ch)
    btns_yt.addWidget(win.btn_disconnect)
    yf.addLayout(btns_yt, 2, 0, 1, 3)
    win.sec_youtube.addLayout(yf)

    tf = QGridLayout()
    tf.addWidget(QLabel("Template:"), 0, 0)
    win.cb_template = QComboBox()  # type: ignore[attr-defined]
    win.cb_template.setMinimumWidth(220)
    tf.addWidget(win.cb_template, 0, 1)
    win.btn_apply_tpl = QPushButton("Apply")  # type: ignore[attr-defined]
    win.btn_apply_tpl.clicked.connect(win._apply_template)  # type: ignore[attr-defined]
    tf.addWidget(win.btn_apply_tpl, 0, 2)
    tpl_btns = QHBoxLayout()
    win.btn_tpl_new = QPushButton("New")  # type: ignore[attr-defined]
    win.btn_tpl_new.clicked.connect(win._on_tpl_new)  # type: ignore[attr-defined]
    win.btn_tpl_edit = QPushButton("Edit")  # type: ignore[attr-defined]
    win.btn_tpl_edit.clicked.connect(win._on_tpl_edit)  # type: ignore[attr-defined]
    win.btn_tpl_del = QPushButton("Delete")  # type: ignore[attr-defined]
    win.btn_tpl_del.clicked.connect(win._on_tpl_delete)  # type: ignore[attr-defined]
    for b in (win.btn_tpl_new, win.btn_tpl_edit, win.btn_tpl_del):
        tpl_btns.addWidget(b)
    tpl_btns.addStretch(1)
    tf.addLayout(tpl_btns, 1, 1, 1, 2)
    win.sec_youtube.addLayout(tf)

    win.sub_metadata = CollapsibleSection("Metadata", expanded=False)  # type: ignore[attr-defined]
    mf = QGridLayout()
    mf.addWidget(QLabel("Title:"), 1, 0)
    win.ed_title = QLineEdit()  # type: ignore[attr-defined]
    mf.addWidget(win.ed_title, 1, 1, 1, 2)
    mf.addWidget(QLabel("Description:"), 2, 0)
    win.ed_desc = QTextEdit()  # type: ignore[attr-defined]
    win.ed_desc.setFixedHeight(90)
    mf.addWidget(win.ed_desc, 2, 1, 1, 2)
    mf.addWidget(QLabel("Tags:"), 3, 0)
    win.ed_tags = QLineEdit()  # type: ignore[attr-defined]
    win.ed_tags.setPlaceholderText("comma, separated")
    mf.addWidget(win.ed_tags, 3, 1, 1, 2)
    mf.addWidget(QLabel("Category:"), 4, 0)
    win.cb_cat = QComboBox()  # type: ignore[attr-defined]
    for cid, name in YOUTUBE_CATEGORIES.items():
        win.cb_cat.addItem(f"{name}", cid)
    mf.addWidget(win.cb_cat, 4, 1)
    mf.addWidget(QLabel("Privacy:"), 4, 2)
    mf.addWidget(QLabel(""), 4, 3)
    win.cb_privacy = QComboBox()  # type: ignore[attr-defined]
    win.cb_privacy.addItems(["private", "unlisted", "public"])
    mf.addWidget(win.cb_privacy, 5, 1)
    win.ck_kids = QCheckBox("Made for Kids")  # type: ignore[attr-defined]
    mf.addWidget(win.ck_kids, 5, 2)
    mf.addWidget(QLabel("Playlist ID:"), 6, 0)
    win.ed_playlist = QLineEdit()  # type: ignore[attr-defined]
    win.ed_playlist.setPlaceholderText("(optional)")
    mf.addWidget(win.ed_playlist, 6, 1, 1, 2)
    win.sub_metadata.addLayout(mf)
    win.sec_youtube.addWidget(win.sub_metadata)

    win.sub_beat = CollapsibleSection("Beat / Artist", expanded=False)  # type: ignore[attr-defined]
    mf = QGridLayout()
    mf.addWidget(QLabel("Beat:"), 0, 0)
    hb = QHBoxLayout()
    win.ed_beat = QLineEdit()  # type: ignore[attr-defined]
    win.ed_beat.setPlaceholderText("Beat title ({{title}})")
    win.ed_artist = QLineEdit()  # type: ignore[attr-defined]
    win.ed_artist.setPlaceholderText("Artist ({{artist}})")
    win.ed_artist2 = QLineEdit()  # type: ignore[attr-defined]
    win.ed_artist2.setPlaceholderText("Artist 2 ({{artist2}})")
    hb.addWidget(win.ed_beat)
    hb.addWidget(win.ed_artist)
    hb.addWidget(win.ed_artist2)
    w = QWidget()
    w.setLayout(hb)
    mf.addWidget(w, 0, 1, 1, 2)
    win.sub_beat.addLayout(mf)
    win.sec_youtube.addWidget(win.sub_beat)

    win.sub_production = CollapsibleSection("Production", expanded=False)  # type: ignore[attr-defined]
    mf = QGridLayout()
    mf.addWidget(QLabel("Producer:"), 0, 0)
    win.ed_producer = QLineEdit()  # type: ignore[attr-defined]
    win.ed_producer.setPlaceholderText("Producer")
    mf.addWidget(win.ed_producer, 0, 1)
    mf.addWidget(QLabel("Genre:"), 0, 2)
    win.ed_genre = QLineEdit()  # type: ignore[attr-defined]
    win.ed_genre.setPlaceholderText("Genre")
    mf.addWidget(win.ed_genre, 0, 3)
    mf.addWidget(QLabel("BPM:"), 1, 0)
    win.ed_bpm = QLineEdit()  # type: ignore[attr-defined]
    win.ed_bpm.setPlaceholderText("BPM")
    mf.addWidget(win.ed_bpm, 1, 1)
    mf.addWidget(QLabel("Key:"), 1, 2)
    win.ed_key = QLineEdit()  # type: ignore[attr-defined]
    win.ed_key.setPlaceholderText("Key")
    mf.addWidget(win.ed_key, 1, 3)
    win.sub_production.addLayout(mf)
    win.sec_youtube.addWidget(win.sub_production)

    win.sub_publishing = CollapsibleSection("Publishing", expanded=False)  # type: ignore[attr-defined]
    mf = QGridLayout()
    mf.addWidget(QLabel("Purchase URL:"), 0, 0)
    win.ed_purchase = QLineEdit()  # type: ignore[attr-defined]
    win.ed_purchase.setPlaceholderText("https://... ({{purchase_url}})")
    mf.addWidget(win.ed_purchase, 0, 1, 1, 2)
    mf.addWidget(QLabel("Schedule:"), 1, 0)
    hs = QHBoxLayout()
    win.ck_schedule = QCheckBox("Publish later")  # type: ignore[attr-defined]
    win.ck_schedule.toggled.connect(win._on_schedule_toggled)  # type: ignore[attr-defined]
    win.dt_schedule = QDateTimeEdit()  # type: ignore[attr-defined]
    win.dt_schedule.setDisplayFormat("dd/MM/yyyy HH:mm")
    win.dt_schedule.setCalendarPopup(True)
    win.dt_schedule.setDateTime(QDateTime.currentDateTime().addDays(1))
    win.dt_schedule.setEnabled(False)
    win.cb_tz = QComboBox()  # type: ignore[attr-defined]
    win.cb_tz.addItems(COMMON_TIMEZONES)
    try:
        win.cb_tz.setCurrentText("Europe/Madrid")
    except Exception:
        pass
    win.cb_tz.setEnabled(False)
    hs.addWidget(win.ck_schedule)
    hs.addWidget(win.dt_schedule)
    hs.addWidget(win.cb_tz)
    w3 = QWidget()
    w3.setLayout(hs)
    mf.addWidget(w3, 1, 1, 1, 2)
    win.sub_publishing.addLayout(mf)
    win.sec_youtube.addWidget(win.sub_publishing)
    win.sections_layout.addWidget(win.sec_youtube)
    win.sections_layout.addStretch(1)
