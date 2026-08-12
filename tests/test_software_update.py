import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from Program_Updater import (
    install_update,
    retry_file_operation,
    safe_extract,
)
from updater.update_service import (
    ApplicationUpdateService,
    is_newer_version,
)


class SoftwareUpdateTests(unittest.TestCase):
    def test_retries_temporary_windows_folder_lock(self):
        attempts = []
        clock = [0.0]

        def operation():
            attempts.append(clock[0])
            if len(attempts) < 3:
                raise PermissionError(32, "file is being used")
            return "renamed"

        def sleep(seconds):
            clock[0] += seconds

        result = retry_file_operation(
            operation,
            "move test application",
            timeout=5,
            retry_interval=0.5,
            sleep_fn=sleep,
            monotonic_fn=lambda: clock[0],
        )

        self.assertEqual(result, "renamed")
        self.assertEqual(len(attempts), 3)

    def test_version_comparison_supports_release_versions(self):
        self.assertTrue(is_newer_version("1.2.0", "1.1.9"))
        self.assertFalse(is_newer_version("1.2.0", "1.2.0"))
        self.assertTrue(is_newer_version("1.2.0", "1.2.0-rc1"))
        self.assertTrue(
            is_newer_version(
                "1.2.0.20260810.153045",
                "1.2.0.20260806.145000",
            )
        )

    def test_checks_relative_manifest_and_stages_verified_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            application = root / "installed"
            release = root / "release"
            application.mkdir()
            release.mkdir()
            (application / "version.json").write_text(
                json.dumps({"version": "1.0.0"}),
                encoding="utf-8",
            )
            package = release / "Test_Automation_Program-1.1.0.zip"
            package.write_bytes(b"update archive")
            checksum = hashlib.sha256(package.read_bytes()).hexdigest()
            manifest = release / "update_manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "version": "1.1.0",
                        "package_url": package.name,
                        "sha256": checksum,
                        "release_notes": "Updater test",
                    }
                ),
                encoding="utf-8",
            )

            service = ApplicationUpdateService(
                manifest,
                base_directory=application,
            )
            status = service.check()
            staged_package = service.stage(status)
            try:
                self.assertTrue(status.update_available)
                self.assertEqual("1.1.0", status.manifest.version)
                self.assertEqual(package.read_bytes(), staged_package.read_bytes())
            finally:
                staged_package.unlink(missing_ok=True)
                staged_package.parent.rmdir()

    def test_installer_replaces_application_and_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "Test_Automation_Program"
            target.mkdir()
            (target / "Test_Automation_Program.exe").write_bytes(b"old")
            old_config = target / "Instrument_Config_Files"
            old_config.mkdir()
            (old_config / "config_Hornbill.txt").write_text(
                "user settings",
                encoding="utf-8",
            )

            payload = root / "payload" / "Test_Automation_Program"
            payload.mkdir(parents=True)
            (payload / "Test_Automation_Program.exe").write_bytes(b"new")
            new_config = payload / "Instrument_Config_Files"
            new_config.mkdir()
            (new_config / "config_Hornbill.txt").write_text(
                "release defaults",
                encoding="utf-8",
            )
            (payload / "new_module.txt").write_text("new", encoding="utf-8")
            package = root / "update.zip"
            with zipfile.ZipFile(package, "w") as archive:
                for path in payload.parent.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(payload.parent.parent))

            backup = install_update(
                package,
                target,
                "Test_Automation_Program.exe",
                ("Instrument_Config_Files",),
            )

            self.assertEqual(
                b"new",
                (target / "Test_Automation_Program.exe").read_bytes(),
            )
            self.assertEqual(
                "user settings",
                (
                    target
                    / "Instrument_Config_Files"
                    / "config_Hornbill.txt"
                ).read_text(encoding="utf-8"),
            )
            self.assertTrue((target / "new_module.txt").is_file())
            self.assertEqual(
                b"old",
                (backup / "Test_Automation_Program.exe").read_bytes(),
            )

    def test_safe_extract_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "unsafe.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("../outside.txt", "unsafe")

            with self.assertRaises(ValueError):
                safe_extract(package, root / "extract")


if __name__ == "__main__":
    unittest.main()
