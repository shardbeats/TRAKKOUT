"""TRAKKOUT entry point."""
from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import SettingsStore
from app.utils.logging_setup import setup_logging

log = logging.getLogger("trakkout")


def main() -> int:
    store = SettingsStore()
    log_dir = PROJECT_ROOT / "logs"
    setup_logging(log_dir)
    settings = store.load()

    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        from app.ui.main_window import MainWindow
        
        # Verify that PySide6 is properly installed
        if not hasattr(QApplication, '__class__'):
            log.error("PySide6 is not installed. Run: pip install -r requirements.txt")
            print("ERROR: PySide6 not installed. Run: pip install -r requirements.txt")
            return 2

    except ImportError as e:
        log.error(f"ImportError loading PySide6: {e}")
        print(f"ERROR: PySide6 not installed. Run: pip install -r requirements.txt")
        return 2

    def _hook(exc_type, exc_value, tb):
        msg = "".join(traceback.format_exception(exc_type, exc_value, tb))[-3000:]
        log.error("Unhandled exception:\n%s", msg)
        try:
            QMessageBox.critical(None, "TRAKKOUT",
                                 "An unexpected error occurred.\nCheck logs/app.log for technical details.")
        except Exception:
            pass

    sys.excepthook = _hook

    app = QApplication(sys.argv)
    app.setApplicationName("TRAKKOUT")
    app.setOrganizationName("TRAKKOUT")
    try:
        from app.ui.theme import apply_theme
        apply_theme(app)
    except Exception as exc:
        log.warning("Could not apply theme: %s", exc)
    win = MainWindow(PROJECT_ROOT, store)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
