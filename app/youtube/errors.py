"""YouTube errors with clear messages + separate technical diagnosis."""
from __future__ import annotations

import json


class YouTubeApiError(RuntimeError):
    def __init__(self, user_message: str, technical: str = "", code: int = 0, reason: str = "") -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.technical = technical
        self.code = code
        self.reason = reason


def explain_http_error(status: int, content: bytes | str, default: str) -> YouTubeApiError:
    reason = ""
    message = ""
    try:
        data = json.loads(content) if isinstance(content, (bytes, bytearray)) else json.loads(content or "{}")
        err = data.get("error", {})
        message = err.get("message", "") or ""
        for e in err.get("errors", []) or []:
            reason = e.get("reason", "") or reason
            break
    except Exception:
        message = str(content or "")[:500]

    tech = f"HTTP {status} reason={reason} msg={message}".strip()
    r = (reason or "").lower()

    if status == 401 or r in ("autherror", "unauthorized"):
        return YouTubeApiError(
            "Google session expired or invalid. Reconnect your Google account.",
            tech, status, reason)
    if status == 403 and r in ("quotaexceeded", "rate_limit_exceeded", "quota_exceeded"):
        return YouTubeApiError(
            "YouTube Data API quota exhausted (daily upload/query limit). "
            "Try again tomorrow or check the quota in Google Cloud Console.",
            tech, status, reason)
    if status == 403 and r in ("accessnotconfigured", "apinotenabled"):
        return YouTubeApiError(
            "YouTube Data API v3 is not enabled in your Google Cloud project. "
            "Enable it in Console > APIs & Services > Enable APIs.",
            tech, status, reason)
    if status == 403 and "insufficient" in r:
        return YouTubeApiError(
            "Insufficient permissions (scopes). Disconnect and reconnect accepting "
            "the YouTube permissions.",
            tech, status, reason)
    if status == 403 and r in ("forbidden", "accountdisabled"):
        return YouTubeApiError("YouTube rejected the operation (account/channel without permission). " + message[:200], tech, status, reason)
    if status == 404:
        return YouTubeApiError("YouTube resource not found (channel/playlist). Check the IDs.", tech, status, reason)
    if status and status >= 500:
        return YouTubeApiError("YouTube is unavailable right now (server error). Retry later.", tech, status, reason)
    return YouTubeApiError(default + (f"\nDetail: {message[:300]}" if message else ""), tech, status, reason)
