import os
import sys
from pathlib import Path


def get_base_folder():
    """
    Returns:
    - EXE directory when running as an EXE
    - Project root directory when running from Python source
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent   # Folder containing the EXE

    # Running from source:
    return Path(__file__).resolve().parent.parent      # Project root folder


BASE_DIR = get_base_folder()


# -------------------------
# Load folders next to EXE
# -------------------------
config_folder = BASE_DIR / "Instrument_Config_Files"
csv_folder = BASE_DIR / "csv"
setup_img_folder = BASE_DIR / "setup_images"

IMAGE_DIR = csv_folder / "images"


# -------------------------
# Define file paths
# -------------------------
DATA_CSV_PATH = csv_folder / "data.csv"
ERROR_CSV_PATH = csv_folder / "error.csv"
ERROR_CSV_PATH_PERCENT = csv_folder / "error_percent.csv"
INSTRUMENT_DATA_PATH = csv_folder / "instrumentData.csv"

IMAGE_PATH = IMAGE_DIR / "Chart.png"
IMAGE_PATH_2 = IMAGE_DIR / "Chart2.png"

POWER_DATA_CSV_PATH = csv_folder / "powerdata.csv"
POWER_ERROR_CSV_PATH = csv_folder / "powererror.csv"
POWER_INSTRUMENT_DATA_PATH = csv_folder / "powerinstrumentData.csv"
POWER_IMAGE_PATH = IMAGE_DIR / "powerChart.png"


__all__ = [
    "config_folder",
    "csv_folder",
    "setup_img_folder",
    "DATA_CSV_PATH",
    "ERROR_CSV_PATH",
    "ERROR_CSV_PATH_PERCENT",
    "INSTRUMENT_DATA_PATH",
    "IMAGE_PATH",
    "IMAGE_PATH_2",
    "POWER_DATA_CSV_PATH",
    "POWER_ERROR_CSV_PATH",
    "POWER_INSTRUMENT_DATA_PATH",
    "POWER_IMAGE_PATH",
]
