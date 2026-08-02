"""Hornbill SCPI voltage sweep with oscilloscope screenshots."""

import threading
import time
import traceback
from decimal import Decimal
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from SCPI_Library.Keysight import Hornbill, Oscilloscope
from instruments.LowVoltageTest import strip_ieee_binary_block


VOLTAGE_INCREMENT = Decimal("0.1")
DEFAULT_INITIAL_VOLTAGE = Decimal("0.8")
DEFAULT_FINAL_VOLTAGE = Decimal("6.0")


class NoiseVoltageSweepStopped(RuntimeError):
    pass


def noise_voltage_points(
    initial_voltage=DEFAULT_INITIAL_VOLTAGE,
    final_voltage=DEFAULT_FINAL_VOLTAGE,
    increment=VOLTAGE_INCREMENT,
):
    initial_voltage = Decimal(str(initial_voltage))
    final_voltage = Decimal(str(final_voltage))
    increment = Decimal(str(increment))
    if increment <= 0:
        raise ValueError("Voltage increment must be greater than zero")
    if initial_voltage > final_voltage:
        raise ValueError(
            "Initial voltage cannot exceed the final voltage"
        )
    points = []
    voltage = initial_voltage
    while voltage <= final_voltage:
        points.append(float(voltage))
        voltage += increment
    if Decimal(str(points[-1])) != final_voltage:
        points.append(float(final_voltage))
    return tuple(points)


class NoiseVoltageSweepCaptureTest:
    def __init__(
        self,
        hornbill_factory=Hornbill,
        oscilloscope_factory=Oscilloscope,
    ):
        self.hornbill_factory = hornbill_factory
        self.oscilloscope_factory = oscilloscope_factory

    @staticmethod
    def _channels(value):
        if isinstance(value, (range, list, tuple, set)):
            return tuple(int(channel) for channel in value)
        return (int(value),)

    @staticmethod
    def _checkpoint(worker):
        if worker is not None:
            worker.checkpoint()

    @staticmethod
    def _wait(worker, seconds):
        if worker is not None:
            worker.interruptible_sleep(seconds)
        else:
            time.sleep(max(0.0, float(seconds)))

    @staticmethod
    def _emit(worker, message):
        if worker is not None:
            worker.progress.emit(message)

    @staticmethod
    def _check_dut_error(dut, voltage):
        response = str(dut.instr.query("SYST:ERR?")).strip()
        if not (response.startswith("0") or response.startswith("+0")):
            raise RuntimeError(
                "Hornbill rejected SCPI voltage "
                f"{voltage:g} V: {response}"
            )

    @staticmethod
    def _configure_scope(scope, configuration):
        channel = int(configuration["OSC_Channel"])
        scope.instr.write(f":CHANnel{channel}:DISPlay ON")
        scope.hardcopy(configuration.get("InkSaver", "ON"))
        optional_commands = (
            (
                configuration.get("Channel_CouplingMode"),
                lambda value: f":CHANnel{channel}:COUPling {value}",
            ),
            (
                configuration.get("TimeScale"),
                lambda value: f":TIMebase:RANGe {value}",
            ),
            (
                configuration.get("VerticalScale"),
                lambda value: f":CHANnel{channel}:SCALe {value}",
            ),
            (
                configuration.get("Trigger_SweepMode"),
                lambda value: f":TRIGger:SWEep {value}",
            ),
        )
        for value, command_factory in optional_commands:
            if value not in (None, ""):
                scope.instr.write(command_factory(value))

    @staticmethod
    def _output_directory(configuration, worker):
        if worker is not None and worker.run_context is not None:
            root = worker.run_context.storage.charts
        else:
            root = Path(
                configuration.get("rawdir")
                or configuration.get("savedir")
                or configuration.get("savelocation")
            )
        output_directory = Path(root) / "noise_voltage_sweep"
        output_directory.mkdir(parents=True, exist_ok=True)
        return output_directory

    def execute(self, configuration, loop_index=0, worker=None):
        voltages = noise_voltage_points(
            configuration["NoiseVoltageInitialVolts"],
            configuration["NoiseVoltageFinalVolts"],
            configuration.get(
                "NoiseVoltageIncrementVolts",
                VOLTAGE_INCREMENT,
            ),
        )
        channels = self._channels(configuration["PSU_Channel"])
        output_directory = self._output_directory(configuration, worker)
        settling_delay = float(configuration.get("updatedelay") or 0)
        scope_run_delay = float(
            configuration.get("ScopeRunCaptureDelay", 3.0)
        )
        dut = None
        scope = None
        enabled_channels = []
        total = len(voltages) * len(channels)
        completed = 0
        captured_images = []

        try:
            dut = self.hornbill_factory(configuration["PSU"])
            scope = self.oscilloscope_factory(configuration["OSC"])
            self._configure_scope(scope, configuration)

            for channel in channels:
                self._checkpoint(worker)
                dut.instr.write("*CLS")
                dut.setMode("VOLTAGE", channel)
                dut.sourVoltageLevelImmediateAmplitude(0, channel)
                dut.sourCurrentLimitPOS("MAX", channel)
                dut.sourCurrentLimitNEG("MAX", channel)
                dut.outputState("ON", channel)
                enabled_channels.append(channel)

                for voltage in voltages:
                    self._checkpoint(worker)
                    dut.sourVoltageLevelImmediateAmplitude(
                        voltage,
                        channel,
                    )
                    self._check_dut_error(dut, voltage)
                    self._emit(
                        worker,
                        "Noise voltage sweep: "
                        f"channel {channel}, {voltage:g} V",
                    )
                    self._wait(worker, settling_delay)
                    scope.run()
                    self._wait(worker, scope_run_delay)
                    scope.stop()
                    image_data = strip_ieee_binary_block(
                        scope.read_binary_data()
                    )
                    image_path = output_directory / (
                        f"loop_{loop_index + 1:03d}_channel_{channel}_"
                        f"voltage_{voltage:g}V.png"
                    )
                    image_path.write_bytes(image_data)
                    captured_images.append(image_path)
                    completed += 1
                    if worker is not None:
                        worker.progress_value.emit(
                            int(completed * 100 / total)
                        )
                    self._emit(worker, f"Screenshot saved: {image_path}")

            return tuple(captured_images)
        finally:
            if scope is not None:
                try:
                    scope.stop()
                except Exception:
                    pass
            if dut is not None:
                for channel in enabled_channels:
                    try:
                        dut.sourVoltageLevelImmediateAmplitude(0, channel)
                        dut.outputState("OFF", channel)
                    except Exception:
                        pass
            for instrument in (scope, dut):
                session = getattr(instrument, "instr", None)
                if session is not None:
                    try:
                        session.close()
                    except Exception:
                        pass


class NoiseVoltageSweepWorker(QThread):
    progress = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    completed = pyqtSignal(object)
    stopped = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, configuration, runner=None):
        super().__init__()
        self.configuration = dict(configuration)
        self.runner = runner or NoiseVoltageSweepCaptureTest()
        self.run_context = None
        self._stop_requested = threading.Event()

    def stop(self):
        self._stop_requested.set()

    def checkpoint(self):
        if self._stop_requested.is_set():
            raise NoiseVoltageSweepStopped(
                "Noise voltage sweep stopped by operator"
            )

    def interruptible_sleep(self, seconds):
        if self._stop_requested.wait(max(0.0, float(seconds))):
            self.checkpoint()

    def run(self):
        try:
            images = self.runner.execute(
                self.configuration,
                worker=self,
            )
            self.completed.emit(images)
        except NoiseVoltageSweepStopped:
            self.stopped.emit()
        except Exception as exception:
            self.progress.emit(
                f"ERROR: {exception}\n{traceback.format_exc()}"
            )
            self.error.emit(str(exception))


class NoiseVoltageSweepDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hornbill Noise Test Voltage Sweep")
        self.resize(760, 620)
        self.worker = None

        self.dut_address = QLineEdit()
        self.dut_address.setPlaceholderText("Hornbill DUT VISA address")
        self.scope_address = QLineEdit()
        self.scope_address.setPlaceholderText("Oscilloscope VISA address")

        self.dut_channel = QSpinBox()
        self.dut_channel.setRange(1, 4)
        self.scope_channel = QSpinBox()
        self.scope_channel.setRange(1, 16)

        self.initial_voltage = QDoubleSpinBox()
        self.initial_voltage.setRange(0, 60)
        self.initial_voltage.setDecimals(3)
        self.initial_voltage.setSingleStep(float(VOLTAGE_INCREMENT))
        self.initial_voltage.setValue(float(DEFAULT_INITIAL_VOLTAGE))
        self.initial_voltage.setSuffix(" V")
        self.final_voltage = QDoubleSpinBox()
        self.final_voltage.setRange(0, 60)
        self.final_voltage.setDecimals(3)
        self.final_voltage.setSingleStep(float(VOLTAGE_INCREMENT))
        self.final_voltage.setValue(float(DEFAULT_FINAL_VOLTAGE))
        self.final_voltage.setSuffix(" V")
        self.voltage_increment = QDoubleSpinBox()
        self.voltage_increment.setRange(0.001, 60)
        self.voltage_increment.setDecimals(3)
        self.voltage_increment.setSingleStep(0.001)
        self.voltage_increment.setValue(float(VOLTAGE_INCREMENT))
        self.voltage_increment.setSuffix(" V")

        self.settling_delay = QDoubleSpinBox()
        self.settling_delay.setRange(0, 3600)
        self.settling_delay.setDecimals(3)
        self.settling_delay.setValue(1.0)
        self.settling_delay.setSuffix(" s")
        self.scope_run_delay = QDoubleSpinBox()
        self.scope_run_delay.setRange(0.1, 3600)
        self.scope_run_delay.setDecimals(3)
        self.scope_run_delay.setValue(3.0)
        self.scope_run_delay.setSuffix(" s")
        self.ink_saver = QComboBox()
        self.ink_saver.addItems(("ON", "OFF"))
        self.ink_saver.setToolTip(
            "ON uses the oscilloscope ink-saving hardcopy background; "
            "OFF keeps the normal display colors."
        )

        self.output_directory = QLineEdit()
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_output_directory)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_directory)
        output_layout.addWidget(browse_button)

        form = QFormLayout()
        form.addRow("Hornbill DUT Address:", self.dut_address)
        form.addRow("Oscilloscope Address:", self.scope_address)
        form.addRow("Hornbill Channel:", self.dut_channel)
        form.addRow("Oscilloscope Channel:", self.scope_channel)
        form.addRow("Initial SCPI Voltage:", self.initial_voltage)
        form.addRow("Final SCPI Voltage:", self.final_voltage)
        form.addRow("Voltage Increment:", self.voltage_increment)
        form.addRow("Voltage Settling Delay:", self.settling_delay)
        form.addRow("Scope Run Capture Delay:", self.scope_run_delay)
        form.addRow("Scope Ink Saver:", self.ink_saver)
        form.addRow("Output Folder:", output_layout)

        self.start_button = QPushButton("Start Capture")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self._start)
        self.stop_button.clicked.connect(self._stop)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.status = QLabel(
            "Ready. One oscilloscope PNG is captured at every configured "
            "SCPI voltage increment."
        )
        self.status.setWordWrap(True)
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(button_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status)
        layout.addWidget(self.log, stretch=1)

    def _browse_output_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Screenshot Output Folder",
        )
        if directory:
            self.output_directory.setText(directory)

    def _configuration(self):
        dut_address = self.dut_address.text().strip()
        scope_address = self.scope_address.text().strip()
        output_directory = self.output_directory.text().strip()
        if not dut_address or not scope_address:
            raise ValueError(
                "Hornbill DUT and oscilloscope addresses are required"
            )
        if dut_address == scope_address:
            raise ValueError(
                "Hornbill DUT and oscilloscope addresses must be different"
            )
        if not output_directory:
            raise ValueError("Select an output folder")
        noise_voltage_points(
            self.initial_voltage.value(),
            self.final_voltage.value(),
            self.voltage_increment.value(),
        )
        return {
            "PSU": dut_address,
            "OSC": scope_address,
            "PSU_Channel": self.dut_channel.value(),
            "OSC_Channel": self.scope_channel.value(),
            "NoiseVoltageInitialVolts": self.initial_voltage.value(),
            "NoiseVoltageFinalVolts": self.final_voltage.value(),
            "NoiseVoltageIncrementVolts": self.voltage_increment.value(),
            "updatedelay": self.settling_delay.value(),
            "ScopeRunCaptureDelay": self.scope_run_delay.value(),
            "InkSaver": self.ink_saver.currentText(),
            "savedir": output_directory,
        }

    def _start(self):
        try:
            configuration = self._configuration()
        except ValueError as exception:
            QMessageBox.warning(self, "Invalid Settings", str(exception))
            return

        self.log.clear()
        self.progress_bar.setValue(0)
        self.worker = NoiseVoltageSweepWorker(configuration)
        self.worker.progress.connect(self.log.append)
        self.worker.progress_value.connect(self.progress_bar.setValue)
        self.worker.completed.connect(self._completed)
        self.worker.stopped.connect(self._stopped)
        self.worker.error.connect(self._error)
        self.worker.finished.connect(self._finished)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status.setText("Noise voltage sweep is running...")
        self.worker.start()

    def _stop(self):
        if self.worker is not None:
            self.worker.stop()
            self.stop_button.setEnabled(False)
            self.status.setText("Stop requested; waiting for a safe point...")

    def _completed(self, images):
        self.progress_bar.setValue(100)
        self.status.setText(
            f"Completed. Captured {len(images)} oscilloscope image(s)."
        )

    def _stopped(self):
        self.status.setText("Noise voltage sweep stopped safely.")

    def _error(self, message):
        self.status.setText("Noise voltage sweep failed.")
        QMessageBox.critical(self, "Noise Voltage Sweep Error", message)

    def _finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.worker = None

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
        super().closeEvent(event)
