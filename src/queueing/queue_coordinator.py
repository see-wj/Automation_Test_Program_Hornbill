"""Coordinate queue persistence, recovery, templates, and queue-widget actions."""

from pathlib import Path

from PyQt5.QtWidgets import QFileDialog

from queueing.queue_persistence import QueuePersistence, QueuePersistenceError
from queueing.queue_template_service import append_queue_template, save_queue_template
from configuration.test_configuration import ParameterSnapshot


class QueueCoordinator:
    def __init__(
        self,
        controller,
        widget,
        queue_file,
        prepare,
        message_sink,
        parent=None,
        template_directory=None,
    ):
        self.controller = controller
        self.widget = widget
        self.persistence = QueuePersistence(queue_file)
        self.prepare = prepare
        self.message_sink = message_sink
        self.parent = parent
        self.template_directory = Path(template_directory or Path(queue_file).parent)
        self._restoring = False
        self._connect_signals()

    def _connect_signals(self):
        self.widget.run_requested.connect(self.controller.start_queue)
        self.widget.remove_requested.connect(self.remove)
        self.widget.move_requested.connect(self.move)
        self.widget.clear_requested.connect(self.controller.clear_pending)
        self.widget.duplicate_requested.connect(self.duplicate)
        self.widget.retry_requested.connect(self.retry)
        self.widget.save_template_requested.connect(self.save_template)
        self.widget.load_template_requested.connect(self.load_template)
        self.controller.request_queued.connect(self._request_added)
        self.controller.request_status_changed.connect(self._status_changed)
        self.controller.request_history_pruned.connect(self.widget.remove_run)
        self.controller.queue_halted.connect(self._queue_halted)
        self.controller.persistence_changed.connect(self.persist)

    def persist(self, *_):
        if self._restoring:
            return
        try:
            self.persistence.save(
                self.controller.pending_requests,
                self.controller.active_request,
                self.controller.interrupted_requests,
            )
        except QueuePersistenceError as exception:
            self.message_sink(f"Queue save warning: {exception}")

    def restore(self):
        self._restoring = True
        try:
            snapshot = self.persistence.load_snapshot()
            interrupted_records = list(snapshot["interrupted"])
            if snapshot["active"]:
                interrupted_records.insert(0, snapshot["active"])
            restored_ids = self._restore_interrupted(interrupted_records)
            self._restore_pending(snapshot["pending"])
            if interrupted_records:
                self.message_sink(
                    f"Recovered {len(restored_ids)} interrupted run(s). "
                    "Review and use Retry Failed to run them again."
                )
            if snapshot["pending"]:
                self.message_sink(
                    f"Restored {len(snapshot['pending'])} pending queue item(s)"
                )
        except (QueuePersistenceError, KeyError, TypeError) as exception:
            self.message_sink(f"Queue restore warning: {exception}")
        finally:
            self._restoring = False
        self.persist()

    def _restore_interrupted(self, records):
        restored_ids = set()
        for record in records:
            run_id = record.get("run_id", "")
            if run_id in restored_ids:
                continue
            restored_ids.add(run_id)
            self.controller.restore_interrupted(
                record["checkbox_states"],
                record["configuration"],
                ParameterSnapshot(record["parameters"]),
                label=record.get("label", "Interrupted Test Run"),
                prepare=self.prepare,
                run_id=run_id,
                recovery_run_directory=record.get("run_directory") or "",
            )
            if record.get("run_directory"):
                self.message_sink(
                    f"Interrupted run artifacts: {record['run_directory']}"
                )
        return restored_ids

    def _restore_pending(self, records):
        for record in records:
            self.controller.enqueue(
                record["checkbox_states"],
                record["configuration"],
                ParameterSnapshot(record["parameters"]),
                label=record.get("label", "Restored Test Run"),
                prepare=self.prepare,
                auto_start=False,
                run_id=record.get("run_id", ""),
            )

    def _request_added(self, request):
        self.widget.add_request(request)
        self.message_sink(f"Queued: {request.label}")

    def _status_changed(self, request, status):
        self.widget.update_status(request, status)
        self.message_sink(f"Queue item '{request.label}': {status}")

    def _queue_halted(self, request, status):
        self.message_sink(
            f"Queue halted after '{request.label}' {status.lower()}. "
            "Review the failure, then click Run Queue to continue pending tests."
        )

    def remove(self, run_id):
        self.controller.remove_pending(run_id)

    def move(self, run_id, offset):
        if self.controller.move_pending(run_id, offset):
            self.widget.reorder(self.controller.pending_requests)

    def duplicate(self, run_id):
        if self.controller.duplicate(run_id) is None:
            self.message_sink("Unable to duplicate the selected queue item")

    def retry(self, run_id):
        if self.controller.retry(run_id) is None:
            self.message_sink(
                "Only failed, aborted, or interrupted queue items can be retried"
            )

    def save_template(self):
        if not self.controller.pending_requests:
            self.message_sink("Queue template not saved: no pending items")
            return
        template_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Save Queue Template",
            str(self.template_directory / "queue_template.json"),
            "Queue Template (*.json)",
        )
        if not template_path:
            return
        try:
            save_queue_template(template_path, self.controller.pending_requests)
            self.message_sink(f"Queue template saved: {template_path}")
        except QueuePersistenceError as exception:
            self.message_sink(f"Queue template save warning: {exception}")

    def load_template(self):
        template_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Load Queue Template",
            str(self.template_directory),
            "Queue Template (*.json)",
        )
        if not template_path:
            return
        try:
            loaded_count = append_queue_template(
                template_path,
                self.controller,
                prepare=self.prepare,
            )
            self.message_sink(f"Loaded {loaded_count} queue template item(s)")
        except (QueuePersistenceError, KeyError, TypeError) as exception:
            self.message_sink(f"Queue template load warning: {exception}")
