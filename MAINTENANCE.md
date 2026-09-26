# Maintenance guide — TRAKKOUT

Practical guide to keep this application running for years.

## 1. Project map (what touches what)

```
trakkout/
├── app/main.py              Entry point. Creates QApplication, applies theme, opens MainWindow.
├── app/ui/main_window.py    Thin shell: __init__ + _build_ui + closeEvent (~490 lines).
├── app/ui/mixins/           ALL window logic, split by domain:
│   ├── base.py              State, progress, navigation, history, settings.
│   ├── collectors.py        Widgets → models readers (video/audio/overlay/beat).
│   ├── media.py             Audio/artwork, drag&drop, probe, BPM/key auto-detection.
│   ├── templates_ui.py      Load/apply/create/edit/delete templates.
│   ├── youtube_auth.py      OAuth, channels, account status.
│   ├── generate_upload.py   Generate video, preview, upload, cancel.
│   └── queue_history.py     Batch queue and SQLite history.
├── app/ui/workers.py        Qt threads (FFmpeg, Upload, OAuth, Channels, Batch).
├── app/ui/dialogs.py        Settings and Preview dialogs.
├── app/ui/template_editor.py Template editor with live preview.
├── app/ui/sections.py       Sidebar + collapsible sections (UI only).
├── app/ui/theme.py + style.qss  Dark theme (editable without touching code).
├── app/templates/           {{variable}} engine (engine.py), JSON presets (presets.py),
│                            tags.py, {var} compatibility (compat.py).
├── app/services/
│   ├── video_generator.py    FFmpeg video generation.
│   ├── queue_manager.py      Persistent queue in SQLite (table `queue`;
│   │                         on startup normalizes Generating/Uploading→Pending,
│   │                         drops Uploaded/Scheduled and revalidates Ready).
│   └── history_store.py      SQLite history (table `history`; auto-migrates the
│                             title/description/tags/category_id columns).
├── app/models/models.py      Models (BeatMetadata with artist2, HistoryEntry with
│                             metadata for Load, VideoSettings.is_vertical).
├── app/ffmpeg/              Everything that talks to ffmpeg/ffprobe.
├── app/youtube/             OAuth (auth.py), HTTP errors (errors.py), uploads (youtube_service.py).
├── app/config/settings.py   settings.json in %APPDATA%\TRAKKOUT.
├── app/utils/beat_names.py  Title/BPM/key parser from the file name.
├── app/resources/templates/ Presets (Free Standard.json). Recreated if missing.
├── start.bat                One-click first-run setup + launch (Windows).
├── build_exe.py + TRAKKOUT.spec  Portable recipe (PyInstaller, one-file, FFmpeg bundled).
└── requirements.txt         Dependencies pinned by range (>=).
```

**Golden rule:** the UI (`app/ui`) never talks to Google or FFmpeg
directly; always through `VideoGenerator`, `YouTubeService` and
`PresetManager`. Respect that and changes won't break each other.

## 2. Suggested maintenance calendar

| When | Task | Where to look |
|---|---|---|
| Every 6–12 months | Update dependencies (`pip install -U ...`, see §3) | `requirements.txt`, `pyproject.toml` |
| Every 12 months | Test the full OAuth flow (connect → channels → private upload) | Google Cloud Console + app |
| Every 12 months | Check YouTube Data API v3 deprecation notices | https://developers.google.com/youtube/v3/revision_history |
| Every 12 months | Test against the latest stable FFmpeg | https://www.gyan.dev/ffmpeg/builds/ |
| After every change | Rebuild the exe and test it in a clean folder | `build_exe.py` |
| Always | Never commit `client_secrets.json`, `token.json`, `*.db`, `*.log` | Already covered by `.gitignore` |

## 3. Updating dependencies without breaking anything

1. Activate the venv and record what's installed: `venv\Scripts\python.exe -m pip freeze > before.txt`
2. Update in groups (never everything at once): first `PySide6`, then `google-*`, then the rest.
3. After each group, run the app and test: open, load audio+artwork,
   apply a template, generate 1 video, connect Google, list channels.
4. If something breaks: `venv\Scripts\python.exe -m pip install -r requirements.txt`
   to roll back, and pin the upper bound (e.g. `PySide6>=6.6,<7`).
5. Only then update the ranges in `requirements.txt`.

**Historically sensitive spots:**
- **PySide6 6.x → 7.x (whenever it lands):** review `QDateTime`, `QFileDialog` and
  the `Signal`s in `workers.py`. Test startup offscreen with the
  real window:
  ```powershell
  $env:QT_QPA_PLATFORM='offscreen'
  venv\Scripts\python.exe -c "from PySide6.QtWidgets import QApplication; from app.config.settings import SettingsStore; from app.ui.main_window import MainWindow; from pathlib import Path; app=QApplication([]); w=MainWindow(Path('.'),SettingsStore()); print('UI OK', w.windowTitle()); w.close()"
  ```
- **google-api-python-client:** the client is built with
  `cache_discovery=False` (`client()` in `app/youtube/youtube_service.py`),
  so the discovery doc is fetched from the network on every fresh start.
  Uploads inherently need connectivity, and a Google-side discovery change
  takes effect immediately (no bundled doc to go stale).
- **Python:** the project asks for `>=3.11`. Before bumping minor versions
  (3.12 → 3.13…), rebuild the exe: PyInstaller is version-sensitive.

## 4. YouTube / Google Cloud (what breaks most often over the years)

- **Testing-mode consent screen:** access expires if the app isn't used;
  reconnecting is enough. If Google changes verification requirements,
  each user fixes it in THEIR project (the repo ships no keys).
- **Quotas:** the project uses each user's quota, not yours. If one day
  the default quota isn't enough, it's extended in the user's Cloud Console.
- **`verify_channel_selection`:** if Google changes how
  `channels.list(mine=true)` behaves with Brand Accounts, this is the first
  place to check (`app/youtube/youtube_service.py`).
- **Scopes:** when adding features (e.g. reading comments), add the
  scope in `auth.py:SCOPES` AND re-authorize (delete `token.json`).

## 5. FFmpeg (what breaks second most often)

- All coupling lives in `app/ffmpeg/ffmpeg_service.py`. If a filter
  changes syntax in the future, only `build_video_filter()` needs touching.
- Square cropping uses `crop='min(iw,ih)':'min(iw,ih)'`, stable syntax
  for years; watch `gblur` and `drawtext` (the font is auto-detected in
  `find_system_font()`).
- The portable exe bundles `ffmpeg.exe` + `ffprobe.exe` (located on PATH
  at build time by `build_exe.py` / `TRAKKOUT.spec`). At runtime the app
  prefers the bundled binaries when frozen (`_bundled_bin()`), while an
  explicit path in **File > Settings** always wins. Source runs still need
  FFmpeg on PATH. To refresh the bundled FFmpeg version, update it on the
  build machine and recompile.

## 6. Rebuilding the portable exe

```powershell
venv\Scripts\python.exe build_exe.py        # builds dist\TRAKKOUT.exe
venv\Scripts\python.exe build_exe.py --check  # prerequisites only
```

- Takes several minutes. The `No module named 'grpc'` warning during the
  build is harmless (a submodule the app doesn't use).
- Quick check: start the exe with `QT_QPA_PLATFORM=offscreen`,
  it must stay alive 20 s without exiting.
- `build/` and `dist/` are git-ignored: the exe ships via
  GitHub Releases, never committed. Expect ~245 MB (Qt + FFmpeg
  bundled; measured 243.7 MB).

## 7. Decided behaviors (not bugs)

- **Batch uses the item's frozen metadata** (from when it was queued);
  single generation uses the live form. Decided on purpose: don't change
  without reviewing `_on_batch_gen_done` and `BatchUploadWorker`.
- **History:** created only on Generate/Upload; touch-ups are manual
  with **Update from form**. No per-keystroke auto-save.
- **Shorts:** vertical + ≤3 min warns, doesn't block; YouTube classifies on its own.
- **Tests:** suite in `tests/` (`python -m pytest tests -q`, CI in `.github/workflows/tests.yml`).
  Covers pure logic without GUI/network/FFmpeg (utils, models, templates, settings, SQLite stores,
  YouTube errors and OAuth validation). Exe verification stays manual.
