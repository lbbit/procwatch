from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_NAME = "ProcWatch"
ZIP_NAME = "ProcWatch-win-x64-portable.zip"
ICON_ICO = ROOT / "assets" / "app_icon.ico"
ICON_PNG = ROOT / "assets" / "app_icon.png"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    if BUILD.exists():
        shutil.rmtree(BUILD)

    command = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--name",
        APP_NAME,
        "--windowed",
        "--onedir",
        "--paths",
        str(ROOT / "src"),
        "--add-data",
        f"{ICON_PNG}{';' if shutil.which('cmd') else ':'}assets",
    ]
    if ICON_ICO.exists():
        command.extend(["--icon", str(ICON_ICO)])
    command.append(str(ROOT / "src" / "procwatch" / "main.py"))

    subprocess.run(command, check=True, cwd=ROOT)
    package_dir = DIST / APP_NAME
    archive_base = DIST / "ProcWatch-win-x64-portable"
    archive_path = Path(shutil.make_archive(str(archive_base), "zip", package_dir))
    final_zip = DIST / ZIP_NAME
    if archive_path != final_zip:
        if final_zip.exists():
            final_zip.unlink()
        archive_path.rename(final_zip)
    sha_path = DIST / "SHA256SUMS.txt"
    sha_path.write_text(f"{sha256_of(final_zip)}  {final_zip.name}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
