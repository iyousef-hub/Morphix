# Morphix 1.4.7 — Studio Input / Focus Isolation

## Why this build exists
On macOS some users observed Morphix Studio visually displayed but refusing mouse
clicks. The previous build switched the *same running Qt application* between
AppKit accessory and regular application policies while keeping an always-on-top
floating wheel alive. This is a plausible cause of focus/input faults, not a
proven diagnosis of every macOS build.

## What changed
- **Separate Studio process** (`python main.py --studio-window`). Studio runs
  as a normal Qt desktop process; the Quick Wheel helper remains an accessory
  background process. Studio does not install any global keyboard monitor.
- Opening Studio hides any floating wheel and stops live selection polling
  first so an invisible transparent tool surface cannot block Studio clicks.
- Removed the application-wide key event filter from Studio; Shift quick-actions
  is now handled only inside the file list.
- Studio Settings are opened in the normal Studio process. Saving them sends
  an IPC reload request to the background helper to re-register hotkeys.
- Studio instances are single-instance. A second open command raises the existing
  Studio window; it does not spawn a second independent window.
- Selected files from Studio can still be sent to the background Quick Wheel.
- Closing Studio exits only the Studio process. The Quick Wheel service continues.
- Added `gui_selftest_v147.py` to confirm real Qt button signals in Studio.

## Upgrade
1. Quit ALL existing Morphix processes, including ones running from older folders.
2. Unzip into a **new folder**. On macOS run `zsh ./Launch_Morphix_Mac.command`.
3. Click the blue M menu bar icon and choose `Open Morphix Studio`.
4. Try Add files, Customize Wheel, Wheel appearance, and Record a shortcut.
5. If the UI looks stuck, quit old versions and run:
   `.venv/bin/python main.py --studio-window`
   This starts Studio alone, without the background service, to isolate input issues.

## Verification
- Static compile of Python modules
- Full portable suite: 92 passed, 2 skipped (Qt GUI tests require real desktop)
- **Not** physically tested on macOS or Windows in the build environment.

## Status
This is a source release and regression fix, not a signed/notarized production app.
RAR creation still requires a separately licensed writer.
TXT/OCR and Office conversion fidelity is dependent on the source document.
