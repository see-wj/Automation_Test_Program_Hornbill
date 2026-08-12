import csv
import inspect
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from instruments.PowerStudy import (
    CSV_COLUMNS,
    DEFAULT_CONDITIONS,
    KNEE_POINTS,
    PowerStudyConfiguration,
    PowerStudyDialog,
    PowerStudyRunner,
)
from SCPI_Library.Keysight import (
    AC_Source_68xx,
    DAQ973A,
    ELOAD_N3300A,
    Excavator,
    Hornbill,
    Oscilloscope,
)


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class FakeHornbill:
    instances = []

    def __init__(self, address):
        self.address = address
        self.calls = []
        self.__class__.instances.append(self)

    def __getattr__(self, name):
        if name == "queryError":
            return lambda: '+0,"No error"'
        return lambda *args: self.calls.append((name, args))


class FakeACSource:
    instances = []

    def __init__(self, address):
        self.address = address
        self.calls = []
        self.__class__.instances.append(self)

    def __getattr__(self, name):
        measurements = {
            "measureVoltage_AC": "230",
            "measureCurrent_AC": "5.7",
            "measurePower_AC_Real": "1300",
            "measurePower_AC_Apparent": "1311",
            "queryError": '+0,"No error"',
        }
        if name in measurements:
            return lambda: measurements[name]
        return lambda *args: self.calls.append((name, args))


class FakeDAQ:
    instances = []

    def __init__(self, address):
        self.address = address
        self.calls = []
        self.scan_channels = (101, 102, 103, 104)
        self.__class__.instances.append(self)

    def configureVoltageMeasurement(self, voltage_range, resolution, channels):
        self.scan_channels = tuple(channels)
        self.calls.append(
            ("configureVoltageMeasurement", (voltage_range, resolution, channels))
        )

    def __getattr__(self, name):
        if name == "queryError":
            return lambda: '+0,"No error"'
        return lambda *args: self.calls.append((name, args))

    def readScan(self):
        self.calls.append(("readScan", ()))
        readings = {101: 60.0, 102: 37.5, 103: 24.0, 104: 15.0}
        return [readings[channel] for channel in self.scan_channels]


class FailingDAQ(FakeDAQ):
    instances = []

    def readScan(self):
        raise RuntimeError("simulated DAQ failure")


class FakeN3300A:
    instances = []

    def __init__(self, address):
        self.address = address
        self.calls = []
        self.__class__.instances.append(self)

    def __getattr__(self, name):
        if name == "queryError":
            return lambda: '+0,"No error"'
        return lambda *args: self.calls.append((name, args))


class FakeExcavator(FakeN3300A):
    instances = []


class FakeOscilloscope:
    instances = []

    def __init__(self, address):
        self.address = address
        self.calls = []
        self.__class__.instances.append(self)

    def hardcopy(self, state):
        self.calls.append(("hardcopy", state))

    def run(self):
        self.calls.append(("run",))

    def stop(self):
        self.calls.append(("stop",))

    def read_binary_data(self):
        self.calls.append(("capture",))
        return b"PNG"


def build_configuration(output_file):
    return PowerStudyConfiguration(
        dut_address="TCPIP::DUT",
        ac_source_address="GPIB::AC",
        daq_address="GPIB::DAQ",
        n3300a_address="GPIB::N3300A",
        excavator_address="USB::EXCAVATOR",
        duration_seconds=1.0,
        sample_interval_seconds=1.0,
        settling_seconds=0.0,
        output_file=output_file,
    )


class PowerStudyTests(unittest.TestCase):
    def setUp(self):
        for fake_class in (
            FakeHornbill,
            FakeACSource,
            FakeDAQ,
            FailingDAQ,
            FakeN3300A,
            FakeExcavator,
            FakeOscilloscope,
        ):
            fake_class.instances.clear()

    def test_knee_points_are_four_simultaneous_300_w_conditions(self):
        self.assertEqual([point.channel for point in KNEE_POINTS], [1, 2, 3, 4])
        self.assertEqual([point.power for point in KNEE_POINTS], [300.0] * 4)

    def test_uses_only_existing_scpi_library_wrappers(self):
        required_methods = {
            Hornbill: (
                "queryError",
                "setMode",
                "senseVoltageSource",
                "sourVoltageLevelImmediateAmplitude",
                "sourCurrentLimitPOS",
                "outputState",
            ),
            AC_Source_68xx: (
                "clearStatus",
                "setFrequency",
                "setOutputCurrent",
                "setOutputVoltage",
                "setOutputState",
                "queryError",
                "measureVoltage_AC",
                "measureCurrent_AC",
                "measurePower_AC_Real",
                "measurePower_AC_Apparent",
            ),
            DAQ973A: (
                "clearStatus",
                "reset",
                "configureVoltageMeasurement",
                "enableAutomaticChannelDelay",
                "setScanChannels",
                "readScan",
                "queryError",
                "openAllChannels",
            ),
            ELOAD_N3300A: (
                "set_SelectChannel",
                "set_Mode",
                "set_ChannelCurrent",
                "set_OutputState",
                "clearStatus",
                "queryError",
            ),
            Excavator: (
                "setSYSTEMEMULationMode",
                "setMode",
                "setOutputCurrent",
                "setOutputState",
                "clearStatus",
                "queryError",
            ),
            Oscilloscope: (
                "hardcopy",
                "run",
                "stop",
                "read_binary_data",
            ),
        }
        for instrument_class, methods in required_methods.items():
            for method in methods:
                self.assertTrue(
                    callable(getattr(instrument_class, method, None)),
                    f"{instrument_class.__name__}.{method} is missing",
                )

        source = inspect.getsource(PowerStudyRunner)
        self.assertNotIn(".instr.write", source)
        self.assertNotIn(".instr.query", source)

    def test_runs_all_channels_calculates_efficiency_and_always_shuts_down(self):
        clock = FakeClock()
        captured = []
        with tempfile.TemporaryDirectory() as directory:
            output_file = Path(directory) / "power.csv"
            runner = PowerStudyRunner(
                hornbill_class=FakeHornbill,
                ac_source_class=FakeACSource,
                daq_class=FakeDAQ,
                n3300a_class=FakeN3300A,
                excavator_class=FakeExcavator,
                sleep_fn=clock.sleep,
                monotonic_fn=clock.monotonic,
                manage_visa_scope=False,
            )

            result = runner.execute(
                build_configuration(output_file),
                sample_callback=captured.append,
            )

            self.assertEqual(result.parent, output_file.parent)
            self.assertRegex(
                result.name,
                r"^power_\d{8}_\d{6}_\d{6}\.csv$",
            )
            self.assertEqual(len(captured), 2)
            self.assertEqual([sample.measured_voltage for sample in captured[0]], [60, 37.5, 24, 15])
            self.assertAlmostEqual(captured[0][0].total_output_power, 1200.0)
            self.assertAlmostEqual(captured[0][0].efficiency_percent, 1200 / 1300 * 100)
            with result.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))
            self.assertEqual(tuple(rows[0]), CSV_COLUMNS)
            self.assertEqual(len(rows), 9)

        dut_calls = FakeHornbill.instances[0].calls
        self.assertIn(("outputState", ("ON", 1)), dut_calls)
        self.assertEqual(dut_calls[-1], ("outputState", ("OFF", 1)))
        ac_output_calls = [
            call
            for call in FakeACSource.instances[0].calls
            if call[0] == "setOutputState"
        ]
        self.assertEqual(ac_output_calls, [("setOutputState", ("ON",))])
        for load in FakeN3300A.instances + FakeExcavator.instances:
            output_calls = [
                call
                for call in load.calls
                if call[0] in {"set_OutputState", "set_Output", "setOutputState"}
            ]
            self.assertTrue(output_calls)
            self.assertIn(output_calls[-1][1][0], {"OFF", False})

        self.assertEqual(len(FakeN3300A.instances), 1)
        n3300a_calls = FakeN3300A.instances[0].calls
        self.assertEqual(
            [args[0] for name, args in n3300a_calls if name == "set_ChannelCurrent"],
            [2.5, 2.5, 8.0, 6.25, 6.25],
        )
        self.assertEqual(len(FakeExcavator.instances), 1)
        self.assertIn(
            ("setOutputCurrent", (20.0,)),
            FakeExcavator.instances[0].calls,
        )
        self.assertIn(
            ("setSYSTEMEMULationMode", ("ELOAD",)),
            FakeExcavator.instances[0].calls,
        )
        self.assertIn(
            ("setMode", ("CURRent",)),
            FakeExcavator.instances[0].calls,
        )
        self.assertIn(
            ("configureVoltageMeasurement", ("AUTO", "MIN", (101, 102, 103, 104))),
            FakeDAQ.instances[0].calls,
        )
        self.assertIn(("reset", ()), FakeDAQ.instances[0].calls)
        self.assertIn(
            ("enableAutomaticChannelDelay", ((101, 102, 103, 104),)),
            FakeDAQ.instances[0].calls,
        )
        self.assertIn(
            ("setScanChannels", ((101, 102, 103, 104),)),
            FakeDAQ.instances[0].calls,
        )

    def test_builds_timestamped_csv_name(self):
        result = PowerStudyRunner._timestamped_output_file(
            Path("results") / "powerstudy.csv",
            datetime(2026, 8, 5, 14, 3, 2, 123456),
        )

        self.assertEqual(
            result,
            Path("results") / "powerstudy_20260805_140302_123456.csv",
        )

    def test_optional_scope_captures_each_sample_and_records_paths(self):
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as directory:
            output_file = Path(directory) / "power.csv"
            configuration = replace(
                build_configuration(output_file),
                scope_enabled=True,
                scope_address="TCPIP::SCOPE",
                scope_ink_saver="OFF",
            )
            runner = PowerStudyRunner(
                hornbill_class=FakeHornbill,
                ac_source_class=FakeACSource,
                daq_class=FakeDAQ,
                n3300a_class=FakeN3300A,
                excavator_class=FakeExcavator,
                oscilloscope_class=FakeOscilloscope,
                sleep_fn=clock.sleep,
                monotonic_fn=clock.monotonic,
                manage_visa_scope=False,
            )

            result = runner.execute(configuration)
            with result.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

            screenshot_paths = {row["Scope_Screenshot"] for row in rows}
            self.assertEqual(len(screenshot_paths), 2)
            self.assertTrue(
                all(Path(path).read_bytes() == b"PNG" for path in screenshot_paths)
            )
            self.assertEqual(
                FakeOscilloscope.instances[0].calls,
                [
                    ("hardcopy", "OFF"),
                    ("run",),
                    ("stop",),
                    ("capture",),
                    ("run",),
                    ("stop",),
                    ("capture",),
                    ("run",),
                ],
            )

    def test_conditions_are_independently_selectable(self):
        with tempfile.TemporaryDirectory() as directory:
            configuration = build_configuration(Path(directory) / "power.csv")
            configuration = PowerStudyConfiguration(
                **{
                    **configuration.__dict__,
                    "conditions": ("Low Knee",) * 4,
                    "channel_currents": (1.0, 2.0, 3.0, 4.0),
                }
            )
            configuration.validate()

        self.assertEqual(
            [(point.voltage, point.current) for point in configuration.knee_points],
            [(15.0, 1.0), (15.0, 2.0), (15.0, 3.0), (15.0, 20.0)],
        )

    def test_formats_progress_time_as_hours_minutes_seconds(self):
        self.assertEqual(PowerStudyDialog._format_seconds(3661), "01:01:01")

    def test_none_condition_runs_only_selected_dut_channel_and_load(self):
        clock = FakeClock()
        captured = []
        with tempfile.TemporaryDirectory() as directory:
            configuration = build_configuration(Path(directory) / "single.csv")
            configuration = PowerStudyConfiguration(
                **{
                    **configuration.__dict__,
                    "conditions": ("None", "Mid Knee 1", "None", "None"),
                    "channel_currents": (5.0, 7.5, 12.5, 20.0),
                }
            )
            runner = PowerStudyRunner(
                hornbill_class=FakeHornbill,
                ac_source_class=FakeACSource,
                daq_class=FakeDAQ,
                n3300a_class=FakeN3300A,
                excavator_class=FakeExcavator,
                sleep_fn=clock.sleep,
                monotonic_fn=clock.monotonic,
                manage_visa_scope=False,
            )

            runner.execute(configuration, sample_callback=captured.append)

        self.assertEqual(len(captured[0]), 1)
        self.assertEqual(captured[0][0].knee.channel, 2)
        self.assertEqual(captured[0][0].knee.current, 7.5)
        self.assertEqual(FakeExcavator.instances, [])
        n3300a_calls = FakeN3300A.instances[0].calls
        self.assertEqual(
            [args[0] for name, args in n3300a_calls if name == "set_ChannelCurrent"],
            [7.5],
        )
        self.assertIn(
            ("configureVoltageMeasurement", ("AUTO", "MIN", (102,))),
            FakeDAQ.instances[0].calls,
        )

    def test_rejects_unknown_condition(self):
        with tempfile.TemporaryDirectory() as directory:
            configuration = build_configuration(Path(directory) / "power.csv")
            configuration = PowerStudyConfiguration(
                **{
                    **configuration.__dict__,
                    "conditions": (*DEFAULT_CONDITIONS[:3], "Unknown"),
                }
            )
            with self.assertRaisesRegex(ValueError, "unsupported condition"):
                configuration.validate()

    def test_measurement_failure_still_disables_every_output(self):
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as directory:
            runner = PowerStudyRunner(
                hornbill_class=FakeHornbill,
                ac_source_class=FakeACSource,
                daq_class=FailingDAQ,
                n3300a_class=FakeN3300A,
                excavator_class=FakeExcavator,
                sleep_fn=clock.sleep,
                monotonic_fn=clock.monotonic,
                manage_visa_scope=False,
            )
            with self.assertRaisesRegex(RuntimeError, "simulated DAQ failure"):
                runner.execute(
                    build_configuration(Path(directory) / "power.csv")
                )

        ac_output_calls = [
            call
            for call in FakeACSource.instances[0].calls
            if call[0] == "setOutputState"
        ]
        self.assertEqual(ac_output_calls, [("setOutputState", ("ON",))])
        self.assertEqual(
            FakeHornbill.instances[0].calls[-1],
            ("outputState", ("OFF", 1)),
        )

    def test_main_test_selection_registers_power_study_dialog(self):
        import GUI

        registry = GUI.MainWindow._create_dialog_registry(object())
        registration = next(
            item
            for item in registry.registrations
            if item.owner_attribute == "power_study_dialog"
        )
        self.assertIs(registration.factory, PowerStudyDialog)
        self.assertIn("power_study_dialog", GUI.MainWindow.TEST_SELECTION_DIALOGS)


if __name__ == "__main__":
    unittest.main()
