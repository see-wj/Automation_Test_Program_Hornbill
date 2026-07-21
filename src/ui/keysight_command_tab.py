"""Developer tab for previewing and executing Keysight library methods."""

import ast
import inspect
import traceback
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import SCPI_Library.Keysight as keysight_library
from SCPI_Library.simulation import create_resource_manager
from common.path import config_folder


class RecordingInstrument:
    """Minimal VISA-like object used to preview generated commands."""

    def __init__(self):
        self.commands = []

    def write(self, command):
        self.commands.append(("write", str(command)))
        return len(str(command))

    def query(self, command):
        self.commands.append(("query", str(command)))
        return "0"

    def read(self):
        self.commands.append(("read", ""))
        return "0"

    def query_ascii_values(self, command, *args, **kwargs):
        self.commands.append(("query_ascii_values", str(command)))
        return [0.0]

    def query_binary_values(self, command, *args, **kwargs):
        self.commands.append(("query_binary_values", str(command)))
        return [0.0]

    def write_ascii_values(self, command, values, *args, **kwargs):
        payload = ",".join(str(value) for value in values)
        return self.write(f"{command} {payload}")

    def write_binary_values(self, command, values, *args, **kwargs):
        return self.write_ascii_values(command, values, *args, **kwargs)


def keysight_classes():
    classes = {}
    for name, value in inspect.getmembers(keysight_library, inspect.isclass):
        if (
            value.__module__ == keysight_library.__name__
            and name != "Subsystem"
        ):
            methods = public_methods(value)
            if methods:
                classes[name] = value
    return classes


def public_methods(instrument_class):
    return {
        name: value
        for name, value in instrument_class.__dict__.items()
        if inspect.isfunction(value) and not name.startswith("_")
    }


def parse_argument(text):
    value = text.strip()
    if not value:
        return ""
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value


def invoke_with_instrument(instrument_class, method_name, instrument, arguments):
    instance = instrument_class.__new__(instrument_class)
    instance.instr = instrument
    return getattr(instance, method_name)(*arguments)


def suggested_argument(parameter):
    if parameter.default is not inspect.Parameter.empty:
        return parameter.default

    name = parameter.name.lower()
    if "channel" in name:
        return 1
    if "sample" in name or "point" in name:
        return 100000
    if "state" in name:
        return "OFF"
    if "mode" in name:
        return "VOLT"
    if "condition" in name:
        return "MIN"
    if "range" in name:
        return "AUTO"
    if "terminal" in name:
        return "FRONT"
    if "source" in name:
        return "BUS"
    if "slope" in name:
        return "POS"
    if "coupling" in name:
        return "DC"
    if "time" in name or "delay" in name or "seconds" in name:
        return 0.1
    if any(
        token in name
        for token in (
            "value",
            "voltage",
            "current",
            "power",
            "frequency",
            "count",
            "level",
            "offset",
            "size",
        )
    ):
        return 1
    return "TEST"


def suggested_arguments(method):
    arguments = []
    for parameter in list(inspect.signature(method).parameters.values())[1:]:
        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue
        arguments.append(suggested_argument(parameter))
    return arguments


def preview_method(instrument_class, method_name, arguments):
    recorder = RecordingInstrument()
    result = invoke_with_instrument(
        instrument_class,
        method_name,
        recorder,
        arguments,
    )
    query_instrument_error(recorder, instrument_class)
    return recorder.commands, result


def format_method_result(result):
    if result is None:
        return "Command sent successfully (write-only; no instrument response expected)."
    return f"Result: {result!r}"


def error_query_for(instrument_class):
    return getattr(instrument_class, "ERROR_QUERY", "SYST:ERR?")


def query_instrument_error(instrument, instrument_class=None):
    error_query = error_query_for(instrument_class)
    response = instrument.query(error_query)
    if isinstance(response, bytes):
        response = response.decode("ascii", errors="replace")
    response = str(response).strip()
    error_code = response.split(",", 1)[0].strip()
    try:
        has_error = float(error_code) != 0
    except ValueError as exception:
        raise RuntimeError(
            f"Unrecognized {error_query} response: {response!r}"
        ) from exception
    if has_error:
        raise RuntimeError(f"Instrument error: {response}")
    return response


def query_system_error(instrument):
    return query_instrument_error(instrument)


def format_checked_result(result, instrument_error, error_query="SYST:ERR?"):
    return f"{format_method_result(result)}\n{error_query}: {instrument_error}"


class KeysightCommandWorker(QThread):
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, instrument_class, method_name, address, arguments, parent=None):
        super().__init__(parent)
        self.instrument_class = instrument_class
        self.method_name = method_name
        self.address = address
        self.arguments = arguments

    def run(self):
        instrument = None
        try:
            instance = self.instrument_class(self.address)
            instrument = instance.instr
            result = getattr(instance, self.method_name)(*self.arguments)
            error_query = error_query_for(self.instrument_class)
            instrument_error = query_instrument_error(
                instrument,
                self.instrument_class,
            )
            self.completed.emit(
                format_checked_result(result, instrument_error, error_query)
            )
        except Exception:
            self.failed.emit(traceback.format_exc())
        finally:
            if instrument is not None:
                try:
                    instrument.close()
                except Exception:
                    pass


class KeysightQueryBatchWorker(QThread):
    command_completed = pyqtSignal(str, str)
    command_failed = pyqtSignal(str, str)
    batch_completed = pyqtSignal(str)

    def __init__(self, instrument_class, address, jobs, parent=None):
        super().__init__(parent)
        self.instrument_class = instrument_class
        self.address = address
        self.jobs = jobs

    def run(self):
        instrument = None
        passed = 0
        failed = 0
        try:
            instance = self.instrument_class(self.address)
            instrument = instance.instr
            for method_name, arguments in self.jobs:
                try:
                    result = getattr(instance, method_name)(*arguments)
                    error_query = error_query_for(self.instrument_class)
                    instrument_error = query_instrument_error(
                        instrument,
                        self.instrument_class,
                    )
                    passed += 1
                    self.command_completed.emit(
                        method_name,
                        format_checked_result(result, instrument_error, error_query),
                    )
                except Exception:
                    failed += 1
                    self.command_failed.emit(method_name, traceback.format_exc())
            self.batch_completed.emit(
                f"Automatic query test finished: {passed} passed, {failed} failed."
            )
        except Exception:
            self.batch_completed.emit(traceback.format_exc())
        finally:
            if instrument is not None:
                try:
                    instrument.close()
                except Exception:
                    pass


class KeysightCommandTab(QWidget):
    PREVIEW_MODE = "Preview only (no hardware)"
    EXECUTE_MODE = "Execute on instrument"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.instrument_classes = keysight_classes()
        self.argument_inputs = []
        self.command_previews = {}
        self.worker = None
        self._build_ui()
        self._populate_addresses()
        self._class_changed(self.class_combo.currentText())

    def _build_ui(self):
        title = QLabel("Keysight.py Command Checker")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #17365d;")
        description = QLabel(
            "Choose a class to automatically generate its complete command catalog. "
            "Select any row to edit example arguments, preview it again, or test it "
            "on a connected instrument. Automatic catalog generation never contacts hardware."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #475569; padding-bottom: 6px;")

        catalog_group = QGroupBox("Automatic Command Catalog")
        catalog_layout = QVBoxLayout(catalog_group)
        catalog_controls = QHBoxLayout()
        self.class_combo = QComboBox()
        self.class_combo.addItems(sorted(self.instrument_classes))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter methods or SCPI commands...")
        self.preview_all_button = QPushButton("Regenerate All")
        catalog_controls.addWidget(QLabel("Keysight Class:"))
        catalog_controls.addWidget(self.class_combo, 1)
        catalog_controls.addWidget(self.search_input, 2)
        catalog_controls.addWidget(self.preview_all_button)
        self.catalog_summary = QLabel()
        self.catalog_summary.setStyleSheet("color: #0f766e; font-weight: bold;")
        self.command_table = QTableWidget(0, 4)
        self.command_table.setHorizontalHeaderLabels(
            ["Method", "Signature", "Generated SCPI / VISA Operation", "Status"]
        )
        self.command_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.command_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.command_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.command_table.setAlternatingRowColors(True)
        self.command_table.verticalHeader().setVisible(False)
        header = self.command_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        catalog_layout.addLayout(catalog_controls)
        catalog_layout.addWidget(self.catalog_summary)
        catalog_layout.addWidget(self.command_table)

        detail_group = QGroupBox("Selected Command Test")
        detail_layout = QVBoxLayout(detail_group)
        connection_layout = QFormLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([self.PREVIEW_MODE, self.EXECUTE_MODE])
        self.address_combo = QComboBox()
        self.address_combo.setEditable(True)
        self.refresh_button = QPushButton("Refresh VISA Addresses")
        address_layout = QHBoxLayout()
        address_layout.addWidget(self.address_combo)
        address_layout.addWidget(self.refresh_button)
        self.method_combo = QComboBox()
        self.method_combo.setVisible(False)
        connection_layout.addRow("Mode:", self.mode_combo)
        connection_layout.addRow("VISA Address:", address_layout)

        self.signature_label = QLabel()
        self.signature_label.setWordWrap(True)
        self.signature_label.setStyleSheet(
            "background: #eaf2f8; border: 1px solid #b8cce4; "
            "padding: 8px; font-family: Consolas;"
        )
        self.arguments_group = QGroupBox("Method Arguments")
        self.arguments_layout = QFormLayout(self.arguments_group)

        self.safety_checkbox = QCheckBox(
            "I understand this method may change instrument output or settings."
        )
        self.safety_checkbox.setStyleSheet("color: #b91c1c; font-weight: bold;")
        self.safety_checkbox.setVisible(False)
        self.run_button = QPushButton("Preview Command")
        self.run_button.setStyleSheet(
            "QPushButton { background: #2563eb; color: white; padding: 8px; "
            "font-weight: bold; border-radius: 4px; }"
            "QPushButton:disabled { background: #94a3b8; }"
        )
        self.clear_button = QPushButton("Clear Log")
        self.auto_test_button = QPushButton("Auto-Test Query Commands")
        self.auto_test_button.setEnabled(False)
        self.auto_test_button.setToolTip(
            "Runs only methods whose automatic preview contains query/read operations "
            "and no write operation."
        )
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.auto_test_button)
        button_layout.addWidget(self.clear_button)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Selected command results appear here.")
        self.output.setStyleSheet(
            "background: #0f172a; color: #d1fae5; font-family: Consolas; "
            "border-radius: 4px; padding: 6px;"
        )

        detail_layout.addLayout(connection_layout)
        detail_layout.addWidget(self.signature_label)
        detail_layout.addWidget(self.arguments_group)
        detail_layout.addWidget(self.safety_checkbox)
        detail_layout.addLayout(button_layout)
        detail_layout.addWidget(self.output)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(catalog_group)
        splitter.addWidget(detail_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([650, 450])

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(splitter, 1)

        self.class_combo.currentTextChanged.connect(self._class_changed)
        self.method_combo.currentTextChanged.connect(self._method_changed)
        self.command_table.itemSelectionChanged.connect(self._catalog_selection_changed)
        self.search_input.textChanged.connect(self._filter_catalog)
        self.preview_all_button.clicked.connect(self.generate_command_catalog)
        self.mode_combo.currentTextChanged.connect(self._mode_changed)
        self.refresh_button.clicked.connect(self.refresh_addresses)
        self.run_button.clicked.connect(self.run_selected_method)
        self.auto_test_button.clicked.connect(self.run_query_catalog)
        self.clear_button.clicked.connect(self.output.clear)

    def _populate_addresses(self):
        addresses = []
        for path in sorted(Path(config_folder).glob("config_*.txt")):
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith(("#", "//")) or "=" not in line:
                    continue
                key, value = (part.strip() for part in line.split("=", 1))
                if key in {"PSU", "DMM", "DMM2", "ELoad", "OSC", "ACSource"}:
                    if value and value not in addresses:
                        addresses.append(value)
        self.address_combo.addItems(addresses)

    def refresh_addresses(self):
        manager = None
        try:
            manager = create_resource_manager()
            addresses = manager.list_resources()
            existing = {
                self.address_combo.itemText(index)
                for index in range(self.address_combo.count())
            }
            for address in addresses:
                if address not in existing:
                    self.address_combo.addItem(address)
            self.output.appendPlainText(
                f"Found {len(addresses)} VISA resource(s)."
            )
        except Exception:
            self.output.appendPlainText(traceback.format_exc())
        finally:
            if manager is not None:
                try:
                    manager.close()
                except Exception:
                    pass

    def _class_changed(self, class_name):
        self.method_combo.clear()
        instrument_class = self.instrument_classes.get(class_name)
        if instrument_class is not None:
            self.method_combo.addItems(sorted(public_methods(instrument_class)))
        self.generate_command_catalog()

    def generate_command_catalog(self):
        instrument_class = self.instrument_classes.get(self.class_combo.currentText())
        methods = public_methods(instrument_class) if instrument_class else {}
        self.command_previews = {}
        self.command_table.setRowCount(len(methods))

        ready_count = 0
        for row, (method_name, method) in enumerate(sorted(methods.items())):
            signature = inspect.signature(method)
            arguments = suggested_arguments(method)
            try:
                commands, result = preview_method(
                    instrument_class,
                    method_name,
                    arguments,
                )
                command_text = "\n".join(
                    f"{operation.upper()}: {command}" if command else operation.upper()
                    for operation, command in commands
                ) or "No VISA command generated"
                status = "Ready"
                ready_count += 1
                error = None
            except Exception as exception:
                commands = []
                result = None
                command_text = str(exception)
                status = "Needs input"
                error = traceback.format_exc()

            self.command_previews[method_name] = {
                "arguments": arguments,
                "commands": commands,
                "result": result,
                "error": error,
            }
            method_item = QTableWidgetItem(method_name)
            method_item.setData(Qt.UserRole, method_name)
            self.command_table.setItem(row, 0, method_item)
            self.command_table.setItem(row, 1, QTableWidgetItem(str(signature)))
            self.command_table.setItem(row, 2, QTableWidgetItem(command_text))
            self.command_table.setItem(row, 3, QTableWidgetItem(status))

        self.catalog_summary.setText(
            f"{len(methods)} methods loaded automatically | "
            f"{ready_count} previews ready | {len(methods) - ready_count} need review"
        )
        self._filter_catalog(self.search_input.text())
        if self.command_table.rowCount():
            self.command_table.selectRow(0)

    def _catalog_selection_changed(self):
        selected_rows = self.command_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        method_item = self.command_table.item(selected_rows[0].row(), 0)
        if method_item is not None:
            self.method_combo.setCurrentText(method_item.data(Qt.UserRole))

    def _filter_catalog(self, text):
        search_text = text.strip().lower()
        visible_count = 0
        for row in range(self.command_table.rowCount()):
            row_text = " ".join(
                self.command_table.item(row, column).text()
                for column in range(self.command_table.columnCount())
                if self.command_table.item(row, column) is not None
            ).lower()
            hidden = bool(search_text and search_text not in row_text)
            self.command_table.setRowHidden(row, hidden)
            if not hidden:
                visible_count += 1
        if search_text:
            self.catalog_summary.setText(
                f"Showing {visible_count} matching command(s)"
            )

    def _method_changed(self, method_name):
        while self.arguments_layout.rowCount():
            self.arguments_layout.removeRow(0)
        self.argument_inputs = []
        instrument_class = self.instrument_classes.get(self.class_combo.currentText())
        method = public_methods(instrument_class).get(method_name) if instrument_class else None
        if method is None:
            self.signature_label.clear()
            return

        signature = inspect.signature(method)
        self.signature_label.setText(
            f"{instrument_class.__name__}.{method_name}{signature}"
        )
        for parameter in list(signature.parameters.values())[1:]:
            input_widget = QLineEdit()
            if parameter.kind in {
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            }:
                input_widget.setPlaceholderText("Optional")
            else:
                input_widget.setText(repr(suggested_argument(parameter)))
            self.arguments_layout.addRow(f"{parameter.name}:", input_widget)
            self.argument_inputs.append((parameter, input_widget))

        preview = self.command_previews.get(method_name)
        if preview is not None:
            self.output.clear()
            self.output.appendPlainText(
                f"AUTO PREVIEW: {instrument_class.__name__}.{method_name}"
            )
            for operation, command in preview["commands"]:
                suffix = f": {command}" if command else ""
                self.output.appendPlainText(f"{operation.upper()}{suffix}")
            if preview["error"]:
                self.output.appendPlainText(preview["error"])

    def _mode_changed(self, mode):
        execute_mode = mode == self.EXECUTE_MODE
        self.safety_checkbox.setVisible(execute_mode)
        self.safety_checkbox.setChecked(False)
        self.auto_test_button.setEnabled(execute_mode)
        self.run_button.setText("Execute Method" if execute_mode else "Preview Command")

    def _arguments(self):
        arguments = []
        for parameter, input_widget in self.argument_inputs:
            text = input_widget.text().strip()
            if not text and parameter.default is not inspect.Parameter.empty:
                arguments.append(parameter.default)
            elif not text and parameter.kind == inspect.Parameter.VAR_POSITIONAL:
                continue
            elif not text:
                raise ValueError(f"Missing required argument: {parameter.name}")
            elif parameter.kind == inspect.Parameter.VAR_POSITIONAL:
                parsed = parse_argument(text)
                if not isinstance(parsed, (list, tuple)):
                    raise ValueError(
                        f"{parameter.name} must be entered as a list or tuple"
                    )
                arguments.extend(parsed)
            else:
                arguments.append(parse_argument(text))
        return arguments

    def run_selected_method(self):
        try:
            arguments = self._arguments()
        except ValueError as exception:
            QMessageBox.warning(self, "Invalid Arguments", str(exception))
            return

        instrument_class = self.instrument_classes[self.class_combo.currentText()]
        method_name = self.method_combo.currentText()
        self.output.appendPlainText(
            f"\n{instrument_class.__name__}.{method_name}({', '.join(map(repr, arguments))})"
        )

        if self.mode_combo.currentText() == self.PREVIEW_MODE:
            self._preview(instrument_class, method_name, arguments)
            return

        address = self.address_combo.currentText().strip()
        if not address:
            QMessageBox.warning(self, "Missing Address", "Enter a VISA address.")
            return
        if not self.safety_checkbox.isChecked():
            QMessageBox.warning(
                self,
                "Safety Acknowledgement Required",
                "Confirm the hardware safety acknowledgement before execution.",
            )
            return

        self._set_running(True)
        self.worker = KeysightCommandWorker(
            instrument_class,
            method_name,
            address,
            arguments,
            self,
        )
        self.worker.completed.connect(self._execution_completed)
        self.worker.failed.connect(self._execution_failed)
        self.worker.finished.connect(lambda: self._set_running(False))
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def run_query_catalog(self):
        address = self.address_combo.currentText().strip()
        if not address:
            QMessageBox.warning(self, "Missing Address", "Enter a VISA address.")
            return
        if not self.safety_checkbox.isChecked():
            QMessageBox.warning(
                self,
                "Safety Acknowledgement Required",
                "Confirm the hardware safety acknowledgement before automatic testing.",
            )
            return

        jobs = self.query_catalog_jobs()

        if not jobs:
            QMessageBox.information(
                self,
                "No Query Commands",
                "This class has no automatically testable query-only commands.",
            )
            return

        self.output.appendPlainText(
            f"\nAUTO TEST: {len(jobs)} query-only method(s) on {address}"
        )
        self._set_running(True)
        instrument_class = self.instrument_classes[self.class_combo.currentText()]
        self.worker = KeysightQueryBatchWorker(
            instrument_class,
            address,
            jobs,
            self,
        )
        self.worker.command_completed.connect(self._batch_command_completed)
        self.worker.command_failed.connect(self._batch_command_failed)
        self.worker.batch_completed.connect(self.output.appendPlainText)
        self.worker.finished.connect(lambda: self._set_running(False))
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def query_catalog_jobs(self):
        query_operations = {
            "query",
            "read",
            "query_ascii_values",
            "query_binary_values",
        }
        jobs = []
        for method_name, preview in self.command_previews.items():
            operations = [operation for operation, _ in preview["commands"]]
            if operations and all(operation in query_operations for operation in operations):
                jobs.append((method_name, preview["arguments"]))
        return jobs

    def _preview(self, instrument_class, method_name, arguments):
        try:
            commands, result = preview_method(
                instrument_class,
                method_name,
                arguments,
            )
            if commands:
                for operation, command in commands:
                    self.output.appendPlainText(f"{operation.upper()}: {command}")
            else:
                self.output.appendPlainText("No VISA command was generated.")
            if result is not None:
                self.output.appendPlainText(f"Preview result: {result!r}")
        except Exception:
            self.output.appendPlainText(traceback.format_exc())

    def _set_running(self, running):
        for widget in (
            self.mode_combo,
            self.address_combo,
            self.refresh_button,
            self.class_combo,
            self.method_combo,
            self.command_table,
            self.search_input,
            self.preview_all_button,
            self.run_button,
            self.auto_test_button,
        ):
            widget.setEnabled(not running)
        if not running:
            self.auto_test_button.setEnabled(
                self.mode_combo.currentText() == self.EXECUTE_MODE
            )

    def _execution_completed(self, message):
        self.output.appendPlainText(message)

    def _execution_failed(self, message):
        self.output.appendPlainText(message)

    def _batch_command_completed(self, method_name, result):
        self._set_catalog_status(method_name, "Passed")
        self.output.appendPlainText(f"PASS {method_name}: {result}")

    def _batch_command_failed(self, method_name, message):
        self._set_catalog_status(method_name, "Failed")
        self.output.appendPlainText(f"FAIL {method_name}\n{message}")

    def _set_catalog_status(self, method_name, status):
        for row in range(self.command_table.rowCount()):
            if self.command_table.item(row, 0).text() == method_name:
                self.command_table.item(row, 3).setText(status)
                return
