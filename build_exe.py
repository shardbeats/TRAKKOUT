"""Build the portable TRAKKOUT.exe whenever you want.

Usage (from the project root):
    venv\\Scripts\\python.exe build_exe.py [--check]

- Installs PyInstaller in the venv if missing.
- Builds dist\\TRAKKOUT.exe from TRAKKOUT.spec (one file, windowed).
- --check only verifies prerequisites without compiling.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / "venv" / "Scripts" / "python.exe"
SPEC = ROOT / "TRAKKOUT.spec"


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    python = str(VENV_PY if VENV_PY.exists() else sys.executable)
    if not SPEC.exists():
        print(f"ERROR: missing {SPEC.name}")
        return 1
    for needed in ("app\\ui\\style.qss", "app\\resources\\templates",
                   "pyinstaller_hooks\\runtime_hook_certs.py"):
        if not (ROOT / needed).exists():
            print(f"ERROR: missing {needed}")
            return 1
    if shutil.which("ffmpeg") is None:
        print("WARNING: ffmpeg not found on PATH. The exe will still build, "
              "but video generation needs FFmpeg installed.")
    rc = run([python, "-m", "PyInstaller", "--version"])
    if rc != 0:
        print("Installing PyInstaller...")
        rc = run([python, "-m", "pip", "install", "pyinstaller"])
        if rc != 0:
            return rc
    # The Google/YouTube connection fails in the exe when the BUILD env lacks
    # the google libs (PyInstaller then bundles nothing). Ensure deps first.
    print("Checking dependencies (requirements.txt)...")
    rc = run([python, "-m", "pip", "install", "-r", "requirements.txt"])
    if rc != 0:
        print("ERROR: could not install requirements.txt")
        return rc
    rc = run([python, "-c",
              "import certifi, httplib2, googleapiclient, google.auth, "
              "google_auth_oauthlib, google_auth_httplib2, cryptography, "
              "pyasn1_modules, uritemplate, pyparsing; "
              "from googleapiclient.discovery import build; "
              "print('google deps OK:', certifi.where())"])
    if rc != 0:
        print("ERROR: Google deps missing after pip install.")
        return rc
    if "--check" in sys.argv:
        print("Prerequisites OK. Run without --check to compile.")
        return 0
    rc = run([python, "-m", "PyInstaller", SPEC.name, "--noconfirm", "--log-level", "WARN"])
    if rc != 0:
        return rc
    exe = ROOT / "dist" / "TRAKKOUT.exe"
    if exe.exists():
        print(f"OK: {exe} ({exe.stat().st_size / 1e6:.1f} MB)")
        return 0
    print("ERROR: build finished but dist\\TRAKKOUT.exe was not created.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
