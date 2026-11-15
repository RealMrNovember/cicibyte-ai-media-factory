"""Make the Mac/Linux icons from packaging/app.ico: build/icons/app.png (512) and, on macOS, app.icns."""

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "icons"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ico = Image.open(ROOT / "packaging" / "app.ico")
    ico.size = max(ico.info.get("sizes", [ico.size]))  # the largest frame of the .ico
    big = ico.convert("RGBA").resize((512, 512), Image.LANCZOS)
    big.save(OUT / "app.png")
    if sys.platform == "darwin" and shutil.which("iconutil"):
        iconset = OUT / "app.iconset"
        iconset.mkdir(exist_ok=True)
        for size in (16, 32, 128, 256, 512):
            big.resize((size, size), Image.LANCZOS).save(iconset / f"icon_{size}x{size}.png")
            big.resize((size * 2, size * 2), Image.LANCZOS).save(iconset / f"icon_{size}x{size}@2x.png")
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(OUT / "app.icns")], check=True)
    print("icons in", OUT)


if __name__ == "__main__":
    main()
