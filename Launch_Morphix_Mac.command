#!/bin/zsh
# Morphix 1.5 — installer / updater for macOS.
#
# Double-click (or: zsh ./Launch_Morphix_Mac.command). It:
#   1. copies Morphix into   ~/Library/Application Support/Morphix/app
#   2. creates its private Python runtime there (…/app/runtime)
#   3. creates ~/Applications/Morphix.app  — open Morphix from there.
# Why not run from this folder? Desktop/Documents are privacy-protected and
# often iCloud-synced; an app launched from Finder cannot load Qt from there
# ("Could not find the Qt platform plugin cocoa").
# Running a newer version's installer later simply updates the same install.
# Internet is needed only the first time (and when components change).
set -u
SRC="${0:A:h}"
SUPPORT="$HOME/Library/Application Support/Morphix"
ROOT="$SUPPORT/app"
PY="$ROOT/runtime/bin/python"
APP="$HOME/Applications/Morphix.app"
LOG_DIR="$HOME/Library/Logs/Morphix"
mkdir -p "$LOG_DIR" "$ROOT" "$HOME/Applications"

# Never let Conda / Homebrew Qt / old plugin paths leak into Morphix.
for V in QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH QT_QPA_PLATFORM QT_QPA_PLATFORMTHEME \
         QT_QPA_FONTDIR QT_QPA_GENERIC_PLUGINS DYLD_LIBRARY_PATH DYLD_FRAMEWORK_PATH PYTHONPATH \
         PYTHONHOME CONDA_PREFIX; do
  unset "$V" 2>/dev/null
done

say() { print -r -- "▸ $*"; }
fail() {
  print -r -- ""; print -r -- "✗ $*"
  osascript -e "display alert \"Morphix setup\" message \"$*\" as critical" >/dev/null 2>&1
  read '?Press Enter to close: '
  exit 1
}

[[ -f "$SRC/main.py" ]] || fail "Run this file from inside the Morphix folder."

# ---------------------------------------------------------------- stop running copies
# Every running Morphix helper (old folders AND a previous install) must stop,
# otherwise it keeps serving its old code through the shared socket.
RUNNING=""
for PID in ${(f)"$(pgrep -f '[Mm]orphix.*main[.]py' 2>/dev/null)"}; do
  [[ -n "$PID" && "$PID" != "$$" ]] || continue
  CMD="$(ps -o command= -p "$PID" 2>/dev/null)"
  [[ "$CMD" == *python* || "$CMD" == *Python* ]] || continue
  [[ "$CMD" == *--morphix-worker* || "$CMD" == *worker_process.py* ]] && continue
  RUNNING+="$PID $CMD"$'\n'
done
RUNNING="${RUNNING%$'\n'}"
if [[ -n "$RUNNING" ]]; then
  say "Morphix is currently running:"
  print -r -- "$RUNNING"
  read '?Quit it so it can be updated? [Y/n] ' ANSWER
  if [[ "${ANSWER:-Y}" != [Nn]* ]]; then
    print -r -- "$RUNNING" | awk '{print $1}' | xargs kill 2>/dev/null || true
    sleep 1.5
  else
    fail "Quit Morphix first (blue M menu → Quit Morphix), then run this again."
  fi
fi

# ---------------------------------------------------------------- copy program files
say "Installing Morphix $(cat "$SRC/VERSION") into Application Support…"
[[ "$SRC" == "$ROOT" ]] || rsync -a --delete \
  --exclude 'runtime/' --exclude '.venv*/' --exclude '__pycache__/' --exclude '.pytest_cache/' \
  --exclude 'Morphix.app/' --exclude 'dist/' --exclude 'build/' \
  "$SRC/" "$ROOT/" || fail "Could not copy Morphix files into $ROOT"
xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null
# A Morphix.app created by an earlier 1.5 setup inside the Desktop folder
# points to the wrong place; remove it so it is not used by mistake.
[[ -d "$SRC/Morphix.app" ]] && rm -rf "$SRC/Morphix.app"

# ---------------------------------------------------------------- Python runtime
if [[ ! -x "$PY" ]]; then
  BASE=""
  for C in /opt/homebrew/opt/python@3.13/bin/python3.13 /opt/homebrew/opt/python@3.12/bin/python3.12 \
           /opt/homebrew/bin/python3 /usr/local/opt/python@3.13/bin/python3.13 /usr/local/bin/python3 \
           /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
           /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
           /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 /usr/bin/python3; do
    [[ -x "$C" ]] || continue
    # Skip Anaconda/Miniconda interpreters (their Qt breaks the Cocoa plugin).
    if "$C" -c 'import sys; sys.exit(1 if ("conda" in sys.prefix.lower() or sys.version_info < (3, 10)) else 0)' 2>/dev/null; then
      BASE="$C"; break
    fi
  done
  [[ -n "$BASE" ]] || fail "Python 3.10+ is required. Install it from python.org (or: brew install python@3.13), then run this file again."
  say "Creating private runtime with $BASE"
  "$BASE" -m venv "$ROOT/runtime" || fail "Could not create the Python runtime."
fi

# ---------------------------------------------------------------- packages
if ! "$PY" -c 'from PySide6.QtWidgets import QApplication; import pymupdf; from PIL import Image; import imageio_ffmpeg; import openpyxl' >/dev/null 2>&1; then
  say "Installing Morphix components (needs internet)…"
  "$PY" -m pip install --upgrade pip >/dev/null 2>&1
  "$PY" -m pip install -r "$ROOT/requirements.txt" || fail "Installing components failed. Check your internet connection and try again."
fi
if ! "$PY" -c 'import faster_whisper' >/dev/null 2>&1; then
  say "Installing the offline Speech → Text engine…"
  "$PY" -m pip install -r "$ROOT/requirements-speech.txt" \
    || say "Speech → Text engine could not be installed on this Mac; all other tools still work."
fi

if ! "$PY" "$ROOT/doctor_qt_macos.py" > "$LOG_DIR/qt_preflight.log" 2>&1; then
  tail -30 "$LOG_DIR/qt_preflight.log"
  fail "The Qt interface runtime is broken. Details: $LOG_DIR/qt_preflight.log"
fi

# ---------------------------------------------------------------- Morphix.app
# Built locally on this Mac, so Gatekeeper does not quarantine it.
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Morphix</string>
  <key>CFBundleDisplayName</key><string>Morphix</string>
  <key>CFBundleIdentifier</key><string>com.iyousefhub.morphix.launcher</string>
  <key>CFBundleVersion</key><string>$(cat "$ROOT/VERSION")</string>
  <key>CFBundleShortVersionString</key><string>$(cat "$ROOT/VERSION")</string>
  <key>CFBundleExecutable</key><string>Morphix</string>
  <key>CFBundleIconFile</key><string>Morphix</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSUIElement</key><true/>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
</dict></plist>
PLIST
cat > "$APP/Contents/MacOS/Morphix" <<LAUNCH
#!/bin/zsh
# Generated by Launch_Morphix_Mac.command — opens Morphix without Terminal.
ROOT="$ROOT"
PY="\$ROOT/runtime/bin/python"
LOG="\$HOME/Library/Logs/Morphix/morphix.log"
mkdir -p "\$HOME/Library/Logs/Morphix"
for V in QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH QT_QPA_PLATFORM DYLD_LIBRARY_PATH DYLD_FRAMEWORK_PATH PYTHONPATH PYTHONHOME; do unset "\$V"; done
if [[ ! -x "\$PY" ]]; then
  osascript -e 'display alert "Morphix" message "Morphix is not installed correctly. Run Launch_Morphix_Mac.command from the Morphix folder once."'
  exit 1
fi
cd "\$ROOT"
print -r -- "--- Morphix.app launch \$(date '+%F %T') ---" >>"\$LOG"
# Already running? This only asks the running Morphix to show Studio.
# Otherwise it starts the background helper and opens Studio.
nohup "\$PY" "\$ROOT/main.py" --studio >>"\$LOG" 2>&1 </dev/null &
PID=\$!
disown
# If it dies at once, capture Qt's detailed reason and tell the user.
sleep 4
if ! kill -0 \$PID 2>/dev/null && tail -5 "\$LOG" | grep -q 'qt.qpa\|Qt platform plugin'; then
  QT_DEBUG_PLUGINS=1 "\$PY" -c 'from PySide6.QtWidgets import QApplication; QApplication([])' \
    >"\$HOME/Library/Logs/Morphix/qt_debug.log" 2>&1
  osascript -e 'display alert "Morphix could not start" message "Details were saved to ~/Library/Logs/Morphix/qt_debug.log"' >/dev/null 2>&1
fi
exit 0
LAUNCH
chmod +x "$APP/Contents/MacOS/Morphix"
if command -v sips >/dev/null && command -v iconutil >/dev/null; then
  ICONSET="$(mktemp -d)/Morphix.iconset"; mkdir -p "$ICONSET"
  for spec in 16:16x16 32:16x16@2x 32:32x32 64:32x32@2x 128:128x128 256:128x128@2x 256:256x256 512:256x256@2x 512:512x512 1024:512x512@2x; do
    sips -s format png -z "${spec%%:*}" "${spec%%:*}" "$ROOT/assets/morphix_logo.png" --out "$ICONSET/icon_${spec#*:}.png" >/dev/null 2>&1
  done
  iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/Morphix.icns" 2>/dev/null
fi
touch "$APP"

open "$APP"
say "Done. Morphix is installed in: ~/Applications/Morphix.app"
say "Look for the blue M in the menu bar. Open Morphix from Applications / Spotlight from now on."
say "Your old Morphix folders on the Desktop are no longer used — you may delete them."
say "Speech → Text: open Studio → Speech models → Download (one time)."
open -R "$APP" 2>/dev/null
sleep 2
