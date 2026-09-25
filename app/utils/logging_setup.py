"""Centralized logging. Tokens/secrets are redacted before writing."""
from __future__ import annotations

import logging
import re
from pathlib import Path


_SENSITIVE_PATTERNS = [
    re.compile(r"(ya29\.[A-Za-z0-9\-_\.]+)"),
    re.compile(r"(refresh[_\- ]?token['\"\s:=]+)([^\s'\"]+)", re.IGNORECASE),
    re.compile(r"(client[_\- ]?secret['\"\s:=]+)([^\s'\"]+)", re.IGNORECASE),
    re.compile(r"(access[_\- ]?token['\"\s:=]+)([^\s'\"]+)", re.IGNORECASE),
]

REDACTED = "***REDACTED***"


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            for rx in _SENSITIVE_PATTERNS:
                msg = rx.sub(REDACTED, msg)
            record.msg = msg
            record.args = ()
        except Exception:
            pass
        return True


_configured = False


def setup_logging(log_dir: str | Path, level: int = logging.INFO) -> Path:
    """Set up file + console logging. Return the log path."""
    global _configured
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    root = logging.getLogger()
    root.setLevel(level)
    filt = RedactingFilter()

    if not _configured:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.addFilter(filt)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"))
        root.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.addFilter(filt)
        ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        root.addHandler(ch)
        _configured = True
    return log_file
