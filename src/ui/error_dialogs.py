"""Reusable GUI error-dialog presentation."""

import traceback

from PyQt5.QtWidgets import QFileDialog, QMessageBox

from common.diagnostics import exception_details
from common.output_logging import print_console_safe


def show_error_dialog(parent, exception, traceback_text=None):
    if traceback_text is None:
        traceback_text = traceback.format_exc()

    print_console_safe("=== CRASH LOG ===")
    print_console_safe(traceback_text)

    message_box = QMessageBox(parent)
    message_box.setIcon(QMessageBox.Critical)
    message_box.setWindowTitle("Error")
    details = exception_details(exception)
    context = details.get("context", {})
    summary = str(exception)
    if context.get("role") or context.get("address"):
        instrument = context.get("role") or "Instrument"
        address = context.get("address", "unknown address")
        summary = f"{summary}\n\n{instrument}: {address}"
    message_box.setText(summary)
    message_box.setInformativeText(
        "Full diagnostic details are available in the run logs when a run folder exists."
    )
    message_box.setDetailedText(traceback_text)
    message_box.setStandardButtons(QMessageBox.Save | QMessageBox.Close)

    if message_box.exec_() != QMessageBox.Save:
        return
    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        "Save Crash Log",
        "crash_log.txt",
        "Text Files (*.txt)",
    )
    if file_path:
        with open(file_path, "w", encoding="utf-8") as crash_log:
            crash_log.write(traceback_text)
