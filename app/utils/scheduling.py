"""Local date/time + timezone to UTC RFC 3339 conversion for YouTube.

The YouTube Data API expects status.publishAt in RFC 3339 format (e.g.
2026-09-20T18:00:00Z). The GUI collects local date/time + IANA timezone
(e.g. Europe/Madrid) and it is converted to UTC here. Stdlib only (zoneinfo).
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

COMMON_TIMEZONES = [
    "Europe/Madrid",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Atlantic/Canary",
    "America/Mexico_City",
    "America/Bogota",
    "America/Lima",
    "America/Santiago",
    "America/Argentina/Buenos_Aires",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "UTC",
]


class ScheduleError(ValueError):
    pass


def resolve_timezone(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo((tz_name or "").strip() or "UTC")
    except ZoneInfoNotFoundError as exc:
        raise ScheduleError(
            f"Unknown timezone: {tz_name!r}. Pick one from the list."
        ) from exc


def local_to_utc_rfc3339(naive_local: datetime, tz_name: str) -> str:
    """Convert a naive datetime (local time in tz_name) to 'YYYY-MM-DDTHH:MM:SSZ'."""
    if naive_local is None:
        raise ScheduleError("Empty date/time.")
    tz = resolve_timezone(tz_name)
    aware = naive_local.replace(tzinfo=tz)
    utc = aware.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_rfc3339(value: str) -> datetime:
    try:
        v = (value or "").strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
    except (ValueError, TypeError) as exc:
        raise ScheduleError(f"Invalid scheduled date: {value!r}.") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def ensure_future_publish_at(publish_at: str, margin_seconds: int = 60) -> str:
    """Validate that publishAt is in the future. Return the normalized value."""
    if not (publish_at or "").strip():
        return ""
    dt = parse_rfc3339(publish_at)
    now = datetime.now(timezone.utc).timestamp()
    if dt.timestamp() < now - abs(margin_seconds):
        raise ScheduleError(
            "The scheduled publish date is in the past. Pick a future date.")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def describe_rfc3339_in_tz(publish_at: str, tz_name: str) -> str:
    """'2026-09-20T18:00:00Z' -> '20/09/2026 20:00 Europe/Madrid' (best effort)."""
    try:
        dt = parse_rfc3339(publish_at).astimezone(resolve_timezone(tz_name))
        return dt.strftime("%d/%m/%Y %H:%M ") + (tz_name or "UTC")
    except ScheduleError:
        return publish_at or "-"
