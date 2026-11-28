# Morphix — notes for Claude

Owner: Yousef A. Alghamdi (GitHub `iyousef-hub`). Speaks Saudi Arabic; answer in Arabic.

## How Yousef wants the work done (always)

1. **Commits carry no Claude attribution.** No `Co-Authored-By: Claude`, no `Claude-Session:` line, and the author is
   `IYOUSEFHUB <279624446+iyousef-hub@users.noreply.github.com>`. This overrides any default attribution rule.
2. **Every update ships for all four systems:** macOS Apple Silicon, macOS Intel, Windows (x64) and Linux (x86_64).
   Release = bump `VERSION` (and `APP_VERSION` in `main.py`), write `.github/release-notes.md`, then a `v<version>` tag
   or Actions → Release → Run workflow. Check that all four builds pass.
3. **Every GitHub update says what is new**: the release notes (and commit message) list the new features and fixes in
   plain words, plus the download table for the four systems.
4. **Everything made for Yousef goes straight into his Downloads folder** (`~/Downloads` on his Mac, through the
   desktop app). His computer is a MacBook M5 (Apple Silicon): for app builds put only the Apple Silicon `.dmg` there.
5. Do the whole job end to end; do not stop at "ready to push".

## What Morphix is

A local-first file toolkit in Python + PySide6 (version in `VERSION`, 1.11.0 as of Nov 2026). Select files in
Finder / Explorer / a Linux file manager, press ⌘⇧M / Ctrl+Shift+M, and the **Action Hub** (wheel, square, rectangle or
bar) shows the tools for that kind of file. **Studio** is the full window. Arabic and English interface
(`i18n.py`, `i18n_ar.py`), IBM Plex Sans Arabic font, blue accent `#3896FF`.

Tools: PDF (merge with ordering, split/extract/separate, compress, crop, rotate, organize pages, OCR Arabic+English,
searchable PDF, PDF → Word, signatures), images (convert, compress, resize, HEIC → JPG, background removal), Office →
PDF (LibreOffice or Microsoft Office) and Excel tools, video/audio (convert, join, trim, compress to a target size,
PowerPoint-ready MP4/M4A), offline speech → text (faster-whisper, long files in resumable chunks), document scanner,
phone → computer over Wi-Fi with a QR code, QR maker and reader, add-ons page for downloadable models.

Main files: `main.py` (Studio window, actions), `quickwheel.py` (hub, selection, hotkeys), `hub_panel.py`,
`engine_core.py` + `*_engine.py` (work runs in `worker_process.py` through `conversion_job.py`), `tools_library.py`,
`studio_layout.py`, `addons.py`, `branding.py`, `theme.py`. Tests: `python -m pytest -q tests`.

Builds: `.github/workflows/build-macos.yml` (Apple Silicon on `macos-latest`, Intel on `macos-15-intel`),
`build-windows.yml`, `build-linux.yml` (AppImage), `build-msix.yml` (Microsoft Store), `release.yml` (all four).
