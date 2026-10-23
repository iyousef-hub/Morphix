# Morphix v1.4.6 — Studio & Shortcut Recorder

This release improves the presentation and everyday desktop behavior of Morphix.
It retains the v1.4.5 file-processing and ordered PDF/image merge engines.

## What's new

- **Studio redesign:** navigation sidebar, professional navy/blue workspace, batch file area, context-aware tool list and activity panel.
- **Keyboard Shortcut Recorder:** click the field, press modifiers (displayed immediately), then a trigger key. For example, Ctrl → Ctrl+Shift → Ctrl+Shift+Del. No typing `<ctrl>+...` manually.
- **Physical-key detection:** macOS compares NSEvent virtual key codes. Windows uses a low-level keyboard scan-code monitor. This is designed to behave the same under English, Arabic and other keyboard layouts. It requires OS keyboard permissions where applicable.
- **Background-only launch:** the Quick Wheel helper is visible in the macOS menu bar or Windows notification area, rather than as an open Studio window. macOS tries to remove its Dock icon in accessory mode and restore a Dock presence when Studio is opened.
- **Launch at Login:** optional checkbox. It is OFF by default and creates only a per-user launch setting when deliberately enabled.
- **Shortcuts persist:** the newly recorded shortcut updates the global monitor after saving preferences and appears on the Studio hero panel.

## How to launch on macOS

```bash
zsh ./Launch_Morphix_Mac.command
```

First launch prepares the `.venv` if necessary. Morphix then stays in the **menu bar (blue M)**. Open Studio or preferences from that icon.

To open the Studio directly (after your project environment is installed):

```bash
.venv/bin/python main.py --studio
```

The shortcut recording field is under **Wheel Settings → Shortcuts** or **Studio → Record a shortcut**.

## Tests and remaining verification

- `pytest -q`: **87 passed, 2 skipped** (skipped tests require a GUI / Qt runtime unavailable in the build container).
- The pure Mac and Windows scan-code matching and shortcut parsing tests passed.
- Files compile with Python's `compileall`.
- macOS Dock policy toggling, actual click-to-record capture on macOS/Windows, foreground focus, and the native Windows hook **still require real-machine testing**.
- For a local GUI smoke test run `.venv/bin/python gui_selftest_v146.py` after installing the project dependencies.
- This remains **source code**, not a signed/notarized `.dmg` or tested Windows `.exe` installer.

## Mac permissions

The global hotkey may require **Input Monitoring** permission for the currently running Python or packaged Morphix. Finder selection may require Automation permission. Do not disable macOS security protection globally.

## Unchanged known limitations

- Creating RAR archives requires a separately licensed encoder. ZIP and TAR.GZ work without it.
- Math OCR and unusual Office files may need special handling; OCR accuracy is not guaranteed.
- An independent, redistributable bundle of LibreOffice and embedded video engines requires build-time packaging and final macOS/Windows verification.
