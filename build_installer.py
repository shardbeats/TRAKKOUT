"""Build the TRAKKOUT Windows installer for inexpert users.

Usage (from the project root):
    python build_installer.py [--check] [--install-inno]

What it does:
  1. Reads the version from pyproject.toml.
  2. Ensures dist\\TRAKKOUT.exe exists (runs build_exe.py if missing).
  3. Downloads FFmpeg essentials (gyan.dev) once into thirdparty\\ffmpeg\\
     and keeps only ffmpeg.exe + ffprobe.exe.
  4. Compiles installer\\installer.iss with Inno Setup (ISCC) into
     dist-installer\\Setup_TRAKKOUT_<version>.exe.

The installer needs nothing on the user's PC: no Python (it travels inside
TRAKKOUT.exe), no PATH tweaks (the app finds ffmpeg\\ next to the exe),
no admin rights (per-user install). The user only connects their own
Google account following GOOGLE_SETUP.txt.
"""
import hashlib
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
THIRD = ROOT / "thirdparty" / "ffmpeg"
ISS = ROOT / "installer" / "installer.iss"
DIST_EXE = ROOT / "dist" / "TRAKKOUT.exe"

FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

ISCC_CANDIDATES = [
    shutil.which("ISCC.exe") or shutil.which("iscc"),
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
]


def run(cmd: list[str]) -> int:
    print("+", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        raise SystemExit("ERROR: version not found in pyproject.toml")
    return m.group(1)


def find_iscc() -> str | None:
    for c in ISCC_CANDIDATES:
        if c and Path(c).is_file():
            return c
    return None


def _verify_sha256(zipp: Path, sha_url: str) -> bool:
    """Check the zip against gyan.dev's published checksum (integrity).

    This catches truncated/corrupted downloads and cache poisoning. It is NOT
    authenticity (same TLS channel); pinned-hash or vendored binaries would be
    stronger but freeze the FFmpeg version forever.
    """
    try:
        with urllib.request.urlopen(sha_url, timeout=30) as resp:
            expected = resp.read().decode("utf-8", "replace").split()[0].lower()
    except Exception as exc:
        print(f"WARNING: no published checksum ({exc}); skipping hash check.")
        return True
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        print(f"WARNING: unexpected checksum format; skipping hash check.")
        return True
    print("Verifying SHA-256...")
    digest = hashlib.sha256()
    with open(zipp, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        print("ERROR: SHA-256 mismatch. Deleted the suspicious file.")
        try:
            zipp.unlink()
        except OSError:
            pass
        return False
    print("OK: SHA-256 matches.")
    return True


def _write_source_txt() -> None:
    """ATTRIBUTION file shipped next to the binaries (GPL redistribution).

    Gyan's builds are GPL; redistributing the .exe requires keeping a source
    offer. This records version + origin so the installed copy complies.
    """
    try:
        out = subprocess.run([str(THIRD / "ffmpeg.exe"), "-version"],
                             capture_output=True, text=True, timeout=30)
        first = (out.stdout or "").splitlines()[0] if out.stdout else "ffmpeg"
    except Exception:
        first = "ffmpeg"
    (THIRD / "SOURCE.txt").write_text(
        f"TRAKKOUT bundles these third-party binaries (unmodified):\n\n"
        f"  {first}\n"
        f"  Origin: {FFMPEG_ZIP_URL}\n\n"
        f"FFmpeg is licensed under the GPL (see https://ffmpeg.org/legal.html).\n"
        f"Complete corresponding source is available from the origin above\n"
        f"and from https://ffmpeg.org/download.html.\n",
        encoding="utf-8")


def ensure_ffmpeg() -> int:
    ff, fp = THIRD / "ffmpeg.exe", THIRD / "ffprobe.exe"
    if ff.is_file() and fp.is_file():
        print(f"FFmpeg already staged in {THIRD}")
        return 0
    THIRD.mkdir(parents=True, exist_ok=True)
    zipp = THIRD / "ffmpeg-release-essentials.zip"
    print(f"Downloading FFmpeg essentials (~40 MB)...\n  {FFMPEG_ZIP_URL}")
    try:
        urllib.request.urlretrieve(FFMPEG_ZIP_URL, zipp)
    except Exception as exc:
        print(f"ERROR: could not download FFmpeg: {exc}")
        print("Download it manually from https://www.gyan.dev/ffmpeg/builds/")
        print(f"and copy bin\\ffmpeg.exe + bin\\ffprobe.exe into {THIRD}")
        return 1
    print("Extracting ffmpeg.exe + ffprobe.exe...")
    if not _verify_sha256(zipp, FFMPEG_ZIP_URL + ".sha256"):
        return 1
    with zipfile.ZipFile(zipp) as zf:
        names = [n for n in zf.namelist()
                 if n.lower().endswith(("bin/ffmpeg.exe", "bin/ffprobe.exe"))]
        if len(names) < 2:
            print(f"ERROR: unexpected zip layout ({len(names)} binaries found).")
            return 1
        for n in names:
            target = THIRD / Path(n).name
            with zf.open(n) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
    try:
        zipp.unlink()
    except OSError:
        pass
    for exe in (ff, fp):
        rc = subprocess.call([str(exe), "-version"],
                             stdout=subprocess.DEVNULL, cwd=str(ROOT))
        if rc != 0:
            print(f"ERROR: {exe.name} does not run (rc={rc}).")
            return 1
        print(f"OK: {exe.name} runs.")
    return 0


def main() -> int:
    version = project_version()
    print(f"TRAKKOUT version: {version}")
    if "--check" in sys.argv:
        ok = True
        if not DIST_EXE.is_file():
            print("TO-BUILD: dist\\TRAKKOUT.exe (run build_exe.py or rerun without --check).")
        else:
            print(f"OK: {DIST_EXE} ({DIST_EXE.stat().st_size / 1e6:.1f} MB)")
        if not ((THIRD / "ffmpeg.exe").is_file() and (THIRD / "ffprobe.exe").is_file()):
            print(f"TO-FETCH: FFmpeg into {THIRD} (~40 MB download).")
        else:
            print(f"OK: FFmpeg staged in {THIRD}")
        iscc = find_iscc()
        print(f"OK: ISCC at {iscc}" if iscc else
              "TO-INSTALL: Inno Setup 6 (winget install --id JRSoftware.InnoSetup -e)")
        return 0 if ok else 0

    if not DIST_EXE.is_file():
        print("dist\\TRAKKOUT.exe missing: building it first (a few minutes)...")
        rc = run([sys.executable, "build_exe.py"])
        if rc != 0 or not DIST_EXE.is_file():
            return rc or 1

    if ensure_ffmpeg() != 0:
        return 1

    iscc = find_iscc()
    if iscc is None:
        if "--install-inno" in sys.argv:
            print("Installing Inno Setup via winget...")
            rc = run(["winget", "install", "--id", "JRSoftware.InnoSetup",
                      "-e", "--silent", "--accept-package-agreements",
                      "--accept-source-agreements"])
            if rc != 0:
                return rc
            iscc = find_iscc()
        if iscc is None:
            print("ERROR: Inno Setup 6 (ISCC.exe) not found.")
            print("Install it once with:")
            print("  winget install --id JRSoftware.InnoSetup -e")
            print("or rerun: python build_installer.py --install-inno")
            return 1

    out = ROOT / "dist-installer" / f"Setup_TRAKKOUT_{version}.exe"
    rc = run([iscc, f"/DAPP_VERSION={version}", str(ISS)])
    if rc != 0:
        return rc
    if out.is_file():
        print(f"OK: {out} ({out.stat().st_size / 1e6:.1f} MB)")
        print("Give that single file to inexpert users: double-click, Next, Next, done.")
        return 0
    print("ERROR: ISCC finished but the installer was not created.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
