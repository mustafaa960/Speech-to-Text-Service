# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['speech_to_text.py'],
    pathex=[],
    binaries=[
        ('.venv/Lib/site-packages/nvidia/cublas/bin/cublas64_12.dll', '.'),
        ('.venv/Lib/site-packages/nvidia/cublas/bin/cublasLt64_12.dll', '.'),
    ],
    datas=[
        ('.venv/Lib/site-packages/faster_whisper/assets', 'faster_whisper/assets'),
    ],
    hiddenimports=[
        'faster_whisper',
        'ctranslate2',
        'huggingface_hub',
        'tokenizers',
        'sounddevice',
        'numpy',
        'keyboard',
        'pyperclip',
        'pystray',
        'PIL._tkinter_finder',
        '_sounddevice_data',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='STT-Service-v1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
