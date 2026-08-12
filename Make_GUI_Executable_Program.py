import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

APPLICATION_NAME = "Test_Automation_Program"
UPDATER_NAME = "Program_Updater"
DEFAULT_PUBLISH_DIRECTORY = Path(
    r"\\remus\BID_RnD\Hornbill\Wei Jing\Test_Automation_Program"
)
VISA_RUNTIME_HOOK = Path("packaging_hooks") / "initialize_native_visa.py"
RUNTIME_FOLDERS = (
    "Instrument_Config_Files",
    "setup_images",
    "csv",
    "video_streaming",
)
GENERATED_RUNTIME_FILES = {
    "csv": (
        "power_study_*.csv",
        "temperature_measurements.csv",
    ),
}
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


def build_version(base_directory, build_time=None):
    version = os.getenv("AUTOMATION_BUILD_VERSION", "").strip()
    if not version:
        version = (
            base_directory / "VERSION"
        ).read_text(encoding="utf-8").strip()
    if not version:
        raise SystemExit("Application version cannot be empty")
    if build_time is not None and not os.getenv(
        "AUTOMATION_BUILD_VERSION", ""
    ).strip():
        version = (
            f"{version}.{build_time:%Y%m%d}.{build_time:%H%M%S}"
        )
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
        for pattern in GENERATED_RUNTIME_FILES.get(folder_name, ()):
            for generated_file in destination.glob(pattern):
                generated_file.unlink()
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


def ensure_tk_runtime(application_directory, python_prefix=None):
    internal_directory = Path(application_directory) / "_internal"
    if not (internal_directory / "_tkinter.pyd").is_file():
        return

    python_prefix = Path(python_prefix or sys.base_prefix)
    source_root = python_prefix / "tcl"
    runtime_directories = {
        "_tcl_data": source_root / "tcl8.6",
        "_tk_data": source_root / "tk8.6",
        "tcl8": source_root / "tcl8",
    }
    for destination_name, source in runtime_directories.items():
        destination = internal_directory / destination_name
        if destination.is_dir():
            continue
        if not source.is_dir():
            raise SystemExit(f"Required Tcl/Tk runtime folder is missing: {source}")
        shutil.copytree(source, destination)
        print(f"Restored bundled Tcl/Tk runtime: {destination_name}/")

    required_files = (
        internal_directory / "_tcl_data" / "init.tcl",
        internal_directory / "_tk_data" / "tk.tcl",
    )
    missing = [path for path in required_files if not path.is_file()]
    if missing:
        raise SystemExit(
            "Packaged Tcl/Tk runtime is incomplete: "
            + ", ".join(str(path) for path in missing)
        )


def publish_release(distribution_directory, publish_directory, version):
    distribution_directory = Path(distribution_directory)
    publish_directory = Path(publish_directory)
    archive_path = next(
        distribution_directory.glob(f"{APPLICATION_NAME}-*.zip"),
        None,
    )
    manifest_path = distribution_directory / "update_manifest.json"
    application_directory = distribution_directory / APPLICATION_NAME
    missing = [
        path
        for path in (application_directory, archive_path, manifest_path)
        if path is None or not path.exists()
    ]
    if missing:
        raise FileNotFoundError(
            "Release publication inputs are missing: "
            + ", ".join(str(path) for path in missing)
        )

    publish_directory.mkdir(parents=True, exist_ok=True)
    release_directory = publish_directory / version
    if release_directory.exists():
        raise FileExistsError(f"Published release already exists: {release_directory}")
    shutil.copytree(distribution_directory, release_directory)

    published_archive = publish_directory / archive_path.name
    shutil.copy2(archive_path, published_archive)
    temporary_manifest = publish_directory / ".update_manifest.tmp"
    shutil.copy2(manifest_path, temporary_manifest)
    os.replace(temporary_manifest, publish_directory / "update_manifest.json")
    (publish_directory / "LATEST_RELEASE.txt").write_text(
        f"Version: {version}\nFolder: {release_directory.name}\n"
        f"Package: {published_archive.name}\n",
        encoding="utf-8",
    )
    return release_directory


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
    build_time = datetime.now()
    build_identifier = build_time.strftime("%Y%m%d_%H%M%S")
    distribution_directory = (
        base_directory / "Executable_Builds" / build_identifier
    )
    application_directory = distribution_directory / APPLICATION_NAME
    version = build_version(base_directory, build_time)
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

    ensure_tk_runtime(application_directory)
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

    published_release = None
    if os.getenv("AUTOMATION_DISABLE_PUBLISH", "").strip().lower() not in {
        "1", "true", "yes", "on"
    }:
        publish_directory = Path(
            os.getenv(
                "AUTOMATION_PUBLISH_DIRECTORY",
                str(DEFAULT_PUBLISH_DIRECTORY),
            )
        )
        try:
            published_release = publish_release(
                distribution_directory,
                publish_directory,
                version,
            )
        except OSError as exception:
            if os.getenv("AUTOMATION_PUBLISH_REQUIRED", "").strip().lower() in {
                "1", "true", "yes", "on"
            }:
                raise
            print(f"Network publication warning: {exception}")

    executable = application_directory / f"{APPLICATION_NAME}.exe"
    print("\nBuild finished.")
    print(f"Executable: {executable}")
    print(f"Update package: {archive_path}")
    print(f"Update manifest: {manifest_path}")
    if published_release is not None:
        print(f"Published release: {published_release}")
    print("Editable runtime folders are located beside the executable.")


if __name__ == "__main__":
    build()
