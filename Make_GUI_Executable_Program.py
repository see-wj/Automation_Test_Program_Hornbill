import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

APPLICATION_NAME = "Test_Automation_Program"
VISA_RUNTIME_HOOK = Path("packaging_hooks") / "initialize_native_visa.py"
RUNTIME_FOLDERS = (
    "Instrument_Config_Files",
    "setup_images",
    "csv",
)
COLLECT_SUBMODULES = (
    "SCPI_Library",
    "DUT_Test_Scripts",
    "External_Auxiliary_Equipment",
)


def validate_inputs(base_directory, script_file, icon_file):
    missing = [
        path
        for path in (
            script_file,
            base_directory / VISA_RUNTIME_HOOK,
            *(base_directory / name for name in RUNTIME_FOLDERS),
        )
        if not path.exists()
    ]
    if missing:
        missing_list = "\n".join(f"  - {path}" for path in missing)
        raise SystemExit(f"Required build input is missing:\n{missing_list}")

    if not icon_file.exists():
        print(f"Icon not found: {icon_file}. Continuing without an icon.")
        return None
    return icon_file


def copy_runtime_folders(base_directory, application_directory):
    for folder_name in RUNTIME_FOLDERS:
        source = base_directory / folder_name
        destination = application_directory / folder_name
        shutil.copytree(source, destination, dirs_exist_ok=True)
        print(f"Copied editable runtime folder: {folder_name}/")

    queue_file = application_directory / "Instrument_Config_Files" / "test_queue.json"
    queue_file.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "pending": [],
                "active": None,
                "interrupted": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Created clean runtime queue: Instrument_Config_Files/test_queue.json")


def build():
    try:
        import PyInstaller.__main__
    except ModuleNotFoundError as exception:
        raise SystemExit(
            "PyInstaller is not installed. Run: "
            ".venv1\\Scripts\\python.exe -m pip install -r requirements-dev.txt"
        ) from exception

    base_directory = Path(__file__).resolve().parent
    script_file = base_directory / "src" / "GUI.py"
    icon_file = validate_inputs(
        base_directory,
        script_file,
        base_directory / "TestingTools.ico",
    )
    build_identifier = datetime.now().strftime("%Y%m%d_%H%M%S")
    distribution_directory = (
        base_directory / "Executable_Builds" / build_identifier
    )
    application_directory = distribution_directory / APPLICATION_NAME

    arguments = [
        str(script_file),
        "--onedir",
        "--console",
        "--noconfirm",
        f"--name={APPLICATION_NAME}",
        f"--distpath={distribution_directory}",
        f"--workpath={base_directory / 'build' / 'pyinstaller_visa'}",
        f"--specpath={base_directory / 'build'}",
        f"--paths={base_directory}",
        f"--paths={base_directory / 'src'}",
        f"--runtime-hook={base_directory / VISA_RUNTIME_HOOK}",
    ]
    arguments.extend(
        f"--collect-submodules={package_name}"
        for package_name in COLLECT_SUBMODULES
    )
    if icon_file is not None:
        arguments.append(f"--icon={icon_file}")

    print("Building main GUI executable...")
    PyInstaller.__main__.run(arguments)
    copy_runtime_folders(base_directory, application_directory)

    executable = application_directory / f"{APPLICATION_NAME}.exe"
    print("\nBuild finished.")
    print(f"Executable: {executable}")
    print("Editable runtime folders are located beside the executable.")


if __name__ == "__main__":
    build()
