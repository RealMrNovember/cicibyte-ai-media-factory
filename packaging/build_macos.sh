#!/bin/bash
# Builds dist/CiciByteMediaFactory-<version>-macOS-<arch>.dmg (+ .sha256). Needs: Python with ".[desktop]" and Pillow.
set -euo pipefail
cd "$(dirname "$0")/.."
VER=$(python -c "import sys; sys.path.insert(0, 'backend'); import mediafactory; print(mediafactory.__version__)")
ARCH=$(uname -m)
APP="CiciByte Media Factory"

python packaging/make_icons.py
pyinstaller --noconfirm --clean --windowed --onedir --name "$APP" \
  --icon build/icons/app.icns --osx-bundle-identifier com.cicibyte.mediafactory \
  --paths backend --add-data "backend/mediafactory/web:mediafactory/web" --add-data "build/icons/app.png:." \
  --distpath dist/mac --workpath build/pyi-mac --specpath build packaging/desktop_entry.py
grep -rqs "pywebview-drag-region" "dist/mac/$APP.app/Contents" --include=app.js || { echo "the bundled panel is missing"; exit 1; }

# Smoke test: the window must open, load the panel and close by itself.
MF_DESKTOP_SMOKE=10 MF_SERVER_URL=http://127.0.0.1:9 "dist/mac/$APP.app/Contents/MacOS/$APP"

rm -rf dist/mac/dmg && mkdir -p dist/mac/dmg
cp -R "dist/mac/$APP.app" dist/mac/dmg/
ln -s /Applications dist/mac/dmg/Applications
OUT="dist/CiciByteMediaFactory-$VER-macOS-$ARCH.dmg"
hdiutil create -volname "$APP" -srcfolder dist/mac/dmg -ov -format UDZO "$OUT"
(cd dist && shasum -a 256 "$(basename "$OUT")" > "$(basename "$OUT").sha256")
echo "built $OUT"
