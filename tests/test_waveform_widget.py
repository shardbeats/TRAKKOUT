"""Headless widget tests: drag math via simulated mouse events (offscreen).

Geometry-only assertions (no fonts, no pixels): safe on any platform.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from app.ffmpeg.waveform import time_to_x
from app.ui.waveform import WaveformWidget

WIDTH = 600.0
DURATION = 200.0
PAD = 8.0


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _make(qapp) -> WaveformWidget:
    w = WaveformWidget()
    w.resize(int(WIDTH), 120)
    peaks = [abs((i % 20) - 10) / 10.0 for i in range(100)]
    w.set_peaks(peaks, DURATION)
    w.set_range(30.0, 60.0)
    return w


def _press(x: float) -> QMouseEvent:
    return QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(x, 60.0),
                       Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)


def _move(x: float) -> QMouseEvent:
    return QMouseEvent(QEvent.Type.MouseMove, QPointF(x, 60.0),
                       Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)


def _release(x: float) -> QMouseEvent:
    return QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(x, 60.0),
                       Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                       Qt.KeyboardModifier.NoModifier)


def _x(t: float) -> float:
    return time_to_x(t, DURATION, WIDTH, PAD)


def test_drag_start_handle(qapp):
    w = _make(qapp)
    emitted: list = []
    w.rangeChanged.connect(lambda s, e: emitted.append((s, e)))
    w.mousePressEvent(_press(_x(30.0) - 3.0))  # grab start handle
    w.mouseMoveEvent(_move(_x(40.0)))
    w.mouseReleaseEvent(_release(_x(40.0)))
    assert w.current_range() == pytest.approx((40.0, 60.0))
    assert emitted and emitted[-1] == pytest.approx((40.0, 60.0))


def test_drag_end_handle_clamped_to_duration(qapp):
    w = _make(qapp)
    emitted: list = []
    w.rangeChanged.connect(lambda s, e: emitted.append((s, e)))
    w.mousePressEvent(_press(_x(60.0) + 2.0))  # grab end handle
    w.mouseMoveEvent(_move(WIDTH + 500.0))  # way past the edge
    w.mouseReleaseEvent(_release(WIDTH + 500.0))
    assert w.current_range() == pytest.approx((30.0, 200.0))


def test_click_jumps_nearest_handle(qapp):
    w = _make(qapp)
    w.mousePressEvent(_press(_x(150.0)))  # far from both: nearest is end
    w.mouseReleaseEvent(_release(_x(150.0)))
    assert w.current_range() == pytest.approx((30.0, 150.0))


def test_set_range_is_silent_and_clamped(qapp):
    w = _make(qapp)
    emitted: list = []
    w.rangeChanged.connect(lambda s, e: emitted.append((s, e)))
    w.set_range(10.0, 20.0)
    assert emitted == []
    assert w.current_range() == (10.0, 20.0)
    w.set_range(-5.0, 999.0)
    assert w.current_range() == (0.0, 200.0)


def test_handles_cannot_cross(qapp):
    w = _make(qapp)
    w.mousePressEvent(_press(_x(30.0)))
    w.mouseMoveEvent(_move(_x(120.0)))  # drag start past end
    w.mouseReleaseEvent(_release(_x(120.0)))
    s, e = w.current_range()
    assert s <= e
