# Morphix v1.4.9 — Fix confirmed macOS Cocoa + clean environment regression

## Root causes reproduced on the user's Mac

1. Qt platform plugin dylibs were marked macOS `UF_HIDDEN`, excluded by Qt's normal QDir enumeration. They still existed and contained valid plugin metadata. Clearing UF_HIDDEN let a standalone Cocoa QWidget launch successfully.
2. `runtime_guard.py` **silently re-executed** `main.py` under `.venv` whenever launched from `.venv_clean`; the original `.venv` was Anaconda-based with nonfunctioning Qt plugins. This explains why the minimal Qt test succeeded but the real Studio did not open.

## Fixes

- Preserve the active `.venv_clean` or `.venv` instead of silently swapping it.
- On an external Python launch, prefer `.venv_clean` when available.
- Restore UF_HIDDEN flags from the active project-local PySide6 Qt plugin dylibs before creating QApplication. No system libraries are modified.
- macOS launcher selects `.venv_clean` automatically if it exists, otherwise uses `.venv`, or creates a venv using Homebrew Python 3.13 when available.
- QT doctor identifies the Cocoa hidden flag, and supports `--fix-hidden`.

## Use with existing Morphix 21

Install update files in Morphix 21, then run:

```sh
.venv_clean/bin/python main.py --studio-window
```

When Studio runs, use the normal launch command to run the background app:

```sh
zsh ./Launch_Morphix_Mac.command
```

The project is still source code, **not** a signed macOS app. GUI behavior must be checked on actual macOS hardware; Linux tests cannot validate window focus/clicking.
