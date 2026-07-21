"""Atomic loop-boundary checkpoints for safe interrupted-run continuation."""

import json
from pathlib import Path


JOURNAL_FILE_NAME = "execution_checkpoint.json"


class ExecutionJournal:
    def __init__(self, path, next_loop_index=0, resumed_from=None):
        self.path = Path(path)
        self.next_loop_index = max(0, int(next_loop_index))
        self.resumed_from = str(resumed_from) if resumed_from else None

    @classmethod
    def for_run(cls, run_context, resume_run_directory=None):
        next_loop_index = 0
        if resume_run_directory:
            previous_path = (
                Path(resume_run_directory) / "logs" / JOURNAL_FILE_NAME
            )
            next_loop_index = cls.load_next_loop(previous_path)
        journal = cls(
            run_context.storage.logs / JOURNAL_FILE_NAME,
            next_loop_index,
            resume_run_directory,
        )
        journal.save()
        return journal

    @staticmethod
    def load_next_loop(path):
        path = Path(path)
        if not path.is_file():
            return 0
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return max(0, int(payload.get("next_loop_index", 0)))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 0

    def complete_loop(self, loop_index):
        self.next_loop_index = max(self.next_loop_index, int(loop_index) + 1)
        self.save()

    def save(self):
        payload = {
            "schema_version": 1,
            "next_loop_index": self.next_loop_index,
            "resumed_from": self.resumed_from,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(self.path)
