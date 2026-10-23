# Morphix 1.4.4 — Runtime & Quick Crop Fix

## What changed

1. `main.py` checks the Python runtime BEFORE importing Qt or creating the wheel. If `.venv` exists but Anaconda Python is executing `main.py`, Morphix automatically re-executes under the matching `.venv` Python. If the runtime is missing, it fails with a clear message instead of letting `fitz`/`pymupdf` fail later.
2. The existing `Launch_Morphix_Mac.command` prepares an isolated `.venv` and installs the declared dependencies before launching the UI. Use the launcher for each fresh extracted source folder.
3. `Crop & Rotate` in Quick Wheel opens **Quick Crop & Rotate**, a standalone, smaller image editor; it no longer opens Morphix Studio. The editor provides a visual crop frame with corner handles, free-angle rotation, 90-degree buttons, quick **Save Copy** and **Save As**. Its controls use a smaller preview while final export uses full-resolution pixels.
4. Core PDF functions now use `import pymupdf as fitz` to avoid reliance on the deprecated `fitz` module alias.
5. PDF range dialogs report missing runtime components as clear warnings instead of uncaught tracebacks.
6. Edits never overwrite the source image, and `Save Copy` picks a new filename automatically.

## Verified

- Automated engine and regression suite includes real PDF conversion and file operations, crop/rotation export, subprocessing and runtime guard checks.
- GUI-level Qt tests are included, but cannot run on the current non-macOS build host without PySide6 and access to macOS Finder. UI interactions, hotkey capture and the floating window **still require direct testing on your Mac**.

## Try on your Mac

1. Close all older Morphix processes from the menu-bar M and Terminal (`Control+C`).
2. Extract the ZIP into its own folder. **Do not mix it with older releases.**
3. Open Terminal in `Morphix`, then run `zsh ./Launch_Morphix_Mac.command`.
   This prepares `.venv` on the first run, including PyMuPDF and PySide6.
4. Use the Quick Wheel on a PNG, choose `Crop & rotate`, adjust frame and angle, then press `Save Copy`. Verify a `*_edited.png` appears next to the source. Studio should remain closed.
5. Test the wheel on a PDF, including Extract Range. Test a PNG to PDF conversion. Test that closing Studio leaves the blue M available in the menu bar.

**Note:** This is a developer source distribution, not a signed, notarized standalone `.app` or `.exe`. The macOS application bundle has to be built and validated on macOS.
