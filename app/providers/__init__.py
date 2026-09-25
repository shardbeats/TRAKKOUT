"""Provider registry. The GUI resolves here; it never instantiates concrete classes.

For now only the local file provider exists: audio and artwork are always
provided by the user from their machine (their legitimate download/license).
If a remote source is added in the future (e.g. an official marketplace API),
it registers here without touching the GUI.
"""
from __future__ import annotations

from .base import MediaProvider, ProviderNotAvailableError
from .local_provider import LocalFileProvider

__all__ = [
    "MediaProvider",
    "ProviderNotAvailableError",
    "LocalFileProvider",
    "get_provider",
    "list_providers",
]


def list_providers() -> list[MediaProvider]:
    return [LocalFileProvider()]


def get_provider(url_or_path: str) -> MediaProvider | None:
    """First enabled provider accepting the input, or None."""
    for p in list_providers():
        try:
            if not p.enabled():
                continue
            if p.can_handle(url_or_path or ""):
                return p
        except Exception:
            continue
    return None
