import os
import sys
from pathlib import Path
import PyInstaller.__main__

# --- Base project path ---
base_dir = Path(__file__).resolve().parent

# Your main script
script_file = base_dir / 'src' / 'GUI.py'

# Resources
icon_file = base_dir / 'TestingTools.ico'  # change if needed
extra_folders = [
    'csv',
    'Instrument_Config_Files',
    'setup_images',
    'SCPI_Library',
]

# --- Validation checks ---
if not script_file.exists():
    sys.exit(f"❌ Script file not found: {script_file}")

if not icon_file.exists():
    print(f"⚠️ Icon not found: {icon_file} (continuing without icon)")
    icon_file = None

# --- Build --add-data args ---
sep = ';' if os.name == 'nt' else ':'
add_data_args = []

for folder in extra_folders:
    folder_path = base_dir / folder
    if folder_path.exists():
        add_data_args.append(f"{str(folder_path)}{sep}{folder}")
    else:
        print(f"⚠️ Missing folder skipped: {folder_path}")

# --- Run PyInstaller ---
print("⚡ Building Main GUI executable...")
args = [
    str(script_file),
    '--onefile',
    '--noconsole',
    '--name=Test_Automation_Program',
    '--distpath=Executable',
    *[f'--add-data={data}' for data in add_data_args]
]

if icon_file:
    args.append(f'--icon={str(icon_file)}')

PyInstaller.__main__.run(args)

print("✅ Build finished. Executable is in ./Executable/")