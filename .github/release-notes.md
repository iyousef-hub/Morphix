## Morphix 1.8.0 — Now on Linux 🐧

Every file tool you need — one shortcut away. PDF, images, Office, audio & video, OCR and offline speech-to-text.

### Download
- **Windows:** `Morphix_Windows_1.8.0.zip` — unzip it and run `Morphix.exe` (keep it together with the `_internal` folder).
- **macOS (Apple Silicon):** `Morphix_macOS_1.8.0.dmg` — open it and drag Morphix into Applications. The first time, right-click Morphix → **Open**.
- **Linux (x86_64):** `Morphix-1.8.0-x86_64.AppImage` — make it executable (right-click → Properties → *Allow executing file as program*, or `chmod +x`) and double-click it.

### New: Linux version
- One file (AppImage) that runs on most distributions — Ubuntu 22.04+, Debian 12+, Fedora, Linux Mint and more. No installation, no Python.
- **Right-click → Morphix** in your file manager opens the Action Hub with the selected files:
  Files/Nautilus (*Scripts → Morphix*), Nemo and Dolphin.
- **Ctrl + Shift + M** works on X11 with any keyboard layout. On Wayland, Morphix adds the shortcut to GNOME's keyboard settings automatically.
  Linux file managers don't share the current selection with other apps, so with the shortcut copy your files first (Ctrl + C).
- Adds itself to the application menu and starts with the computer (can be turned off in Settings).
- Every tool works on Linux: PDF, OCR, images, Office → PDF (with LibreOffice), Excel tools, audio & video, speech-to-text, background removal.

### Fixes
- The Action Hub no longer shows black corners on Linux desktops without visual effects (compositor).

### Earlier fixes (1.7.1 – 1.7.2)
- Squeezed windows and cut-off text with the new font — fixed (1.7.2).
- Office → PDF failed silently on Windows; much faster conversion with Microsoft Office when installed (1.7.1).
- Overlapping text in the Studio sidebar; Mac app signing when built from an iCloud Desktop (1.7.1).

> These builds are not digitally signed. Windows may show a SmartScreen warning (**More info → Run anyway**), and Smart App Control may block the app if it is turned on.
