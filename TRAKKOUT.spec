# PyInstaller spec for the portable one-file TRAKKOUT.exe.
# Build with: venv\Scripts\python.exe build_exe.py
# (or: venv\Scripts\python.exe -m PyInstaller TRAKKOUT.spec)
# Output: dist\TRAKKOUT.exe (FFmpeg still required on PATH, not bundled).
#
# NOTE on Google/YouTube: the exe failed to connect because (1) CA certificates
# (certifi/httplib2) were not bundled, (2) several google/* hidden imports and
# native binaries (cryptography) were missing, and (3) app code wrote
# logs/presets into sys._MEIPASS. collect_all() below fixes (1)+(2) because it
# gathers submodules + binaries + datas together (collect_submodules alone
# misses binaries and fails silently on google.* namespace packages);
# app/main.py + app/templates/presets.py fix (3).
from PyInstaller.utils.hooks import collect_all, copy_metadata

block_cipher = None

all_binaries: list[tuple[str, str]] = []
all_datas: list[tuple[str, str]] = []
all_hidden: list[str] = []

# Packages that MUST travel inside the exe or YouTube/Google breaks.
# collect_all returns (binaries, datas, hiddenimports).
# NOTE: single-file modules (google_auth_httplib2, cachetools) are NOT packages:
# collect_all skips them, so they go in all_hidden below instead.
for pkg in (
    "googleapiclient",
    "google.auth",
    "google.oauth2",
    "google_auth_oauthlib",
    "google.api_core",
    "httplib2",
    "oauthlib",
    "requests_oauthlib",
    "urllib3",
    "certifi",
    "cryptography",
    "pyasn1",
    "pyasn1_modules",
    "uritemplate",
    "pyparsing",
    "packaging",
    "proto",
    "google.protobuf",
    "requests",
    "charset_normalizer",
    "idna",
):
    try:
        b, d, h = collect_all(pkg)
        all_binaries += b
        all_datas += d
        all_hidden += h
    except Exception as exc:
        print(f"WARNING: collect_all({pkg!r}) failed: {exc}")

for dist_name in (
    "google-api-python-client",
    "google-auth",
    "google-auth-oauthlib",
    "google-auth-httplib2",
    "google-api-core",
    "certifi",
    "cryptography",
):
    try:
        all_datas += copy_metadata(dist_name)
    except Exception:
        pass

all_hidden += [
    "google_auth_httplib2",
    "wsgiref.simple_server",
    "wsgiref.util",
    "wsgiref.headers",
    "googleapiclient.discovery_cache",
    "googleapiclient.discovery_cache.file_cache",
]

a = Analysis(
    ["app\\main.py"],
    pathex=["."],
    binaries=all_binaries,
    datas=[
        ("app\\resources", "app\\resources"),
        ("app\\ui\\style.qss", "app\\ui"),
    ] + all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["pyinstaller_hooks\\runtime_hook_certs.py"],
    # NOTE: do NOT exclude "unittest" (stdlib): pyparsing/__init__ imports
    # .testing unconditionally and testing.py needs unittest; excluding it
    # breaks "from googleapiclient.discovery import build" via
    # httplib2 -> pyparsing inside the frozen exe.
    excludes=["tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="TRAKKOUT",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    # console=False for release. If Google/YouTube still fails, rebuild once
    # with console=True to see the real SSL/OAuth error in the terminal.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="trakkout.ico",
)
