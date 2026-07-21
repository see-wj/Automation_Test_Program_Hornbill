import json
import tempfile
import unittest
from pathlib import Path

from Make_GUI_Executable_Program import RUNTIME_FOLDERS, copy_runtime_folders


class ExecutableBuildTests(unittest.TestCase):
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
