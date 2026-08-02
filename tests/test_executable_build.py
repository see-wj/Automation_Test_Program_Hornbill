import json
import tempfile
import unittest
from pathlib import Path

from Make_GUI_Executable_Program import (
    COLLECT_SUBMODULES,
    RUNTIME_FOLDERS,
    build_version,
    copy_runtime_folders,
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


if __name__ == "__main__":
    unittest.main()
