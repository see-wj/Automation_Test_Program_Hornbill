"""Developer review UI for non-executable test integration blueprints."""

import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from analysis.integration_blueprint import create_integration_blueprint
from analysis.gui_scaffold_generator import (
    generate_gui_scaffold_source,
    suggested_scaffold_filename,
)
from ui.blueprint_generated_gui import BlueprintGeneratedGui


INSTRUMENT_ROLES = (
    "DUT/Hornbill",
    "DMM",
    "ELOAD",
    "OSCILLOSCOPE",
    "DAQ",
    "EXTERNALSOURCE",
    "UNKNOWN",
)


class IntegrationBlueprintReviewWidget(QWidget):
    """Collect explicit developer decisions before any code generation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.analysis = None
        self.blueprint = None
        self.role_selectors = {}
        self.parameter_controls = {}
        self.command_controls = []

        warning = QLabel(
            "Review only: generating a blueprint does not create or execute test code."
        )
        warning.setStyleSheet(
            "background: #fff3cd; color: #664d03; padding: 8px; font-weight: bold;"
        )
        warning.setWordWrap(True)

        self.review_tabs = QTabWidget()
        self.role_table = QTableWidget(0, 4)
        self.role_table.setHorizontalHeaderLabels(
            ("Variable", "Address", "Inferred Evidence", "Approved Role")
        )
        self.role_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.role_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        self.parameter_table = QTableWidget(0, 5)
        self.parameter_table.setHorizontalHeaderLabels(
            ("GUI", "Name", "Type", "Prompt", "Default")
        )
        self.parameter_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.parameter_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch
        )

        roles_parameters_page = QWidget()
        roles_parameters_layout = QVBoxLayout(roles_parameters_page)
        roles_parameters_layout.addWidget(QLabel("Instrument Role Review"))
        roles_parameters_layout.addWidget(self.role_table)
        roles_parameters_layout.addWidget(QLabel("GUI Parameter Review"))
        roles_parameters_layout.addWidget(self.parameter_table)

        self.command_table = QTableWidget(0, 6)
        self.command_table.setHorizontalHeaderLabels(
            ("Approved", "Line", "Receiver", "Operation", "SCPI Command", "Mapping")
        )
        self.command_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.command_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.Stretch
        )
        command_page = QWidget()
        command_layout = QVBoxLayout(command_page)
        approve_suggestions_button = QPushButton("Approve All Suggested Mappings")
        approve_suggestions_button.clicked.connect(self.approve_suggested_mappings)
        command_layout.addWidget(approve_suggestions_button)
        command_layout.addWidget(self.command_table)

        safety_page = QWidget()
        safety_layout = QVBoxLayout(safety_page)
        identity_group = QGroupBox("Blueprint Identity")
        identity_form = QFormLayout(identity_group)
        self.test_name_input = QLineEdit()
        identity_form.addRow("Test Name:", self.test_name_input)

        safety_group = QGroupBox("Safety and Execution Controls")
        safety_form = QFormLayout(safety_group)
        self.maximum_voltage_input = QLineEdit()
        self.maximum_current_input = QLineEdit()
        self.maximum_power_input = QLineEdit()
        self.polling_timeout_input = QDoubleSpinBox()
        self.polling_timeout_input.setRange(0.1, 3600.0)
        self.polling_timeout_input.setValue(30.0)
        self.polling_timeout_input.setSuffix(" s")
        self.settling_delay_input = QDoubleSpinBox()
        self.settling_delay_input.setRange(0.0, 3600.0)
        self.settling_delay_input.setValue(1.0)
        self.settling_delay_input.setSuffix(" s")
        self.checkpoint_checkbox = QCheckBox("Pause/abort checkpoint at every point")
        self.checkpoint_checkbox.setChecked(True)
        self.shutdown_checkbox = QCheckBox("Guaranteed shutdown in finally/cleanup")
        self.shutdown_checkbox.setChecked(True)
        self.safety_confirmed_checkbox = QCheckBox(
            "I reviewed these limits against the physical setup"
        )
        inferred_limit_note = QLabel(
            "Prefilled voltage/current values come from source sweep stop values "
            "and may be exclusive endpoints. Replace them with verified hardware "
            "limits before confirming."
        )
        inferred_limit_note.setWordWrap(True)
        inferred_limit_note.setStyleSheet("color: #b02a37;")
        safety_form.addRow("Maximum Voltage:", self.maximum_voltage_input)
        safety_form.addRow("Maximum Current:", self.maximum_current_input)
        safety_form.addRow("Maximum Power:", self.maximum_power_input)
        safety_form.addRow("Polling Timeout:", self.polling_timeout_input)
        safety_form.addRow("Settling Delay:", self.settling_delay_input)
        safety_form.addRow(self.checkpoint_checkbox)
        safety_form.addRow(self.shutdown_checkbox)
        safety_form.addRow(self.safety_confirmed_checkbox)
        safety_form.addRow(inferred_limit_note)

        action_layout = QHBoxLayout()
        self.generate_button = QPushButton("Generate Reviewed Blueprint")
        self.generate_button.clicked.connect(self.generate_blueprint)
        self.save_button = QPushButton("Save Blueprint JSON")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_blueprint)
        action_layout.addWidget(self.generate_button)
        action_layout.addWidget(self.save_button)

        self.blueprint_status = QLabel("Analyze a script to begin review.")
        self.blueprint_preview = QPlainTextEdit()
        self.blueprint_preview.setReadOnly(True)
        safety_layout.addWidget(identity_group)
        safety_layout.addWidget(safety_group)
        safety_layout.addLayout(action_layout)
        safety_layout.addWidget(self.blueprint_status)
        safety_layout.addWidget(self.blueprint_preview, 1)

        generated_page = QWidget()
        generated_layout = QVBoxLayout(generated_page)
        self.generated_gui_status = QLabel(
            "Approve a blueprint to generate its simulation-only GUI."
        )
        self.generated_gui_status.setWordWrap(True)
        self.export_gui_button = QPushButton("Export Simulation GUI Scaffold")
        self.export_gui_button.setEnabled(False)
        self.export_gui_button.clicked.connect(self.export_gui_scaffold)
        self.generated_gui_container = QVBoxLayout()
        generated_layout.addWidget(self.generated_gui_status)
        generated_layout.addWidget(self.export_gui_button)
        generated_layout.addLayout(self.generated_gui_container, 1)
        self.generated_gui_preview = None

        self.review_tabs.addTab(roles_parameters_page, "Roles and Parameters")
        self.review_tabs.addTab(command_page, "Command Approval")
        self.review_tabs.addTab(safety_page, "Safety and Blueprint")
        self.review_tabs.addTab(generated_page, "Generated GUI")

        layout = QVBoxLayout(self)
        layout.addWidget(warning)
        layout.addWidget(self.review_tabs, 1)

    def set_analysis(self, analysis):
        self.analysis = analysis
        self.blueprint = None
        self.save_button.setEnabled(False)
        self._clear_generated_gui()
        self.test_name_input.setText(Path(analysis.source_path).stem)
        self._populate_roles(analysis)
        self._populate_parameters(analysis)
        self._populate_commands(analysis)
        self._populate_safety_suggestions(analysis)
        self.blueprint_status.setText(
            "Review roles, mappings, parameters, and safety limits."
        )
        self.blueprint_preview.clear()

    def _populate_roles(self, analysis):
        self.role_selectors.clear()
        self.role_table.setRowCount(len(analysis.instrument_roles))
        for row, finding in enumerate(analysis.instrument_roles):
            for column, value in enumerate(
                (finding.variable, finding.address, finding.evidence)
            ):
                self.role_table.setItem(row, column, QTableWidgetItem(str(value)))
            selector = QComboBox()
            selector.addItems(INSTRUMENT_ROLES)
            index = selector.findText(finding.role)
            selector.setCurrentIndex(index if index >= 0 else selector.findText("UNKNOWN"))
            self.role_table.setCellWidget(row, 3, selector)
            self.role_selectors[finding.variable] = selector

    def _populate_parameters(self, analysis):
        self.parameter_controls.clear()
        self.parameter_table.setRowCount(len(analysis.parameters))
        for row, finding in enumerate(analysis.parameters):
            include_checkbox = QCheckBox()
            include_checkbox.setChecked(True)
            default_input = QLineEdit()
            self.parameter_table.setCellWidget(row, 0, include_checkbox)
            self.parameter_table.setItem(row, 1, QTableWidgetItem(finding.name))
            self.parameter_table.setItem(row, 2, QTableWidgetItem(finding.conversion))
            self.parameter_table.setItem(row, 3, QTableWidgetItem(finding.prompt))
            self.parameter_table.setCellWidget(row, 4, default_input)
            self.parameter_controls[finding.name] = (
                include_checkbox,
                default_input,
            )

    def _populate_commands(self, analysis):
        self.command_controls = []
        self.command_table.setRowCount(len(analysis.commands))
        role_by_receiver = {
            finding.variable: finding.role for finding in analysis.instrument_roles
        }
        for row, finding in enumerate(analysis.commands):
            approved_checkbox = QCheckBox()
            mapping_selector = QComboBox()
            mapping_selector.setEditable(True)
            mapping_selector.addItem("")
            mapping_selector.addItems(finding.mappings)
            if finding.mappings:
                mapping_selector.setCurrentText(finding.mappings[0])
            self.command_table.setCellWidget(row, 0, approved_checkbox)
            values = (
                finding.line,
                f"{finding.receiver} ({role_by_receiver.get(finding.receiver, 'UNKNOWN')})",
                finding.operation,
                finding.command,
            )
            for column, value in enumerate(values, 1):
                self.command_table.setItem(row, column, QTableWidgetItem(str(value)))
            self.command_table.setCellWidget(row, 5, mapping_selector)
            self.command_controls.append((approved_checkbox, mapping_selector))

    def _populate_safety_suggestions(self, analysis):
        maximum_power = next(
            (
                finding.expression
                for finding in analysis.safety_limits
                if "power" in finding.name.lower()
            ),
            "",
        )
        maximum_voltage = ""
        maximum_current = ""
        for sweep in analysis.sweeps:
            normalized = f"{sweep.name} {sweep.start} {sweep.stop} {sweep.step}".lower()
            if "curr" in normalized:
                maximum_current = sweep.stop
            elif "volt" in normalized or "sweep_values" in normalized:
                maximum_voltage = sweep.stop
        numeric_delays = []
        for finding in analysis.delays:
            try:
                numeric_delays.append(float(finding.expression))
            except ValueError:
                continue
        self.maximum_voltage_input.setText(maximum_voltage)
        self.maximum_current_input.setText(maximum_current)
        self.maximum_power_input.setText(maximum_power)
        if numeric_delays:
            self.settling_delay_input.setValue(max(numeric_delays))
        self.safety_confirmed_checkbox.setChecked(False)

    def approve_suggested_mappings(self):
        for approved_checkbox, mapping_selector in self.command_controls:
            if mapping_selector.currentText().strip():
                approved_checkbox.setChecked(True)

    def generate_blueprint(self):
        if self.analysis is None:
            return None
        role_settings = {
            variable: selector.currentText()
            for variable, selector in self.role_selectors.items()
        }
        parameter_settings = {
            name: {
                "include_in_gui": include_checkbox.isChecked(),
                "default": default_input.text().strip(),
            }
            for name, (include_checkbox, default_input) in self.parameter_controls.items()
        }
        command_settings = {
            index: {
                "approved": approved_checkbox.isChecked(),
                "selected_mapping": mapping_selector.currentText().strip(),
            }
            for index, (approved_checkbox, mapping_selector) in enumerate(
                self.command_controls
            )
        }
        safety_settings = {
            "maximum_voltage": self.maximum_voltage_input.text().strip(),
            "maximum_current": self.maximum_current_input.text().strip(),
            "maximum_power": self.maximum_power_input.text().strip(),
            "polling_timeout_seconds": self.polling_timeout_input.value(),
            "settling_delay_seconds": self.settling_delay_input.value(),
            "checkpoint_each_point": self.checkpoint_checkbox.isChecked(),
            "guaranteed_shutdown": self.shutdown_checkbox.isChecked(),
            "confirmed_by_developer": self.safety_confirmed_checkbox.isChecked(),
        }
        self.blueprint = create_integration_blueprint(
            self.analysis,
            test_name=self.test_name_input.text(),
            instrument_roles=role_settings,
            parameter_settings=parameter_settings,
            command_settings=command_settings,
            safety_settings=safety_settings,
        )
        self.blueprint_preview.setPlainText(
            json.dumps(self.blueprint.to_dict(), indent=2)
        )
        if self.blueprint.status == "approved":
            self.blueprint_status.setText(
                "APPROVED blueprint - simulation GUI generated for review."
            )
            self.blueprint_status.setStyleSheet("color: #146c43; font-weight: bold;")
            self._show_generated_gui()
        else:
            self.blueprint_status.setText(
                "REVIEW REQUIRED: " + " | ".join(self.blueprint.review_issues)
            )
            self.blueprint_status.setStyleSheet("color: #b02a37; font-weight: bold;")
            self._clear_generated_gui()
        self.save_button.setEnabled(True)
        return self.blueprint

    def save_blueprint(self):
        if self.blueprint is None:
            return
        default_path = str(
            Path(self.analysis.source_path).with_suffix(".blueprint.json")
        )
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Integration Blueprint",
            default_path,
            "JSON Files (*.json)",
        )
        if not output_path:
            return
        Path(output_path).write_text(
            json.dumps(self.blueprint.to_dict(), indent=2),
            encoding="utf-8",
        )
        self.blueprint_status.setText(
            f"{self.blueprint.status.upper()} blueprint saved to {output_path}"
        )

    def _show_generated_gui(self):
        self._clear_generated_gui()
        self.generated_gui_preview = BlueprintGeneratedGui(self.blueprint)
        self.generated_gui_container.addWidget(self.generated_gui_preview)
        self.generated_gui_status.setText(
            "Generated automatically from approved instruments, parameters, safety "
            "limits, and command mappings. Hardware execution remains disabled."
        )
        self.generated_gui_status.setStyleSheet(
            "color: #146c43; font-weight: bold;"
        )
        self.export_gui_button.setEnabled(True)

    def _clear_generated_gui(self):
        if self.generated_gui_preview is not None:
            self.generated_gui_container.removeWidget(self.generated_gui_preview)
            self.generated_gui_preview.deleteLater()
            self.generated_gui_preview = None
        self.export_gui_button.setEnabled(False)
        self.generated_gui_status.setText(
            "Approve a blueprint to generate its simulation-only GUI."
        )
        self.generated_gui_status.setStyleSheet("")

    def export_gui_scaffold(self):
        if self.blueprint is None or self.blueprint.status != "approved":
            return
        default_path = Path(__file__).resolve().parents[1] / "instruments" / (
            suggested_scaffold_filename(self.blueprint.test_name)
        )
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Simulation GUI Scaffold",
            str(default_path),
            "Python Scripts (*.py)",
        )
        if not output_path:
            return
        Path(output_path).write_text(
            generate_gui_scaffold_source(self.blueprint),
            encoding="utf-8",
        )
        self.generated_gui_status.setText(
            f"Simulation-only GUI scaffold exported to {output_path}"
        )


__all__ = ["INSTRUMENT_ROLES", "IntegrationBlueprintReviewWidget"]
