"""Sesión de beat: audio nuevo / Clear resetean sin tocar el historial."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QDateTimeEdit, QDoubleSpinBox,
        QLabel, QLineEdit, QSpinBox, QTableWidget, QTextEdit,
    )
except ImportError as exc:
    if "libEGL.so.1" in str(exc):
        pytest.skip("PySide6 QtGui requires libEGL.so.1", allow_module_level=True)
    raise

from app.models.models import BeatMetadata, HistoryEntry
from app.ui.mixins.base import FeedbackMixin
from app.ui.mixins.collectors import CollectorsMixin
from app.ui.mixins.history_mixin import HistoryMixin
from app.ui.mixins.media import MediaMixin
from app.ui.mixins.session_mixin import SessionMixin
from app.ui.waveform import WaveformWidget


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


class FakeHistory:
    def __init__(self, entries):
        self.entries = list(entries)
        self.updated: list[int] = []

    def list(self, limit: int = 200):
        return list(self.entries)

    def update(self, entry) -> None:
        self.updated.append(entry.id)


class Stub(SessionMixin, MediaMixin, HistoryMixin, CollectorsMixin,
           FeedbackMixin):
    """Ventana mínima con widgets reales para probar la sesión."""

    def __init__(self):
        self.settings = SimpleNamespace(
            default_category="10", default_privacy="private",
            made_for_kids=False, overlay_enabled=False,
            overlay_text="{beat_name}", overlay_position="bottom-center",
            overlay_font_size=48, overlay_opacity=0.9, overlay_margin=60,
        )
        self.beat = BeatMetadata()
        self.history = FakeHistory([])
        self.audio_info = None
        self.image_info = None
        self.current_video = ""
        self.channels = []
        self._session_audio = ""
        self._fresh_cover = False
        self._history_link_id = None
        self._history_dirty = False
        self._history_save_timer = QTimer()
        self._history_save_timer.setSingleShot(True)
        self._trim_audio_path = ""
        self._wave_audio_path = ""
        self._last_gen_audio = ""
        self._last_trim = (0.0, 0.0)
        self._op_start = 0.0
        self._op_total = 0.0

        self.ed_audio = QLineEdit()
        self.ed_cover = QLineEdit()
        self.ed_beat = QLineEdit()
        self.ed_artist = QLineEdit()
        self.ed_artist2 = QLineEdit()
        self.ed_producer = QLineEdit()
        self.ed_genre = QLineEdit()
        self.ed_bpm = QLineEdit()
        self.ed_key = QLineEdit()
        self.ed_purchase = QLineEdit()
        self.ed_title = QLineEdit()
        self.ed_tags = QLineEdit()
        self.ed_playlist = QLineEdit()
        self.ed_desc = QTextEdit()
        self.ed_overlay = QLineEdit()
        self.ed_bg = QLineEdit("000000")
        self.cb_cat = QComboBox()
        self.cb_cat.addItem("Film & Animation", "1")
        self.cb_cat.addItem("Music", "10")
        self.cb_cat.setCurrentIndex(1)
        self.cb_privacy = QComboBox()
        self.cb_privacy.addItems(["private", "unlisted", "public"])
        self.cb_ov_pos = QComboBox()
        self.cb_ov_pos.addItems(["top-left", "top-center", "top-right", "center",
                                 "bottom-left", "bottom-center", "bottom-right"])
        self.cb_ov_pos.setCurrentText("bottom-center")
        self.ck_kids = QCheckBox()
        self.ck_overlay = QCheckBox()
        self.ck_schedule = QCheckBox()
        self.cb_tz = QComboBox()
        self.cb_tz.addItems(["Europe/Madrid", "UTC"])
        self.dt_schedule = QDateTimeEdit()
        self.sp_ov_size = QSpinBox()
        self.sp_ov_size.setRange(12, 160)
        self.sp_ov_op = QDoubleSpinBox()
        self.sp_ov_op.setRange(0.1, 1.0)
        self.sp_ov_margin = QSpinBox()
        self.sp_ov_margin.setRange(0, 300)
        self.sp_trim_start = QDoubleSpinBox()
        self.sp_trim_start.setRange(0.0, 3600.0)
        self.sp_trim_end = QDoubleSpinBox()
        self.sp_trim_end.setRange(0.0, 3600.0)
        self.wave = WaveformWidget()
        self.lbl_cover_prev = QLabel()
        self.lbl_media_info = QLabel()
        self.lbl_source = QLabel()
        self.lbl_clip_info = QLabel()
        self.lbl_status = QLabel()
        self.tbl_hist = QTableWidget(0, 6)
        self._sb = SimpleNamespace(showMessage=lambda *a: None)
        # Cableado que en la app hacen los builders (views/action_views,
        # views/youtube_section): autosave + toggle de schedule.
        self._wire_history_autosave()
        self.ck_schedule.toggled.connect(self._on_schedule_toggled)
        # Sin binarios: el probeo se sustituye por test.
        self._probe_audio = lambda p: None  # noqa: E731
        self._probe_image = lambda p: None  # noqa: E731

    def statusBar(self):
        return self._sb


def _fill_old_beat(w: Stub) -> None:
    w.ed_audio.setText("A.mp3")
    w.ed_cover.setText("A.png")
    w.ed_beat.setText("OldBeat")
    w.ed_title.setText("OldTitle")
    w.ed_tags.setText("old, tags")
    w.ed_desc.setPlainText("Old description")
    w.ed_producer.setText("OldProd")
    w.cb_privacy.setCurrentText("unlisted")
    w.sp_trim_start.setValue(5.0)
    w.sp_trim_end.setValue(20.0)
    w.ed_overlay.setText("Custom overlay")
    w._session_audio = "A.mp3"


def test_new_audio_resets_form_and_preserves_old_entry(qapp):
    w = Stub()
    _fill_old_beat(w)
    w.history = FakeHistory([HistoryEntry(id=7, beat_name="OldBeat",
                                          audio_path="A.mp3", title="OldTitle")])
    w._set_history_link(7)
    w.ed_title.setText("OldTitle edit")  # dirty sobre la entrada 7

    w._set_audio_file("B.mp3")

    assert w._history_link_id is None
    assert w.ed_audio.text() == "B.mp3"
    assert w.ed_title.text() == ""
    assert w.ed_beat.text() == ""
    assert w.ed_tags.text() == ""
    assert w.ed_desc.toPlainText() == ""
    assert w.ed_cover.text() == ""  # el cover viejo no se mezcla
    assert w.ed_producer.text() == ""
    assert w.ed_overlay.text() == "{beat_name}"  # default de settings
    assert w.cb_privacy.currentText() == "private"
    assert w.sp_trim_start.value() == 0.0
    assert w.sp_trim_end.value() == 0.0
    assert w._session_audio == "B.mp3"
    # La fila vieja conserva lo suyo (flush previo con el audio viejo).
    assert w.history.updated == [7]
    old = w.history.entries[0]
    assert old.audio_path == "A.mp3"
    assert old.title == "OldTitle edit"


def test_fresh_cover_survives_following_audio_pick(qapp):
    w = Stub()
    _fill_old_beat(w)
    w._set_cover_file("B.png")  # flujo cover-primero
    assert w._fresh_cover is True

    w._set_audio_file("B.mp3")

    assert w.ed_cover.text() == "B.png"
    assert w.ed_title.text() == ""  # el resto sí se reseteó
    assert w._fresh_cover is False  # one-shot consumido


def test_same_audio_only_reprobes(qapp):
    w = Stub()
    _fill_old_beat(w)
    w._set_audio_file("A.mp3")

    assert w.ed_title.text() == "OldTitle"
    assert w.ed_cover.text() == "A.png"
    assert w._history_link_id is None


def test_clear_resets_everything_to_defaults(qapp):
    w = Stub()
    _fill_old_beat(w)
    w.history = FakeHistory([HistoryEntry(id=7, beat_name="OldBeat",
                                          audio_path="A.mp3")])
    w._set_history_link(7)
    w.ck_schedule.setChecked(True)
    assert w.cb_privacy.isEnabled() is False  # el schedule lo bloquea

    w._clear_media()

    assert w._history_link_id is None
    assert w.ed_audio.text() == ""
    assert w.ed_cover.text() == ""
    assert w.ed_title.text() == ""
    assert w.ed_desc.toPlainText() == ""
    assert w.cb_privacy.currentText() == "private"
    assert w.cb_privacy.isEnabled() is True
    assert w.ck_schedule.isChecked() is False
    assert w._session_audio == ""
    assert w._fresh_cover is False
