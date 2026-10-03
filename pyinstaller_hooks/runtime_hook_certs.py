"""Runtime hook: make HTTPS work inside the frozen TRAKKOUT.exe.

PyInstaller does not set SSL_CERT_FILE automatically, so certifi/httplib2/
requests/google-auth fail to validate googleapis.com certificates and every
YouTube/Google call fails. This runs at startup (see TRAKKOUT.spec
runtime_hooks) before any network code.
"""
import os
import sys
from pathlib import Path


def _apply() -> None:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidates: list[Path] = []
    try:
        import certifi  # type: ignore

        candidates.append(Path(certifi.where()))
    except Exception:
        pass
    candidates += [
        base / "certifi" / "cacert.pem",
        base / "_certifi" / "cacert.pem",
        base / "httplib2" / "cacerts.txt",
    ]
    for pem in candidates:
        try:
            if pem.is_file():
                os.environ.setdefault("SSL_CERT_FILE", str(pem))
                os.environ.setdefault("REQUESTS_CA_BUNDLE", str(pem))
                # httplib2 honours HTTPLIB2_CA_CERTS in some versions.
                os.environ.setdefault("HTTPLIB2_CA_CERTS", str(pem))
                break
        except Exception:
            continue


_apply()
