# PyInstaller spec for the portable one-file TRAKKOUT.exe.
# Build with: venv\Scripts\python.exe build_exe.py
# (or: venv\Scripts\python.exe -m PyInstaller TRAKKOUT.spec)
# Output: dist\TRAKKOUT.exe (FFmpeg still required on PATH, not bundled).
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ["app\\main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("app\\resources", "app\\resources"),
        ("app\\ui\\style.qss", "app\\ui"),
    ],
    hiddenimports=(
        collect_submodules("googleapiclient")
        + collect_submodules("google.auth")
        + collect_submodules("google_auth_oauthlib")
        + collect_submodules("google.api_core")
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pytest", "_pytest"],
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="trakkout.ico",
)
