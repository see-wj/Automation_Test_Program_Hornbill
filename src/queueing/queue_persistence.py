"""Versioned, atomic persistence for queued and interrupted test runs."""

import json
from pathlib import Path


SCHEMA_VERSION = 2


class QueuePersistenceError(RuntimeError):
    pass


class QueuePersistence:
    def __init__(self, path):
        self.path = Path(path)

    def save(self, requests, active_request=None, interrupted_requests=()):
        payload = {
            "schema_version": SCHEMA_VERSION,
            "pending": [self._serialize(request) for request in requests],
            "active": self._serialize(active_request) if active_request else None,
            "interrupted": [
                self._serialize(request) for request in interrupted_requests
            ],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            temporary_path.write_text(
                json.dumps(payload, indent=2, default=str),
                encoding="utf-8",
            )
            temporary_path.replace(self.path)
        except OSError as exception:
            raise QueuePersistenceError(
                f"Unable to save test queue: {exception}"
            ) from exception

    def load(self):
        return self.load_snapshot()["pending"]

    def load_snapshot(self):
        if not self.path.exists():
            return {"pending": [], "active": None, "interrupted": []}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exception:
            raise QueuePersistenceError(
                f"Unable to load test queue: {exception}"
            ) from exception
        schema_version = payload.get("schema_version")
        if schema_version not in {1, SCHEMA_VERSION}:
            raise QueuePersistenceError(
                f"Unsupported test queue schema: {schema_version}"
            )
        pending = payload.get("pending")
        if not isinstance(pending, list):
            raise QueuePersistenceError("Test queue pending data must be a list")
        if schema_version == 1:
            return {"pending": pending, "active": None, "interrupted": []}
        active = payload.get("active")
        interrupted = payload.get("interrupted", [])
        if active is not None and not isinstance(active, dict):
            raise QueuePersistenceError("Test queue active data must be an object")
        if not isinstance(interrupted, list):
            raise QueuePersistenceError("Test queue interrupted data must be a list")
        return {
            "pending": pending,
            "active": active,
            "interrupted": interrupted,
        }

    @staticmethod
    def _serialize(request):
        parameters = request.parameters
        if not isinstance(parameters, dict):
            parameters = vars(parameters)
        parameters = dict(parameters)
        run_context = parameters.pop("run_context", None)
        run_directory = getattr(request, "recovery_run_directory", None) or None
        if run_context is not None:
            run_directory = str(run_context.storage.root)
            output_root = str(run_context.output_root)
            parameters.update(
                savelocation=output_root,
                savedir=output_root,
                rawdir=None,
            )
        return {
            "run_id": request.run_id,
            "label": request.label,
            "checkbox_states": dict(request.checkbox_states),
            "configuration": dict(request.configuration),
            "parameters": parameters,
            "run_directory": run_directory,
        }
