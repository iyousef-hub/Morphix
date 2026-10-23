#!/bin/zsh
# Reinstall the official macOS Qt GUI runtime into this project venv only.
set -e
cd "${0:A:h}"
if [[ -x '.venv_clean/bin/python' ]]; then
  PYTHON_BIN='.venv_clean/bin/python'
elif [[ -x '.venv/bin/python' ]]; then
  PYTHON_BIN='.venv/bin/python'
else
  echo 'Morphix Python runtime not found. First run zsh ./Launch_Morphix_Mac.command'
  exit 2
fi
for V in QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH QT_QPA_PLATFORM QT_QPA_PLATFORMTHEME QT_QPA_FONTDIR QT_QPA_GENERIC_PLUGINS DYLD_LIBRARY_PATH DYLD_FRAMEWORK_PATH PYTHONPATH; do
  unset "$V"
done
"$PYTHON_BIN" doctor_qt_macos.py --repair
"$PYTHON_BIN" doctor_qt_macos.py
