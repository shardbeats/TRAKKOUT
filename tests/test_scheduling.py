"""Tests for scheduling helpers (stdlib zoneinfo only)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.utils.scheduling import (
    COMMON_TIMEZONES,
    ScheduleError,
    describe_rfc3339_in_tz,
    ensure_future_publish_at,
    local_to_utc_rfc3339,
    parse_rfc3339,
    resolve_timezone,
)


def test_common_timezones_non_empty():
    assert "UTC" in COMMON_TIMEZONES
    assert "Europe/Madrid" in COMMON_TIMEZONES


def test_resolve_timezone_ok_and_unknown():
    assert str(resolve_timezone("UTC")) == "UTC"
    with pytest.raises(ScheduleError):
        resolve_timezone("Mars/Olympus")


def test_local_to_utc_rfc3339_madrid_summer():
    # Europe/Madrid is UTC+2 in September.
    out = local_to_utc_rfc3339(datetime(2026, 9, 20, 20, 0), "Europe/Madrid")
    assert out == "2026-09-20T18:00:00Z"


def test_local_to_utc_none_raises():
    with pytest.raises(ScheduleError):
        local_to_utc_rfc3339(None, "UTC")  # type: ignore[arg-type]


def test_parse_rfc3339_variants():
    assert parse_rfc3339("2026-09-20T18:00:00Z").tzinfo is not None
    assert parse_rfc3339("2026-09-20T20:00:00+02:00").strftime("%H:%M") == "18:00"
    # Naive values are assumed UTC.
    assert parse_rfc3339("2026-09-20T18:00:00").tzinfo == timezone.utc
    with pytest.raises(ScheduleError):
        parse_rfc3339("not-a-date")


def test_ensure_future_publish_at():
    assert ensure_future_publish_at("") == ""
    future = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert ensure_future_publish_at(future) == future
    past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with pytest.raises(ScheduleError):
        ensure_future_publish_at(past)


def test_describe_valid_and_invalid():
    described = describe_rfc3339_in_tz("2026-09-20T18:00:00Z", "Europe/Madrid")
    assert described.startswith("20/09/2026 20:00")
    assert "Europe/Madrid" in described
    assert describe_rfc3339_in_tz("broken", "Europe/Madrid") == "broken"
