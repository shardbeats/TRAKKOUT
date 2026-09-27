"""Headless history-autosave tests (offscreen, isolated APPDATA).

Covers link → edit → flush, selection-change flush, stale links and the
manual Update path. QApplication without event loop: signals fire
synchronously (direct connections), timers never elapse on their own.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.config.settings import SettingsStore
from app.models.models import HistoryEntry
from app.ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def win(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.app_data_dir",
                        lambda: tmp_path / "appdata")
    store = SettingsStore(config_path=tmp_path / "settings.json")
    w = MainWindow(Path("."), store)
    yield w
    w.close()


def _add(win, **kwargs) -> int:
    entry = HistoryEntry(beat_name="Beat", status="Generated", **kwargs)
    return win.history.add(entry)


def test_autosave_flow(win):
    row_id = _add(win, title="Old")
    win._refresh_history_table()
    win._set_history_link(row_id)
    assert win._history_link_id == row_id

    win.ed_title.setText("New")  # fires textChanged synchronously
    assert win._history_dirty is True
    assert win._history_save_timer.isActive()

    win._flush_history_link()
    assert win._history_dirty is False
    assert win._history_link_id == row_id
    assert win.history.list()[0].title == "New"


def test_no_link_no_save(win):
    row_id = _add(win, title="Keep")
    win._refresh_history_table()
    assert win._history_link_id is None
    win.ed_title.setText("Changed")
    assert win._history_dirty is False
    win._flush_history_link()
    assert win.history.list()[0].title == "Keep"


def test_stale_link_clears(win):
    row_id = _add(win, title="Gone")
    win._refresh_history_table()
    win._set_history_link(row_id)
    win.ed_title.setText("Edited")
    win.history.clear()
    win._flush_history_link()
    assert win._history_link_id is None
    assert win._history_dirty is False


def test_selection_change_flushes(win):
    _add(win, title="A")
    _add(win, title="B")
    win._refresh_history_table()
    # list() is newest-first: row 0 = B, row 1 = A.
    linked = [e for e in win.history.list() if e.title == "A"][0]
    win._set_history_link(linked.id)
    win.ed_title.setText("A-edited")
    win.tbl_hist.selectRow(1)  # fires itemSelectionChanged synchronously
    by_title = {e.title for e in win.history.list()}
    assert "A-edited" in by_title


def test_manual_update_still_works(win):
    _add(win, title="Before")
    win._refresh_history_table()
    win.tbl_hist.selectRow(0)
    win.ed_title.setText("Manual")
    win._history_update_selected()
    assert win.history.list()[0].title == "Manual"


def test_log_history_returns_id(win):
    new_id = win._log_history(HistoryEntry(beat_name="X", status="Generated"))
    assert isinstance(new_id, int) and new_id > 0
