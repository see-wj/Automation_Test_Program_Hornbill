"""Hornbill PSU voltage calibration using an HP/Keysight 3458A DMM."""

import threading
import traceback

from pyvisa.rname import ResourceName
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from SCPI_Library.simulation import create_resource_manager


class CalibrationStopped(RuntimeError):
    pass


def normalize_visa_address(address):
    raw_address = str(address).strip()
    try:
        return str(ResourceName.from_string(raw_address))
    except Exception as exception:
        raise ValueError(f"Invalid VISA address: {raw_address!r}") from exception


class CalWorker(QThread):
    log = pyqtSignal(str)
    error = pyqtSignal(str)
    stopped = pyqtSignal()

    DMM_RANGES = {"P1": 10, "P2": 100}
    DMM_LABEL = "3458A"

    def __init__(
        self,
        psu_addr,
        dmm_addr,
        password,
        channel,
        cal_points,
        *,
        resource_manager_factory=create_resource_manager,
        command_delay=0.2,
        settling_delay=5.0,
        calibration_time=60.0,
        resource_manager=None,
        psu=None,
        dmm=None,
    ):
        super().__init__()
        self.psu_addr = psu_addr
        self.dmm_addr = dmm_addr
        self.password = password
        self.channels = self._normalize_channels(channel)
        self.channel = self.channels[0]
        self.cal_points = [point.upper() for point in cal_points]
        self.resource_manager_factory = resource_manager_factory
        self.command_delay = float(command_delay)
        self.settling_delay = float(settling_delay)
        self.calibration_time = float(calibration_time)
        self.resource_manager = resource_manager
        self.psu = psu
        self.dmm = dmm
        self._stop_requested = threading.Event()

    @staticmethod
    def _normalize_channels(channels):
        if isinstance(channels, str):
            values = [value.strip() for value in channels.split(",") if value.strip()]
        elif isinstance(channels, (list, tuple, set)):
            values = list(channels)
        else:
            values = [channels]

        normalized = []
        for value in values:
            channel = int(value)
            if channel not in normalized:
                normalized.append(channel)
        return normalized

    def stop(self):
        self._stop_requested.set()

    def _checkpoint(self):
        if self._stop_requested.is_set():
            raise CalibrationStopped("Calibration stopped by operator")

    def _wait(self, seconds):
        if self._stop_requested.wait(max(0.0, float(seconds))):
            raise CalibrationStopped("Calibration stopped by operator")

    def _write(self, instrument, command, delay=None):
        self._checkpoint()
        instrument.write(command)
        self._wait(self.command_delay if delay is None else delay)

    def _check_psu_error(self, psu, *, retries=3, retry_delay=0.5):
        last_error = None
        for attempt in range(retries):
            self._checkpoint()
            try:
                error = psu.query("SYST:ERR?").strip()
            except Exception as exception:
                if attempt < retries - 1:
                    self._wait(retry_delay)
                    continue
                raise RuntimeError(f"Unable to read PSU error: {exception}") from exception
            if error.startswith("0") or error.startswith("+0"):
                return
            last_error = error
            if attempt < retries - 1:
                self._wait(retry_delay)
                continue
        raise RuntimeError(f"PSU error: {last_error}")

    def _configure_3458a(self, dmm):
        commands = (
            "PRESET NORM",
            "OFORMAT ASCII",
            "DCV 10",
            "TARM HOLD",
            "TRIG AUTO",
            "NPLC 100",
            "NRDGS 1,AUTO",
            "MEM OFF",
            "END ALWAYS",
            "NDIG 9",
            "AZERO ON",
            "DISP ON",
        )
        for command in commands:
            self._write(dmm, command, delay=0)

    def _measure_3458a(self, dmm):
        self._checkpoint()
        reading = dmm.query("TARM SGL,1").strip()
        try:
            float(reading)
        except ValueError as exception:
            raise RuntimeError(f"Invalid 3458A reading: {reading!r}") from exception
        return reading

    def _configure_dmm(self, dmm):
        self._configure_3458a(dmm)

    def _set_dmm_range(self, dmm, dmm_range):
        self._write(dmm, f"DCV {dmm_range}", delay=0)

    def _measure_dmm(self, dmm):
        return self._measure_3458a(dmm)

    def _validate(self):
        if not self.psu_addr or not self.dmm_addr:
            raise ValueError("PSU and DMM VISA addresses are required")
        if not self.password:
            raise ValueError("Calibration password is required")
        if not self.channels:
            raise ValueError("At least one calibration channel is required")
        invalid_channels = [
            channel for channel in self.channels if not 1 <= channel <= 4
        ]
        if invalid_channels:
            raise ValueError("Calibration channels must be between 1 and 4")
        if not self.cal_points:
            raise ValueError("At least one calibration point is required")
        if self.calibration_time < 0:
            raise ValueError("Calibration time cannot be negative")
        unsupported = [
            point for point in self.cal_points if point not in self.DMM_RANGES
        ]
        if unsupported:
            raise ValueError(
                f"{self.DMM_LABEL} voltage calibration supports only P1 and P2"
            )
        self.psu_addr = normalize_visa_address(self.psu_addr)
        self.dmm_addr = normalize_visa_address(self.dmm_addr)

    @staticmethod
    def _open_resource(resource_manager, address, role):
        try:
            return resource_manager.open_resource(address)
        except Exception as exception:
            try:
                visible_resources = ", ".join(resource_manager.list_resources())
            except Exception:
                visible_resources = "unavailable"
            raise RuntimeError(
                f"Unable to open {role} at {address!r}. "
                f"Visible VISA resources: {visible_resources}. "
                f"Original error: {exception}"
            ) from exception

    def run(self):
        resource_manager = self.resource_manager
        psu = self.psu
        dmm = self.dmm
        calibration_enabled = False
        try:
            self._validate()
            self._checkpoint()
            if resource_manager is None:
                self.log.emit("Opening VISA resources...")
                resource_manager = self.resource_manager_factory()
            if psu is None:
                self.log.emit(f"Opening PSU: {self.psu_addr}")
                psu = self._open_resource(resource_manager, self.psu_addr, "PSU")
            else:
                self.log.emit(f"Using connected PSU: {self.psu_addr}")
            psu.timeout = 60000
            if dmm is None:
                self.log.emit(f"Opening {self.DMM_LABEL}: {self.dmm_addr}")
                dmm = self._open_resource(
                    resource_manager,
                    self.dmm_addr,
                    self.DMM_LABEL,
                )
            else:
                self.log.emit(
                    f"Using connected {self.DMM_LABEL}: {self.dmm_addr}"
                )
            dmm.timeout = 10000

            self.log.emit("Resetting PSU...")
            self._write(psu, "*RST")
            for channel in self.channels:
                self._write(psu, f"OUTPut:STATe OFF, (@{channel})")
                self.log.emit(
                    f"Preparing channel {channel}: 6 V, output ON, four-wire sense..."
                )
                self._write(
                    psu,
                    f"SOURce:VOLTage:LEVel:IMMediate:AMPLitude 6, (@{channel})",
                )
                self._write(psu, f"OUTPut:STATe ON, (@{channel})")
                self._write(
                    psu,
                    f"SOURce:VOLTage:SENSe:SOURce EXT, (@{channel})",
                )
                self._write(psu, f"DIAG:POKE 50{channel-1}, 2865")

            self.log.emit("Enabling PSU calibration mode...")
            self._write(psu, f'CAL:STAT ON,"{self.password}"')
            calibration_enabled = True
            self._check_psu_error(psu)
            self._wait(2.0)

            self.log.emit(f"Configuring {self.DMM_LABEL} DMM...")
            self._configure_dmm(dmm)
            self._wait(0.5)

            for channel in self.channels:
                self.log.emit(f"Selecting 60 V calibration on channel {channel}...")
                self._write(psu, f"CAL:VOLT 60,(@{channel})")
                self._check_psu_error(psu)
                self._wait(2.0)

                for point in self.cal_points:
                    dmm_range = self.DMM_RANGES[point]
                    self._set_dmm_range(dmm, dmm_range)
                    self.log.emit(
                        f"Channel {channel}: selecting calibration level {point}..."
                    )
                    self._write(psu, f"CAL:LEV {point}")
                    self._wait(max(self.settling_delay, 2.0))
                    self._check_psu_error(psu)
                    self._wait(max(self.settling_delay, 2.0))

                    self.log.emit(
                        f"Channel {channel}: measuring {point} with the "
                        f"{self.DMM_LABEL} after {self.calibration_time:g} s..."
                    )
                    self._wait(self.calibration_time)
                    reading = self._measure_dmm(dmm)
                    self.log.emit(f"{self.DMM_LABEL} reading = {reading}")

                    self.log.emit(
                        f"Channel {channel}: writing calibration data for {point}..."
                    )
                    self._write(psu, f"CAL:DATA {reading}")
                    self._check_psu_error(psu)
                    self._wait(2.0)

            self._checkpoint()
            self.log.emit("Saving calibration constants...")
            self._write(psu, "CAL:SAVE")
            self._check_psu_error(psu)
            self._wait(2.0)

            self.log.emit("Disabling PSU calibration mode...")
            self._write(psu, "CAL:STAT OFF")
            calibration_enabled = False
            self._check_psu_error(psu)
            self.log.emit("Calibration completed successfully")
        except CalibrationStopped as exception:
            self.log.emit(str(exception))
            self.stopped.emit()
        except Exception as exception:
            self.log.emit(f"ERROR: {exception}\n{traceback.format_exc()}")
            self.error.emit(str(exception))
        finally:
            if psu is not None:
                if calibration_enabled:
                    try:
                        psu.write("CAL:STAT OFF")
                    except Exception as exception:
                        self.log.emit(
                            f"Unable to disable calibration mode: {exception}"
                        )
                for channel in self.channels:
                    try:
                        psu.write(f"OUTPUT:STATE OFF,(@{channel})")
                    except Exception as exception:
                        self.log.emit(
                            f"Unable to disable PSU channel {channel} output: {exception}"
                        )
            for instrument in (dmm, psu):
                if instrument is not None:
                    try:
                        instrument.close()
                    except Exception:
                        pass
            if resource_manager is not None and hasattr(resource_manager, "close"):
                try:
                    resource_manager.close()
                except Exception:
                    pass


class VoltageCalibrationDialog(QDialog):
    WORKER_CLASS = CalWorker
    DMM_LABEL = "3458A"
    DEFAULT_DMM_ADDRESS = "GPIB0::22::INSTR"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            f"Hornbill Voltage Calibration - {self.DMM_LABEL}"
        )
        self.resize(800, 520)

        form = QFormLayout()
        self.psu_input = QLineEdit()
        self.psu_input.setPlaceholderText("Enter Hornbill PSU VISA address")
        form.addRow("PSU Address:", self.psu_input)

        self.dmm_input = QLineEdit(self.DEFAULT_DMM_ADDRESS)
        self.dmm_input.setPlaceholderText(
            f"Enter {self.DMM_LABEL} VISA address"
        )
        form.addRow(f"{self.DMM_LABEL} Address:", self.dmm_input)

        self.pw_input = QLineEdit("PP8000A")
        self.pw_input.setEchoMode(QLineEdit.Password)
        form.addRow("Calibration Password:", self.pw_input)

        self.channel_input = QLineEdit("1")
        self.channel_input.setPlaceholderText("Examples: 1 or 1,2,3,4")
        form.addRow("Channels (csv):", self.channel_input)

        self.points_input = QLineEdit("P1,P2")
        form.addRow("Calibration Points:", self.points_input)

        self.calibration_time_input = QDoubleSpinBox()
        self.calibration_time_input.setRange(0.0, 3600.0)
        self.calibration_time_input.setDecimals(1)
        self.calibration_time_input.setSingleStep(5.0)
        self.calibration_time_input.setValue(60.0)
        self.calibration_time_input.setSuffix(" s")
        self.calibration_time_input.setToolTip(
            "Wait time after each P1/P2 calibration level before reading the DMM."
        )
        form.addRow("Calibration Time:", self.calibration_time_input)

        self.start_btn = QPushButton("Start Calibration")
        self.start_btn.clicked.connect(self.on_start)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.on_stop)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(button_layout)
        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log)

        self.worker = None

    def append_log(self, text):
        self.log.append(text)
        self.log.moveCursor(self.log.textCursor().End)

    def on_start(self):
        psu_addr = self.psu_input.text().strip()
        dmm_addr = self.dmm_input.text().strip()
        password = self.pw_input.text().strip()
        calibration_time = self.calibration_time_input.value()
        channel_text = self.channel_input.text().strip()
        try:
            channels = self.WORKER_CLASS._normalize_channels(channel_text)
        except (TypeError, ValueError):
            QMessageBox.warning(
                self,
                "Invalid Channels",
                "Enter channel numbers from 1 to 4, separated by commas.",
            )
            return
        if not channels or any(channel < 1 or channel > 4 for channel in channels):
            QMessageBox.warning(
                self,
                "Invalid Channels",
                "Enter at least one channel from 1 to 4.",
            )
            return
        points = [
            point.strip()
            for point in self.points_input.text().split(",")
            if point.strip()
        ]

        if not psu_addr or not dmm_addr:
            QMessageBox.warning(
                self,
                "Missing Address",
                f"Provide both PSU and {self.DMM_LABEL} VISA addresses.",
            )
            return
        if [point.upper() for point in points] != ["P1", "P2"]:
            QMessageBox.warning(
                self,
                "Invalid Points",
                f"The supported {self.DMM_LABEL} voltage calibration "
                "sequence is P1,P2.",
            )
            return

        reply = QMessageBox.warning(
            self,
            "Confirm Calibration",
            "Calibration changes instrument constants. Verify wiring, channels "
            f"{', '.join(str(channel) for channel in channels)}, "
            f"and the {self.DMM_LABEL} connection before continuing.",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply != QMessageBox.Ok:
            return

        resource_manager = None
        psu = None
        dmm = None
        try:
            psu_addr = normalize_visa_address(psu_addr)
            dmm_addr = normalize_visa_address(dmm_addr)
            resource_manager = create_resource_manager()
            psu = self.WORKER_CLASS._open_resource(
                resource_manager,
                psu_addr,
                "PSU",
            )
            dmm = self.WORKER_CLASS._open_resource(
                resource_manager,
                dmm_addr,
                self.DMM_LABEL,
            )
        except Exception as exception:
            for instrument in (dmm, psu):
                if instrument is not None:
                    try:
                        instrument.close()
                    except Exception:
                        pass
            if resource_manager is not None and hasattr(resource_manager, "close"):
                try:
                    resource_manager.close()
                except Exception:
                    pass
            QMessageBox.critical(self, "VISA Connection Error", str(exception))
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log.clear()
        self.append_log(
            f"Starting {self.DMM_LABEL} voltage calibration..."
        )

        self.worker = self.WORKER_CLASS(
            psu_addr,
            dmm_addr,
            password,
            channels,
            points,
            calibration_time=calibration_time,
            resource_manager=resource_manager,
            psu=psu,
            dmm=dmm,
        )
        self.worker.log.connect(self.append_log)
        self.worker.error.connect(self.on_error)
        self.worker.stopped.connect(
            lambda: self.append_log("Calibration stopped safely")
        )
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_stop(self):
        if self.worker and self.worker.isRunning():
            self.append_log("Stop requested; waiting for a safe checkpoint...")
            self.worker.stop()
            self.stop_btn.setEnabled(False)

    def on_finished(self):
        self.append_log("Calibration worker finished")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.worker = None

    def on_error(self, message):
        QMessageBox.critical(
            self,
            "Calibration Error",
            f"Calibration error:\n{message}",
        )

    def closeEvent(self, event):
        if not self.worker or not self.worker.isRunning():
            event.accept()
            return
        QMessageBox.information(
            self,
            "Calibration Running",
            "Stop the calibration and wait for the worker to finish before closing.",
        )
        event.ignore()
