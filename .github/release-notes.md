## Morphix 1.7.1 — Bug fixes

Every file tool you need — one shortcut away. PDF, images, Office, audio & video, OCR and offline speech-to-text.

### Download
- **Windows:** `Morphix_Windows_1.7.1.zip` — unzip it and run `Morphix.exe` (keep it together with the `_internal` folder).
- **macOS (Apple Silicon):** `Morphix_macOS_1.7.1.dmg` — open it and drag Morphix into Applications. The first time, right-click Morphix → **Open**.

### Bug fixes

**1. Office → PDF failed on Windows with an empty error**
- *The error:* converting a PowerPoint/Word/Excel file showed
  `Office conversion failed for Embedded system.pptx:` with nothing after the colon, and no PDF was created.
- *The cause:* Morphix told LibreOffice to use its "svp" headless display mode. That mode only exists on macOS/Linux,
  so on Windows LibreOffice quit silently without converting.
- *The fix:* the mode is no longer forced on Windows, Morphix waits for LibreOffice through its console launcher
  (`soffice.com`), and if a conversion ever fails the message now always says why.

**2. Converting presentations on Windows was very slow (≈ 1.5 minutes for one file)**
- *The cause:* every conversion started LibreOffice with a brand-new profile (its whole first-start cost each time),
  and LibreOffice is slow at exporting presentations that contain many pictures.
- *The fix:*
  - When **Microsoft Office** is installed, Morphix now lets PowerPoint / Word / Excel export the PDF themselves —
    much faster and with exactly the same look as in Office. It runs invisibly, never closes a PowerPoint you have
    open, and falls back to LibreOffice automatically if Office is missing or does not answer.
  - The LibreOffice profile is now kept between conversions, so every conversion after the first starts faster.

**3. Overlapping text in the Studio sidebar**
- *The error:* in the "Running in the background" card the lines were drawn on top of each other and the title was
  cut off ("RUNNING IN THE BACKGROUN").
- *The fix:* the card now measures the real height of the wrapped text and reserves it, in Arabic and English.

**4. The Mac app could not be signed when built from the Desktop**
- *The error:* `codesign … resource fork, Finder information, or similar detritus not allowed`
  — an unsigned app does not open on Apple Silicon Macs.
- *The cause:* the Desktop is synced with iCloud, which adds hidden Finder metadata to every file.
- *The fix:* the build now runs outside iCloud, clears that metadata and verifies the signature.

### Also in this version (Windows)
- Helper programs (FFmpeg, LibreOffice…) no longer flash black console windows.
- Mac words in the interface are shown with their Windows names (Finder → File Explorer, menu bar → taskbar tray, ⌘ → Win).
- The memory check for the "Finest edges" background-removal model works on Windows.
- Without a console, Morphix writes its messages to `%LOCALAPPDATA%\Morphix\logs` for troubleshooting.

> These builds are not digitally signed. Windows may show a SmartScreen warning (**More info → Run anyway**), and Smart App Control may block the app if it is turned on.
