import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from Make_GUI_Executable_Program import (
    COLLECT_SUBMODULES,
    RUNTIME_FOLDERS,
    build_version,
    copy_runtime_folders,
    ensure_tk_runtime,
    publish_release,
    sha256_file,
)


class ExecutableBuildTests(unittest.TestCase):
    def test_build_collects_all_active_application_packages(self):
        self.assertTrue(
            {
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
            }.issubset(COLLECT_SUBMODULES)
        )

    def test_build_version_and_checksum_helpers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "VERSION").write_text("1.2.3\n", encoding="utf-8")
            package = root / "package.zip"
            package.write_bytes(b"verified update")

            self.assertEqual("1.2.3", build_version(root))
            self.assertEqual(
                "1.2.3.20260810.153045",
                build_version(root, datetime(2026, 8, 10, 15, 30, 45)),
            )
            self.assertEqual(
                "59f19f34399b14e5f1628642e9ce341d660094ba"
                "76898e4db6b1875f525b6a6a",
                sha256_file(package),
            )

    def test_runtime_folders_are_copied_with_clean_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            destination = root / "application"
            for folder_name in RUNTIME_FOLDERS:
                folder = source / folder_name
                folder.mkdir(parents=True)
                (folder / "example.txt").write_text(folder_name, encoding="utf-8")
            (source / "Instrument_Config_Files" / "test_queue.json").write_text(
                '{"schema_version": 2, "interrupted": [{"run_id": "old"}]}',
                encoding="utf-8",
            )
            generated_csv = source / "csv" / "power_study_20260806.csv"
            generated_csv.write_text("generated", encoding="utf-8")
            temperature_csv = source / "csv" / "temperature_measurements.csv"
            temperature_csv.write_text("generated", encoding="utf-8")

            copy_runtime_folders(source, destination)

            for folder_name in RUNTIME_FOLDERS:
                self.assertEqual(
                    (destination / folder_name / "example.txt").read_text(
                        encoding="utf-8"
                    ),
                    folder_name,
                )
            queue = json.loads(
                (
                    destination
                    / "Instrument_Config_Files"
                    / "test_queue.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(queue["pending"], [])
            self.assertIsNone(queue["active"])
            self.assertEqual(queue["interrupted"], [])
            self.assertFalse(
                (destination / "csv" / generated_csv.name).exists()
            )
            self.assertFalse(
                (destination / "csv" / temperature_csv.name).exists()
            )

    def test_missing_tk_runtime_is_restored_for_frozen_application(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            application = root / "application"
            internal = application / "_internal"
            internal.mkdir(parents=True)
            (internal / "_tkinter.pyd").write_bytes(b"extension")
            python_prefix = root / "python"
            for relative_path, filename in (
                (("tcl", "tcl8.6"), "init.tcl"),
                (("tcl", "tk8.6"), "tk.tcl"),
                (("tcl", "tcl8"), "package.tcl"),
            ):
                source = python_prefix.joinpath(*relative_path)
                source.mkdir(parents=True)
                (source / filename).write_text("runtime", encoding="utf-8")

            ensure_tk_runtime(application, python_prefix)

            self.assertTrue((internal / "_tcl_data" / "init.tcl").is_file())
            self.assertTrue((internal / "_tk_data" / "tk.tcl").is_file())
            self.assertTrue((internal / "tcl8" / "package.tcl").is_file())

    def test_release_is_published_to_versioned_folder_and_latest_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            distribution = root / "distribution"
            application = distribution / "Test_Automation_Program"
            application.mkdir(parents=True)
            (application / "Test_Automation_Program.exe").write_bytes(b"exe")
            archive = distribution / "Test_Automation_Program-1.2.3.zip"
            archive.write_bytes(b"zip")
            manifest = distribution / "update_manifest.json"
            manifest.write_text('{"version":"1.2.3"}', encoding="utf-8")
            publish_directory = root / "published"

            release = publish_release(
                distribution,
                publish_directory,
                "1.2.3.20260810.153045",
            )

            self.assertEqual(
                publish_directory / "1.2.3.20260810.153045",
                release,
            )
            self.assertTrue(
                (release / "Test_Automation_Program" / "Test_Automation_Program.exe").is_file()
            )
            self.assertEqual(
                b"zip",
                (publish_directory / archive.name).read_bytes(),
            )
            self.assertEqual(
                manifest.read_text(encoding="utf-8"),
                (publish_directory / "update_manifest.json").read_text(
                    encoding="utf-8"
                ),
            )


if __name__ == "__main__":
    unittest.main()
