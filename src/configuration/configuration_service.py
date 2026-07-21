"""Load DUT setup defaults from the project's text configuration files."""

from pathlib import Path


CONFIG_NAMES = {
    "Excavator": "config_Excavator.txt",
    "Dolphin": "config_Dolphin.txt",
    "SMU": "config_SMU.txt",
    "Hornbill": "config_Hornbill.txt",
}


def configuration_path(config_directory, selected_dut):
    file_name = CONFIG_NAMES.get(selected_dut, "config_Others.txt")
    return Path(config_directory) / file_name


def load_configuration(path):
    values = {}
    with Path(path).open("r", encoding="utf-8") as configuration_file:
        for raw_line in configuration_file:
            line = raw_line.strip()
            if not line or line.startswith(("#", "//")) or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def apply_configuration(target, values, preserve_save_location=True):
    for key, value in values.items():
        if key == "savelocation" and preserve_save_location:
            existing = getattr(target, "savelocation", None)
            if existing:
                continue
        setattr(target, key, value)
