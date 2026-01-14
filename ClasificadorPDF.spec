# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\tomas\\Desktop\\CLASSPDF\\version.json', '.'), ('C:\\Users\\tomas\\Desktop\\CLASSPDF\\build_config.json', '.'), ('C:\\Users\\tomas\\Desktop\\CLASSPDF\\Intramaq-logo-mail.png', '.')]
binaries = []
hiddenimports = ['fitz', 'PIL']
tmp_ret = collect_all('fitz')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\tomas\\Desktop\\CLASSPDF\\proglite.py'],
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
    name='ClasificadorPDF',
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
    icon=['C:\\Users\\tomas\\Desktop\\CLASSPDF\\Intramaq-logo-mail.png'],
    manifest='C:\\Users\\tomas\\Desktop\\CLASSPDF\\uac_manifest.xml',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ClasificadorPDF',
)
