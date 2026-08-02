import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

APPLICATION_NAME = "Test_Automation_Program"
UPDATER_NAME = "Program_Updater"
VISA_RUNTIME_HOOK = Path("packaging_hooks") / "initialize_native_visa.py"
RUNTIME_FOLDERS = (
    "Instrument_Config_Files",
    "setup_images",
    "csv",
    "video_streaming",
)
COLLECT_SUBMODULES = (
    "SCPI_Library",
    "DUT_Test_Scripts",
    "External_Auxiliary_Equipment",
    "analysis",
    "common",
    "configuration",
    "execution",
    "integrations",
    "instruments",
    "queueing",
    "reporting",
    "ui",
    "updater",
)


def validate_inputs(base_directory, script_file, icon_file):
    missing = [
        path
        for path in (
            script_file,
            base_directory / "Program_Updater.py",
            base_directory / "VERSION",
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


def build_version(base_directory):
    version = os.getenv("AUTOMATION_BUILD_VERSION", "").strip()
    if not version:
        version = (
            base_directory / "VERSION"
        ).read_text(encoding="utf-8").strip()
    if not version:
        raise SystemExit("Application version cannot be empty")
    return version


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    version = build_version(base_directory)
    work_directory = (
        base_directory
        / "build"
        / "pyinstaller_visa"
        / build_identifier
    )

    arguments = [
        str(script_file),
        "--onedir",
        "--console",
        "--clean",
        "--noconfirm",
        f"--name={APPLICATION_NAME}",
        f"--distpath={distribution_directory}",
        f"--workpath={work_directory}",
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

    updater_arguments = [
        str(base_directory / "Program_Updater.py"),
        "--onefile",
        "--noconsole",
        "--clean",
        "--noconfirm",
        f"--name={UPDATER_NAME}",
        f"--distpath={application_directory}",
        f"--workpath={work_directory / 'updater'}",
        f"--specpath={base_directory / 'build'}",
    ]
    if icon_file is not None:
        updater_arguments.append(f"--icon={icon_file}")
    print("Building external updater executable...")
    PyInstaller.__main__.run(updater_arguments)

    copy_runtime_folders(base_directory, application_directory)
    (application_directory / "version.json").write_text(
        json.dumps(
            {
                "application": APPLICATION_NAME,
                "version": version,
                "built_at": datetime.now().isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    archive_base = distribution_directory / f"{APPLICATION_NAME}-{version}"
    archive_path = Path(
        shutil.make_archive(
            str(archive_base),
            "zip",
            root_dir=distribution_directory,
            base_dir=APPLICATION_NAME,
        )
    )
    manifest_path = distribution_directory / "update_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": version,
                "package_url": archive_path.name,
                "sha256": sha256_file(archive_path),
                "executable": f"{APPLICATION_NAME}.exe",
                "mandatory": False,
                "release_notes": (
                    f"{APPLICATION_NAME} version {version}"
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    executable = application_directory / f"{APPLICATION_NAME}.exe"
    print("\nBuild finished.")
    print(f"Executable: {executable}")
    print(f"Update package: {archive_path}")
    print(f"Update manifest: {manifest_path}")
    print("Editable runtime folders are located beside the executable.")


if __name__ == "__main__":
    build()
