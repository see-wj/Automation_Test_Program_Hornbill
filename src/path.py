"""import os

This path.py was created for easier modification of the location path
if the script folder or file has been moved to the new location

#Location of the csv folder
current_dir = os.path.dirname(os.path.abspath(__file__))  # src/
project_root = os.path.abspath(os.path.join(current_dir, "..")) #Test Script Main Folder
setup_img_folder = os.path.join(project_root, "setup_images")
config_folder = os.path.join(project_root, "Instrument_Config_Files")
csv_folder = os.path.join(project_root, "csv")  #csv folder

#General Path
DATA_CSV_PATH = os.path.join(csv_folder, "data.csv")
ERROR_CSV_PATH = os.path.join(csv_folder, "error.csv")
ERROR_CSV_PATH_PERCENT = os.path.join(csv_folder, "error_percent.csv")
INSTRUMENT_DATA_PATH = os.path.join(csv_folder, "instrumentData.csv")

IMAGE_DIR = os.path.join(csv_folder, "images")
IMAGE_PATH = os.path.join(IMAGE_DIR, "Chart.png")
IMAGE_PATH_2 = os.path.join(IMAGE_DIR, "Chart2.png")

#Power Path
POWER_DATA_CSV_PATH = os.path.join(csv_folder, "powerdata.csv")
POWER_ERROR_CSV_PATH = os.path.join(csv_folder, "powererror.csv")
POWER_INSTRUMENT_DATA_PATH = os.path.join(csv_folder, "powerinstrumentData.csv")

POWER_IMAGE_DIR = os.path.join(csv_folder, "images")
POWER_IMAGE_PATH = os.path.join(IMAGE_DIR, "powerChart.png")

#Variables to be import for other files
__all__ = [
    "setup_img_folder",
    "config_folder",
    "csv_folder",
    "DATA_CSV_PATH",
    "ERROR_CSV_PATH",
    "ERROR_CSV_PATH_PERCENT",
    "INSTRUMENT_DATA_PATH",
    "IMAGE_DIR",
    "IMAGE_PATH",
    "IMAGE_PATH_2",
    "POWER_DATA_CSV_PATH",
    "POWER_ERROR_CSV_PATH",
    "POWER_INSTRUMENT_DATA_PATH",
    "POWER_IMAGE_PATH",
]"""

import os
import sys
from pathlib import Path

def get_base_path():
    """Return correct base path whether running normally or as PyInstaller EXE."""
    if getattr(sys, 'frozen', False):  # Running as EXE
        return Path(sys._MEIPASS)  # Temp folder containing bundled files
    else:  # Running from .py source
        return Path(__file__).resolve().parent.parent  # src/ → project folder

# Base project root
project_root = get_base_path()

# Folders bundled by PyInstaller
csv_folder = project_root / "csv"
config_folder = project_root / "Instrument_Config_Files"
setup_img_folder = project_root / "setup_images"

# General CSV paths
DATA_CSV_PATH = csv_folder / "data.csv"
ERROR_CSV_PATH = csv_folder / "error.csv"
ERROR_CSV_PATH_PERCENT = csv_folder / "error_percent.csv"
INSTRUMENT_DATA_PATH = csv_folder / "instrumentData.csv"

# Images
IMAGE_DIR = csv_folder / "images"
IMAGE_PATH = IMAGE_DIR / "Chart.png"
IMAGE_PATH_2 = IMAGE_DIR / "Chart2.png"

# Power Paths
POWER_DATA_CSV_PATH = csv_folder / "powerdata.csv"
POWER_ERROR_CSV_PATH = csv_folder / "powererror.csv"
POWER_INSTRUMENT_DATA_PATH = csv_folder / "powerinstrumentData.csv"

POWER_IMAGE_PATH = IMAGE_DIR / "powerChart.png"

__all__ = [
    "setup_img_folder",
    "config_folder",
    "csv_folder",
    "DATA_CSV_PATH",
    "ERROR_CSV_PATH",
    "ERROR_CSV_PATH_PERCENT",
    "INSTRUMENT_DATA_PATH",
    "IMAGE_DIR",
    "IMAGE_PATH",
    "IMAGE_PATH_2",
    "POWER_DATA_CSV_PATH",
    "POWER_ERROR_CSV_PATH",
    "POWER_INSTRUMENT_DATA_PATH",
    "POWER_IMAGE_PATH"
]
