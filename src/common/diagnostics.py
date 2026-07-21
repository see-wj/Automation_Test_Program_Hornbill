import datetime
import json


def exception_details(exception):
    if hasattr(exception, "to_dict"):
        return exception.to_dict()
    return {
        "type": type(exception).__name__,
        "message": str(exception),
        "context": {},
    }


def append_diagnostic(path, event, level="INFO", message=None, exception=None,
                      traceback_text=None, **context):
    record = {
        "timestamp": datetime.datetime.now().isoformat(timespec="milliseconds"),
        "level": level,
        "event": event,
    }
    if message is not None:
        record["message"] = str(message)
    if context:
        record["context"] = context
    if exception is not None:
        record["exception"] = exception_details(exception)
    if traceback_text:
        record["traceback"] = traceback_text

    with path.open("a", encoding="utf-8") as diagnostic_file:
        diagnostic_file.write(json.dumps(record, default=str) + "\n")
