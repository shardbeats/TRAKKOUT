"""Builders de la shell principal: menús, sidebar y QStackedWidget."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QWidget, QFrame, QScrollArea,
)

if TYPE_CHECKING:
    from app.ui.mixins.protocol import MainWindowProtocol


def build_shell(win: MainWindowProtocol) -> None:
    """Crea central + menús + sidebar + views + scroll. Sin secciones."""
    from PySide6.QtGui import QAction, QActionGroup

    from app.ui.sections import Sidebar

    central = QWidget()
    win.setCentralWidget(central)

    menubar = win.menuBar()
    m_file = menubar.addMenu("&File")
    act_settings = QAction("Settings…", win)
    act_settings.triggered.connect(win._open_settings)  # type: ignore[attr-defined]
    m_file.addAction(act_settings)
    act_oauth_help = QAction("How to set up Google OAuth…", win)
    act_oauth_help.triggered.connect(win._show_oauth_help)  # type: ignore[attr-defined]
    m_file.addAction(act_oauth_help)
    act_quit = QAction("Exit", win)
    act_quit.triggered.connect(win.close)
    m_file.addAction(act_quit)

    m_view = menubar.addMenu("&View")
    win._view_group = QActionGroup(win)  # type: ignore[attr-defined]
    win._view_group.setExclusive(True)
    win._view_actions = []  # type: ignore[attr-defined]
    for i, (label, shortcut) in enumerate(
            [("Main", "Ctrl+1"), ("Queue", "Ctrl+2"),
             ("History", "Ctrl+3"), ("Log", "Ctrl+4")]):
        act = QAction(label, win, checkable=True)
        act.setShortcut(shortcut)
        act.triggered.connect(lambda checked=False, idx=i: win._show_view(idx))
        m_view.addAction(act)
        win._view_group.addAction(act)
        win._view_actions.append(act)
    win._view_actions[0].setChecked(True)

    root = QHBoxLayout(central)
    root.setContentsMargins(8, 8, 8, 8)
    root.setSpacing(8)
    win.sidebar = Sidebar()  # type: ignore[attr-defined]
    win.sidebar.setFixedWidth(124)
    win.sidebar.navigated.connect(win._goto_section)  # type: ignore[attr-defined]
    root.addWidget(win.sidebar)

    from PySide6.QtWidgets import QStackedWidget
    win.views = QStackedWidget()  # type: ignore[attr-defined]
    root.addWidget(win.views, 1)

    page_main = QWidget()
    page_main_layout = QVBoxLayout(page_main)
    page_main_layout.setContentsMargins(0, 0, 0, 0)
    page_main_layout.setSpacing(8)
    win.views.addWidget(page_main)
    win._page_main_layout = page_main_layout  # type: ignore[attr-defined]

    win.scroll = QScrollArea()  # type: ignore[attr-defined]
    win.scroll.setWidgetResizable(True)
    win.scroll.setFrameShape(QFrame.NoFrame)
    scroll_inner = QWidget()
    win.sections_layout = QVBoxLayout(scroll_inner)  # type: ignore[attr-defined]
    win.sections_layout.setContentsMargins(0, 0, 2, 0)
    win.sections_layout.setSpacing(8)
    win.scroll.setWidget(scroll_inner)
    page_main_layout.addWidget(win.scroll, 1)

    win._sections = {}  # type: ignore[attr-defined]
