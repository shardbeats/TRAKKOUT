"""Build the portable TRAKKOUT.exe whenever you want.

Usage (from the project root):
    venv\\Scripts\\python.exe build_exe.py [--check]

- Requires ffmpeg.exe + ffprobe.exe on PATH: they are bundled INSIDE the
  exe (see TRAKKOUT.spec), so the result runs anywhere with no setup.
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


def find_ffmpeg_bins() -> tuple[str, str] | None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg and ffprobe:
        return ffmpeg, ffprobe
    return None


def main() -> int:
    python = str(VENV_PY if VENV_PY.exists() else sys.executable)
    if not SPEC.exists():
        print(f"ERROR: missing {SPEC.name}")
        return 1
    bins = find_ffmpeg_bins()
    if bins is None:
        print("ERROR: ffmpeg/ffprobe not found on PATH. They are bundled "
              "inside the exe, so the build cannot continue without them.")
        print("  Install with: winget install Gyan.FFmpeg")
        return 1
    print(f"Bundling FFmpeg:  {bins[0]}")
    print(f"Bundling FFprobe: {bins[1]}")
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
