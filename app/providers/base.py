"""Base interface for media providers. The GUI only talks to MediaProvider.

Contract:
- can_handle(url_or_path): True if the provider handles that input.
- enabled(): True if the provider is operational (e.g. official API configured).
- fetch_info(url_or_path) -> BeatMetadata with the available metadata.
  Must NEVER bypass DRM, logins, paywalls or technical protections: only
  public metadata or official integrations with the user's credentials.
- download_artwork(...): optional, public artwork only (OpenGraph etc.).
  Downloading full audio is NOT part of the contract: the user provides
  their local files (their legitimate license/download).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.models import BeatMetadata


class ProviderNotAvailableError(RuntimeError):
    """The provider exists but cannot operate (e.g. official API not configured)."""


class MediaProvider(ABC):
    name: str = "base"
    label: str = "Base"

    def enabled(self) -> bool:
        return True

    @abstractmethod
    def can_handle(self, url_or_path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch_info(self, url_or_path: str) -> BeatMetadata:
        """Return metadata. Must not bypass DRM/paywalls."""
        raise NotImplementedError

    def download_artwork(self, beat: BeatMetadata, dest_dir: str) -> str:
        """Download public artwork only. Return path or ''."""
        return ""
