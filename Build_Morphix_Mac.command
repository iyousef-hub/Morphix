#!/bin/zsh
# Build Morphix.app + Morphix.dmg — a standalone Mac app for people WITHOUT Python.
#
# Run this on YOUR Mac (the developer machine) after Launch_Morphix_Mac.command
# has been run once. The result in dist/ contains its own Python, Qt, PDF, OCR,
# FFmpeg and the offline Speech → Text engine. Users just open the DMG and drag
# Morphix into Applications. (Speech models, ~0.5–3 GB, are downloaded once
# from inside the app; nothing else needs installing.)
set -e
cd "${0:A:h}"
ROOT="$PWD"
exec > >(tee "$ROOT/build_log.txt") 2>&1
function goodbye { echo; read '?Press Enter to close this window: '; }
trap goodbye EXIT
[[ "$(uname -s)" == 'Darwin' ]] || { echo 'Build requires macOS.'; exit 1; }

PY="$HOME/Library/Application Support/Morphix/app/runtime/bin/python"
[[ -x "$PY" ]] || { echo 'Run Launch_Morphix_Mac.command once first; it prepares the Morphix runtime.'; exit 1; }
for V in QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH DYLD_LIBRARY_PATH DYLD_FRAMEWORK_PATH PYTHONPATH; do unset "$V"; done

echo '▸ Installing the build tools…'
"$PY" -m pip install -q -r requirements.txt -r requirements-speech.txt 'pyinstaller>=6.10,<7'

ICON_ARGS=()
# Build OUTSIDE the Desktop: iCloud adds Finder metadata to every file there,
# and codesign refuses a bundle that carries it ("detritus not allowed").
WORK="$HOME/Library/Caches/Morphix-build"
rm -rf "$WORK"; mkdir -p "$WORK" "$ROOT/dist"
ICONSET="$WORK/Morphix.iconset"
if command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
  mkdir -p "$ICONSET"
  for spec in '16:16x16' '32:16x16@2x' '32:32x32' '64:32x32@2x' '128:128x128' '256:128x128@2x' '256:256x256' '512:256x256@2x' '512:512x512' '1024:512x512@2x'; do
    sips -s format png -z "${spec%%:*}" "${spec%%:*}" assets/morphix_logo.png --out "$ICONSET/icon_${spec#*:}.png" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o "$WORK/Morphix.icns"
  ICON_ARGS=(--icon "$WORK/Morphix.icns")
fi

echo '▸ Building Morphix.app (this takes a few minutes)…'
"$PY" -m PyInstaller --noconfirm --clean --windowed --onedir \
  --distpath "$WORK/dist" --workpath "$WORK/build" --specpath "$WORK" --paths "$ROOT" \
  --name Morphix --osx-bundle-identifier com.iyousefhub.morphix \
  --collect-all imageio_ffmpeg --collect-all pymupdf \
  --collect-all faster_whisper --collect-all ctranslate2 --collect-all onnxruntime --collect-all rapidocr --collect-all pillow_heif --collect-all pdf2docx --collect-all docx --collect-all bidi --hidden-import cv2 \
  --collect-submodules huggingface_hub --collect-submodules tokenizers \
  --collect-submodules AppKit --collect-submodules Foundation --collect-submodules objc \
  --hidden-import worker_process --hidden-import engine_core --hidden-import transcription_engine \
  --hidden-import hub_panel --hidden-import i18n_ar --hidden-import ui_kit --hidden-import theme \
  --hidden-import tools_engine --hidden-import ocr_models --hidden-import latex_ocr --hidden-import action_dialogs --hidden-import signature_dialog --hidden-import docs_engine --hidden-import background_engine --hidden-import background_dialog \
  --collect-submodules openpyxl \
  --add-data "$ROOT/assets:assets" "${ICON_ARGS[@]}" "$ROOT/main.py"
APP="$WORK/dist/Morphix.app"
[[ -d "$APP" ]] || { echo 'Morphix.app was not created.'; exit 1; }

# Menu-bar app, and the permission text macOS shows when Morphix reads the
# Finder selection (without it macOS silently refuses Finder access).
PLIST="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :LSUIElement bool true' "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c 'Add :NSAppleEventsUsageDescription string Morphix reads the files you select in Finder so it can show the right tools.' "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $(cat VERSION)" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $(cat VERSION)" "$PLIST" 2>/dev/null || true

# Office → PDF is optional: bundled only when LibreOffice is installed here.
LO_SOURCE="${MORPHIX_LIBREOFFICE_APP:-/Applications/LibreOffice.app}"
if [[ -x "$LO_SOURCE/Contents/MacOS/soffice" ]]; then
  echo '▸ Adding LibreOffice for Office → PDF…'
  mkdir -p "$APP/Contents/Resources/office_runtime"
  ditto "$LO_SOURCE" "$APP/Contents/Resources/office_runtime/LibreOffice.app"
else
  echo '▸ LibreOffice not found — Office → PDF will be unavailable in this build (everything else works).'
fi

# Ad-hoc signature so macOS accepts the bundle on Apple Silicon.
echo '▸ Signing…'
xattr -cr "$APP"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP" && echo '  ✓ Signature OK'


echo '▸ Creating Morphix.dmg…'
STAGE="$WORK/dmg"
rm -rf "$STAGE"; mkdir -p "$STAGE"
ditto "$APP" "$STAGE/Morphix.app"
ln -s /Applications "$STAGE/Applications"
rm -f "$ROOT/dist/Morphix.dmg"
hdiutil create -volname Morphix -srcfolder "$STAGE" -ov -format UDZO "$ROOT/dist/Morphix.dmg" >/dev/null
rm -rf "$ROOT/dist/Morphix.app" "$ROOT/dist/Morphix" "$ROOT/build"
open -R "$ROOT/dist/Morphix.dmg"
print ''
print "✓ Done: $ROOT/dist/Morphix.dmg"
print '  Users open it and drag Morphix into Applications — no Python or Terminal needed.'
print '  First open on another Mac: right-click Morphix → Open (the app is not notarized by Apple).'
