"""YouTubeService: channels, resumable upload, playlists. No GUI code.

IMPORTANT NOTE on Brand Accounts / multiple channels (official behavior):
YouTube Data API v3 has NO parameter to "pick a channel" in videos.insert.
Uploads always go to the channel tied to the active OAuth credentials
(channels.list(mine=true)). To publish to another Brand Account, the user
must authenticate while picking that channel in Google's account picker.
This class enforces it: before uploading it verifies that the selected
channel matches the authenticated channel and, if not, aborts with a clear
message instead of uploading to the wrong channel.
"""
from __future__ import annotations

import logging
import mimetypes
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from app.models.models import ChannelInfo, YouTubeMetadata
from app.youtube.auth import GoogleAuth
from app.youtube.errors import YouTubeApiError, explain_http_error

log = logging.getLogger(__name__)

UploadProgress = Callable[[int, int, float], None]  # (sent, total, pct)
CHUNK_SIZE = 8 * 1024 * 1024


class YouTubeNotConfiguredError(RuntimeError):
    pass


def coerce_privacy_for_schedule(privacy: str) -> tuple[str, bool]:
    """The API requires privacyStatus=private when scheduling (publishAt).

    Return (effective_privacy, changed). Rule documented in the README.
    """
    p = (privacy or "private").strip().lower()
    if p not in ("private", "unlisted", "public"):
        p = "private"
    if p != "private":
        return "private", True
    return "private", False


def build_video_body(meta: YouTubeMetadata) -> dict:
    """Build the videos.insert body. Testable without network.

    If meta.publish_at is set (RFC 3339 UTC), status.publishAt is added
    to schedule publishing and privacy is forced to private (API requirement).
    """
    from app.utils.scheduling import ensure_future_publish_at

    tags = [t.strip() for t in (meta.tags or []) if t and t.strip()][:30]
    title = (meta.title or "").strip()[:100]
    privacy = meta.privacy if meta.privacy in ("private", "unlisted", "public") else "private"
    status: dict = {
        "privacyStatus": privacy,
        "madeForKids": bool(meta.made_for_kids),
        "selfDeclaredMadeForKids": bool(meta.made_for_kids),
    }
    publish_at = (getattr(meta, "publish_at", "") or "").strip()
    if publish_at:
        publish_at = ensure_future_publish_at(publish_at)
        privacy, _changed = coerce_privacy_for_schedule(privacy)
        status["privacyStatus"] = privacy
        status["publishAt"] = publish_at
    body = {
        "snippet": {
            "title": title,
            "description": meta.description or "",
            "tags": tags,
            "categoryId": str(meta.category_id or "10"),
        },
        "status": status,
    }
    return body


def video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


class YouTubeService:
    def __init__(self, auth: GoogleAuth) -> None:
        self.auth = auth
        self._service = None

    # ---- client ----
    def _require_libs(self):
        # With an injected client (e.g. test mocks), don't require libraries.
        if self._service is not None:
            return
        try:
            from googleapiclient.discovery import build  # noqa: F401
            from googleapiclient.errors import HttpError  # noqa: F401
            from googleapiclient.http import MediaFileUpload  # noqa: F401
        except ImportError as exc:
            raise YouTubeNotConfiguredError(
                "Missing YouTube libraries (google-api-python-client).\n"
                "Run: pip install -r requirements.txt"
            ) from exc

    def client(self, force_new: bool = False):
        self._require_libs()
        from googleapiclient.discovery import build

        if self._service is not None and not force_new:
            return self._service
        creds = self.auth.load_credentials()
        if creds is None:
            raise YouTubeNotConfiguredError(
                "No active Google session. Press 'Connect Google Account'.")
        self._service = build("youtube", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def is_connected(self) -> bool:
        try:
            return self.auth.load_credentials() is not None
        except Exception:
            return False

    # ---- channels ----
    def list_channels(self) -> list[ChannelInfo]:
        """Return the channels visible to the authenticated identity.

        In practice, channels.list(mine=true) returns THE active channel of
        that OAuth identity. If the user has several Brand Accounts, they
        see one here; to switch, they must re-authenticate picking the other
        channel in Google (the app explains this in the verify error).
        We also try to resolve the stored channel by id for display.
        """
        self._require_libs()
        try:
            from googleapiclient.errors import HttpError
        except ImportError:
            HttpError = Exception  # type: ignore[assignment,misc]

        yt = self.client()
        out: list[ChannelInfo] = []
        try:
            resp = yt.channels().list(mine=True, part="snippet,contentDetails").execute()
        except HttpError as exc:
            raise explain_http_error(exc.resp.status, exc.content, "Could not fetch channels.") from exc
        except Exception as exc:
            raise YouTubeApiError(f"Could not fetch channels: {exc}") from exc
        for item in resp.get("items", []) or []:
            sn = item.get("snippet", {}) or {}
            thumbs = sn.get("thumbnails", {}) or {}
            thumb = (thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
            out.append(ChannelInfo(
                channel_id=item.get("id", ""),
                title=sn.get("title", ""),
                thumbnail_url=thumb,
                custom_url=sn.get("customUrl", ""),
            ))
        return out

    def verify_channel_selection(self, selected_channel_id: str) -> ChannelInfo:
        """Ensure the upload will go to the selected channel.

        Raise YouTubeApiError when the authenticated channel does not match,
        instead of silently publishing to another channel.
        """
        if not selected_channel_id:
            raise YouTubeApiError("No YouTube channel selected.")
        channels = self.list_channels()
        if not channels:
            raise YouTubeApiError(
                "This Google account has no YouTube channel.\n"
                "Create one at youtube.com and try again.")
        mine = channels[0]
        if mine.channel_id == selected_channel_id:
            return mine
        # The selected channel is not the authenticated one: explain the flow.
        raise YouTubeApiError(
            "The selected channel does not match the channel authenticated with Google.\n\n"
            f"Currently authenticated: {mine.title} ({mine.channel_id})\n"
            f"Selected: {selected_channel_id}\n\n"
            "The YouTube API always publishes to the active session's channel "
            "(there is no parameter to pick another channel).\n"
            "To publish to that other channel/Brand Account: press 'Disconnect' and "
            "reconnect, picking THAT channel in Google's account picker."
        )

    # ---- upload ----
    def upload_video(
        self,
        video_path: str | Path,
        meta: YouTubeMetadata,
        channel_id: str = "",
        playlist_id: str = "",
        on_progress: Optional[UploadProgress] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> dict:
        self._require_libs()
        try:
            from googleapiclient.errors import HttpError
            from googleapiclient.http import MediaFileUpload
            _has_google = True
        except ImportError:
            HttpError = Exception  # type: ignore[assignment,misc]
            MediaFileUpload = None  # type: ignore[assignment]
            _has_google = self._service is not None  # mocks injected in tests only
            if not _has_google:
                raise YouTubeNotConfiguredError(
                    "Missing YouTube libraries (google-api-python-client).\n"
                    "Run: pip install -r requirements.txt")

        p = Path(str(video_path))
        if not p.exists():
            raise YouTubeApiError(f"Video does not exist:\n{p}")
        if not (meta.title or "").strip():
            raise YouTubeApiError("Title is required to upload to YouTube.")
        if (getattr(meta, "publish_at", "") or "").strip():
            from app.utils.scheduling import ScheduleError as _ScheduleError
            from app.utils.scheduling import ensure_future_publish_at as _ensure_future
            try:
                meta.publish_at = _ensure_future(meta.publish_at)
            except _ScheduleError as exc:
                raise YouTubeApiError(str(exc)) from exc
        if channel_id:
            self.verify_channel_selection(channel_id)

        yt = self.client()
        body = build_video_body(meta)
        mime, _ = mimetypes.guess_type(str(p))
        if MediaFileUpload is not None:
            media = MediaFileUpload(str(p), mimetype=mime or "video/mp4",
                                    chunksize=CHUNK_SIZE, resumable=True)
        else:
            media = None  # mock client in tests
        try:
            request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        except HttpError as exc:
            raise explain_http_error(exc.resp.status, exc.content, "Could not start the upload.") from exc

        total = p.stat().st_size
        response = None
        try:
            while response is None:
                if cancel_event is not None and cancel_event.is_set():
                    raise YouTubeApiError("Upload cancelled by the user.")
                status, response = request.next_chunk()
                if status is not None and on_progress:
                    sent = getattr(status, "resumable_progress", 0) or 0
                    pct = min(100.0, sent / total * 100.0) if total else 0.0
                    on_progress(int(sent), int(total), pct)
        except YouTubeApiError:
            raise
        except HttpError as exc:
            raise explain_http_error(exc.resp.status, exc.content, "Error during the YouTube upload.") from exc
        except Exception as exc:
            raise YouTubeApiError(f"Upload interrupted: {exc}") from exc

        video_id = (response or {}).get("id", "")
        if not video_id:
            raise YouTubeApiError("YouTube returned no video ID (unexpected response).")
        if on_progress:
            on_progress(total, total, 100.0)

        channel_title = ""
        try:
            ch = self.list_channels()
            if ch:
                channel_title = ch[0].title
        except Exception:
            pass

        effective_playlist = playlist_id or (meta.playlist_id or "")
        if effective_playlist:
            try:
                self.add_to_playlist(video_id, effective_playlist)
            except YouTubeApiError as exc:
                log.warning("Video uploaded (%s) but playlist failed: %s", video_id, exc.user_message)

        return {
            "video_id": video_id,
            "url": video_url(video_id),
            "channel_id": channel_id or "",
            "channel_title": channel_title,
        }

    def add_to_playlist(self, video_id: str, playlist_id: str) -> None:
        self._require_libs()
        try:
            from googleapiclient.errors import HttpError
        except ImportError:
            HttpError = Exception  # type: ignore[assignment,misc]

        yt = self.client()
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        }
        try:
            yt.playlistItems().insert(part="snippet", body=body).execute()
        except HttpError as exc:
            raise explain_http_error(exc.resp.status, exc.content, "Could not add to the playlist.") from exc
