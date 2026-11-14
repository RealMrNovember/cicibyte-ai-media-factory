"""Desktop app self-update from GitHub Releases.

The installer is only taken from this repository's release downloads and must match the SHA-256 published
next to it (the .exe is not code-signed yet, so the checksum is what proves it is ours).
"""

import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

from mediafactory import __version__

REPO = "RealMrNovember/cicibyte-ai-media-factory"
LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_PREFIX = f"https://github.com/{REPO}/releases/download/"
INSTALLER = re.compile(r"^CiciByteMediaFactory-Setup-[\d.]+\.exe$")


class UpdateError(Exception):
    pass


def _parse(version: str) -> tuple[int, ...] | None:
    m = re.fullmatch(r"v?(\d+(?:\.\d+)*)", version.strip())
    return tuple(int(x) for x in m.group(1).split(".")) if m else None


def newer(candidate: str, current: str) -> bool:
    a, b = _parse(candidate), _parse(current)
    return bool(a and b and a > b)


def pick_update(release: dict, *, current: str = __version__) -> dict | None:
    """Update info from a GitHub release, or None when it is not newer / incomplete / not from our repository."""
    tag = str(release.get("tag_name", ""))
    if not newer(tag, current):
        return None
    assets = {a.get("name", ""): a.get("browser_download_url", "") for a in release.get("assets") or []}
    exe = next((n for n in assets if INSTALLER.match(n)), None)
    if not exe or f"{exe}.sha256" not in assets:
        return None
    urls = (assets[exe], assets[f"{exe}.sha256"])
    if not all(u.startswith(DOWNLOAD_PREFIX) for u in urls):
        return None
    return {"version": tag.lstrip("v"), "installer": urls[0], "sha256_url": urls[1],
            "notes": str(release.get("body") or "")[:2000], "page": release.get("html_url")}  # fmt: skip


def _fetch(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": f"CiciByteMediaFactory/{__version__}",
                                               "Accept": "application/vnd.github+json"})  # fmt: skip
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (fixed https GitHub URLs)
        return r.read()


def check() -> dict | None:
    """Ask GitHub for the latest release; None when up to date or unreachable."""
    try:
        return pick_update(json.loads(_fetch(LATEST_API, timeout=15)))
    except Exception:
        return None


def download(info: dict, folder: Path) -> Path:
    expected = _fetch(info["sha256_url"]).decode("ascii", "replace").split()[0].lower()
    data = _fetch(info["installer"], timeout=600)
    if hashlib.sha256(data).hexdigest() != expected:
        raise UpdateError("the downloaded installer does not match its published checksum")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"CiciByteMediaFactory-Setup-{info['version']}.exe"
    path.write_bytes(data)
    return path


def launch_installer(path: Path) -> None:
    """Start the installer silently and detached; it closes this app, updates it and starts it again."""
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    args = [str(path), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"]
    if sys.platform == "win32":
        subprocess.Popen(args, creationflags=flags, close_fds=True)  # noqa: S603
    else:  # pragma: no cover - the installer is Windows-only
        raise UpdateError("automatic install is only available on Windows")
