"""GUI tab for safely analyzing external Python instrument test scripts."""

import json
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from analysis.test_script_analyzer import analyze_test_script
from ui.integration_blueprint_review import IntegrationBlueprintReviewWidget


class ScriptAnalysisWorker(QThread):
    analysis_ready = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, script_path, parent=None):
        super().__init__(parent)
        self.script_path = Path(script_path)

    def run(self):
        try:
            self.analysis_ready.emit(analyze_test_script(self.script_path))
        except Exception as exception:
            self.failed.emit(str(exception))


class TestScriptAssistantTab(QWidget):
    """Analyze scripts without executing them or modifying production files."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.analysis = None

        title = QLabel("Test Script Import Assistant")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        description = QLabel(
            "Select another developer's Python test script. The assistant performs "
            "static analysis only: it never executes the selected script or sends "
            "commands to instruments."
        )
        description.setWordWrap(True)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select a Python test script...")
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.select_script)
        self.analyze_button = QPushButton("Analyze Script")
        self.analyze_button.clicked.connect(self.start_analysis)
        self.export_button = QPushButton("Export Analysis JSON")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_analysis)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_input, 1)
        path_layout.addWidget(browse_button)
        path_layout.addWidget(self.analyze_button)
        path_layout.addWidget(self.export_button)

        self.status_label = QLabel("Ready - no script has been executed.")
        self.status_label.setStyleSheet("font-weight: bold; color: #1f4e79;")

        self.result_tabs = QTabWidget()
        self.overview_output = QPlainTextEdit()
        self.overview_output.setReadOnly(True)
        self.command_table = QTableWidget(0, 5)
        self.command_table.setHorizontalHeaderLabels(
            ("Line", "Operation", "Receiver", "SCPI Command", "Likely Mapping")
        )
        self.command_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.command_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch
        )
        self.flow_output = QPlainTextEdit()
        self.flow_output.setReadOnly(True)
        self.warning_output = QPlainTextEdit()
        self.warning_output.setReadOnly(True)
        self.integration_output = QPlainTextEdit()
        self.integration_output.setReadOnly(True)
        self.blueprint_review = IntegrationBlueprintReviewWidget()
        self.result_tabs.addTab(self.overview_output, "Overview")
        self.result_tabs.addTab(self.command_table, "SCPI Mapping")
        self.result_tabs.addTab(self.flow_output, "Execution Flow")
        self.result_tabs.addTab(self.warning_output, "Warnings")
        self.result_tabs.addTab(self.integration_output, "Integration Plan")
        self.result_tabs.addTab(self.blueprint_review, "Review & Blueprint")

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(path_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.result_tabs, 1)

    def select_script(self):
        script_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Instrument Test Script",
            self.path_input.text().strip(),
            "Python Scripts (*.py)",
        )
        if script_path:
            self.path_input.setText(script_path)

    def start_analysis(self):
        if self.worker is not None and self.worker.isRunning():
            return
        script_path = Path(self.path_input.text().strip())
        if not script_path.is_file():
            QMessageBox.warning(
                self,
                "Invalid Script",
                "Select an existing Python test script.",
            )
            return

        self.analysis = None
        self.export_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.status_label.setText("Analyzing source code - nothing is being executed...")
        self.worker = ScriptAnalysisWorker(script_path, parent=self)
        self.worker.analysis_ready.connect(self.show_analysis)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.analysis_finished)
        self.worker.start()

    def show_analysis(self, analysis):
        self.analysis = analysis
        mapped_count = sum(bool(command.mappings) for command in analysis.commands)
        self.status_label.setText(
            f"Analysis complete: {len(analysis.commands)} command(s), "
            f"{mapped_count} mapped, {len(analysis.warnings)} warning(s)."
        )
        self.export_button.setEnabled(True)
        self._show_overview(analysis)
        self._show_commands(analysis)
        self.flow_output.setPlainText("\n".join(analysis.execution_flow))
        self.warning_output.setPlainText(
            "\n".join(
                f"{index}. {warning}"
                for index, warning in enumerate(analysis.warnings, 1)
            )
            or "No structural warnings detected."
        )
        self.integration_output.setPlainText(
            "\n".join(
                f"{index}. {step}"
                for index, step in enumerate(analysis.integration_steps, 1)
            )
        )
        self.blueprint_review.set_analysis(analysis)

    def _show_overview(self, analysis):
        sections = (
            ("Source", [analysis.source_path]),
            ("Imports", analysis.imports),
            ("Classes", analysis.classes),
            ("Functions", analysis.functions),
            ("Detected VISA Addresses", analysis.visa_addresses),
            ("Known Keysight Classes", analysis.instrument_classes),
            (
                "Inferred Instrument Roles",
                [
                    f"{item.variable}: {item.role} | {item.address} | {item.evidence}"
                    for item in analysis.instrument_roles
                ],
            ),
            (
                "Interactive Parameters",
                [
                    f"Line {item.line}: {item.name} ({item.conversion}) - {item.prompt}"
                    for item in analysis.parameters
                ],
            ),
            (
                "Safety Limits",
                [
                    f"Line {item.line}: {item.name} = {item.expression}"
                    for item in analysis.safety_limits
                ],
            ),
            (
                "Sweep Definitions",
                [
                    f"Line {item.line}: {item.name} = "
                    f"[{item.start}, {item.stop}, step {item.step}]"
                    for item in analysis.sweeps
                ],
            ),
            (
                "Data Fields",
                analysis.data_fields,
            ),
            (
                "Output Files",
                [
                    f"Line {item.line}: {item.operation} -> {item.path}"
                    for item in analysis.outputs
                ],
            ),
            (
                "Stop and Control Logic",
                [
                    f"Line {item.line}: {item.kind} - {item.expression}"
                    for item in analysis.controls
                ],
            ),
            (
                "Timing",
                [
                    f"Line {delay.line}: {delay.expression}"
                    for delay in analysis.delays
                ],
            ),
            (
                "Loops",
                [
                    f"Line {loop.line}: {loop.kind} {loop.expression}"
                    for loop in analysis.loops
                ],
            ),
        )
        lines = []
        for heading, values in sections:
            lines.append(heading)
            lines.append("=" * len(heading))
            lines.extend(f"- {value}" for value in values)
            if not values:
                lines.append("- None detected")
            lines.append("")
        self.overview_output.setPlainText("\n".join(lines))

    def _show_commands(self, analysis):
        self.command_table.setRowCount(len(analysis.commands))
        for row, command in enumerate(analysis.commands):
            values = (
                command.line,
                command.operation,
                command.receiver,
                command.command,
                "\n".join(command.mappings) or "Unmapped",
            )
            for column, value in enumerate(values):
                self.command_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(str(value)),
                )

    def show_error(self, message):
        self.status_label.setText("Analysis failed")
        QMessageBox.critical(self, "Script Analysis Error", message)

    def analysis_finished(self):
        worker = self.worker
        self.worker = None
        self.analyze_button.setEnabled(True)
        if worker is not None:
            worker.deleteLater()

    def export_analysis(self):
        if self.analysis is None:
            return
        default_path = str(Path(self.analysis.source_path).with_suffix(".analysis.json"))
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Script Analysis",
            default_path,
            "JSON Files (*.json)",
        )
        if not output_path:
            return
        Path(output_path).write_text(
            json.dumps(self.analysis.to_dict(), indent=2),
            encoding="utf-8",
        )
        self.status_label.setText(f"Analysis exported to {output_path}")


__all__ = ["ScriptAnalysisWorker", "TestScriptAssistantTab"]
