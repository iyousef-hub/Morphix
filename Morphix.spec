# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets')]
binaries = []
hiddenimports = ['worker_process', 'engine_core', 'transcription_engine', 'hub_panel', 'i18n_ar', 'ui_kit', 'docs_engine', 'background_engine', 'background_dialog',
                 'tools_engine', 'ocr_models', 'latex_ocr', 'action_dialogs', 'signature_dialog', 'cv2']
hiddenimports += collect_submodules('huggingface_hub')
hiddenimports += collect_submodules('tokenizers')
hiddenimports += collect_submodules('AppKit')
hiddenimports += collect_submodules('Foundation')
hiddenimports += collect_submodules('objc')
hiddenimports += collect_submodules('openpyxl')
tmp_ret = collect_all('imageio_ffmpeg')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pymupdf')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('faster_whisper')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('ctranslate2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('onnxruntime')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
for _pkg in ('rapidocr', 'pillow_heif', 'pdf2docx', 'docx', 'bidi'):
    tmp_ret = collect_all(_pkg)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Morphix',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['/Users/youssef/Desktop/Morphix/Morphix 24/build/Morphix.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Morphix',
)
app = BUNDLE(
    coll,
    name='Morphix.app',
    icon='/Users/youssef/Desktop/Morphix/Morphix 24/build/Morphix.icns',
    bundle_identifier='com.iyousefhub.morphix',
)
