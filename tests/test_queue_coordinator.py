import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from queueing.queue_coordinator import QueueCoordinator
from queueing.queue_persistence import QueuePersistence
from configuration.test_configuration import ParameterSnapshot
from execution.test_run_controller import TestRunController, TestRunRequest


class DummySignal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in tuple(self.callbacks):
            callback(*args)


class DummyQueueWidget:
    def __init__(self):
        for name in (
            "run_requested",
            "remove_requested",
            "move_requested",
            "clear_requested",
            "duplicate_requested",
            "retry_requested",
            "save_template_requested",
            "load_template_requested",
        ):
            setattr(self, name, DummySignal())
        self.added = []
        self.statuses = []
        self.reordered = []
        self.removed = []

    def add_request(self, request):
        self.added.append(request)

    def update_status(self, request, status):
        self.statuses.append((request.run_id, status))

    def reorder(self, requests):
        self.reordered.append(tuple(request.run_id for request in requests))

    def remove_run(self, run_id):
        self.removed.append(run_id)


class QueueCoordinatorTests(unittest.TestCase):
    def _coordinator(self, path):
        controller = TestRunController()
        widget = DummyQueueWidget()
        messages = []
        coordinator = QueueCoordinator(
            controller,
            widget,
            path,
            prepare=lambda request: None,
            message_sink=messages.append,
        )
        return coordinator, controller, widget, messages

    def test_restore_recovers_active_without_starting_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queue.json"
            active = TestRunRequest(
                {"Voltage_Test": True},
                {"DUT": "Dolphin"},
                ParameterSnapshot(noofloop="1", savelocation="output"),
                label="Interrupted voltage",
                run_id="active-run",
                recovery_run_directory="output/active-run",
            )
            pending = TestRunRequest(
                {"Current_Test": True},
                {"DUT": "Hornbill"},
                ParameterSnapshot(noofloop="2", savelocation="output"),
                label="Pending current",
                run_id="pending-run",
            )
            QueuePersistence(path).save([pending], active)
            coordinator, controller, widget, messages = self._coordinator(path)

            coordinator.restore()

            self.assertIsNone(controller.active_worker)
            self.assertEqual(controller.pending_count, 1)
            self.assertEqual(controller.status_for("active-run"), "Interrupted")
            self.assertEqual(
                [request.run_id for request in widget.added],
                ["active-run", "pending-run"],
            )
            self.assertIn(("active-run", "Interrupted"), widget.statuses)
            self.assertTrue(
                any("output/active-run" in message for message in messages)
            )

    def test_widget_actions_delegate_and_reorder_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            coordinator, controller, widget, _ = self._coordinator(
                Path(directory) / "queue.json"
            )
            first = controller.enqueue({}, {}, {}, auto_start=False)
            second = controller.enqueue({}, {}, {}, auto_start=False)

            widget.move_requested.emit(second.run_id, -1)
            widget.duplicate_requested.emit(first.run_id)

            self.assertEqual(widget.reordered[-1], (second.run_id, first.run_id))
            self.assertEqual(controller.pending_count, 3)
            self.assertIs(coordinator.controller, controller)

    def test_persist_records_active_and_interrupted_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queue.json"
            coordinator, controller, _, _ = self._coordinator(path)
            interrupted = controller.restore_interrupted(
                {}, {}, {}, run_id="interrupted-run"
            )
            active = controller.enqueue({}, {}, {}, auto_start=False)
            controller._queue.clear()
            controller.active_request = active

            coordinator.persist()
            snapshot = QueuePersistence(path).load_snapshot()

            self.assertEqual(snapshot["active"]["run_id"], active.run_id)
            self.assertEqual(
                snapshot["interrupted"][0]["run_id"],
                interrupted.run_id,
            )


if __name__ == "__main__":
    unittest.main()
