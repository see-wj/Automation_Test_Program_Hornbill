"""Four-channel Hornbill power study at the 300 W autoranging knees."""

import csv
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
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

from SCPI_Library.Keysight import (
    AC_Source_68xx,
    DAQ973A,
    ELOAD_N3300A,
    Excavator,
    Hornbill,
    Oscilloscope,
)
from SCPI_Library.session_manager import (
    begin_visa_session_scope,
    close_visa_session_scope,
)
from common.path import config_folder, csv_folder
from configuration.configuration_service import configuration_path, load_configuration


@dataclass(frozen=True)
class KneePoint:
    name: str
    channel: int
    voltage: float
    current: float

    @property
    def power(self):
        return self.voltage * self.current


KNEE_CONDITIONS = (
    ("High Knee", 60.0, 5.0),
    ("Mid Knee 1", 37.5, 8.0),
    ("Mid Knee 2", 24.0, 12.5),
    ("Low Knee", 15.0, 20.0),
)
DISABLED_CONDITION = "None"
CONDITION_BY_NAME = {
    name: (voltage, current)
    for name, voltage, current in KNEE_CONDITIONS
}
DEFAULT_CONDITIONS = tuple(name for name, _voltage, _current in KNEE_CONDITIONS)
EXCAVATOR_CURRENT_A = 20.0


def build_knee_points(condition_names, channel_currents=None):
    if channel_currents is None:
        channel_currents = (None,) * len(condition_names)
    if len(condition_names) != len(channel_currents):
        raise ValueError("Conditions and channel currents must have equal lengths")
    points = []
    for channel, (condition_name, configured_current) in enumerate(
        zip(condition_names, channel_currents), start=1
    ):
        if condition_name == DISABLED_CONDITION:
            points.append(None)
            continue
        try:
            voltage, default_current = CONDITION_BY_NAME[condition_name]
        except KeyError as exception:
            raise ValueError(
                f"DUT channel {channel}: unsupported condition {condition_name!r}"
            ) from exception
        if channel == 4:
            current = EXCAVATOR_CURRENT_A
        else:
            current = (
                default_current
                if configured_current is None
                else float(configured_current)
            )
        points.append(KneePoint(condition_name, channel, voltage, current))
    return tuple(points)


KNEE_POINTS = build_knee_points(DEFAULT_CONDITIONS)


@dataclass(frozen=True)
class LoadConfiguration:
    driver: str
    address: str
    instrument_channel: int = 1

    def validate(self, dut_channel):
        if self.driver not in {"N3300A", "Excavator"}:
            raise ValueError(f"Channel {dut_channel}: unsupported load driver")
        if not self.address.strip():
            raise ValueError(f"Channel {dut_channel}: load address is required")
        if self.driver == "N3300A" and self.instrument_channel < 1:
            raise ValueError(f"Channel {dut_channel}: load channel must be positive")


@dataclass(frozen=True)
class PowerStudyConfiguration:
    dut_address: str
    ac_source_address: str
    daq_address: str
    n3300a_address: str
    excavator_address: str
    conditions: tuple = DEFAULT_CONDITIONS
    channel_currents: tuple = (5.0, 8.0, 12.5, 20.0)
    daq_channels: tuple = (101, 102, 103, 104)
    duration_seconds: float = 3600.0
    sample_interval_seconds: float = 10.0
    settling_seconds: float = 5.0
    ac_voltage: float = 230.0
    ac_current_limit: float = 10.0
    ac_frequency: float = 50.0
    voltage_sense: str = "INT"
    daq_voltage_range: str = "AUTO"
    daq_voltage_resolution: str = "MIN"
    scope_enabled: bool = False
    scope_address: str = ""
    scope_ink_saver: str = "ON"
    output_file: Path = Path("power_study.csv")

    @property
    def channel_points(self):
        return build_knee_points(self.conditions, self.channel_currents)

    @property
    def knee_points(self):
        return tuple(point for point in self.channel_points if point is not None)

    @property
    def active_daq_channels(self):
        return tuple(
            daq_channel
            for point, daq_channel in zip(self.channel_points, self.daq_channels)
            if point is not None
        )

    def validate(self):
        required = {
            "Hornbill DUT": self.dut_address,
            "AC source": self.ac_source_address,
            "DAQ34970A internal DMM": self.daq_address,
        }
        for label, address in required.items():
            if not str(address).strip():
                raise ValueError(f"{label} address is required")
        if len(self.conditions) != 4:
            raise ValueError("Select one condition for each of the four DUT channels")
        if len(self.channel_currents) != 4:
            raise ValueError("Provide one current configuration per DUT channel")
        if not self.knee_points:
            raise ValueError("Enable at least one DUT channel")
        for point in self.knee_points:
            if point.current <= 0 or point.current > 20:
                raise ValueError(
                    f"DUT channel {point.channel}: current must be above 0 A "
                    "and at most 20 A"
                )
        if any(point.channel <= 3 for point in self.knee_points):
            if not str(self.n3300a_address).strip():
                raise ValueError("N3300A address is required for DUT channels 1-3")
        if any(point.channel == 4 for point in self.knee_points):
            if not str(self.excavator_address).strip():
                raise ValueError("Excavator address is required for DUT channel 4")
        if len(self.daq_channels) != 4:
            raise ValueError("Provide one DAQ channel per DUT channel")
        if len(set(self.active_daq_channels)) != len(self.active_daq_channels):
            raise ValueError("Enabled DUT channels must use unique DAQ channels")
        if self.duration_seconds <= 0:
            raise ValueError("Test duration must be greater than zero")
        if self.sample_interval_seconds <= 0:
            raise ValueError("Sample interval must be greater than zero")
        if self.settling_seconds < 0:
            raise ValueError("Settling delays cannot be negative")
        if self.ac_voltage <= 0 or self.ac_current_limit <= 0:
            raise ValueError("AC source voltage and current limit must be positive")
        if self.voltage_sense not in {"INT", "EXT"}:
            raise ValueError("Voltage sense must be INT or EXT")
        if not str(self.output_file):
            raise ValueError("CSV output file is required")
        if not str(self.daq_voltage_range).strip():
            raise ValueError("DAQ voltage range is required")
        if not str(self.daq_voltage_resolution).strip():
            raise ValueError("DAQ voltage resolution is required")
        if self.scope_enabled and not str(self.scope_address).strip():
            raise ValueError("Oscilloscope address is required when capture is enabled")
        if self.scope_ink_saver not in {"ON", "OFF"}:
            raise ValueError("Oscilloscope ink saver must be ON or OFF")


@dataclass(frozen=True)
class PowerStudySample:
    timestamp: datetime
    elapsed_seconds: float
    knee: KneePoint
    daq_channel: int
    measured_voltage: float
    input_voltage: float
    input_current: float
    input_real_power: float
    input_apparent_power: float
    total_output_power: float
    efficiency_percent: float
    scope_screenshot: str = ""

    @property
    def output_power(self):
        return self.measured_voltage * self.knee.current

    def csv_row(self):
        return (
            self.timestamp.isoformat(timespec="seconds"),
            f"{self.elapsed_seconds:.3f}",
            self.knee.name,
            self.knee.channel,
            self.daq_channel,
            self.knee.voltage,
            self.knee.current,
            f"{self.measured_voltage:.9g}",
            f"{self.output_power:.9g}",
            f"{self.input_voltage:.9g}",
            f"{self.input_current:.9g}",
            f"{self.input_real_power:.9g}",
            f"{self.input_apparent_power:.9g}",
            f"{self.total_output_power:.9g}",
            f"{self.efficiency_percent:.9g}",
            self.scope_screenshot,
        )


CSV_COLUMNS = (
    "Timestamp",
    "Elapsed_s",
    "Knee",
    "DUT_Channel",
    "DAQ_Channel",
    "Voltage_Set_V",
    "Load_Current_Set_A",
    "DAQ_Internal_DMM_Voltage_V",
    "Channel_Output_Power_W",
    "AC_Input_Voltage_V",
    "AC_Input_Current_A",
    "AC_Input_Real_Power_W",
    "AC_Input_Apparent_Power_VA",
    "Total_Output_Power_W",
    "Efficiency_Percent",
    "Scope_Screenshot",
)


class PowerStudyStopped(RuntimeError):
    pass


class ElectronicLoad:
    def __init__(self, configuration, instrument):
        self.configuration = configuration
        self.instrument = instrument

    def _select(self):
        if self.configuration.driver == "N3300A":
            self.instrument.set_SelectChannel(self.configuration.instrument_channel)

    def configure(self, current):
        self._select()
        if self.configuration.driver == "N3300A":
            self.instrument.clearStatus()
            self.instrument.set_Mode("CURR")
            self.instrument.set_ChannelCurrent(current)
        else:
            self.instrument.clearStatus()
            self.instrument.setSYSTEMEMULationMode("ELOAD")
            self.instrument.setMode("CURRent")
            self.instrument.setOutputCurrent(current)

    def set_output(self, enabled):
        self._select()
        if self.configuration.driver == "N3300A":
            self.instrument.set_OutputState("ON" if enabled else "OFF")
        else:
            self.instrument.setOutputState("ON" if enabled else "OFF")

    def query_error(self):
        self._select()
        return self.instrument.queryError()


class PowerStudyRunner:
    def __init__(
        self,
        hornbill_class=Hornbill,
        ac_source_class=AC_Source_68xx,
        daq_class=DAQ973A,
        n3300a_class=ELOAD_N3300A,
        excavator_class=Excavator,
        oscilloscope_class=Oscilloscope,
        sleep_fn=time.sleep,
        monotonic_fn=time.monotonic,
        manage_visa_scope=True,
    ):
        self.hornbill_class = hornbill_class
        self.ac_source_class = ac_source_class
        self.daq_class = daq_class
        self.n3300a_class = n3300a_class
        self.excavator_class = excavator_class
        self.oscilloscope_class = oscilloscope_class
        self.sleep_fn = sleep_fn
        self.monotonic_fn = monotonic_fn
        self.manage_visa_scope = manage_visa_scope
        self.dut = None
        self.ac_source = None
        self.daq = None
        self.scope = None
        self.load_groups = []

    @staticmethod
    def _number(value):
        return float(str(value).strip().split(",", 1)[0])

    @staticmethod
    def _check_error(label, response):
        text = str(response).strip()
        code = text.split(",", 1)[0].strip()
        if code not in {"0", "+0"}:
            raise RuntimeError(f"{label} reported {text}")

    @staticmethod
    def _timestamped_output_file(output_file, timestamp=None):
        output_file = Path(output_file)
        timestamp = timestamp or datetime.now()
        suffix = output_file.suffix or ".csv"
        return output_file.with_name(
            f"{output_file.stem}_{timestamp:%Y%m%d_%H%M%S_%f}{suffix}"
        )

    def _checkpoint(self, stop_requested):
        if stop_requested():
            raise PowerStudyStopped("Power study stopped by user")

    def _wait(self, seconds, stop_requested):
        deadline = self.monotonic_fn() + max(0.0, seconds)
        while True:
            self._checkpoint(stop_requested)
            remaining = deadline - self.monotonic_fn()
            if remaining <= 0:
                return
            self.sleep_fn(min(0.1, remaining))

    def _open_instruments(self, configuration):
        self.dut = self.hornbill_class(configuration.dut_address)
        self.ac_source = self.ac_source_class(configuration.ac_source_address)
        self.daq = self.daq_class(configuration.daq_address)
        self.scope = (
            self.oscilloscope_class(configuration.scope_address)
            if configuration.scope_enabled
            else None
        )
        active_channels = {point.channel for point in configuration.knee_points}
        n3300a = (
            self.n3300a_class(configuration.n3300a_address)
            if active_channels.intersection({1, 2, 3})
            else None
        )
        excavator = (
            self.excavator_class(configuration.excavator_address)
            if 4 in active_channels
            else None
        )
        n3300a_loads = {}
        if n3300a is not None:
            n3300a_loads = {
                channel: ElectronicLoad(
                    LoadConfiguration(
                        "N3300A", configuration.n3300a_address, channel
                    ),
                    n3300a,
                )
                for channel in range(1, 6)
            }
        self.load_groups = [
            tuple(n3300a_loads[channel] for channel in (1, 2))
            if n3300a_loads else (),
            (n3300a_loads[3],) if n3300a_loads else (),
            tuple(n3300a_loads[channel] for channel in (4, 5))
            if n3300a_loads else (),
            (
                ElectronicLoad(
                    LoadConfiguration(
                        "Excavator", configuration.excavator_address
                    ),
                    excavator,
                ),
            ) if excavator is not None else (),
        ]

    def _all_loads(self):
        return tuple(load for group in self.load_groups for load in group)

    def _active_loads(self, configuration):
        return tuple(
            load
            for point in configuration.knee_points
            for load in self.load_groups[point.channel - 1]
        )

    def _disable_dut_and_load_outputs(self, log, strict=False):
        failures = []
        for index, load in reversed(tuple(enumerate(self._all_loads(), start=1))):
            try:
                load.set_output(False)
            except Exception as exception:
                failures.append(f"load CH{index}: {exception}")
        if self.dut is not None:
            for channel in range(4, 0, -1):
                try:
                    self.dut.outputState("OFF", channel)
                except Exception as exception:
                    failures.append(f"DUT CH{channel}: {exception}")
        if self.daq is not None:
            try:
                self.daq.openAllChannels()
            except Exception as exception:
                failures.append(f"DAQ: {exception}")
        if failures:
            message = "Shutdown warning: " + "; ".join(failures)
            log(message)
            if strict:
                raise RuntimeError(message)

    def _configure(self, configuration, stop_requested, log):
        self._disable_dut_and_load_outputs(log, strict=True)
        self._checkpoint(stop_requested)

        self.ac_source.clearStatus()
        self.ac_source.setFrequency(configuration.ac_frequency)
        self.ac_source.setOutputCurrent(configuration.ac_current_limit)
        self.ac_source.setOutputVoltage(configuration.ac_voltage)
        self.ac_source.setOutputState("ON")
        self._check_error("AC source", self.ac_source.queryError())

        self.daq.clearStatus()
        self.daq.reset()
        self.daq.configureVoltageMeasurement(
            configuration.daq_voltage_range,
            configuration.daq_voltage_resolution,
            configuration.active_daq_channels,
        )
        self.daq.enableAutomaticChannelDelay(configuration.active_daq_channels)
        self.daq.setScanChannels(configuration.active_daq_channels)
        self._check_error("DAQ", self.daq.queryError())
        if self.scope is not None:
            self.scope.hardcopy(configuration.scope_ink_saver)
            self.scope.run()

        for knee in configuration.knee_points:
            load_group = self.load_groups[knee.channel - 1]
            self._checkpoint(stop_requested)
            self.dut.setMode("VOLTAGE", knee.channel)
            self.dut.senseVoltageSource(configuration.voltage_sense, knee.channel)
            self.dut.sourVoltageLevelImmediateAmplitude(knee.voltage, knee.channel)
            self.dut.sourCurrentLimitPOS(min(20.0, knee.current * 1.05), knee.channel)
            current_per_load = knee.current / len(load_group)
            for load in load_group:
                load.configure(current_per_load)
                self._check_error(
                    f"load for DUT CH{knee.channel}", load.query_error()
                )

        self._check_error("Hornbill", self.dut.queryError())
        log("All instruments configured; AC source remains ON")
        for knee in configuration.knee_points:
            self.dut.outputState("ON", knee.channel)
        self._wait(configuration.settling_seconds, stop_requested)
        for load in self._active_loads(configuration):
            load.set_output(True)
        self._wait(configuration.settling_seconds, stop_requested)

    def _measure(self, configuration, elapsed_seconds, stop_requested):
        self._checkpoint(stop_requested)
        voltages = self.daq.readScan()
        expected_count = len(configuration.knee_points)
        if len(voltages) != expected_count:
            raise RuntimeError(
                "DAQ internal DMM returned "
                f"{len(voltages)} values; expected {expected_count}"
            )

        input_voltage = self._number(self.ac_source.measureVoltage_AC())
        input_current = self._number(self.ac_source.measureCurrent_AC())
        input_real_power = self._number(self.ac_source.measurePower_AC_Real())
        input_apparent_power = self._number(
            self.ac_source.measurePower_AC_Apparent()
        )
        total_output_power = sum(
            voltage * knee.current
            for voltage, knee in zip(voltages, configuration.knee_points)
        )
        efficiency = (
            total_output_power / input_real_power * 100.0
            if input_real_power > 0
            else 0.0
        )
        timestamp = datetime.now()
        return tuple(
            PowerStudySample(
                timestamp=timestamp,
                elapsed_seconds=elapsed_seconds,
                knee=knee,
                daq_channel=daq_channel,
                measured_voltage=voltage,
                input_voltage=input_voltage,
                input_current=input_current,
                input_real_power=input_real_power,
                input_apparent_power=input_apparent_power,
                total_output_power=total_output_power,
                efficiency_percent=efficiency,
            )
            for knee, daq_channel, voltage in zip(
                configuration.knee_points,
                configuration.active_daq_channels,
                voltages,
            )
        )

    def _capture_scope(self, output_file, capture_index, stop_requested):
        if self.scope is None:
            return None
        self._checkpoint(stop_requested)
        image_directory = output_file.with_name(f"{output_file.stem}_scope")
        image_directory.mkdir(parents=True, exist_ok=True)
        image_path = image_directory / f"capture_{capture_index:06d}.png"
        self.scope.stop()
        try:
            image_path.write_bytes(bytes(self.scope.read_binary_data()))
        finally:
            self.scope.run()
        return image_path

    def execute(
        self,
        configuration,
        stop_requested=lambda: False,
        sample_callback=lambda _samples: None,
        log=lambda _message: None,
        started_callback=lambda _duration: None,
    ):
        configuration.validate()
        output_file = self._timestamped_output_file(configuration.output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        scope_started = False
        if self.manage_visa_scope:
            begin_visa_session_scope()
            scope_started = True
        try:
            self._open_instruments(configuration)
            self._configure(configuration, stop_requested, log)
            started_at = self.monotonic_fn()
            started_callback(configuration.duration_seconds)
            with output_file.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(CSV_COLUMNS)
                capture_index = 0
                while True:
                    self._checkpoint(stop_requested)
                    elapsed = self.monotonic_fn() - started_at
                    samples = self._measure(
                        configuration, elapsed, stop_requested
                    )
                    capture_index += 1
                    scope_image = self._capture_scope(
                        output_file,
                        capture_index,
                        stop_requested,
                    )
                    if scope_image is not None:
                        samples = tuple(
                            replace(sample, scope_screenshot=str(scope_image))
                            for sample in samples
                        )
                        log(f"Oscilloscope screenshot saved: {scope_image}")
                    writer.writerows(sample.csv_row() for sample in samples)
                    csv_file.flush()
                    sample_callback(samples)
                    if elapsed >= configuration.duration_seconds:
                        break
                    self._wait(
                        min(
                            configuration.sample_interval_seconds,
                            configuration.duration_seconds - elapsed,
                        ),
                        stop_requested,
                    )
            log(f"Power study complete: {output_file}")
            return output_file
        finally:
            self._disable_dut_and_load_outputs(log)
            log("AC source output left ON as required for DUT standby power")
            if scope_started:
                failures = close_visa_session_scope()
                for failure in failures:
                    log(f"VISA close warning ({failure.address}): {failure.exception}")


def _hornbill_defaults():
    try:
        return load_configuration(configuration_path(config_folder, "Hornbill"))
    except OSError:
        return {}


class PowerStudyWorker(QThread):
    sample_ready = pyqtSignal(object)
    log_ready = pyqtSignal(str)
    timing_started = pyqtSignal(float)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)
    stopped = pyqtSignal()

    def __init__(self, configuration, parent=None):
        super().__init__(parent)
        self.configuration = configuration
        self._stop_requested = threading.Event()

    def request_stop(self):
        self._stop_requested.set()

    def run(self):
        try:
            output_file = PowerStudyRunner().execute(
                self.configuration,
                stop_requested=self._stop_requested.is_set,
                sample_callback=self.sample_ready.emit,
                log=self.log_ready.emit,
                started_callback=self.timing_started.emit,
            )
            self.completed.emit(output_file)
        except PowerStudyStopped:
            self.stopped.emit()
        except Exception as exception:
            self.failed.emit(str(exception))


class PowerStudyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self._timing_started_at = None
        self._run_duration_seconds = 0.0
        self._completed_normally = False
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(1000)
        self.progress_timer.timeout.connect(self._update_timer)
        self.setWindowTitle("Hornbill Four-Channel Power Study")
        self.resize(980, 760)
        defaults = _hornbill_defaults()

        self.dut_address = QLineEdit(defaults.get("PowerStudy_DUT", ""))
        self.ac_address = QLineEdit(defaults.get("PowerStudy_ACSource", ""))
        self.daq_address = QLineEdit(defaults.get("PowerStudy_DAQ", ""))
        self.n3300a_address = QLineEdit(defaults.get("PowerStudy_N3300A", ""))
        self.excavator_address = QLineEdit(
            defaults.get("PowerStudy_Excavator", "")
        )
        self.scope_enabled = QCheckBox("Capture full-screen oscilloscope image per sample")
        self.scope_address = QLineEdit(
            defaults.get("PowerStudy_OSC", defaults.get("OSC", ""))
        )
        self.scope_address.setEnabled(False)
        self.scope_ink_saver = QComboBox()
        self.scope_ink_saver.addItems(("ON", "OFF"))
        self.scope_ink_saver.setEnabled(False)
        self.scope_enabled.toggled.connect(self.scope_address.setEnabled)
        self.scope_enabled.toggled.connect(self.scope_ink_saver.setEnabled)
        address_form = QFormLayout()
        address_form.addRow("Hornbill DUT:", self.dut_address)
        address_form.addRow("AC Source 68xxA:", self.ac_address)
        address_form.addRow("DAQ34970A with Internal DMM:", self.daq_address)
        address_form.addRow("N3300A Five-Channel Load:", self.n3300a_address)
        address_form.addRow("CH4 Excavator ELoad:", self.excavator_address)
        address_form.addRow("Oscilloscope Capture:", self.scope_enabled)
        address_form.addRow("Oscilloscope Address:", self.scope_address)
        address_form.addRow("Oscilloscope Ink Saver:", self.scope_ink_saver)
        address_group = QGroupBox("Instrument Addresses")
        address_group.setLayout(address_form)

        self.load_rows = []
        load_layout = QGridLayout()
        for column, title in enumerate(
            (
                "DUT",
                "Condition",
                "Configured Current",
                "Fixed Load Assignment",
                "DAQ Channel",
            )
        ):
            load_layout.addWidget(QLabel(title), 0, column)
        load_assignments = (
            "N3300A CH1 + CH2 (current split equally)",
            "N3300A CH3",
            "N3300A CH4 + CH5 (current split equally)",
            "Excavator ELoad (fixed 20 A)",
        )
        for row, (default_condition, load_assignment) in enumerate(
            zip(DEFAULT_CONDITIONS, load_assignments), start=1
        ):
            condition = QComboBox()
            condition.addItems((DISABLED_CONDITION, *DEFAULT_CONDITIONS))
            condition.setCurrentText(default_condition)
            current = QDoubleSpinBox()
            current.setRange(0.001, 20.0)
            current.setDecimals(3)
            current.setSuffix(" A")
            current.setValue(CONDITION_BY_NAME[default_condition][1])
            if row == 4:
                current.setValue(EXCAVATOR_CURRENT_A)
                current.setEnabled(False)
            daq_channel = QSpinBox()
            daq_channel.setRange(1, 999)
            daq_channel.setValue(100 + row)
            load_layout.addWidget(QLabel(f"CH{row}"), row, 0)
            load_layout.addWidget(condition, row, 1)
            load_layout.addWidget(current, row, 2)
            load_layout.addWidget(QLabel(load_assignment), row, 3)
            load_layout.addWidget(daq_channel, row, 4)
            condition.currentTextChanged.connect(
                lambda text, current_input=current, daq_input=daq_channel,
                dut_channel=row: self._condition_changed(
                    text, current_input, daq_input, dut_channel
                )
            )
            self.load_rows.append((condition, current, daq_channel))
        condition_details = QLabel(
            "High Knee: 60 V / 5 A | Mid Knee 1: 37.5 V / 8 A | "
            "Mid Knee 2: 24 V / 12.5 A | Low Knee: 15 V / 20 A"
        )
        condition_details.setWordWrap(True)
        load_layout.addWidget(condition_details, 5, 0, 1, 5)
        channel_buttons = QHBoxLayout()
        enable_all_button = QPushButton("Enable All")
        enable_all_button.clicked.connect(self._enable_all_channels)
        channel_buttons.addWidget(enable_all_button)
        for channel in range(1, 5):
            channel_button = QPushButton(f"CH{channel} Only")
            channel_button.clicked.connect(
                lambda _checked=False, selected_channel=channel:
                    self._select_only_channel(selected_channel)
            )
            channel_buttons.addWidget(channel_button)
        load_layout.addLayout(channel_buttons, 6, 0, 1, 5)
        load_group = QGroupBox("Per-Channel Conditions, Current, and Fixed Load Wiring")
        load_group.setLayout(load_layout)

        self.duration = QDoubleSpinBox()
        self.duration.setRange(0.1, 10000.0)
        self.duration.setValue(1.0)
        self.duration_unit = QComboBox()
        self.duration_unit.addItems(("Hours", "Minutes"))
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(self.duration)
        duration_layout.addWidget(self.duration_unit)
        self.interval = QDoubleSpinBox()
        self.interval.setRange(0.5, 3600.0)
        self.interval.setValue(10.0)
        self.interval.setSuffix(" s")
        self.settling = QDoubleSpinBox()
        self.settling.setRange(0.0, 300.0)
        self.settling.setValue(5.0)
        self.settling.setSuffix(" s")
        self.ac_voltage = QDoubleSpinBox()
        self.ac_voltage.setRange(1.0, 500.0)
        self.ac_voltage.setValue(230.0)
        self.ac_voltage.setSuffix(" V")
        self.ac_current = QDoubleSpinBox()
        self.ac_current.setRange(0.1, 100.0)
        self.ac_current.setValue(10.0)
        self.ac_current.setSuffix(" A")
        self.ac_frequency = QDoubleSpinBox()
        self.ac_frequency.setRange(1.0, 1000.0)
        self.ac_frequency.setValue(50.0)
        self.ac_frequency.setSuffix(" Hz")
        self.voltage_sense = QComboBox()
        self.voltage_sense.addItems(("INT", "EXT"))
        self.daq_voltage_range = QLineEdit("AUTO")
        self.daq_voltage_resolution = QLineEdit("MIN")
        timing_form = QFormLayout()
        timing_form.addRow("Test Duration:", duration_layout)
        timing_form.addRow("Sample Interval:", self.interval)
        timing_form.addRow("Power Settling Delay:", self.settling)
        timing_form.addRow("AC Input Voltage:", self.ac_voltage)
        timing_form.addRow("AC Current Limit:", self.ac_current)
        timing_form.addRow("AC Frequency:", self.ac_frequency)
        timing_form.addRow("DUT Voltage Sense:", self.voltage_sense)
        timing_form.addRow("DAQ DC Voltage Range:", self.daq_voltage_range)
        timing_form.addRow("DAQ DC Voltage Resolution:", self.daq_voltage_resolution)
        timing_group = QGroupBox("Timing and Input Conditions")
        timing_group.setLayout(timing_form)

        self.output_file = QLineEdit(str(Path(csv_folder) / "power_study.csv"))
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_output)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_file)
        output_layout.addWidget(browse_button)

        self.start_button = QPushButton("Start Power Study")
        self.start_button.clicked.connect(self.start_test)
        self.stop_button = QPushButton("Stop and Safe Shutdown")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_test)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        self.status = QLabel("Ready - enable any combination of DUT channels")
        self.time_status = QLabel("Elapsed 00:00:00 | Remaining --:--:--")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Power Study %p%")
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addWidget(address_group)
        layout.addWidget(load_group)
        layout.addWidget(timing_group)
        layout.addLayout(output_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.status)
        layout.addWidget(self.time_status)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log, 1)

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Power Study", self.output_file.text(), "CSV Files (*.csv)"
        )
        if path:
            self.output_file.setText(path)

    @staticmethod
    def _condition_changed(
        condition_name, current_input, daq_input, dut_channel=None
    ):
        enabled = condition_name != DISABLED_CONDITION
        current_input.setEnabled(enabled and dut_channel != 4)
        daq_input.setEnabled(enabled)
        if enabled:
            current_input.setValue(
                EXCAVATOR_CURRENT_A
                if dut_channel == 4
                else CONDITION_BY_NAME[condition_name][1]
            )

    def _enable_all_channels(self):
        for row, default_condition in zip(self.load_rows, DEFAULT_CONDITIONS):
            row[0].setCurrentText(default_condition)

    def _select_only_channel(self, selected_channel):
        for channel, (row, default_condition) in enumerate(
            zip(self.load_rows, DEFAULT_CONDITIONS), start=1
        ):
            row[0].setCurrentText(
                default_condition
                if channel == selected_channel
                else DISABLED_CONDITION
            )

    def _configuration(self):
        multiplier = 3600.0 if self.duration_unit.currentText() == "Hours" else 60.0
        return PowerStudyConfiguration(
            dut_address=self.dut_address.text().strip(),
            ac_source_address=self.ac_address.text().strip(),
            daq_address=self.daq_address.text().strip(),
            n3300a_address=self.n3300a_address.text().strip(),
            excavator_address=self.excavator_address.text().strip(),
            conditions=tuple(row[0].currentText() for row in self.load_rows),
            channel_currents=tuple(row[1].value() for row in self.load_rows),
            daq_channels=tuple(row[2].value() for row in self.load_rows),
            duration_seconds=self.duration.value() * multiplier,
            sample_interval_seconds=self.interval.value(),
            settling_seconds=self.settling.value(),
            ac_voltage=self.ac_voltage.value(),
            ac_current_limit=self.ac_current.value(),
            ac_frequency=self.ac_frequency.value(),
            voltage_sense=self.voltage_sense.currentText(),
            daq_voltage_range=self.daq_voltage_range.text().strip(),
            daq_voltage_resolution=self.daq_voltage_resolution.text().strip(),
            scope_enabled=self.scope_enabled.isChecked(),
            scope_address=self.scope_address.text().strip(),
            scope_ink_saver=self.scope_ink_saver.currentText(),
            output_file=Path(self.output_file.text().strip()),
        )

    def start_test(self):
        if self.worker is not None and self.worker.isRunning():
            return
        try:
            configuration = self._configuration()
            configuration.validate()
        except ValueError as exception:
            QMessageBox.warning(self, "Invalid Power Study Settings", str(exception))
            return
        self.log.clear()
        enabled_channels = [
            point.channel for point in configuration.knee_points
        ]
        self.log.append(
            "Starting Power Study for DUT channel(s): "
            + ", ".join(map(str, enabled_channels))
        )
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status.setText("Starting instruments...")
        self._completed_normally = False
        self._timing_started_at = None
        self._run_duration_seconds = configuration.duration_seconds
        self.progress_bar.setValue(0)
        self.time_status.setText("Preparing instruments | Remaining --:--:--")
        self.worker = PowerStudyWorker(configuration, self)
        self.worker.sample_ready.connect(self._sample_ready)
        self.worker.log_ready.connect(self.log.append)
        self.worker.timing_started.connect(self._timing_started)
        self.worker.completed.connect(self._completed)
        self.worker.failed.connect(self._failed)
        self.worker.stopped.connect(lambda: self.log.append("Stopped by user"))
        self.worker.finished.connect(self._finished)
        self.worker.start()

    def stop_test(self):
        if self.worker is not None and self.worker.isRunning():
            self.stop_button.setEnabled(False)
            self.status.setText("Stopping and disabling all outputs...")
            self.worker.request_stop()

    def _sample_ready(self, samples):
        first = samples[0]
        channel_values = ", ".join(
            f"CH{sample.knee.channel}={sample.measured_voltage:.4f} V"
            for sample in samples
        )
        self.status.setText(
            f"Running | {first.elapsed_seconds:.1f} s | "
            f"{first.total_output_power:.1f} W | {first.efficiency_percent:.2f}%"
        )
        self.log.append(channel_values)

    @staticmethod
    def _format_seconds(seconds):
        total_seconds = max(0, int(round(float(seconds))))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _timing_started(self, duration_seconds):
        self._run_duration_seconds = float(duration_seconds)
        self._timing_started_at = time.monotonic()
        self.progress_timer.start()
        self._update_timer()

    def _update_timer(self):
        if self._timing_started_at is None:
            return
        elapsed = max(0.0, time.monotonic() - self._timing_started_at)
        remaining = max(0.0, self._run_duration_seconds - elapsed)
        progress = min(
            100,
            int(elapsed * 100 / self._run_duration_seconds),
        )
        self.progress_bar.setValue(progress)
        self.time_status.setText(
            f"Elapsed {self._format_seconds(elapsed)} | "
            f"Remaining {self._format_seconds(remaining)}"
        )

    def _completed(self, output_file):
        self._completed_normally = True
        self.progress_timer.stop()
        self.progress_bar.setValue(100)
        self.time_status.setText(
            f"Elapsed {self._format_seconds(self._run_duration_seconds)} | "
            "Remaining 00:00:00"
        )
        self.log.append(f"Completed: {output_file}")

    def _failed(self, message):
        self.status.setText("Power study failed - outputs shut down")
        self.log.append(f"ERROR: {message}")
        QMessageBox.critical(self, "Power Study Error", message)

    def _finished(self):
        self.progress_timer.stop()
        failed = self.status.text().startswith("Power study failed")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if self._completed_normally:
            self.status.setText("Power study complete - DUT and loads disabled")
        elif not failed:
            self.status.setText("Power study stopped - all outputs disabled")
        worker = self.worker
        self.worker = None
        if worker is not None:
            worker.deleteLater()

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.stop_test()
            event.ignore()
            return
        event.accept()


__all__ = [
    "CSV_COLUMNS",
    "ElectronicLoad",
    "KNEE_POINTS",
    "KneePoint",
    "LoadConfiguration",
    "PowerStudyConfiguration",
    "PowerStudyDialog",
    "PowerStudyRunner",
    "PowerStudySample",
    "PowerStudyStopped",
    "PowerStudyWorker",
]
