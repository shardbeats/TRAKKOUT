"""Application data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

FitMode = Literal["cover", "fit", "crop", "letterbox"]
AudioFormat = Literal["aac", "mp3", "opus", "wav"]
Privacy = Literal["private", "unlisted", "public"]
QueueStatus = Literal["Pending", "Generating", "Ready", "Uploading", "Uploaded", "Failed"]


def resolve_clip_range(trim_start: float, trim_end: float, duration: float) -> tuple[float, float]:
    """Clamp a (start, end) clip selection to [0, duration].

    ``trim_end`` <= 0 means "to the end". Returns ``(start, end)`` with
    0 <= start <= end <= max(duration, 0). Tolerant to garbage input
    (old DB rows, None): falls back to the full range. Callers that need
    start < end must validate separately (see validators.validate_trim).
    """
    total = max(0.0, float(duration or 0.0))
    try:
        start = max(0.0, float(trim_start or 0.0))
    except (TypeError, ValueError):
        start = 0.0
    try:
        end = float(trim_end or 0.0)
    except (TypeError, ValueError):
        end = 0.0
    if end <= 0.0:
        end = total
    end = min(max(end, 0.0), total)
    start = min(start, end)
    return start, end


@dataclass
class AudioInfo:
    path: str = ""
    duration: float = 0.0
    format_name: str = ""
    codec: str = ""
    sample_rate: int = 0
    channels: int = 0
    bit_rate: int = 0
    size_bytes: int = 0

    @property
    def file_name(self) -> str:
        return Path(self.path).name if self.path else ""


@dataclass
class ImageInfo:
    path: str = ""
    width: int = 0
    height: int = 0
    format_name: str = ""
    size_bytes: int = 0

    @property
    def file_name(self) -> str:
        return Path(self.path).name if self.path else ""

    @property
    def resolution(self) -> str:
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "-"


@dataclass
class OverlaySettings:
    enabled: bool = False
    text: str = ""
    position: str = "bottom-center"  # top-left|top-center|top-right|center|bottom-left|bottom-center|bottom-right
    font_size: int = 48
    opacity: float = 0.9
    margin: int = 60
    font_path: str = ""


@dataclass
class VideoSettings:
    width: int = 1920
    height: int = 1080
    fit_mode: FitMode = "cover"  # type: ignore[assignment]
    blurred_background: bool = True
    background_color: str = "000000"
    fps: int = 30
    preset: str = "medium"
    audio_format: AudioFormat = "aac"  # type: ignore[assignment]
    audio_bitrate: str = "192k"
    trim_start: float = 0.0  # clip start in seconds (Shorts). 0 = from the beginning.
    trim_end: float = 0.0    # clip end in seconds. <= 0 = to the end.

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"

    @property
    def is_vertical(self) -> bool:
        """9:16 Shorts format (height > width)."""
        return self.height > self.width

    def clip_range(self, duration: float) -> tuple[float, float]:
        """Effective (start, end) clamped to the audio duration."""
        return resolve_clip_range(self.trim_start, self.trim_end, duration)

    def clip_duration(self, duration: float) -> float:
        """Effective clip length in seconds."""
        s, e = self.clip_range(duration)
        return max(0.0, e - s)

    @property
    def has_trim(self) -> bool:
        """Whether a sub-range (not the full audio) is selected."""
        return (self.trim_start or 0.0) > 0.0 or (self.trim_end or 0.0) > 0.0


@dataclass
class BeatMetadata:
    """Beat data (manual or via provider). Source for the TemplateEngine."""
    title: str = ""
    producer: str = ""
    artist: str = ""
    artist2: str = ""
    genre: str = ""
    bpm: str = ""
    key: str = ""
    purchase_url: str = ""
    tags: list[str] = field(default_factory=list)
    description: str = ""
    contact: str = ""
    # Links to local files (provided by the user) and remote public ones.
    # Remote audio/artwork ONLY if public and unprotected.
    artwork_url: str = ""
    artwork_path: str = ""
    audio_path: str = ""
    preview_audio_url: str = ""
    # Origin: manual | local
    source: str = "manual"
    fetched_at: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "BeatMetadata":
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.replace(";", ",").split(",") if t.strip()]
        return cls(
            title=str(data.get("title", "") or ""),
            producer=str(data.get("producer", "") or ""),
            artist=str(data.get("artist", "") or ""),
            artist2=str(data.get("artist2", "") or ""),
            genre=str(data.get("genre", "") or ""),
            bpm=str(data.get("bpm", "") or ""),
            key=str(data.get("key", "") or ""),
            purchase_url=str(data.get("purchase_url", "") or ""),
            tags=list(tags),
            description=str(data.get("description", "") or ""),
            contact=str(data.get("contact", "") or ""),
            artwork_url=str(data.get("artwork_url", "") or ""),
            artwork_path=str(data.get("artwork_path", "") or ""),
            audio_path=str(data.get("audio_path", "") or ""),
            preview_audio_url=str(data.get("preview_audio_url", "") or ""),
            source=str(data.get("source", "") or "manual"),
            fetched_at=str(data.get("fetched_at", "") or ""),
        )

    def to_dict(self) -> dict:
        return {
            "title": self.title, "producer": self.producer, "artist": self.artist,
            "artist2": self.artist2,
            "genre": self.genre, "bpm": self.bpm, "key": self.key,
            "purchase_url": self.purchase_url,
            "tags": list(self.tags), "description": self.description,
            "contact": self.contact, "artwork_url": self.artwork_url,
            "artwork_path": self.artwork_path, "audio_path": self.audio_path,
            "preview_audio_url": self.preview_audio_url,
            "source": self.source, "fetched_at": self.fetched_at,
        }


@dataclass
class YouTubeMetadata:
    title: str = ""
    description: str = ""
    tags: str = ""
    category_id: str = "10"
    privacy: Privacy = "private"  # type: ignore[assignment]
    playlist_id: str = ""
    made_for_kids: bool = False
    publish_at: str = ""  # RFC 3339 UTC ("" = publicar inmediatamente)


@dataclass
class ChannelInfo:
    channel_id: str = ""
    title: str = ""
    thumbnail_url: str = ""
    custom_url: str = ""

    @property
    def display(self) -> str:
        if self.title and self.channel_id:
            return f"{self.title} ({self.channel_id})"
        return self.title or self.channel_id or "(sin canal)"


@dataclass
class QueueItem:
    id: int = 0
    beat_name: str = ""
    audio_path: str = ""
    artwork_path: str = ""
    title: str = ""
    description: str = ""
    tags: str = ""
    category_id: str = "10"
    privacy: str = "private"
    channel_id: str = ""
    publish_at: str = ""
    video_path: str = ""
    status: QueueStatus = "Pending"
    error: str = ""
    trim_start: float = 0.0
    trim_end: float = 0.0


@dataclass
class HistoryEntry:
    id: int = 0
    created_at: str = ""
    beat_name: str = ""
    audio_path: str = ""
    video_path: str = ""
    channel_id: str = ""
    channel_title: str = ""
    video_id: str = ""
    video_url: str = ""
    privacy: str = ""
    status: str = ""
    error: str = ""
    title: str = ""
    description: str = ""
    tags: str = ""
    category_id: str = "10"
    trim_start: float = 0.0
    trim_end: float = 0.0
