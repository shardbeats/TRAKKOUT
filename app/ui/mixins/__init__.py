"""Mixins de MainWindow por dominio (sin lógica propia)."""
from app.ui.mixins.base import FeedbackMixin
from app.ui.mixins.collectors import CollectorsMixin
from app.ui.mixins.generate_upload import GenerateUploadMixin
from app.ui.mixins.media import MediaMixin
from app.ui.mixins.queue_history import QueueHistoryMixin
from app.ui.mixins.templates_ui import TemplatesMixin
from app.ui.mixins.youtube_auth import YouTubeAuthMixin

__all__ = [
    "CollectorsMixin",
    "FeedbackMixin",
    "GenerateUploadMixin",
    "MediaMixin",
    "QueueHistoryMixin",
    "TemplatesMixin",
    "YouTubeAuthMixin",
]
