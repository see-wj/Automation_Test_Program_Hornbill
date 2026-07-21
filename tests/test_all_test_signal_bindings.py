import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.all_test_signal_bindings import (
    CLICKED_BINDINGS,
    CURRENT_TEXT_BINDINGS,
    STATE_CHANGED_BINDINGS,
    TEXT_EDITED_BINDINGS,
    connect_all_test_signals,
)


class DummySignal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class DummyWidget:
    def __init__(self):
        self.textEdited = DummySignal()
        self.currentTextChanged = DummySignal()
        self.currentIndexChanged = DummySignal()
        self.stateChanged = DummySignal()
        self.clicked = DummySignal()


class DummyDialog:
    def __init__(self):
        names = {
            name
            for bindings in (
                TEXT_EDITED_BINDINGS,
                CURRENT_TEXT_BINDINGS,
                STATE_CHANGED_BINDINGS,
                CLICKED_BINDINGS,
            )
            for name, _ in bindings
        }
        names.add("queue_test_button")
        for name in names:
            setattr(self, name, DummyWidget())
        handlers = {
            name
            for bindings in (
                TEXT_EDITED_BINDINGS,
                CURRENT_TEXT_BINDINGS,
                STATE_CHANGED_BINDINGS,
                CLICKED_BINDINGS,
            )
            for _, name in bindings
        }
        handlers.add("on_current_index_changed")
        for name in handlers:
            if name == "executeTest":
                continue
            setattr(self, name, lambda *args: None)
        self.execute_calls = []

    def executeTest(self, queue_only=False):
        self.execute_calls.append(queue_only)


class AllTestSignalBindingTests(unittest.TestCase):
    def test_connects_every_declared_binding(self):
        dialog = DummyDialog()

        connect_all_test_signals(dialog)

        for widget_name, _ in TEXT_EDITED_BINDINGS:
            self.assertEqual(len(getattr(dialog, widget_name).textEdited.callbacks), 1)
        for widget_name, _ in CURRENT_TEXT_BINDINGS:
            self.assertEqual(
                len(getattr(dialog, widget_name).currentTextChanged.callbacks),
                1,
            )
        for widget_name, _ in STATE_CHANGED_BINDINGS:
            self.assertEqual(len(getattr(dialog, widget_name).stateChanged.callbacks), 1)
        for widget_name, _ in CLICKED_BINDINGS:
            self.assertEqual(len(getattr(dialog, widget_name).clicked.callbacks), 1)

    def test_queue_button_requests_queue_only_execution(self):
        dialog = DummyDialog()
        connect_all_test_signals(dialog)

        callback = dialog.queue_test_button.clicked.callbacks[0]
        callback()

        self.assertEqual(dialog.execute_calls, [True])


if __name__ == "__main__":
    unittest.main()
