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
    a.binaries + [('python311.dll', 'C:\\Users\\tomas\\AppData\\Local\\Programs\\Python\\Python311\\python311.dll', 'BINARY')],
    a.datas,
    [],
    name='ClasificadorPDF',
    debug=True, # Enable debug to see more detailed error in console
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None, # Temporarily removed icon to avoid potential issues if it's not a valid .ico
)
