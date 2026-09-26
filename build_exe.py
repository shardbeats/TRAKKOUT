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
    if shutil.which("ffmpeg") is None:
        print("WARNING: ffmpeg not found on PATH. The exe will still build, "
              "but video generation needs FFmpeg installed.")
    rc = run([python, "-m", "PyInstaller", "--version"])
    if rc != 0:
        print("Installing PyInstaller...")
        rc = run([python, "-m", "pip", "install", "pyinstaller"])
        if rc != 0:
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
