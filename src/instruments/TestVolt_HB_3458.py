"""Hornbill PSU voltage calibration using an HP/Keysight 3458A DMM."""

import threading
import traceback

from pyvisa.rname import ResourceName
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
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
        resource_manager=None,
        psu=None,
        dmm=None,
    ):
        super().__init__()
        self.psu_addr = psu_addr
        self.dmm_addr = dmm_addr
        self.password = password
        self.channel = int(channel)
        self.cal_points = [point.upper() for point in cal_points]
        self.resource_manager_factory = resource_manager_factory
        self.command_delay = float(command_delay)
        self.settling_delay = float(settling_delay)
        self.resource_manager = resource_manager
        self.psu = psu
        self.dmm = dmm
        self._stop_requested = threading.Event()

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

    def _check_psu_error(self, psu):
        error = psu.query("SYST:ERR?").strip()
        if error.startswith("0") or error.startswith("+0"):
            return
        raise RuntimeError(f"PSU error: {error}")

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

    def _validate(self):
        if not self.psu_addr or not self.dmm_addr:
            raise ValueError("PSU and DMM VISA addresses are required")
        if not self.password:
            raise ValueError("Calibration password is required")
        if not 1 <= self.channel <= 4:
            raise ValueError("Calibration channel must be between 1 and 4")
        if not self.cal_points:
            raise ValueError("At least one calibration point is required")
        unsupported = [
            point for point in self.cal_points if point not in self.DMM_RANGES
        ]
        if unsupported:
            raise ValueError(
                "3458A voltage calibration supports only P1 and P2"
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
                self.log.emit(f"Opening 3458A: {self.dmm_addr}")
                dmm = self._open_resource(resource_manager, self.dmm_addr, "3458A")
            else:
                self.log.emit(f"Using connected 3458A: {self.dmm_addr}")
            dmm.timeout = 10000

            self.log.emit("Enabling Four Wire.")
            self._write(psu, f"SOURce:VOLTage:SENSe:SOURce EXT, (@{self.channel})")
            self._write(psu, f"DIAG:POKE 50{self.channel-1}, 2865")

            self.log.emit("Enabling PSU calibration mode...")
            self._write(psu, f'CAL:STAT ON,"{self.password}"')
            calibration_enabled = True
            self._check_psu_error(psu)

            self.log.emit(f"Selecting 60 V calibration on channel {self.channel}...")
            self._write(psu, f"CAL:VOLT 60,(@{self.channel})")
            self._check_psu_error(psu)

            self.log.emit("Configuring 3458A DMM...")
            self._configure_3458a(dmm)
            self._wait(0.5)

            for point in self.cal_points:
                dmm_range = self.DMM_RANGES[point]
                self._write(dmm, f"DCV {dmm_range}", delay=0)
                self.log.emit(f"Selecting calibration level {point}...")
                self._write(psu, f"CAL:LEV {point}")
                self._check_psu_error(psu)
                self._wait(self.settling_delay)

                self.log.emit(f"Measuring {point} with the 3458A...")
                reading = self._measure_3458a(dmm)
                self.log.emit(f"3458A reading = {reading}")

                self.log.emit(f"Writing calibration data for {point}...")
                self._write(psu, f"CAL:DATA {reading}")
                self._check_psu_error(psu)
                self._wait(1.0)

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
                try:
                    psu.write(f"OUTPUT:STATE OFF,(@{self.channel})")
                except Exception as exception:
                    self.log.emit(f"Unable to disable PSU output: {exception}")
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hornbill Voltage Calibration - 3458A")
        self.resize(800, 520)

        form = QFormLayout()
        self.psu_input = QLineEdit()
        self.psu_input.setPlaceholderText("Enter Hornbill PSU VISA address")
        form.addRow("PSU Address:", self.psu_input)

        self.dmm_input = QLineEdit("GPIB0::22::INSTR")
        self.dmm_input.setPlaceholderText("Enter 3458A VISA address")
        form.addRow("3458A Address:", self.dmm_input)

        self.pw_input = QLineEdit("PP8000A")
        self.pw_input.setEchoMode(QLineEdit.Password)
        form.addRow("Calibration Password:", self.pw_input)

        self.channel_input = QSpinBox()
        self.channel_input.setRange(1, 4)
        self.channel_input.setValue(1)
        form.addRow("Channel:", self.channel_input)

        self.points_input = QLineEdit("P1,P2")
        form.addRow("Calibration Points:", self.points_input)

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
        channel = self.channel_input.value()
        points = [
            point.strip()
            for point in self.points_input.text().split(",")
            if point.strip()
        ]

        if not psu_addr or not dmm_addr:
            QMessageBox.warning(
                self,
                "Missing Address",
                "Provide both PSU and 3458A VISA addresses.",
            )
            return
        if [point.upper() for point in points] != ["P1", "P2"]:
            QMessageBox.warning(
                self,
                "Invalid Points",
                "The supported 3458A voltage calibration sequence is P1,P2.",
            )
            return

        reply = QMessageBox.warning(
            self,
            "Confirm Calibration",
            "Calibration changes instrument constants. Verify wiring, channel, "
            "and the 3458A connection before continuing.",
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
            psu = CalWorker._open_resource(resource_manager, psu_addr, "PSU")
            dmm = CalWorker._open_resource(resource_manager, dmm_addr, "3458A")
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
        self.append_log("Starting 3458A voltage calibration...")

        self.worker = CalWorker(
            psu_addr,
            dmm_addr,
            password,
            channel,
            points,
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
