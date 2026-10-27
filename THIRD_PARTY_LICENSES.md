# Third-party engines and redistribution

This is a packaging checklist, not legal advice.

- **PyMuPDF**: AGPL-3.0 or a commercial license. If Morphix is publicly distributed, follow PyMuPDF's licensing obligations (including source availability as applicable) or obtain a commercial license.
- **Tesseract tessdata**: `assets/tessdata/eng.traineddata` and `ara.traineddata` from the Tesseract project, distributed under Apache License 2.0. Retain notices. Official source: https://github.com/tesseract-ocr/tessdata
- **LibreOffice**: packaged copies include a complete LibreOffice runtime from the build machine. Retain LibreOffice licensing, notices and required license files. Refer to https://www.libreoffice.org/about-us/licenses/ . Very large bundles are expected. Test unsigned/notarization and execution on fresh target machines.
- **FFmpeg**: codec configuration affects licensing. See https://ffmpeg.org/legal.html . `imageio-ffmpeg` includes platform executables; inspect the actual shipped FFmpeg build.
- **RAR**: creating archives requires a genuine licensed RAR encoder. According to https://www.rarlab.com/license.htm , distributing parts of RAR or bundling trial WinRAR/RAR inside another application requires permission. Morphix intentionally does not ship that writer. RAR creation becomes available only when a duly licensed writer is provided and found by Morphix. ZIP is the default fully included alternative.

Before distributing a signed Windows installer or macOS DMG, review all these licenses for your specific usage and packaging approach.

## Speech → Text (v1.5)

- **faster-whisper** (SYSTRAN) — MIT License. https://github.com/SYSTRAN/faster-whisper
- **CTranslate2** (OpenNMT) — MIT License.
- **Silero VAD** model shipped inside faster-whisper — MIT License.
- **onnxruntime** (Microsoft) — MIT License.
- **Whisper model weights** (OpenAI; CTranslate2 conversions by Systran / mobiuslabs) — MIT License.
  Models are downloaded by the user on first use and are not bundled by default.

## Version 1.9 tools

- **RapidOCR** (RapidAI) — Apache License 2.0. https://github.com/RapidAI/RapidOCR
- **PaddleOCR PP-OCR models** (PaddlePaddle; ONNX conversions by RapidAI) — Apache License 2.0. The Arabic
  recognition model is downloaded by the user from the Add-ons page.
- **RapidLaTeXOCR** ONNX models (RapidAI) — Apache License 2.0; based on **pix2tex / LaTeX-OCR** (Lukas Blecher) —
  MIT License. Downloaded by the user from the Add-ons page; `latex_ocr.py` is a compact re-implementation.
- **pdf2docx** — MIT License (depends on python-docx — MIT, and OpenCV — Apache License 2.0).
- **pillow-heif** — BSD-3-Clause; bundles libheif (LGPL-3.0) and codec libraries — review the shipped wheel.
- **python-bidi** — LGPL-3.0 (used by RapidOCR for right-to-left text).
- **tokenizers** (Hugging Face) — Apache License 2.0.
