"""Tests for app.models.models dataclasses."""
from __future__ import annotations

from app.models.models import (
    AudioInfo,
    BeatMetadata,
    ChannelInfo,
    HistoryEntry,
    ImageInfo,
    QueueItem,
    VideoSettings,
    YouTubeMetadata,
)


def test_beat_metadata_defaults():
    beat = BeatMetadata()
    assert beat.title == ""
    assert beat.tags == []
    assert beat.source == "manual"


def test_beat_metadata_from_dict_parses_tags_string():
    beat = BeatMetadata.from_dict({"title": "Wolf", "tags": "dark, trap; boombap "})
    assert beat.title == "Wolf"
    assert beat.tags == ["dark", "trap", "boombap"]


def test_beat_metadata_from_dict_keeps_tags_list_and_casts():
    beat = BeatMetadata.from_dict({"bpm": 140, "tags": ["a", "b"], "title": None})
    assert beat.bpm == "140"
    assert beat.tags == ["a", "b"]
    assert beat.title == ""


def test_beat_metadata_roundtrip():
    beat = BeatMetadata(title="T", artist="A", bpm="95", key="Bm", tags=["x"])
    clone = BeatMetadata.from_dict(beat.to_dict())
    assert clone.title == "T"
    assert clone.bpm == "95"
    assert clone.tags == ["x"]


def test_audio_info_file_name():
    assert AudioInfo().file_name == ""
    assert AudioInfo(path="/tmp/my beat.mp3").file_name == "my beat.mp3"


def test_image_info_resolution():
    assert ImageInfo().resolution == "-"
    assert ImageInfo(width=1920, height=1080).resolution == "1920x1080"


def test_video_settings_resolution_and_vertical():
    assert VideoSettings().resolution == "1920x1080"
    assert VideoSettings().is_vertical is False
    assert VideoSettings(width=1080, height=1920).is_vertical is True


def test_youtube_metadata_defaults():
    meta = YouTubeMetadata()
    assert meta.privacy == "private"
    assert meta.category_id == "10"
    assert meta.publish_at == ""


def test_channel_info_display():
    assert ChannelInfo().display == "(sin canal)"
    assert ChannelInfo(channel_id="UC123").display == "UC123"
    assert ChannelInfo(channel_id="UC123", title="My Channel").display == "My Channel (UC123)"


def test_queue_and_history_defaults():
    assert QueueItem().status == "Pending"
    assert QueueItem().privacy == "private"
    assert HistoryEntry().category_id == "10"
