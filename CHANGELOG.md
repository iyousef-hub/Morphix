## v1.7.0 — Background removal, documents & Excel tools

- **Add-ons** page (Studio, Settings and the M menu): every downloadable component with its size, a short
  description, install status, Download / Remove buttons and live progress.
- About: “Yousef A.Alghamdi” (Arabic: «من تطوير: يوسف الغامدي | Yousef A.Alghamdi»).

- **Remove background** for images (offline): ISNet “Standard” (default) and BiRefNet “Finest edges”
  (Macs with 16 GB+). The subject keeps its exact original pixels and full resolution (lossless PNG);
  transparent, white or black background. Model downloads once on first use.
- **Mixed documents** (Word + PowerPoint + Excel + images + PDF): “Merge everything into one PDF”
  (with order dialog) or “Convert each file to its own PDF”. Several Word/PowerPoint files can be merged too.
- **Excel tools**: PDF with each sheet fitted on one page, CSV per sheet (UTF-8, Arabic-safe),
  split sheets into files (formatting kept), merge workbooks (formatting, widths, merged cells, formulas),
  CSV → Excel (keeps leading zeros, right-to-left for Arabic data).
- Settings in Arabic: right-aligned sidebar with the symbol after the words; file-action list draws its own
  tick boxes (macOS showed only one in right-to-left lists).
- About page: centred design, “completely free” note, developer line centred in a smaller font.
- Morphix now starts with the computer by default (can be turned off in Settings → Startup).

## v1.6.0 — Action Hub, Arabic interface, stronger compression

- Settings preview is rendered as an image of the real hub, so tiles never overlap.
- Arabic: sliders fill from the right; check boxes / radio buttons sit at the right of their text.
- About: mission statement and “Developed by: Yousef bin Abdulaziz Alghamdi” with contact links.
- Speech → Text: “Maximum accuracy” (large-v3 at full precision, beam 8) and optional audio clean-up.
- Build_Morphix_Mac.command produces a standalone Morphix.dmg for users without Python
  (LibreOffice now optional; Finder permission text and menu-bar mode added to the bundle).

- **Quick Wheel → Action Hub**: shapes (wheel / square / rectangle / bar), screen position
  (pointer, center, top, bottom, left, right, remembered), and visibility (shortcut only / always on screen,
  refreshes the Finder selection on hover). Labels wrap instead of being cut.
- **Bilingual interface (Arabic / English)**: asked on first launch, changeable in Settings → Language
  (Morphix restarts itself). Arabic is a full right-to-left layout with natural, non-literal wording.
- **OCR** action in the hub for PDFs (makes scanned PDFs searchable).
- **PDF compression**: stronger image down-sampling and a new “Extreme” level that redraws pages as
  compressed images (110→55 DPI), plus a black-and-white option. The smallest valid result always wins.
- **Speech → Text accuracy**: new “Most accurate (large-v3)” model, Arabic/English style prompts, context
  carried across parts, tuned VAD and hallucination filters.
- Studio redesign: logo beside the name, *By Yousef*, tool buttons with icons, “Show in Finder” after a task.
- Fixed: a ⌘ shortcut recorded in Settings was saved as Ctrl on macOS (Qt swaps the keys) and never fired.
- Fixed: Studio tool list squashed its buttons instead of scrolling; “&” rendered as an underscore.
- macOS: Morphix asks for Accessibility permission itself and enables the shortcut as soon as it is granted.

## v1.5.0 — Offline Speech → Text + stability

### New
- **Speech → Text (Arabic / English, offline)** for audio *and* video files, from the Quick Wheel and Studio.
  Outputs TXT (paragraphs), TXT with timestamps, SRT and WebVTT.
- Built for long recordings (tested pipeline on a 5-hour file: flat ~160 MB memory):
  silence-aware ~10 min chunks, live partial transcript, checkpoint + automatic resume,
  live progress / time remaining, Cancel, keeps the Mac awake while running.
- Studio → **Speech models**: one-time model download (Fast ≈480 MB / Accurate ≈1.6 GB);
  afterwards the model always loads with `local_files_only=True`.
- More audio/video types recognised (m4b, opus, wma, amr, caf, mts, wmv, flv, …).
- `Morphix.app` launcher generated on first setup — daily use without Terminal.

### Fixed
- **Open Studio from the M menu crashed** (`NameError: sys` in quickwheel.py).
- Minimising Studio quit it (spontaneous hide event treated as close).
- "Start at login" used the old `.venv` (Anaconda) instead of `.venv_clean`.
- Launcher required Homebrew Python; now also accepts python.org Python and skips Anaconda.
- Launcher's old-instance detection could match its own grep; can now stop old helpers for you.
- Studio and Quick Wheel had two diverging copies of the conversion engine; `main.execute` now
  delegates to `engine_core`.
- Error dialogs show the actual message instead of a full Python traceback.
- Closing Studio / quitting during a task now offers to cancel instead of blocking.

## v1.4.11 — Background M menu / wheel input fixes

- Prevent QSystemTrayIcon macOS click Trigger from launching the wheel behind its native menu.
- Defer menu actions until after dismissal; macOS wheel is a focusable Window and explicitly activates.
- Nonblocking Finder selection with QProcess + timeout instead of blocking the GUI with osascript.
- Detect old background Morphix helpers from other extracted folders and prefer Homebrew .venv_clean.
- Add GUI wheel native click diagnostic.

## 1.4.5 — Ordered PDF + Image Merge

- Contextual wheel profile for PDF and image mixtures.
- Merge to PDF supports interleaved PDF / PNG / JPEG / other Pillow-supported raster images.
- Full multi-page PDFs remain intact in their exact sequence position.
- Before conversion, a drag-to-reorder dialog confirms the sequence in Wheel and Studio.
- Incremental selection highlights retain already selected order while the wheel is monitoring Finder.
- Compression safeguard prevents rewriter from choosing a smaller PDF when page images disappeared.
- Regression tests cover mixed ordering, multi-page documents, transparency and conversion subprocess.

## v1.1 — 2026-10-21

- Added compression levels and strength slider from wheel and Studio.
- Optional image resizing, first-image size preview, and PDF image-aware optimization.
- Added six new compression engine regression tests.

### v0.8.3
- Interactive start now always displays a welcome launcher; `--background` is opt-in.
- Added `--studio`, `--settings`, `--test-wheel`, and `--background` startup routes.
- Eliminated persistent welcome flag as a cause of no visible window.

## v0.8
- Settings redesigned with blue-glass sidebar layout, live wheel preview, color accents, size, opacity, edge-glow, animation speed and pointer-position controls.
- Real desktop Quick Wheel and preview share the same renderer.
- File Actions tab supports per-file-type reordering and visibility; Shortcuts and About tabs included.
- Settings are saved only on confirmation; Cancel discards the draft.
- Background menu-bar mode and Finder shortcut from v0.7 retained.
- Native OS backdrop blur, login launch, signed installers, and bundled Office engine remain future work.

# Morphix Changelog

## v0.7
- New original logo: M + file-conversion orbit, blue gradient.
- Logo replaces former diamond throughout Splash / About / menu-bar / app icon.
- Quiet startup: Studio stays hidden; menu-bar utility remains running until Quit.
- Smaller cursor-anchored Quick Wheel (290px default, 240–380px adjustable).
- Transparent glass-style blue ring, editable opacity and options.
- Global keyboard hotkey remains macOS AppKit main-thread registration.

# Morphix Changelog

## v0.5.1 — Branding + Contact
- Dark-blue translucent splash screen with short fade-in and italic `By Yousef`.
- About / Contact: clickable LinkedIn, Reddit, and Gmail links.
- Recolored main window accents in blue.
- No feedback form.
- Future: global Quick Wheel, macOS Finder and Windows Explorer integrations.

# Morphix changelog

## v0.5
- Added `visual_editor.py` with visual PDF page organizer and image crop editor.
- Integrated both into context-aware action list and Shift quick actions.
- Kept v0.4 conversion and batch-processing actions.
- Source compiles; GUI runtime and cross-platform packaging not yet verified.

## v0.6 preview — Finder/Explorer Quick Wheel

- Translucent dark-blue radial Quick Wheel drawn in Qt, context-aware shortcuts.
- macOS Finder selection retrieval through AppleScript, foreground Windows Explorer selection through pywin32.
- Global shortcut via pynput, editable in settings; macOS may require Accessibility and Automation permissions.
- Tray/menu-bar app remains running when Studio closes; Studio is available from the tray.
- Wheel Editor reorders/hides actions by file category, with a maximum of six visible sectors.
- Multi-page PDF → PNG/JPG produces Page_001.. images in one ZIP; single-page PDFs export a single image.
- Smart actions save beside inputs in one folder, or into ~/Documents/Morphix Output for files across folders.
- NOT yet a self-contained macOS/Windows installer; Office engine still not bundled.

## v0.6.1 — Fix macOS native shortcut crash
- Replaced macOS `pynput` listener with AppKit `NSEvent` monitoring registered on the main thread.
- Split keyboard dependencies by OS: PyObjC on macOS, pynput on Windows.
- Updated permissions documentation and added lightweight shortcut tests.
- Known limitation: not yet runtime-verified on a Mac with macOS 27.

## v1.4.6 — Studio redesign and shortcut recorder
- Modern batch Studio with sidebar, hero shortcut, file workspace, actionable tools and job activity.
- Native-style shortcut recorder: click and press keys; visible modifiers and keys; saved to QSettings.
- Stable key-position matching on Mac, plus Windows scan-code hook (device verification pending).
- Quiet menu-bar/tray startup, optional launch at login, conditional macOS Dock visibility.
- Source runtime/CLI unchanged; no new external runtime dependency required.

## v1.4.7 — Studio process isolation
- Isolated Studio window in normal separate Qt process, keeping background wheel as a stable accessory.
- Dismissed translucent always-on-top wheel before opening Studio.
- Removed process-global key event filter from Studio; Shift key is scoped to file list.
- IPC for navigation, selected files, wheel settings, and hotkey reloads.
- Added interactive macOS/Windows Qt click self-test.
