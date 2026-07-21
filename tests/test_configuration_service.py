import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from configuration.configuration_service import (
    apply_configuration,
    configuration_path,
    load_configuration,
)


class Target:
    savelocation = "chosen-output"


class ConfigurationServiceTests(unittest.TestCase):
    def test_resolves_known_and_fallback_files(self):
        self.assertEqual(
            configuration_path("config", "Dolphin").name,
            "config_Dolphin.txt",
        )
        self.assertEqual(
            configuration_path("config", "Unknown").name,
            "config_Others.txt",
        )

    def test_loads_values_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.txt"
            path.write_text("# comment\nDUT = Dolphin\n// ignored\nnoofloop=2\n", encoding="utf-8")

            values = load_configuration(path)

        self.assertEqual(values, {"DUT": "Dolphin", "noofloop": "2"})

    def test_preserves_user_selected_save_location(self):
        target = Target()

        apply_configuration(target, {"savelocation": "default", "DUT": "Dolphin"})

        self.assertEqual(target.savelocation, "chosen-output")
        self.assertEqual(target.DUT, "Dolphin")


if __name__ == "__main__":
    unittest.main()
