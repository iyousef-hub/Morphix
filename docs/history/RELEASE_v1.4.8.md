# Morphix v1.4.8 — macOS Cocoa / Studio startup fix

This release addresses the separate Morphix Studio process not opening and the
`qt.qpa.plugin: Could not find the Qt platform plugin "cocoa"` crash.

## Changes
- `qt_macos_runtime.py`: removes inherited Qt/Conda overrides, requires the
  matching `libqcocoa.dylib` in the active PySide6-Essentials runtime *before*
  importing QtWidgets. A missing plugin now causes an intelligible message.
- `doctor_qt_macos.py`: diagnoses missing Cocoa and can repair Qt packages into
  the project `.venv`; optional `--probe` attempts a real Qt load in a subprocess.
- `Launch_Morphix_Mac.command`: performs a Cocoa preflight and targeted pip
  reinstall when missing, preserving all existing project files and settings.
- `studio_host.py`: detached Studio now logs startup failures to
  `~/Library/Logs/Morphix/studio.log` instead of discarding stdout/stderr.
- `quickwheel.py`: checks if Studio child exits immediately and shows a system
  notification (not a blocking dialog in the accessory process).

## Important limitations
- Qt Cocoa GUI cannot be tested from this Linux workspace. The diagnosis of
  missing Cocoa is grounded in the user's macOS log; any deeper plugin loading
  or focus issue will need the `studio.log` and optional Qt diagnostic output.
- No other conversion capabilities are claimed as newly implemented here.
- Source project, not a signed or notarized standalone macOS .app.
