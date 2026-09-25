"""Reusable interface components: sidebar and collapsible sections.

No business logic: navigation and containers only.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget,
)


class CollapsibleSection(QFrame):
    """Panel with a header that collapses/expands its content (real collapse).

    Collapsed: only shows the header; controls are hidden with
    setVisible(False) but keep their state.
    """

    def __init__(self, title: str, icon: str = "", expanded: bool = True,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("section")
        self._title = title
        self._icon = icon
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.header = QPushButton()
        self.header.setObjectName("sectionHeader")
        self.header.setCheckable(True)
        self.header.setChecked(expanded)
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.toggled.connect(self._on_toggled)
        lay.addWidget(self.header)

        self.content = QFrame()
        self.content.setObjectName("sectionContent")
        self._content_lay = QVBoxLayout(self.content)
        self._content_lay.setContentsMargins(10, 8, 10, 10)
        self._content_lay.setSpacing(6)
        lay.addWidget(self.content)

        self._refresh_header()
        self.content.setVisible(expanded)

    def _refresh_header(self):
        arrow = "▾" if self.header.isChecked() else "▸"
        prefix = f"{self._icon}  " if self._icon else ""
        self.header.setText(f"{arrow}  {prefix}{self._title}")

    def _on_toggled(self, checked: bool):
        self.content.setVisible(checked)
        self._refresh_header()

    def setExpanded(self, expanded: bool):
        self.header.setChecked(expanded)

    def isExpanded(self) -> bool:
        return self.header.isChecked()

    def addWidget(self, w: QWidget):
        self._content_lay.addWidget(w)

    def addLayout(self, layout):
        self._content_lay.addLayout(layout)


NAV_ITEMS = [
    ("media", "♪", "Media"),
    ("video", "▣", "Video"),
    ("texto", "T", "Text"),
    ("youtube", "▶", "YouTube"),
]


class Sidebar(QFrame):
    """Narrow navigation sidebar + account status."""

    navigated = Signal(str)  # section id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 8, 6, 8)
        lay.setSpacing(4)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        for sid, icon, label in NAV_ITEMS:
            b = QPushButton(f"{icon}\n{label}")
            b.setObjectName("navButton")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda checked=False, _sid=sid: self.navigated.emit(_sid))
            self._group.addButton(b)
            self._buttons[sid] = b
            lay.addWidget(b)
        self._buttons["media"].setChecked(True)

        lay.addStretch(1)
        self.lbl_account_dot = QLabel("○")
        self.lbl_account_dot.setObjectName("accountDot")
        self.lbl_account_dot.setAlignment(Qt.AlignCenter)
        self.lbl_account_name = QLabel("Not connected")
        self.lbl_account_name.setObjectName("accountName")
        self.lbl_account_name.setAlignment(Qt.AlignCenter)
        self.lbl_account_name.setWordWrap(True)
        lay.addWidget(self.lbl_account_dot)
        lay.addWidget(self.lbl_account_name)

    def set_active(self, sid: str):
        if sid in self._buttons:
            self._buttons[sid].setChecked(True)

    def set_account(self, connected: bool, name: str):
        self.lbl_account_dot.setText("●" if connected else "○")
        self.lbl_account_dot.setProperty("connected", "true" if connected else "false")
        # Refresh styling after changing the dynamic property.
        self.lbl_account_dot.style().unpolish(self.lbl_account_dot)
        self.lbl_account_dot.style().polish(self.lbl_account_dot)
        self.lbl_account_name.setText(name or ("Connected" if connected else "Not connected"))
