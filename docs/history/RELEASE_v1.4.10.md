# Morphix 1.4.10 — Studio interaction crash fix

## Fixed from the actual macOS traceback

1. ShortcutRecorder now initializes `_recording` (and `_saved`) **before** the parent `QLineEdit` runs any lifecycle code. Its event/focus/key handlers also guard against early events. Previously opening Wheel appearance / Record a shortcut raised `AttributeError` at `setReadOnly(True)`.
2. `Window.open_quick_wheel()` now calls `StudioController.open_quick_wheel()` instead of nonexistent `show_wheel(use_studio_selection=True)`. This routes wheel requests to the background helper via IPC.
3. Updated the Preferences sidebar version label.

The previous Qt/Cocoa `UF_HIDDEN` repair and `.venv_clean` runtime selection from v1.4.9 are preserved.

## Installation on existing Morphix 22

1. Quit all Morphix processes and close Studio.
2. Copy the contents **inside the update ZIP's `Morphix/` directory** over the existing project folder (containing `main.py`), replacing matching files. Do **not** move or delete `.venv_clean`.
3. From the existing project directory, launch Studio:
   `.venv_clean/bin/python main.py --studio-window`
4. Check that Wheel appearance and Record a shortcut open without traceback. To test Quick Wheel, run the background helper as well with `.venv_clean/bin/python main.py --background` in a second Terminal, or `zsh ./Launch_Morphix_Mac.command` (which uses `.venv_clean`).
5. Optional real macOS GUI smoke test: `.venv_clean/bin/python gui_selftest_v1410.py`.

The Studio instance is deliberately separate from the background Quick Wheel. If you start Studio alone with `--studio-window`, the Quick Wheel action needs the background helper to be running; it will show an informational dialog when it is absent. The Studio window should nevertheless respond.

## Verification

104 automated project tests passed, 2 GUI-dependent tests skipped on the build environment. The standalone GUI smoke test is included but **has not been run on macOS here**.
