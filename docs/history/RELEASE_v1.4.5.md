# Morphix 1.4.5 — Ordered Merge

Supports PDF + PNG + JPEG mixed selections via **Merge to PDF**.
Each image contributes exactly one page, and PDF files contribute ALL their pages.
A confirmation/reorder window is shown before merging because Finder/Explorer
does not reliably provide the temporal order in which files were selected.
The final list order controls the merged PDF. Existing originals remain unchanged.

Includes Merge + Compress and guards against rewritten PDFs losing embedded images.

## Testing

Run `python -m pytest -q` for tests. To smoke test merge-order dialog on macOS:
`./.venv/bin/python gui_selftest_v145.py`
Native macOS / Windows Qt GUI and packaged executables are not tested here.

## How to run (macOS)

From the extracted `Morphix` directory: `zsh ./Launch_Morphix_Mac.command`

## Known limitation

Finder does not expose the exact chronological order of selection clicks;
users can explicitly reorder the selected files before merging.
