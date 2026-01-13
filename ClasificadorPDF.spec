# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['proglite.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('Intramaq-logo-mail.png', '.'),
        ('version.json', '.'),
        ('build_config.json', '.')
    ],
    hiddenimports=[],
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
    name='ClasificadorPDF',
    debug=True, # Keep debug to see detailed errors
    bootloader_ignore_signals=False,
    strip=False,
    upx=False, # UPX is often the culprit for DLL errors
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True, # Keep console to capture logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
