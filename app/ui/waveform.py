"""Waveform widget with two draggable clip selectors (Short Clip section).

Two-way sync design (loop-free by construction):
- user drags   → ``rangeChanged(start, end)`` → MainWindow sets the spinboxes
- spinbox edit → ``set_range()`` (silent, never emits) → widget repaints
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.ffmpeg.waveform import clamp_range, time_to_x, x_to_time
from app.utils.formatting import fmt_hms


class WaveformWidget(QWidget):
    """Audio peaks with draggable start/end handles. All times in seconds."""

    rangeChanged = Signal(float, float)

    _PAD = 8.0
    _GRAB_PX = 13.0

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("waveform")
        self.setMinimumHeight(110)
        self.setMouseTracking(True)
        self._peaks: list[float] = []
        self._duration = 0.0
        self._start = 0.0
        self._end = 0.0
        self._loading = False
        self._drag: str | None = None

    # ---------------- data API (never emits) ----------------

    def has_peaks(self) -> bool:
        return bool(self._peaks)

    def set_loading(self, loading: bool = True) -> None:
        self._loading = loading
        self.update()

    def set_duration(self, duration: float) -> None:
        self._duration = max(0.0, float(duration or 0.0))
        self._start, self._end = clamp_range(self._start, self._end, self._duration)
        self.update()

    def set_peaks(self, peaks: list[float] | None, duration: float | None = None) -> None:
        self._peaks = [min(1.0, max(0.0, float(p or 0.0))) for p in (peaks or [])]
        if duration is not None:
            self._duration = max(0.0, float(duration))
        self._loading = False
        self._start, self._end = clamp_range(self._start, self._end, self._duration)
        self.update()

    def set_range(self, start: float, end: float) -> None:
        """Move handles silently (called when spinboxes change)."""
        self._start, self._end = clamp_range(start, end, self._duration)
        self.update()

    def current_range(self) -> tuple[float, float]:
        return (self._start, self._end)

    def clear(self) -> None:
        self._peaks = []
        self._duration = 0.0
        self._start = 0.0
        self._end = 0.0
        self._loading = False
        self._drag = None
        self.update()

    # ---------------- painting ----------------

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            self._paint(painter)
        finally:
            painter.end()

    def _paint(self, p: QPainter) -> None:
        w, h = float(self.width()), float(self.height())
        p.fillRect(self.rect(), QColor("#151617"))
        if self._loading:
            p.setPen(QColor("#92959A"))
            p.drawText(self.rect(), Qt.AlignCenter, "Loading waveform…")
            return
        if not self._peaks or self._duration <= 0:
            p.setPen(QColor("#6E7175"))
            p.drawText(self.rect(), Qt.AlignCenter, "No waveform — load an audio file")
            return
        mid = h / 2.0
        amp = max(4.0, h / 2.0 - 18.0)
        n = len(self._peaks)
        xs = time_to_x(self._start, self._duration, w, self._PAD)
        xe = time_to_x(self._end, self._duration, w, self._PAD)
        # Dim the unselected regions.
        dim = QColor(0, 0, 0, 110)
        p.fillRect(QRectF(0, 0, xs, h), dim)
        p.fillRect(QRectF(xe, 0, w - xe, h), dim)
        # Selection wash.
        p.fillRect(QRectF(xs, 0, max(0.0, xe - xs), h), QColor(245, 166, 35, 26))
        # Bars.
        pen_in = QPen(QColor("#F5A623"))
        pen_out = QPen(QColor("#45474A"))
        current_pen = None
        pad, span = self._PAD, max(1.0, w - 2.0 * self._PAD)
        for x_px in range(int(pad), int(w - pad) + 1):
            frac = (x_px - pad) / span
            idx = min(n - 1, int(frac * n))
            v = self._peaks[idx] if 0 <= idx < n else 0.0
            inside = xs - 0.5 <= x_px <= xe + 0.5
            pen = pen_in if inside else pen_out
            if pen is not current_pen:
                p.setPen(pen)
                current_pen = pen
            y0 = mid - v * amp
            p.drawLine(x_px, int(y0), x_px, int(mid + v * amp))
        # Center line.
        p.setPen(QPen(QColor("#33363B")))
        p.drawLine(int(pad), int(mid), int(w - pad), int(mid))
        # Handles + time labels.
        handle_pen = QPen(QColor("#FFB52E"))
        handle_pen.setWidth(4)
        p.setPen(handle_pen)
        p.drawLine(int(xs), 0, int(xs), int(h))
        p.drawLine(int(xe), 0, int(xe), int(h))
        p.setPen(QColor("#E5E5E5"))
        p.drawText(QRectF(xs - 44, 2, 88, 14), Qt.AlignCenter, fmt_hms(self._start))
        p.drawText(QRectF(xe - 44, 2, 88, 14), Qt.AlignCenter, fmt_hms(self._end))

    # ---------------- mouse ----------------

    def _handle_at(self, x: float) -> str | None:
        if not self._peaks or self._duration <= 0:
            return None
        w = float(self.width())
        xs = time_to_x(self._start, self._duration, w, self._PAD)
        xe = time_to_x(self._end, self._duration, w, self._PAD)
        ds, de = abs(x - xs), abs(x - xe)
        if min(ds, de) > self._GRAB_PX:
            return None
        return "start" if ds <= de else "end"

    def _apply_drag(self, which: str, t: float) -> None:
        if which == "start":
            s, e = clamp_range(t, self._end, self._duration)
        else:
            s, e = clamp_range(self._start, t, self._duration)
        if (s, e) != (self._start, self._end):
            self._start, self._end = s, e
            self.update()
            self.rangeChanged.emit(s, e)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton:
            return
        x = float(event.position().x())
        handle = self._handle_at(x)
        if handle is None:
            if not self._peaks or self._duration <= 0:
                return
            # Click-to-jump: grab the nearest handle.
            t = x_to_time(x, self._duration, float(self.width()), self._PAD)
            handle = ("start" if abs(t - self._start) <= abs(t - self._end)
                      else "end")
        self._drag = handle
        self._apply_drag(handle, x_to_time(x, self._duration,
                                           float(self.width()), self._PAD))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        x = float(event.position().x())
        if self._drag is not None and event.buttons() & Qt.LeftButton:
            self._apply_drag(self._drag, x_to_time(x, self._duration,
                                                   float(self.width()), self._PAD))
            return
        # Hover feedback (no buttons pressed).
        self.setCursor(Qt.SizeHorCursor if self._handle_at(x) is not None
                       else Qt.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag = None
