import os
import sys
from pathlib import Path
import PyInstaller.__main__

# --- Base project path ---
base_dir = Path(__file__).resolve().parent

# Your main script
script_file = base_dir / 'src' / 'GUI.py'

# Icon
icon_file = base_dir / 'TestingTools.ico'

# FOLDERS THAT SHOULD EXIST NEXT TO THE EXE (NOT BUNDLED)
external_folders = [
    'csv',
    'Instrument_Config_Files',
    'setup_images',
    'SCPI_Library',
    'External_Auxiliary_Equipment',
]

# --- Validation checks ---
if not script_file.exists():
    sys.exit(f"❌ Script file not found: {script_file}")

if not icon_file.exists():
    print(f"⚠️ Icon not found: {icon_file} (continuing without icon)")
    icon_file = None

print("⚡ Building Main GUI executable...")

args = [
    str(script_file),
    '--onedir',
    '--console',
    '--name=Test_Automation_Program',
    '--distpath=Executable',
    '--hidden-import=numpy.core._dtype_ctypes',
    '--hidden-import=numpy._globals',
    '--exclude-module=numpy.core._multiarray_umath',
]

if icon_file:
    args.append(f'--icon={str(icon_file)}')

PyInstaller.__main__.run(args)

print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("✅ Build finished.")
print("📁 Executable is in: ./Executable/")
print("📌 REMINDER: Copy these folders next to the EXE:")
for f in external_folders:
    print(f"   → {f}/")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
