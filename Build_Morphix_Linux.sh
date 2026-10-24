#!/usr/bin/env bash
# Build Morphix-<version>-x86_64.AppImage — one file that runs on most Linux
# distributions (Ubuntu 22.04+, Debian 12+, Fedora, Mint, …) without Python.
#
#   ./Build_Morphix_Linux.sh            (uses python3 from PATH)
#   PYTHON=python3.12 ./Build_Morphix_Linux.sh
#
# Needs: python3 with pip, and the internet for the first run.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
PY="${PYTHON:-python3}"
VERSION="$(tr -d '[:space:]' < VERSION)"
WORK="${MORPHIX_BUILD_DIR:-$ROOT/build_linux}"
OUT="$ROOT/dist"
mkdir -p "$WORK" "$OUT"

if [[ "${SKIP_PIP:-0}" != 1 ]]; then
  echo '▸ Installing the build tools…'
  "$PY" -m pip install -q -r requirements.txt -r requirements-speech.txt 'pyinstaller>=6.10,<7'
fi

# Qt 6.5+ needs libxcb-cursor on X11; many desktops do not install it, so bundle it.
EXTRA=()
for lib in libxcb-cursor.so.0; do
  found="$(ldconfig -p 2>/dev/null | awk -v l="$lib" '$1==l {print $NF; exit}')"
  [[ -n "$found" ]] && EXTRA+=(--add-binary "$found:.")
done

echo '▸ Building Morphix (a few minutes)…'
rm -rf "$WORK/dist" "$WORK/build"
"$PY" -m PyInstaller --noconfirm --clean --windowed --onedir \
  --distpath "$WORK/dist" --workpath "$WORK/build" --specpath "$WORK" --paths "$ROOT" \
  --name Morphix \
  --collect-all imageio_ffmpeg --collect-all pymupdf \
  --collect-all faster_whisper --collect-all ctranslate2 --collect-all onnxruntime \
  --collect-submodules huggingface_hub --collect-submodules tokenizers --collect-submodules openpyxl \
  --collect-submodules Xlib \
  --hidden-import worker_process --hidden-import engine_core --hidden-import transcription_engine \
  --hidden-import hub_panel --hidden-import i18n_ar --hidden-import ui_kit --hidden-import win_compat \
  --hidden-import docs_engine --hidden-import background_engine --hidden-import background_dialog \
  --hidden-import theme --hidden-import linux_hotkeys --hidden-import linux_integration \
  "${EXTRA[@]}" \
  --add-data "$ROOT/assets:assets" "$ROOT/main.py"
[[ -x "$WORK/dist/Morphix/Morphix" ]] || { echo 'Morphix was not built.'; exit 1; }

echo '▸ Making the AppImage…'
APPDIR="$WORK/Morphix.AppDir"
rm -rf "$APPDIR"; mkdir -p "$APPDIR/usr/lib"
cp -a "$WORK/dist/Morphix" "$APPDIR/usr/lib/morphix"
cp assets/morphix_logo.png "$APPDIR/morphix.png"
cp assets/morphix_logo.png "$APPDIR/.DirIcon"
cat > "$APPDIR/morphix.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Morphix
Comment=Every file tool you need — one shortcut away
Exec=Morphix --studio %F
Icon=morphix
Terminal=false
Categories=Utility;Office;
X-AppImage-Version=$VERSION
DESK
cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/morphix/Morphix" "$@"
RUN
chmod +x "$APPDIR/AppRun"

TOOL="$WORK/appimagetool-x86_64.AppImage"
if [[ ! -x "$TOOL" ]]; then
  curl -fsSL -o "$TOOL" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi
TARGET="$OUT/Morphix-$VERSION-x86_64.AppImage"
rm -f "$TARGET"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" --no-appstream "$APPDIR" "$TARGET" >/dev/null
chmod +x "$TARGET"
echo
echo "✓ Done: $TARGET"
echo '  Users: make it executable (right-click → Properties → Allow executing) and double-click.'
