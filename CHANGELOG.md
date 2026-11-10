# Changelog

## 1.1.0 - 2026-11-10
Feature release: animated artwork and bitrate control.

- Animated artwork covers: GIF and MP4 loops are accepted as video cover — probed, validated and rendered as a looping background (`tests/test_artwork_animated.py`)
- Output bitrate capped with VBV `maxrate`/`bufsize` per resolution, so renders stay within a predictable bitrate envelope
- Artwork/media probing extended in `app/ffmpeg/probe.py`; file helpers and validators updated
- NOTICE.md + THIRD-PARTY-NOTICES.md now shipped in the installer (MIT kept)
- 140 tests passing

## 1.0.3 - 2026-10-13
CPU/stability hardening.

- ffprobe bounded everywhere (timeouts); render-loop stall watchdog kills ffmpeg after 10 min without progress
- Clips over 12 h rejected; `-nostdin` added to the render command
- Waveform hardened: >250 MB rejected pre-decode, 150 MB PCM cap, cancellable decode
- Batch upload cancel now interrupts the in-flight file; queue capped at 500; single-row status updates
- 127 tests passing

## 1.0.2 - 2026-10-03
Frozen-exe fix + installer.

- Google/YouTube connection works again in the frozen exe (SSL cert env vars, bundled FFmpeg detection, presets/theme paths)
- New Inno Setup installer with FFmpeg essentials, SHA-256 verification and GPL attribution

## 1.0.1 — 2026-09-29
Bugfix: history records no longer get overwritten by a new beat.

- Loading a different audio file (or pressing Clear) now resets the whole
  form to defaults, unlinks the open history entry (pending edits are
  flushed to it first) and starts a fresh session — the next Generate /
  Upload creates a brand-new history record
- Cover-first flow supported: a freshly picked cover survives the reset
  triggered by the following audio pick (one-shot)
- Clear can no longer blank a linked entry via the autosave debounce timer
- 4 new session tests (`tests/test_session_reset.py`); 127 passed

## 1.0.0 — 2026-09-25
First public release.

- Beat + artwork → 1080p MP4 via local FFmpeg (square center-cropped artwork, blurred background, optional text overlay)
- YouTube Data API v3 upload with OAuth, channel picker (Brand Accounts), scheduling and playlists
- Editable `{{variable}}` templates with live preview, batch queue, SQLite history
- Filename auto-detection for title, BPM and key
- Dark themed sidebar UI (English)
