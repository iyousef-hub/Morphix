# Morphix v1.4.11 — Background Menu & Quick Wheel Input Fix

## Why v1.4.10 looked frozen

The user's screenshot showed the native macOS **M menu open in front of the wheel**.
The macOS QSystemTrayIcon could emit `Trigger` while opening the menu, and the
old handler simultaneously displayed a `Qt.Tool` wheel underneath. Native
menus capture input while open; the wheel was visible, but not clickable.

Additionally, the macOS Finder `osascript` selection lookup ran **synchronously
in the GUI event thread** during shortcut/menu handling, for up to 10 seconds.
An Automation permission prompt could therefore make the entire interface
appear hung.

Finally, all Morphix folders share one per-user background socket. Starting a
new extracted version could leave an older helper servicing the tray menu and
wheel. The launcher now detects running helpers and prints their processes.

## Changes

1. Clicking the macOS menu-bar M opens its menu **only**. Click `Quick Wheel`
   inside the menu or press your configured global shortcut to show the wheel.
2. Close the native M menu before opening Quick Wheel, Studio or a file dialog.
3. The macOS wheel uses a focusable top-level `Qt.Window` (while Windows retains
   `Qt.Tool`), and explicitly requests focus while remaining a background
   accessory application without a Dock icon.
4. Finder selection is fetched by **nonblocking QProcess** with a 6.5-second
   timeout; the UI loop no longer waits synchronously on AppleScript.
5. Existing Finder live-poll processes also have a timeout.
6. The macOS launcher prefers a clean Homebrew `.venv_clean`, creates one when
   needed, and alerts when any *other* Morphix version is already running.
7. A manual native-mouse click test `gui_selftest_v1411.py` is included.

## Update an existing Morphix 23

1. Close Studio; quit all old background Morphix instances from the blue M
   menu. If the old menu is unresponsive, use macOS **Activity Monitor** to
   quit the relevant Python process, after verifying its command belongs to
   Morphix. Do not kill unrelated Python programs.
2. Extract update ZIP and copy contents of its `Morphix/` folder over the
   current Morphix 23 project folder (`main.py` is in the folder). **Keep**
   `.venv_clean` and your conversion outputs.
3. From the project folder run `zsh ./Launch_Morphix_Mac.command`. It checks
   for old processes and starts the background helper without opening Studio.
4. Click M at the top-right. The wheel must not pop up just from opening the
   M menu. Choose `Open Morphix Studio`, or select files in Finder and choose
   `Quick Wheel` from the menu; the shortcut also works.
5. If the wheel is visible yet still does not click, run
   `.venv_clean/bin/python gui_selftest_v1411.py` after closing Morphix; click
   the top sector and look for `CLICK RECEIVED`.
6. For diagnostics, inspect `~/Library/Logs/Morphix/morphix.log`.

## Verification

110 local automated tests passed; 2 tests require a graphical Qt environment
and were skipped. macOS-specific native window clicks require a real Mac test;
this release is a targeted fix, not a guarantee of native macOS UI behavior.
