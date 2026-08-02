"""Runtime GUI generated from an approved integration blueprint."""

from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFileDialog,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from analysis.blueprint_execution import enrich_blueprint_execution_metadata
from execution.blueprint_simulation_executor import (
    BlueprintExecutionControl,
    BlueprintSimulationCancelled,
    BlueprintSimulationExecutor,
)


class BlueprintSimulationWorker(QThread):
    progress = pyqtSignal(str, int, int)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)
    aborted = pyqtSignal(str)

    def __init__(
        self,
        blueprint,
        configuration,
        output_root,
        honor_settling_delay,
        parent=None,
    ):
        super().__init__(parent)
        self.control = BlueprintExecutionControl()
        self.result = None
        self.error_message = None
        self.executor = BlueprintSimulationExecutor(
            blueprint,
            configuration,
            output_root=output_root,
            control=self.control,
            progress_callback=self.progress.emit,
            honor_settling_delay=honor_settling_delay,
        )

    def run(self):
        try:
            self.result = self.executor.run()
            self.completed.emit(self.result)
        except BlueprintSimulationCancelled as exception:
            self.error_message = str(exception)
            self.aborted.emit(str(exception))
        except Exception as exception:
            self.error_message = str(exception)
            self.failed.emit(str(exception))


class BlueprintGeneratedGui(QWidget):
    """Build a non-executing configuration GUI from blueprint metadata."""

    def __init__(self, blueprint, parent=None):
        super().__init__(parent)
        blueprint_data = (
            blueprint.to_dict() if hasattr(blueprint, "to_dict") else dict(blueprint)
        )
        self.blueprint = enrich_blueprint_execution_metadata(blueprint_data)
        self.instrument_inputs = {}
        self.parameter_inputs = {}
        self.worker = None

        layout = QVBoxLayout(self)
        title = QLabel(self.blueprint.get("test_name", "Generated Test GUI"))
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        note = QLabel(
            "Simulation-only generated GUI. It validates configuration but does not "
            "open VISA sessions or execute instrument commands."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "background: #e7f3ff; color: #084298; padding: 8px; font-weight: bold;"
        )
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(self._build_instrument_group())
        layout.addWidget(self._build_parameter_group())
        layout.addWidget(self._build_safety_group())
        layout.addWidget(self._build_command_table(), 1)

        self.simulation_checkbox = QCheckBox(
            "Simulation mode required - no physical instrument control"
        )
        self.simulation_checkbox.setChecked(True)
        self.simulation_checkbox.setEnabled(False)
        self.validate_button = QPushButton("Validate Generated Configuration")
        self.validate_button.clicked.connect(self.validate_configuration)
        self.validation_status = QLabel("Enter or review the generated values.")
        self.validation_status.setWordWrap(True)
        self.output_root_input = QLineEdit(str(Path.cwd() / "csv"))
        output_browse_button = QPushButton("Browse Output...")
        output_browse_button.clicked.connect(self._browse_output_root)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_root_input, 1)
        output_layout.addWidget(output_browse_button)
        self.honor_delay_checkbox = QCheckBox(
            "Apply approved settling delays during simulation"
        )
        self.start_button = QPushButton("Run Simulation")
        self.pause_button = QPushButton("Pause")
        self.resume_button = QPushButton("Resume")
        self.abort_button = QPushButton("Abort")
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.abort_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_simulation)
        self.pause_button.clicked.connect(self.pause_simulation)
        self.resume_button.clicked.connect(self.resume_simulation)
        self.abort_button.clicked.connect(self.abort_simulation)
        execution_buttons = QHBoxLayout()
        execution_buttons.addWidget(self.start_button)
        execution_buttons.addWidget(self.pause_button)
        execution_buttons.addWidget(self.resume_button)
        execution_buttons.addWidget(self.abort_button)
        self.simulation_progress = QProgressBar()
        self.simulation_progress.setRange(0, 100)
        self.simulation_log = QPlainTextEdit()
        self.simulation_log.setReadOnly(True)
        self.simulation_log.setMaximumBlockCount(500)
        layout.addWidget(self.simulation_checkbox)
        layout.addWidget(self.validate_button)
        layout.addWidget(self.validation_status)
        layout.addWidget(QLabel("Simulation Output Root:"))
        layout.addLayout(output_layout)
        layout.addWidget(self.honor_delay_checkbox)
        layout.addLayout(execution_buttons)
        layout.addWidget(self.simulation_progress)
        layout.addWidget(self.simulation_log)

    def _build_instrument_group(self):
        group = QGroupBox("Instrument Addresses")
        form = QFormLayout(group)
        for instrument in self.blueprint.get("instruments", []):
            variable = instrument.get("variable", "instrument")
            role = instrument.get("role", "UNKNOWN")
            address_input = QLineEdit(str(instrument.get("address", "")))
            address_input.setPlaceholderText(f"{role} address")
            form.addRow(f"{role} ({variable}):", address_input)
            self.instrument_inputs[variable] = address_input
        if not self.instrument_inputs:
            form.addRow(QLabel("No instrument addresses were detected."))
        return group

    def _build_parameter_group(self):
        group = QGroupBox("Test Parameters")
        form = QFormLayout(group)
        for parameter in self.blueprint.get("parameters", []):
            if not parameter.get("include_in_gui", True):
                continue
            name = parameter.get("name", "parameter")
            value_type = str(parameter.get("value_type", "str")).lower()
            value_input = QLineEdit(str(parameter.get("default", "")))
            value_input.setPlaceholderText(parameter.get("prompt", name))
            if value_type == "float":
                value_input.setValidator(QDoubleValidator(value_input))
            elif value_type == "int":
                value_input.setValidator(QIntValidator(value_input))
            form.addRow(f"{name} ({value_type}):", value_input)
            self.parameter_inputs[name] = (value_type, value_input)
        if not self.parameter_inputs:
            form.addRow(QLabel("No interactive parameters were selected."))
        return group

    def _build_safety_group(self):
        safety = self.blueprint.get("safety", {})
        group = QGroupBox("Approved Safety Envelope")
        form = QFormLayout(group)
        form.addRow("Maximum Voltage:", QLabel(f"{safety.get('maximum_voltage', '')} V"))
        form.addRow("Maximum Current:", QLabel(f"{safety.get('maximum_current', '')} A"))
        form.addRow("Maximum Power:", QLabel(f"{safety.get('maximum_power', '')} W"))
        form.addRow(
            "Settling Delay:", QLabel(f"{safety.get('settling_delay_seconds', 0)} s")
        )
        form.addRow(
            "Polling Timeout:", QLabel(f"{safety.get('polling_timeout_seconds', 0)} s")
        )
        return group

    def _build_command_table(self):
        group = QGroupBox("Reviewed Command Plan")
        layout = QVBoxLayout(group)
        commands = self.blueprint.get("commands", [])
        bindings = {
            int(binding["line"]): binding
            for binding in self.blueprint.get("command_bindings", [])
        }
        table = QTableWidget(len(commands), 5)
        table.setHorizontalHeaderLabels(
            ("Line", "Receiver", "SCPI", "Mapping", "Arguments")
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for row, command in enumerate(commands):
            arguments = bindings.get(int(command.get("line", 0)), {}).get(
                "arguments", []
            )
            argument_text = ", ".join(
                f"{argument['name']}={argument['expression']}"
                for argument in arguments
            )
            values = (
                command.get("line", ""),
                command.get("receiver", ""),
                command.get("command", ""),
                command.get("selected_mapping", ""),
                argument_text,
            )
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(str(value)))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.command_table = table
        layout.addWidget(table)
        return group

    def configuration(self):
        parameters = {}
        for name, (value_type, value_input) in self.parameter_inputs.items():
            text = value_input.text().strip()
            if not text:
                raise ValueError(f"Parameter '{name}' is required.")
            if value_type == "float":
                value = float(text)
            elif value_type == "int":
                value = int(text)
            elif value_type == "bool":
                normalized = text.lower()
                if normalized not in {"true", "false", "1", "0", "yes", "no"}:
                    raise ValueError(f"Parameter '{name}' must be true or false.")
                value = normalized in {"true", "1", "yes"}
            else:
                value = text
            parameters[name] = value

        instruments = {
            variable: address_input.text().strip()
            for variable, address_input in self.instrument_inputs.items()
        }
        missing = [variable for variable, address in instruments.items() if not address]
        if missing:
            raise ValueError(
                "Instrument address is required for: " + ", ".join(missing)
            )
        for name, value in parameters.items():
            if name.endswith("_start") and isinstance(value, (int, float)) and value < 0:
                raise ValueError(f"Parameter '{name}' must be non-negative.")
            if name.endswith("_step") and isinstance(value, (int, float)) and value <= 0:
                raise ValueError(f"Parameter '{name}' must be greater than zero.")
        return {
            "test_name": self.blueprint.get("test_name", ""),
            "simulation_mode": True,
            "instruments": instruments,
            "parameters": parameters,
            "safety": dict(self.blueprint.get("safety", {})),
        }

    def validate_configuration(self):
        try:
            self.configuration()
        except (TypeError, ValueError) as exception:
            self.validation_status.setText(f"Configuration incomplete: {exception}")
            self.validation_status.setStyleSheet("color: #b02a37; font-weight: bold;")
            return False
        self.validation_status.setText(
            "Configuration valid for simulation scaffold generation."
        )
        self.validation_status.setStyleSheet("color: #146c43; font-weight: bold;")
        return True

    def _browse_output_root(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Simulation Output Directory",
            self.output_root_input.text().strip(),
        )
        if directory:
            self.output_root_input.setText(directory)

    def start_simulation(self):
        if self.worker is not None and self.worker.isRunning():
            return
        if not self.validate_configuration():
            return
        output_root = self.output_root_input.text().strip()
        if not output_root:
            self.validation_status.setText("Simulation output directory is required.")
            return
        self.simulation_log.clear()
        self.simulation_progress.setValue(0)
        self.worker = BlueprintSimulationWorker(
            self.blueprint,
            self.configuration(),
            output_root,
            self.honor_delay_checkbox.isChecked(),
            parent=self,
        )
        self.worker.progress.connect(self._show_progress)
        self.worker.completed.connect(self._simulation_completed)
        self.worker.failed.connect(self._simulation_failed)
        self.worker.aborted.connect(self._simulation_aborted)
        self.worker.finished.connect(self._simulation_finished)
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.abort_button.setEnabled(True)
        self.worker.start()

    def pause_simulation(self):
        if self.worker is None:
            return
        self.worker.control.pause()
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(True)
        self.simulation_log.appendPlainText("Pause requested...")

    def resume_simulation(self):
        if self.worker is None:
            return
        self.worker.control.resume()
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)
        self.simulation_log.appendPlainText("Simulation resumed.")

    def abort_simulation(self):
        if self.worker is None:
            return
        self.worker.control.abort()
        self.abort_button.setEnabled(False)
        self.simulation_log.appendPlainText("Abort requested...")

    def _show_progress(self, message, completed, total):
        percent = int((completed / total) * 100) if total else 0
        self.simulation_progress.setValue(max(0, min(100, percent)))
        self.simulation_log.appendPlainText(message)

    def _simulation_completed(self, result):
        self.simulation_progress.setValue(100)
        self.simulation_log.appendPlainText(
            f"Simulation completed: {len(result.rows)} point(s)."
        )
        self.simulation_log.appendPlainText(f"CSV: {result.csv_path}")

    def _simulation_failed(self, message):
        self.simulation_log.appendPlainText(f"Simulation failed: {message}")

    def _simulation_aborted(self, message):
        self.simulation_log.appendPlainText(message)

    def _simulation_finished(self):
        worker = self.worker
        self.worker = None
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.abort_button.setEnabled(False)
        if worker is not None:
            worker.deleteLater()


__all__ = ["BlueprintGeneratedGui", "BlueprintSimulationWorker"]
