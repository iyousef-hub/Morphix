@echo off
chcp 65001 >nul
setlocal EnableExtensions
REM ==========================================================================
REM  Build Morphix.exe for Windows - a standalone app for people WITHOUT Python.
REM  Double-click this file. The first run needs the internet (it downloads
REM  Python and the build tools, ~10-15 minutes). The result is copied to:
REM      dist\Morphix\Morphix.exe      (keep the whole Morphix folder)
REM      dist\Morphix_Windows.zip      (the same folder, zipped, to share)
REM ==========================================================================
cd /d "%~dp0"
set "ROOT=%CD%"
REM Build outside OneDrive / Desktop sync folders, which lock files mid-build.
set "WORK=%LOCALAPPDATA%\Morphix-build"
set "VENV=%WORK%\venv"
set "PY=%VENV%\Scripts\python.exe"
set "LOG=%ROOT%\build_log.txt"
echo Morphix Windows build > "%LOG%"

echo.
echo  == Morphix for Windows ==
echo.

REM ---------------------------------------------------------------- Python
set "PYL="
where py >nul 2>&1 && set "PYL=py"
if not defined PYL if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" set "PYL=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
if not defined PYL if exist "%WINDIR%\py.exe" set "PYL=%WINDIR%\py.exe"
if defined PYL (
  "%PYL%" -3.12 -c "import sys" >nul 2>&1 || set "PYL="
)
if not defined PYL (
  echo [1/5] Installing Python 3.12 ^(one time^)...
  winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements >> "%LOG%" 2>&1
  if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" set "PYL=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
  if not defined PYL if exist "%WINDIR%\py.exe" set "PYL=%WINDIR%\py.exe"
)
if not defined PYL (
  echo.
  echo  Python 3.12 could not be installed automatically.
  echo  Install it from https://www.python.org/downloads/release/python-3128/
  echo  ^(Windows installer 64-bit^), then run this file again.
  goto :error
)
echo [1/5] Python 3.12 found.

REM ---------------------------------------------------------------- venv
if not exist "%PY%" (
  echo [2/5] Creating the build environment...
  if not exist "%WORK%" mkdir "%WORK%"
  "%PYL%" -3.12 -m venv "%VENV%" >> "%LOG%" 2>&1 || goto :error
) else (
  echo [2/5] Build environment found.
)

echo [3/5] Installing components ^(first time takes several minutes^)...
"%PY%" -m pip install --upgrade pip >> "%LOG%" 2>&1
"%PY%" -m pip install -r requirements.txt -r requirements-speech.txt "pyinstaller>=6.10,<7" >> "%LOG%" 2>&1 || goto :error

REM Smart App Control blocks unsigned DLLs (PyAV / faster-whisper). A build made
REM while it is on silently leaves Speech -> Text out, so stop and explain.
"%PY%" -c "import av, faster_whisper, ctranslate2" >> "%LOG%" 2>&1
if errorlevel 1 (
  findstr /C:"Application Control" "%LOG%" >nul && goto :sac
  echo       Speech engine check failed - see build_log.txt. Continuing without it.
)

REM ---------------------------------------------------------------- build
echo [4/5] Building Morphix.exe ^(a few minutes^)...
if exist "%WORK%\dist" rmdir /s /q "%WORK%\dist"
"%PY%" -m PyInstaller --noconfirm --clean --windowed --onedir ^
  --distpath "%WORK%\dist" --workpath "%WORK%\build" --specpath "%WORK%" --paths "%ROOT%" ^
  --name Morphix --icon "%ROOT%\assets\morphix.ico" ^
  --collect-all imageio_ffmpeg --collect-all pymupdf ^
  --collect-all faster_whisper --collect-all ctranslate2 --collect-all onnxruntime --collect-all rapidocr --collect-all pillow_heif --collect-all pdf2docx --collect-all docx --collect-all bidi --hidden-import cv2 ^
  --collect-submodules huggingface_hub --collect-submodules tokenizers --collect-submodules openpyxl ^
  --hidden-import win32com.client --hidden-import pythoncom --hidden-import pywintypes ^
  --hidden-import worker_process --hidden-import engine_core --hidden-import transcription_engine ^
  --hidden-import hub_panel --hidden-import i18n_ar --hidden-import ui_kit --hidden-import win_compat ^
  --hidden-import tools_engine --hidden-import ocr_models --hidden-import latex_ocr --hidden-import action_dialogs --hidden-import signature_dialog --hidden-import docs_engine --hidden-import background_engine --hidden-import background_dialog ^
  --hidden-import windows_hotkeys --hidden-import theme --hidden-import ms_office ^
  --hidden-import win32gui --hidden-import win32com.shell.shell ^
  --add-data "%ROOT%\assets;assets" "%ROOT%\main.py" >> "%LOG%" 2>&1 || goto :error
if not exist "%WORK%\dist\Morphix\Morphix.exe" goto :error

REM Office -> PDF is optional: bundled only when LibreOffice is installed here.
set "LO=%ProgramFiles%\LibreOffice"
if defined MORPHIX_LIBREOFFICE_DIR set "LO=%MORPHIX_LIBREOFFICE_DIR%"
if exist "%LO%\program\soffice.exe" (
  echo       Adding LibreOffice for Office to PDF...
  robocopy "%LO%" "%WORK%\dist\Morphix\office_runtime" /E /NFL /NDL /NJH /NJS >nul
) else (
  echo       LibreOffice not found - Office to PDF will ask the user to install it.
)

REM ---------------------------------------------------------------- output
echo [5/5] Copying the result...
if exist "%ROOT%\dist\Morphix" rmdir /s /q "%ROOT%\dist\Morphix"
if not exist "%ROOT%\dist" mkdir "%ROOT%\dist"
robocopy "%WORK%\dist\Morphix" "%ROOT%\dist\Morphix" /E /NFL /NDL /NJH /NJS >nul
if errorlevel 8 goto :error
if exist "%ROOT%\dist\Morphix_Windows.zip" del /q "%ROOT%\dist\Morphix_Windows.zip"
powershell -NoProfile -Command "Compress-Archive -Path '%WORK%\dist\Morphix' -DestinationPath '%ROOT%\dist\Morphix_Windows.zip' -Force" >> "%LOG%" 2>&1

echo.
echo  Done!
echo    %ROOT%\dist\Morphix\Morphix.exe
echo    %ROOT%\dist\Morphix_Windows.zip  ^(to share^)
echo.
echo  Keep the whole Morphix folder - Morphix.exe needs the files next to it.
echo  First open: Windows may show "Windows protected your PC" -^> More info -^> Run anyway.
echo.
start "" explorer "%ROOT%\dist\Morphix"
pause
exit /b 0

:sac
echo.
echo  Windows "Smart App Control" is blocking the speech engine files.
echo  Turn it off: Settings ^> Privacy ^& security ^> Windows Security ^>
echo  App ^& browser control ^> Smart App Control settings ^> Off
echo  Then run this file again.
pause
exit /b 1

:error
echo.
echo  Build failed. The details are in:
echo    %LOG%
echo  Send that file to get it fixed.
pause
exit /b 1
