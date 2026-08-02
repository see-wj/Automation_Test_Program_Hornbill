"""Standalone DAQ973A temperature measurement dialog."""

import threading
import time
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from common.path import config_folder, csv_folder
from configuration.configuration_service import (
    configuration_path,
    load_configuration,
)
from External_Auxiliary_Equipment.Temperature_Measurement import (
    DEFAULT_CHANNEL_TYPES,
    TemperatureMeasurement,
    TemperatureSample,
    measure_temperature,
)


def parse_channel_types(text):
    """Parse comma-separated DAQ channel/type pairs such as ``101:T``."""
    channel_types = {}
    for item in str(text).split(","):
        item = item.strip()
        if not item:
            continue
        try:
            channel_text, thermocouple_type = item.split(":", 1)
            channel = int(channel_text.strip())
        except (TypeError, ValueError) as exception:
            raise ValueError(
                "Channels must use the format 101:T, 103:T, 104:E"
            ) from exception
        thermocouple_type = thermocouple_type.strip().upper()
        if not thermocouple_type:
            raise ValueError(f"Thermocouple type is missing for channel {channel}")
        channel_types[channel] = thermocouple_type
    if not channel_types:
        raise ValueError("At least one DAQ channel is required")
    return channel_types


def default_daq_address():
    try:
        values = load_configuration(
            configuration_path(config_folder, "Hornbill")
        )
    except OSError:
        return ""
    return values.get("DAQ", "").strip()


class TemperatureMeasurementWorker(QThread):
    sample_ready = pyqtSignal(object, int, float)
    failed = pyqtSignal(str)

    def __init__(
        self,
        visa_address,
        channel_types,
        output_file,
        interval_seconds,
        duration_seconds=0,
        parent=None,
    ):
        super().__init__(parent)
        self.visa_address = visa_address
        self.channel_types = dict(channel_types)
        self.output_file = Path(output_file) if output_file else None
        self.interval_seconds = float(interval_seconds)
        self.duration_seconds = float(duration_seconds)
        self._stop_requested = threading.Event()

    def request_stop(self):
        self._stop_requested.set()

    def run(self):
        monitor = None
        try:
            monitor = TemperatureMeasurement(
                self.visa_address,
                channel_types=self.channel_types,
                output_file=self.output_file,
            )
            started_at = time.monotonic()
            sample_count = 0
            while not self._stop_requested.is_set():
                sample = monitor.measure(loop_index=sample_count)
                sample_count += 1
                elapsed_seconds = time.monotonic() - started_at
                self.sample_ready.emit(
                    sample,
                    sample_count,
                    elapsed_seconds,
                )
                if (
                    self.duration_seconds > 0
                    and elapsed_seconds >= self.duration_seconds
                ):
                    break

                wait_seconds = self.interval_seconds
                if self.duration_seconds > 0:
                    wait_seconds = min(
                        wait_seconds,
                        max(0, self.duration_seconds - elapsed_seconds),
                    )
                if self._stop_requested.wait(wait_seconds):
                    break
        except Exception as exception:
            self.failed.emit(str(exception))
        finally:
            if monitor is not None:
                try:
                    monitor.close()
                except Exception:
                    pass


class TemperatureMeasurementDialog(QDialog):
    """Configure a DAQ973A, acquire one scan, and optionally save it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.setWindowTitle("DAQ973A Temperature Measurement")
        self.resize(720, 480)

        self.address_input = QLineEdit(default_daq_address())
        self.address_input.setPlaceholderText("DAQ973A VISA address")
        self.channels_input = QLineEdit(
            ", ".join(
                f"{channel}:{thermocouple_type}"
                for channel, thermocouple_type in DEFAULT_CHANNEL_TYPES.items()
            )
        )
        self.channels_input.setToolTip(
            "Comma-separated DAQ channel and thermocouple type pairs"
        )
        self.output_input = QLineEdit(
            str(Path(csv_folder) / "temperature_measurements.csv")
        )
        self.interval_input = QDoubleSpinBox()
        self.interval_input.setRange(0.5, 3600.0)
        self.interval_input.setDecimals(1)
        self.interval_input.setValue(5.0)
        self.interval_input.setSuffix(" s")
        self.duration_input = QDoubleSpinBox()
        self.duration_input.setRange(0.0, 10080.0)
        self.duration_input.setDecimals(1)
        self.duration_input.setValue(0.0)
        self.duration_input.setSuffix(" min")
        self.duration_input.setSpecialValueText("Until stopped")
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.select_output_file)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(browse_button)

        form = QFormLayout()
        form.addRow("DAQ VISA Address:", self.address_input)
        form.addRow("Channels and Types:", self.channels_input)
        form.addRow("Recording Interval:", self.interval_input)
        form.addRow("Recording Duration:", self.duration_input)
        form.addRow("CSV Output:", output_layout)

        self.measure_button = QPushButton("Start Recording")
        self.measure_button.clicked.connect(self.start_measurement)
        self.stop_button = QPushButton("Stop Recording")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_measurement)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.measure_button)
        button_layout.addWidget(self.stop_button)
        self.status_label = QLabel("Ready")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(button_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_output)

    def select_output_file(self):
        selected_file, _ = QFileDialog.getSaveFileName(
            self,
            "Save Temperature Measurements",
            self.output_input.text().strip(),
            "CSV Files (*.csv)",
        )
        if selected_file:
            self.output_input.setText(selected_file)

    def start_measurement(self):
        if self.worker is not None and self.worker.isRunning():
            return
        visa_address = self.address_input.text().strip()
        if not visa_address:
            QMessageBox.warning(self, "Missing Address", "Enter a DAQ VISA address.")
            return
        try:
            channel_types = parse_channel_types(self.channels_input.text())
        except ValueError as exception:
            QMessageBox.warning(self, "Invalid Channels", str(exception))
            return

        output_file = self.output_input.text().strip() or None
        self.measure_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Starting temperature recording...")
        self.log_output.append(f"Opening {visa_address}")
        self.worker = TemperatureMeasurementWorker(
            visa_address,
            channel_types,
            output_file,
            interval_seconds=self.interval_input.value(),
            duration_seconds=self.duration_input.value() * 60.0,
            parent=self,
        )
        self.worker.sample_ready.connect(self.measurement_completed)
        self.worker.failed.connect(self.measurement_failed)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()

    def stop_measurement(self):
        if self.worker is None or not self.worker.isRunning():
            return
        self.stop_button.setEnabled(False)
        self.status_label.setText("Stopping temperature recording...")
        self.worker.request_stop()

    def measurement_completed(self, sample, sample_count, elapsed_seconds):
        self.status_label.setText(
            f"Recording | {sample_count} sample(s) | "
            f"{elapsed_seconds:.1f} s elapsed"
        )
        self.log_output.append(
            f"#{sample_count} | {sample.timestamp:%H:%M:%S} | "
            f"{sample.status_text()}"
        )

    def measurement_failed(self, message):
        self.status_label.setText("Measurement failed")
        self.log_output.append(f"ERROR: {message}")
        QMessageBox.critical(self, "Temperature Measurement Error", message)

    def worker_finished(self):
        worker = self.worker
        self.worker = None
        self.measure_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if not self.status_label.text().startswith("Measurement failed"):
            self.status_label.setText("Temperature recording stopped")
        if self.output_input.text().strip():
            self.log_output.append(f"Saved to {self.output_input.text().strip()}")
        if worker is not None:
            worker.deleteLater()

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.stop_measurement()
            event.ignore()
            return
        event.accept()


__all__ = [
    "DEFAULT_CHANNEL_TYPES",
    "TemperatureMeasurement",
    "TemperatureMeasurementDialog",
    "TemperatureMeasurementWorker",
    "TemperatureSample",
    "default_daq_address",
    "measure_temperature",
    "parse_channel_types",
]
