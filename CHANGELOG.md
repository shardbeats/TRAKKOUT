# Changelog

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
