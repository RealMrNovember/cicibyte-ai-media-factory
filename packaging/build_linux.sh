#!/bin/bash
# Builds dist/CiciByteMediaFactory-<version>-x86_64.AppImage (+ .sha256) with a Qt WebEngine window.
# Needs: Python with ".[desktop]" and Pillow, and appimagetool on PATH (or APPIMAGETOOL=/path).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
VER=$(python -c "import sys; sys.path.insert(0, 'backend'); import mediafactory; print(mediafactory.__version__)")
ARCH=x86_64
NAME=CiciByteMediaFactory

python packaging/make_icons.py
pyinstaller --noconfirm --clean --onedir --name "$NAME" \
  --paths "$ROOT/backend" --add-data "$ROOT/backend/mediafactory/web:mediafactory/web" --add-data "$ROOT/build/icons/app.png:." \
  --hidden-import qtpy --collect-submodules webview.platforms \
  --distpath dist/linux --workpath build/pyi-linux --specpath "$ROOT/build" "$ROOT/packaging/desktop_entry.py"
grep -rqs "pywebview-drag-region" "dist/linux/$NAME" --include=app.js || { echo "the bundled panel is missing"; exit 1; }

APPDIR=dist/linux/AppDir
rm -rf "$APPDIR" && mkdir -p "$APPDIR/usr/bin"
cp -R "dist/linux/$NAME/." "$APPDIR/usr/bin/"
cp build/icons/app.png "$APPDIR/cicibyte-media-factory.png"
cat > "$APPDIR/cicibyte-media-factory.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=CiciByte AI Media Factory
Comment=AI YouTube Shorts and Instagram Reels factory (client)
Exec=CiciByteMediaFactory
Icon=cicibyte-media-factory
Categories=AudioVideo;Video;
Terminal=false
EOF
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
# Qt WebEngine's sandbox needs user namespaces that many distributions and AppImages do not allow.
export QTWEBENGINE_DISABLE_SANDBOX=1
export PYWEBVIEW_GUI="${PYWEBVIEW_GUI:-qt}"
exec "$HERE/usr/bin/CiciByteMediaFactory" "$@"
EOF
chmod +x "$APPDIR/AppRun"

OUT="dist/$NAME-$VER-$ARCH.AppImage"
ARCH=$ARCH ${APPIMAGETOOL:-appimagetool} --no-appstream "$APPDIR" "$OUT"
chmod +x "$OUT"

# Smoke test on a virtual display: the window must open, load the panel and close by itself.
MF_DESKTOP_SMOKE=12 MF_SERVER_URL=http://127.0.0.1:9 xvfb-run -a "$OUT" --appimage-extract-and-run

(cd dist && sha256sum "$(basename "$OUT")" > "$(basename "$OUT").sha256")
echo "built $OUT"
