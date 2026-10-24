# Morphix 1.5.0 — Quick Wheel + Studio

Morphix is a local-first file toolkit with a blue desktop Quick Wheel and a complete Studio.

### What works in the source project

- PDF: merge PDFs and images together in a user-confirmed order (with all PDF pages preserved), bounded single-range extraction, multi-part separation with + row controls, page-to-image export, compression, crop, rotation, selectable-text extraction, Arabic/English OCR of scanned PDFs into `.txt`, and **make scanned PDFs searchable**.
- Images: format conversions, combine into one PDF, compression, resize, Arabic/English text OCR, and visual crop plus free-angle rotation (with rule-of-thirds guides).
- Office: convert Word / PowerPoint / Excel / ODF documents into PDF through LibreOffice; the **build scripts require LibreOffice on the developer's build computer and embed it into the output app**.
- Video/audio: convert and merge using bundled imageio-ffmpeg executable.
- Archive: ZIP and TAR.GZ work locally with standard libraries. RAR creation requires a separately licensed genuine RAR encoder and will otherwise be disabled. Never rename a ZIP to `.rar`.

### macOS use

Unzip into a new folder and run `Launch_Morphix_Mac.command` **once** (needs internet once). It creates a private
runtime and a local **`Morphix.app`** — afterwards just double-click `Morphix.app`; no Terminal needed.
Arabic quick start: `START_HERE_AR.md`. To build a larger standalone `.app` / `.dmg` on a **Mac developer system with LibreOffice installed**, run `Build_Morphix_Mac.command`. This is **not a prebuilt, signed or notarized DMG**.

### Linux use

Download `Morphix-<version>-x86_64.AppImage` from the Releases page, make it executable
(right-click → Properties → *Allow executing file as program*, or `chmod +x`) and double-click it.
On first start Morphix adds itself to the application menu and to the right-click menu of
Files (Nautilus → *Scripts → Morphix*), Nemo and Dolphin (*Morphix*): select files, right-click,
and the Action Hub opens with them. The global shortcut (Ctrl + Shift + M) works on X11 directly;
on Wayland, GNOME gets a system shortcut automatically. Linux file managers have no shared
"current selection", so with the shortcut copy the files first (Ctrl + C). To build the AppImage
yourself: `./Build_Morphix_Linux.sh`.

### Windows use

Use Python and `pip install -r requirements.txt`, then run `python main.py`. To build `dist/Morphix/Morphix.exe` and its complete runtime folder on a **Windows developer system with LibreOffice installed**, run `Build_Morphix_Windows.bat`. Do not distribute only the EXE; distribute the entire folder or make an installer after testing it.

### Speech → Text (offline, Arabic / English)

Audio and video files get a **Speech → Text** action (faster-whisper, local CPU). Download a model once from
Studio → Speech models (or `python download_speech_models.py`), then it works offline. Long files (hours) are
processed in silence-aligned chunks with checkpoints, so a cancelled job resumes where it stopped.
Engine dependencies live in `requirements-speech.txt` so other tools work even where that engine cannot install.

### Diagnostic check

`python doctor_engines.py` (no graphical UI needed), or select **Morphix M menu → Conversion Engines · Status** in the running app.

### Notes

OCR supports Arabic and English image-only pages via bundled language datasets. Native pages retain extractable text without OCR; the explicit OCR option can re-recognize all pages. OCR accuracy depends on scan clarity. Building a searchable PDF rasterizes image-only pages.

**Licensing:** Morphix depends on PyMuPDF (AGPL/commercial license), Tesseract language data (Apache-2.0), FFmpeg and LibreOffice. Before redistribution check all upstream licenses, attribution, codecs and obligations in `THIRD_PARTY_LICENSES.md`. RARLab forbids bundling its trial program into unrelated application packages without written permission.

Native GUI and bundled Office engine have been **unit/integration tested on Linux only**; the final macOS and Windows app builds must be tested on those systems. Never claim a distribution is platform-tested from Python source tests alone.

### Selection behavior (v1.4)

A new Finder/Explorer selection **replaces** the previous one automatically.
Deselecting everything clears the wheel after two polls; press the shortcut again to open it on a new selection.
To intentionally gather files across different folders, use the center menu → **Add more files…** or drag files onto the wheel. Those explicitly added items stay until **Clear selection**.

### Page tools

- **Extract range** asks for two numbers: From / To. Bounds are 1..page count and outputs a single PDF.
- **Separate PDF** lets you add as many From / To pairs as necessary with **+ Add another part**. Overlapping ranges are rejected, and one PDF is saved for each part.

### Text and equations

Wheel has one **Extract text** action for PDFs with automatic OCR of scanned pages, and image selection has **Extract text** through OCR.
Studio retains **Searchable PDF**, which outputs a new PDF with an OCR text layer rather than TXT.
Native PDF text equations may retain encoded math glyphs; **complex equation images are not automatically converted to reliable LaTeX**. Check the original page if exact math is important.

### Testing

Run `python -m pytest -q` in a development environment to test non-GUI engines. The native GUI and global shortcut still require real macOS / Windows verification. The ZIP is source code, **not** a tested `.app` or `.exe` installer.

### Mixed PDF + image merge (v1.4.5)

The wheel now recognizes PDF-and-image selections separately from arbitrary mixed files.
**Merge to PDF** and **Merge + Compress** accept PNG/JPEG and PDFs in any sequence.
An ordering dialog is presented before processing so the user can drag files into
precisely the intended sequence; an image becomes one page, and a PDF retains all
its pages in the corresponding position. The ordering step is necessary because
Finder/Explorer may not return the chronology of selection clicks.

The headless engine reuses this merge logic for image-only PDF assembly and guards
against rewritten PDFs which unexpectedly lose images during heavy compression.
