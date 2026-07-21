import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.dialog_registry import DialogRegistration, DialogRegistry


class DummyDialog:
    def __init__(self):
        self.shown = False

    def show(self):
        self.shown = True


class DialogRegistryTests(unittest.TestCase):
    def test_opens_dialog_and_keeps_owner_reference(self):
        owner = object.__new__(type("Owner", (), {}))
        registry = DialogRegistry(
            (
                DialogRegistration("Bundle", "Production", "bundle", DummyDialog),
                DialogRegistration("Screenshot", "Capture", "screenshot", DummyDialog),
                DialogRegistration("Voltage", "Measure", "voltage", DummyDialog),
            )
        )

        dialog = registry.open(owner, 2)

        self.assertIs(owner.voltage, dialog)
        self.assertTrue(dialog.shown)
        self.assertEqual(registry.selection_options, (("Voltage", "Measure"),))

    def test_invalid_index_reports_message(self):
        messages = []
        registry = DialogRegistry((), messages.append)

        self.assertIsNone(registry.open(object(), 3))
        self.assertEqual(messages, ["Invalid dialog index: 3"])


if __name__ == "__main__":
    unittest.main()
