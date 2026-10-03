"""TRAKKOUT entry point."""
from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- PyInstaller frozen support -------------------------------------------------
# In a one-file exe, __file__ lives inside a temp dir (sys._MEIPASS) that is
# deleted on exit and must never be used for writable data (logs, presets).
# PROJECT_ROOT is kept for bundled read-only resources; writable data goes to
# %APPDATA%/TRAKKOUT when frozen.
IS_FROZEN = bool(getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"))


def _bundle_dir() -> Path:
    """Read-only dir with bundled resources (works frozen and from source)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return PROJECT_ROOT


def _writable_dir() -> Path:
    """Writable dir: next to the exe when frozen, PROJECT_ROOT from source."""
    if IS_FROZEN:
        try:
            return Path(sys.executable).resolve().parent
        except Exception:
            pass
        if os.name == "nt":
            base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
            return Path(base) / "TRAKKOUT"
        return Path.home() / ".trakkout"
    return PROJECT_ROOT


if not IS_FROZEN:
    sys.path.insert(0, str(PROJECT_ROOT))


def _ensure_ssl_certs() -> None:
    """Point SSL/Requests/Google libs at the bundled CA bundle when frozen.

    This is the #1 cause of "can't connect to Google/YouTube" in PyInstaller
    exes: certifi/httplib2/requests can't find their cacert.pem once frozen,
    so every HTTPS call to googleapis.com fails with SSL errors.
    The .spec bundles certifi + httplib2 data; here we just export the path.
    """
    try:
        import certifi  # type: ignore

        bundle = certifi.where()
        if bundle and Path(bundle).is_file():
            os.environ.setdefault("SSL_CERT_FILE", bundle)
            os.environ.setdefault("REQUESTS_CA_BUNDLE", bundle)
            os.environ.setdefault("HTTPLIB2_CA_CERTS", bundle)
    except Exception:
        pass


_ensure_ssl_certs()

from app.config.settings import SettingsStore
from app.utils.logging_setup import setup_logging

log = logging.getLogger("trakkout")


def main() -> int:
    store = SettingsStore()
    if IS_FROZEN:
        # Logs next to settings in %APPDATA% (always writable), never in _MEIPASS.
        try:
            log_dir = store.config_path.parent / "logs"
        except Exception:
            log_dir = _writable_dir() / "logs"
    else:
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
        from PySide6.QtWidgets import QStyleFactory
        if "Fusion" in QStyleFactory.keys():
            # Native Windows styles compute identical hit rects for both
            # spinbox arrows under stylesheets (up arrow never fires);
            # Fusion is software-only and identical on every machine.
            app.setStyle("Fusion")
    except Exception as exc:
        log.warning("Could not force Fusion style: %s", exc)
    log.info("Qt style: %s", app.style().objectName())
    try:
        from app.ui.theme import apply_theme
        apply_theme(app)
    except Exception as exc:
        log.warning("Could not apply theme: %s", exc)
    win = MainWindow(_bundle_dir(), store)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
