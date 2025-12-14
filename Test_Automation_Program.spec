# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\shamlee3\\OneDrive - Keysight Technologies\\Desktop\\Automation_Test_Program_Hornbill\\src\\GUI.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['numpy.core._dtype_ctypes', 'numpy._globals'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy.core._multiarray_umath'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Test_Automation_Program',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\shamlee3\\OneDrive - Keysight Technologies\\Desktop\\Automation_Test_Program_Hornbill\\TestingTools.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Test_Automation_Program',
)
