"""Builders de MainWindow por dominio (Fase 1)."""
from app.ui.views.action_views import (
    build_all, build_bottom_bar, build_history_view, build_log_view,
    build_queue_view,
)
from app.ui.views.media_section import build_media_section
from app.ui.views.shell import build_shell
from app.ui.views.video_sections import (
    build_clip_section, build_overlay_section, build_video_section,
)
from app.ui.views.youtube_section import YOUTUBE_CATEGORIES, build_youtube_section

__all__ = [
    "YOUTUBE_CATEGORIES",
    "build_all",
    "build_bottom_bar",
    "build_clip_section",
    "build_history_view",
    "build_log_view",
    "build_media_section",
    "build_overlay_section",
    "build_queue_view",
    "build_shell",
    "build_video_section",
    "build_youtube_section",
]
