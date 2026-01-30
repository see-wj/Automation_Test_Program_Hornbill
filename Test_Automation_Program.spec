# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Automation_Test_Program_Hornbill-1\\src\\GUI.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Automation_Test_Program_Hornbill-1\\csv', 'csv'), ('C:\\Automation_Test_Program_Hornbill-1\\Instrument_Config_Files', 'Instrument_Config_Files'), ('C:\\Automation_Test_Program_Hornbill-1\\setup_images', 'setup_images'), ('C:\\Automation_Test_Program_Hornbill-1\\SCPI_Library', 'SCPI_Library'), ('C:\\Automation_Test_Program_Hornbill-1\\External_Auxiliary_Equipment', 'External_Auxiliary_Equipment')],
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
    a.binaries,
    a.datas,
    [],
    name='Test_Automation_Program',
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
    icon=['C:\\Automation_Test_Program_Hornbill-1\\TestingTools.ico'],
)
