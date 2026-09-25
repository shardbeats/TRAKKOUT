"""Tests for time formatting and secret redaction in logs."""
from __future__ import annotations

import logging

from app.utils.formatting import fmt_hms
from app.utils.logging_setup import REDACTED, RedactingFilter, setup_logging


def test_fmt_hms():
    assert fmt_hms(None) == "--:--"
    assert fmt_hms(-5) == "--:--"
    assert fmt_hms(0) == "00:00"
    assert fmt_hms(65) == "01:05"
    assert fmt_hms(3661) == "01:01:01"


def test_redacting_filter_hides_secrets():
    filt = RedactingFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="token ya29.secret123 and refresh_token=abc and client_secret: xyz",
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is True
    assert "ya29.secret123" not in record.msg
    assert "abc" not in record.msg
    assert REDACTED in record.msg


def test_redacting_filter_keeps_normal_messages():
    filt = RedactingFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Ready. FFmpeg 7.1",
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is True
    assert record.msg == "Ready. FFmpeg 7.1"


def test_setup_logging_creates_file(tmp_path):
    log_file = setup_logging(tmp_path / "logs")
    assert log_file.exists()
    assert log_file.name == "app.log"
