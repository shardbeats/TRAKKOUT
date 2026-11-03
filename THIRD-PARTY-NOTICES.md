# THIRD-PARTY-NOTICES — TRAKKOUT

TRAKKOUT code is MIT (`LICENSE`). The components below keep their
own licenses, in source runs AND inside the frozen exe/installer.

| Component | License | Notes |
|---|---|---|
| PySide6 + Qt | LGPLv3 | GUI toolkit. https://www.qt.io + https://pypi.org/project/PySide6/ |
| FFmpeg + FFprobe (system PATH in dev, bundled in exe) | LGPLv2.1+ | Video render (audio + artwork → 1080p MP4). https://ffmpeg.org/download.html |
| requests | Apache-2.0 | HTTP. https://requests.readthedocs.io/ |
| google-auth / google-auth-oauthlib / google-api-python-client | Apache-2.0 | YouTube Data API v3 OAuth + upload. https://github.com/googleapis/google-api-python-client |
| tzdata | MIT | Windows timezone data. |
| Python stdlib (sqlite3) | PSF | Upload history DB. |

Service terms (not a license, but binding on use): YouTube API
Services Terms + Google API Terms apply when you upload.
Your `client_secret*.json` + tokens stay in `%APPDATA%\TRAKKOUT\`
and must never be committed.

Build tools only: PyInstaller (GPLv2 + bootloader exception),
Inno Setup 6 (free), pytest/pytest-bdd (MIT, dev only).

Compliance: ship `LICENSE` + `NOTICE.md` + this file (installer
already ships `LICENSE`; add these two the same way). LGPL/Apache
texts via the links above.
