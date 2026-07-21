"""Save and append reusable queue templates without GUI dependencies."""

from queueing.queue_persistence import QueuePersistence
from configuration.test_configuration import ParameterSnapshot


def save_queue_template(path, requests):
    QueuePersistence(path).save(requests)


def append_queue_template(path, controller, prepare=None):
    records = QueuePersistence(path).load()
    for record in records:
        controller.enqueue(
            record["checkbox_states"],
            record["configuration"],
            ParameterSnapshot(record["parameters"]),
            label=record.get("label", "Template Test Run"),
            prepare=prepare,
            auto_start=False,
        )
    return len(records)
