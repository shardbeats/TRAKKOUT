"""Build the fast portable TRAKKOUT (one-dir inside a ZIP).

Why: PyInstaller *one-file* re-extracts the whole payload to %TMP% on EVERY
launch (~468 MB, ~5 s). The *one-dir* build starts instantly because nothing
is extracted. The portable is therefore shipped as a ZIP the user unzips once:

    dist\\TRAKKOUT-portable-<version>.zip
        TRAKKOUT\\
            TRAKKOUT.exe
            _internal\\   (Qt, FFmpeg, certs, ...)
            LICENSE / NOTICE.md / THIRD-PARTY-NOTICES.md / GOOGLE_SETUP.md

Usage (from the project root):
    python build_portable.py
"""
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = ROOT / "TRAKKOUT.spec"
EXE_DIR = ROOT / "dist" / "portable" / "TRAKKOUT"
DOCS = ("LICENSE", "NOTICE.md", "THIRD-PARTY-NOTICES.md", "GOOGLE_SETUP.md")


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        raise SystemExit("ERROR: version not found in pyproject.toml")
    return m.group(1)


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT), env=dict(os.environ, TRAKKOUT_ONEDIR="1"))


def main() -> int:
    version = project_version()
    print(f"TRAKKOUT portable version: {version}")

    if EXE_DIR.exists():
        shutil.rmtree(EXE_DIR, ignore_errors=True)

    rc = run([
        sys.executable, "-m", "PyInstaller", SPEC.name, "--noconfirm",
        "--distpath", "dist/portable", "--workpath", "build/portable",
        "--log-level", "WARN",
    ])
    if rc != 0:
        return rc

    exe = EXE_DIR / "TRAKKOUT.exe"
    if not exe.is_file():
        print(f"ERROR: {exe} was not created.")
        return 1

    for name in DOCS:
        src = ROOT / name
        if src.is_file():
            shutil.copy2(src, EXE_DIR / name)

    out = ROOT / "dist" / f"TRAKKOUT-portable-{version}.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(EXE_DIR.rglob("*")):
            if p.is_file():
                zf.write(p, Path("TRAKKOUT") / p.relative_to(EXE_DIR))

    print(f"OK: {out} ({out.stat().st_size / 1e6:.1f} MB)")
    print("Unzip once, then run TRAKKOUT\\TRAKKOUT.exe (no per-launch extraction).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
