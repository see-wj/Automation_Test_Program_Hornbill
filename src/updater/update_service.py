"""Manifest-based application update discovery, download, and launch."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


APPLICATION_NAME = "Test_Automation_Program"
UPDATER_EXECUTABLE = "Program_Updater.exe"
MANIFEST_ENVIRONMENT_VARIABLE = "AUTOMATION_UPDATE_MANIFEST"
DEFAULT_PRESERVE_PATHS = (
    "Instrument_Config_Files",
    "csv",
)
VERSION_PATTERN = re.compile(
    r"^(?P<core>\d+(?:\.\d+)*)(?:[-+](?P<label>[A-Za-z0-9.-]+))?$"
)


def application_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def application_version(base_directory=None):
    base_directory = Path(base_directory or application_directory())
    version_json = base_directory / "version.json"
    if version_json.is_file():
        try:
            return str(
                json.loads(version_json.read_text(encoding="utf-8"))["version"]
            ).strip()
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            pass
    version_file = base_directory / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


def settings_path():
    if getattr(sys, "frozen", False):
        local_data = Path(
            os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
        directory = local_data / APPLICATION_NAME
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "update_settings.json"
    return application_directory() / ".update_settings.json"


def version_key(version):
    match = VERSION_PATTERN.fullmatch(str(version).strip())
    if match is None:
        raise ValueError(f"Invalid application version: {version!r}")
    core = tuple(int(part) for part in match.group("core").split("."))
    core = core + (0,) * (4 - len(core))
    label = match.group("label")
    return core, 1 if label is None else 0, label or ""


def is_newer_version(candidate, current):
    return version_key(candidate) > version_key(current)


@dataclass(frozen=True)
class UpdateManifest:
    version: str
    package_url: str
    sha256: str
    executable: str = f"{APPLICATION_NAME}.exe"
    release_notes: str = ""
    mandatory: bool = False

    @classmethod
    def from_mapping(cls, values):
        required = ("version", "package_url", "sha256")
        missing = [name for name in required if not str(values.get(name, "")).strip()]
        if missing:
            raise ValueError(
                "Update manifest is missing: " + ", ".join(missing)
            )
        checksum = str(values["sha256"]).strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("Update manifest sha256 must contain 64 hex characters")
        version_key(values["version"])
        return cls(
            version=str(values["version"]).strip(),
            package_url=str(values["package_url"]).strip(),
            sha256=checksum,
            executable=str(
                values.get("executable") or f"{APPLICATION_NAME}.exe"
            ).strip(),
            release_notes=str(values.get("release_notes") or "").strip(),
            mandatory=bool(values.get("mandatory", False)),
        )


@dataclass(frozen=True)
class UpdateStatus:
    current_version: str
    manifest: UpdateManifest
    update_available: bool
    manifest_source: str
    package_source: str


class ApplicationUpdateService:
    def __init__(self, manifest_source=None, base_directory=None):
        self.base_directory = Path(base_directory or application_directory())
        self.current_version = application_version(self.base_directory)
        self.manifest_source = (
            str(manifest_source).strip()
            if manifest_source
            else self.configured_manifest_source()
        )

    @staticmethod
    def configured_manifest_source():
        environment_source = os.getenv(
            MANIFEST_ENVIRONMENT_VARIABLE,
            "",
        ).strip()
        if environment_source:
            return environment_source
        path = settings_path()
        if not path.is_file():
            return ""
        try:
            values = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return ""
        return str(values.get("manifest_source") or "").strip()

    @staticmethod
    def save_manifest_source(source):
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"manifest_source": str(source).strip()},
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _is_url(source):
        return urlparse(str(source)).scheme.lower() in {"http", "https", "file"}

    @classmethod
    def _read_source(cls, source):
        if cls._is_url(source):
            request = Request(
                source,
                headers={"User-Agent": f"{APPLICATION_NAME}-Updater"},
            )
            with urlopen(request, timeout=30) as response:
                return response.read()
        return Path(source).expanduser().resolve().read_bytes()

    @classmethod
    def _resolve_package_source(cls, manifest_source, package_url):
        if cls._is_url(package_url):
            return package_url
        if cls._is_url(manifest_source):
            return urljoin(manifest_source, package_url)
        return str(
            (Path(manifest_source).expanduser().resolve().parent / package_url)
            .resolve()
        )

    def check(self):
        if not self.manifest_source:
            raise ValueError(
                "Update manifest source is not configured. Enter a network "
                "path or HTTPS URL."
            )
        raw_manifest = self._read_source(self.manifest_source)
        try:
            values = json.loads(raw_manifest.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exception:
            raise ValueError("Update manifest is not valid UTF-8 JSON") from exception
        manifest = UpdateManifest.from_mapping(values)
        package_source = self._resolve_package_source(
            self.manifest_source,
            manifest.package_url,
        )
        return UpdateStatus(
            current_version=self.current_version,
            manifest=manifest,
            update_available=is_newer_version(
                manifest.version,
                self.current_version,
            ),
            manifest_source=self.manifest_source,
            package_source=package_source,
        )

    @classmethod
    def _download(cls, source, destination, progress_callback=None):
        destination = Path(destination)
        if cls._is_url(source):
            request = Request(
                source,
                headers={"User-Agent": f"{APPLICATION_NAME}-Updater"},
            )
            with urlopen(request, timeout=120) as response, destination.open(
                "wb"
            ) as output_file:
                total = int(response.headers.get("Content-Length") or 0)
                downloaded = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output_file.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total)
            return

        source_path = Path(source).expanduser().resolve()
        total = source_path.stat().st_size
        copied = 0
        with source_path.open("rb") as input_file, destination.open(
            "wb"
        ) as output_file:
            while True:
                chunk = input_file.read(1024 * 1024)
                if not chunk:
                    break
                output_file.write(chunk)
                copied += len(chunk)
                if progress_callback:
                    progress_callback(copied, total)

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with Path(path).open("rb") as package:
            for chunk in iter(lambda: package.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def stage(self, status, progress_callback=None):
        if not status.update_available:
            raise ValueError("The installed application is already up to date")
        staging_directory = Path(
            tempfile.mkdtemp(prefix=f"{APPLICATION_NAME}_update_")
        )
        package_path = staging_directory / "update.zip"
        try:
            self._download(
                status.package_source,
                package_path,
                progress_callback,
            )
            checksum = self._sha256(package_path)
            if checksum.lower() != status.manifest.sha256.lower():
                raise ValueError(
                    "Downloaded update failed SHA-256 verification"
                )
            return package_path
        except Exception:
            shutil.rmtree(staging_directory, ignore_errors=True)
            raise

    def launch_installer(self, package_path, status):
        if not getattr(sys, "frozen", False):
            raise RuntimeError(
                "Update installation is available only in the packaged application"
            )
        updater = self.base_directory / UPDATER_EXECUTABLE
        if not updater.is_file():
            raise FileNotFoundError(
                f"Updater helper is missing: {updater}"
            )
        temporary_updater = (
            Path(tempfile.gettempdir())
            / f"{APPLICATION_NAME}_Updater_{os.getpid()}.exe"
        )
        shutil.copy2(updater, temporary_updater)
        arguments = [
            str(temporary_updater),
            "--package",
            str(Path(package_path).resolve()),
            "--target",
            str(self.base_directory.resolve()),
            "--executable",
            status.manifest.executable,
            "--pid",
            str(os.getpid()),
        ]
        for preserve_path in DEFAULT_PRESERVE_PATHS:
            arguments.extend(("--preserve", preserve_path))
        subprocess.Popen(
            arguments,
            close_fds=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return temporary_updater
