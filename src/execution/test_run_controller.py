"""Lifecycle and queue orchestration for background test workers."""

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
import traceback
from uuid import uuid4

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from execution.test_worker import TestWorker


@dataclass
class TestRunRequest:
    checkbox_states: dict
    configuration: dict
    parameters: object
    label: str = "Test Run"
    prepare: object = None
    run_id: str = ""
    recovery_run_directory: str = ""

    def __post_init__(self):
        if not self.run_id:
            self.run_id = uuid4().hex


class TestRunController(QObject):
    worker_created = pyqtSignal(object)
    queue_changed = pyqtSignal(int)
    queue_finished = pyqtSignal()
    request_queued = pyqtSignal(object)
    request_started = pyqtSignal(object)
    request_status_changed = pyqtSignal(object, str)
    request_setup_failed = pyqtSignal(object, object, str)
    request_history_pruned = pyqtSignal(str)
    queue_halted = pyqtSignal(object, str)
    persistence_changed = pyqtSignal()

    TERMINAL_STATUSES = {
        "Completed", "Failed", "Aborted", "Interrupted", "Retried", "Removed"
    }

    def __init__(
        self,
        worker_factory=TestWorker,
        parent=None,
        history_limit=200,
        halt_on_failure=True,
    ):
        super().__init__(parent)
        self._worker_factory = worker_factory
        self._history_limit = max(0, int(history_limit))
        self.halt_on_failure = bool(halt_on_failure)
        self._queue = deque()
        self._terminal_history = deque()
        self._requests_by_id = {}
        self._statuses_by_id = {}
        self.active_worker = None
        self.active_request = None

    @property
    def pending_count(self):
        return len(self._queue)

    @property
    def pending_requests(self):
        return tuple(self._queue)

    @property
    def interrupted_requests(self):
        return tuple(
            request
            for run_id, request in self._requests_by_id.items()
            if self._statuses_by_id.get(run_id) == "Interrupted"
        )

    @property
    def is_running(self):
        return bool(self.active_worker and self.active_worker.isRunning())

    def start(self, checkbox_states, configuration, parameters, **request_options):
        if self.active_worker or self._queue:
            raise RuntimeError("A test run is already active")
        return self.enqueue(
            checkbox_states,
            configuration,
            parameters,
            auto_start=True,
            **request_options,
        )

    def enqueue(
        self,
        checkbox_states,
        configuration,
        parameters,
        *,
        label="Test Run",
        prepare=None,
        auto_start=True,
        run_id="",
    ):
        request = TestRunRequest(
            dict(checkbox_states),
            dict(configuration),
            parameters,
            label=label,
            prepare=prepare,
            run_id=run_id,
        )
        self._queue.append(request)
        self._requests_by_id[request.run_id] = request
        self.queue_changed.emit(len(self._queue))
        self.request_queued.emit(request)
        self._set_status(request, "Pending")
        self.persistence_changed.emit()
        if auto_start:
            self.start_queue()
        return request

    def start_queue(self):
        self._start_next()

    def remove_pending(self, run_id):
        requests = list(self._queue)
        for index, request in enumerate(requests):
            if request.run_id == run_id:
                requests.pop(index)
                self._queue = deque(requests)
                self.queue_changed.emit(len(self._queue))
                self._set_status(request, "Removed")
                self.persistence_changed.emit()
                return True
        request = self.request_for(run_id)
        if request and self.status_for(run_id) == "Interrupted":
            self._set_status(request, "Removed")
            self.persistence_changed.emit()
            return True
        return False

    def move_pending(self, run_id, offset):
        requests = list(self._queue)
        index = next(
            (i for i, request in enumerate(requests) if request.run_id == run_id),
            None,
        )
        if index is None:
            return False
        target = index + offset
        if target < 0 or target >= len(requests):
            return False
        requests[index], requests[target] = requests[target], requests[index]
        self._queue = deque(requests)
        self.queue_changed.emit(len(self._queue))
        self.persistence_changed.emit()
        return True

    def clear_pending(self):
        removed = tuple(self._queue)
        self._queue.clear()
        self.queue_changed.emit(0)
        for request in removed:
            self._set_status(request, "Removed")
        self.persistence_changed.emit()

    def request_for(self, run_id):
        return self._requests_by_id.get(run_id)

    def status_for(self, run_id):
        return self._statuses_by_id.get(run_id)

    @property
    def history_count(self):
        return len(self._terminal_history)

    def duplicate(self, run_id, auto_start=False):
        source = self.request_for(run_id)
        if source is None:
            return None
        return self.enqueue(
            deepcopy(source.checkbox_states),
            deepcopy(source.configuration),
            deepcopy(source.parameters),
            label=f"{source.label} (Copy)",
            prepare=source.prepare,
            auto_start=auto_start,
        )

    def retry(self, run_id, auto_start=False):
        status = self.status_for(run_id)
        if status not in {"Failed", "Aborted", "Interrupted"}:
            return None
        source = self.request_for(run_id)
        if source is None:
            return None
        retry = self.enqueue(
            deepcopy(source.checkbox_states),
            deepcopy(source.configuration),
            deepcopy(source.parameters),
            label=f"{source.label} (Retry)",
            prepare=source.prepare,
            auto_start=auto_start,
        )
        if status == "Interrupted":
            if source.recovery_run_directory:
                if isinstance(retry.parameters, dict):
                    retry.parameters["resume_run_directory"] = (
                        source.recovery_run_directory
                    )
                else:
                    setattr(
                        retry.parameters,
                        "resume_run_directory",
                        source.recovery_run_directory,
                    )
            self._set_status(source, "Retried")
            self.persistence_changed.emit()
        return retry

    def restore_interrupted(
        self,
        checkbox_states,
        configuration,
        parameters,
        *,
        label="Interrupted Test Run",
        prepare=None,
        run_id="",
        recovery_run_directory="",
    ):
        request = TestRunRequest(
            dict(checkbox_states),
            dict(configuration),
            parameters,
            label=label,
            prepare=prepare,
            run_id=run_id,
            recovery_run_directory=recovery_run_directory,
        )
        self._requests_by_id[request.run_id] = request
        self.request_queued.emit(request)
        self._set_status(request, "Interrupted")
        return request

    def pause(self):
        if self.is_running:
            self.active_worker.pause()

    def resume(self):
        if self.is_running:
            self.active_worker.resume()

    def request_stop(self, clear_pending=True):
        if clear_pending:
            self.clear_pending()
        if self.is_running:
            self.active_worker.request_stop()

    def _start_next(self):
        if self.active_worker is not None:
            return
        if not self._queue:
            self.queue_finished.emit()
            return

        request = self._queue.popleft()
        self.active_request = request
        self.queue_changed.emit(len(self._queue))
        self.persistence_changed.emit()
        try:
            if request.prepare:
                request.prepare(request)
            self.persistence_changed.emit()
        except Exception as exception:
            traceback_text = traceback.format_exc()
            self._set_status(request, "Failed")
            self.request_setup_failed.emit(request, exception, traceback_text)
            self.active_request = None
            self.persistence_changed.emit()
            self._advance_queue(request, "Failed")
            return
        worker = self._worker_factory(
            request.checkbox_states,
            request.configuration,
            request.parameters,
        )
        self.active_worker = worker
        worker.finished.connect(lambda: self._worker_ended(request, "Completed"))
        worker.aborted.connect(lambda: self._worker_ended(request, "Aborted"))
        failure_signal = getattr(worker, "failed", worker.error)
        failure_signal.connect(lambda *_: self._worker_ended(request, "Failed"))
        worker.state_changed.connect(
            lambda state: self._worker_state_changed(request, state)
        )
        self.request_started.emit(request)
        self._set_status(request, "Running")
        self.worker_created.emit(worker)
        worker.start()

    def _worker_ended(self, request, status):
        if request is not self.active_request:
            return
        worker = self.active_worker
        if worker is not None and hasattr(worker, "wait"):
            worker.wait()
        self._set_status(request, status)
        self.active_worker = None
        self.active_request = None
        self.persistence_changed.emit()
        self._advance_queue(request, status)

    def _advance_queue(self, request, status):
        if status == "Failed" and self.halt_on_failure and self._queue:
            self.queue_halted.emit(request, status)
            return
        QTimer.singleShot(0, self._start_next)

    def _worker_state_changed(self, request, state):
        if request is not self.active_request:
            return
        status = {
            "RUNNING": "Running",
            "PAUSING": "Pausing",
            "PAUSED": "Paused",
            "STOPPING": "Stopping",
        }.get(state)
        if status:
            self._set_status(request, status)

    def _set_status(self, request, status):
        if self._statuses_by_id.get(request.run_id) == status:
            return
        self._statuses_by_id[request.run_id] = status
        self.request_status_changed.emit(request, status)
        if status not in self.TERMINAL_STATUSES:
            return
        if request.run_id in self._terminal_history:
            self._terminal_history.remove(request.run_id)
        self._terminal_history.append(request.run_id)
        while len(self._terminal_history) > self._history_limit:
            expired_run_id = self._terminal_history.popleft()
            self._requests_by_id.pop(expired_run_id, None)
            self._statuses_by_id.pop(expired_run_id, None)
            self.request_history_pruned.emit(expired_run_id)
