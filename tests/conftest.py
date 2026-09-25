"""Shared pytest fixtures (stdlib only, no Qt)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def tmp_audio(tmp_path: Path) -> Path:
    p = tmp_path / "beat.mp3"
    p.write_bytes(b"fake-audio-content")
    return p


@pytest.fixture
def tmp_image(tmp_path: Path) -> Path:
    p = tmp_path / "cover.png"
    p.write_bytes(b"fake-image-content")
    return p
