import base64
import csv
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook
from PyQt5.QtWidgets import QApplication, QLabel

from instruments.LowVoltageTest import (
    LowVoltageScopeCaptureTest,
    LowVoltageTestDialog,
    diag_channel_selector,
    low_voltage_points,
    strip_ieee_binary_block,
)


class FakeSession:
    def __init__(self):
        self.queries = []
        self.writes = []
        self.closed = False

    def query(self, command):
        self.queries.append(command)
        return '+0,"No error"'

    def write(self, command):
        self.writes.append(command)

    def close(self):
        self.closed = True


class FakeHornbill:
    instances = []

    def __init__(self, address):
        self.address = address
        self.instr = FakeSession()
        self.commands = []
        self.__class__.instances.append(self)

    def setMode(self, mode, channel):
        self.commands.append(("mode", mode, channel))

    def sourVoltageLevelImmediateAmplitude(self, value, channel):
        self.commands.append(("voltage", value, channel))

    def senseVoltageSource(self, mode, channel):
        self.commands.append(("sense", mode, channel))

    def diag_POKE_LOW_VOLTAGE_CONTROL(self, channel, point):
        self.commands.append(("poke", channel, point))

    def outputState(self, state, channel):
        self.commands.append(("output", state, channel))


class FakeOscilloscope:
    instances = []
    image_data = b"#13PNG\n"

    def __init__(self, address):
        self.address = address
        self.instr = FakeSession()
        self.commands = []
        self.__class__.instances.append(self)

    def run(self):
        self.commands.append("run")

    def stop(self):
        self.commands.append("stop")

    def hardcopy(self, state):
        self.commands.append(("ink_saver", state))

    def read_binary_data(self):
        self.commands.append("capture")
        return self.image_data

    def measureVMIN(self, channel):
        self.commands.append(("vmin", channel))
        return [0.79]

    def measureVMAX(self, channel):
        self.commands.append(("vmax", channel))
        return [0.81]


class FakeDmmSession(FakeSession):
    def __init__(self, readings):
        super().__init__()
        self.readings = iter(readings)

    def query(self, command):
        self.queries.append(command)
        return str(next(self.readings))


class FakeDMM344:
    instances = []
    readings = (0.8, 0.9, 1.0)

    def __init__(self, address):
        self.address = address
        self.instr = FakeDmmSession(self.readings)
        self.__class__.instances.append(self)


class FakeDMM3458:
    instances = []
    readings = (1.234,)

    def __init__(self, address):
        self.address = address
        self.instr = FakeSession()
        self.commands = []
        self._readings = iter(self.readings)
        self.__class__.instances.append(self)

    def setDCV(self, value):
        self.commands.append(("dcv", value))

    def setNPLC(self, value):
        self.commands.append(("nplc", value))

    def setAutoZeroMode(self, value):
        self.commands.append(("azero", value))

    def queryMeasurement(self):
        self.commands.append(("measure",))
        return str(next(self._readings))


class SignalRecorder:
    def __init__(self):
        self.values = []

    def emit(self, value):
        self.values.append(value)


class FakeWorker:
    def __init__(self):
        self.run_context = None
        self.progress = SignalRecorder()
        self.progress_value = SignalRecorder()
        self.checkpoints = 0

    def checkpoint(self):
        self.checkpoints += 1

    def interruptible_sleep(self, seconds):
        return None


class LowVoltageTestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        FakeHornbill.instances.clear()
        FakeOscilloscope.instances.clear()
        FakeOscilloscope.image_data = b"#13PNG\n"
        FakeDMM344.instances.clear()
        FakeDMM3458.instances.clear()

    def test_default_points_follow_100_increment(self):
        points = low_voltage_points()

        self.assertEqual(53, len(points))
        self.assertEqual(800, points[0])
        self.assertEqual(6000, points[-1])
        self.assertTrue(
            all(
                right - left == 100
                for left, right in zip(points, points[1:])
            )
        )

    def test_user_channels_map_to_zero_based_diag_selectors(self):
        self.assertEqual(
            [0, 1, 2, 3],
            [diag_channel_selector(channel) for channel in range(1, 5)],
        )

    def test_strips_scope_ieee_binary_header(self):
        self.assertEqual(b"PNG", strip_ieee_binary_block(b"#13PNG\n"))

    def test_dialog_exposes_configurable_endpoints(self):
        dialog = LowVoltageTestDialog()
        try:
            self.assertEqual(800, dialog.initial_point.value())
            self.assertEqual(6000, dialog.final_point.value())
            self.assertEqual(100, dialog.increment.value())
            self.assertEqual(3.0, dialog.scope_run_delay.value())
            self.assertEqual("ON", dialog.ink_saver.currentText())
            self.assertTrue(dialog.scope_vpp_enabled.isChecked())
            self.assertTrue(dialog.excel_report_enabled.isChecked())
            self.assertFalse(dialog.dmm_enabled.isChecked())
            self.assertFalse(dialog.dmm_address.isEnabled())
        finally:
            dialog.close()

    def test_custom_increment_controls_generated_points(self):
        self.assertEqual(
            (800, 850, 900, 950, 1000),
            low_voltage_points(800, 1000, 50),
        )

    def test_main_test_selection_registers_low_voltage_dialog(self):
        import GUI

        registry = GUI.MainWindow._create_dialog_registry(object())
        registration = next(
            item
            for item in registry.registrations
            if item.owner_attribute == "low_voltage_test_dialog"
        )

        self.assertEqual(
            "Hornbill Low Voltage Scope Capture",
            registration.title,
        )
        self.assertIs(registration.factory, LowVoltageTestDialog)

    def test_captures_one_png_for_every_diag_point(self):
        worker = FakeWorker()
        with tempfile.TemporaryDirectory() as temporary_directory:
            test = LowVoltageScopeCaptureTest(
                hornbill_factory=FakeHornbill,
                oscilloscope_factory=FakeOscilloscope,
            )
            images = test.execute(
                {
                    "PSU": "DUT",
                    "OSC": "SCOPE",
                    "PSU_Channel": 2,
                    "LowVoltageInitialPoint": 800,
                    "LowVoltageFinalPoint": 1000,
                    "LowVoltageIncrement": 50,
                    "OSC_Channel": 1,
                    "updatedelay": 0,
                    "ScopeRunCaptureDelay": 0,
                    "InkSaver": "OFF",
                    "savedir": temporary_directory,
                },
                loop_index=0,
                worker=worker,
            )

            self.assertEqual(5, len(images))
            self.assertTrue(all(Path(path).read_bytes() == b"PNG" for path in images))
            self.assertFalse(
                list(Path(temporary_directory).rglob("*.csv"))
            )

        dut = FakeHornbill.instances[0]
        self.assertEqual(
            [
                ("sense", "EXT", 1),
                ("mode", "VOLTAGE", 2),
                ("voltage", 0, 2),
                ("output", "ON", 2),
                ("poke", 1, 800),
                ("poke", 1, 850),
                ("poke", 1, 900),
                ("poke", 1, 950),
                ("poke", 1, 1000),
                ("output", "OFF", 2),
            ],
            dut.commands,
        )
        self.assertEqual(["SYST:ERR?"] * 5, dut.instr.queries)
        self.assertEqual([], dut.instr.writes)
        self.assertTrue(dut.instr.closed)
        self.assertTrue(FakeOscilloscope.instances[0].instr.closed)
        self.assertIn(
            ":CHANnel1:DISPlay ON",
            FakeOscilloscope.instances[0].instr.writes,
        )
        self.assertIn(
            ("ink_saver", "OFF"),
            FakeOscilloscope.instances[0].commands,
        )
        self.assertEqual(100, worker.progress_value.values[-1])

    def test_excel_report_embeds_waveform_and_scope_vpp(self):
        FakeOscilloscope.image_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
            "/x8AAusB9Y9Z4G8AAAAASUVORK5CYII="
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            test = LowVoltageScopeCaptureTest(
                hornbill_factory=FakeHornbill,
                oscilloscope_factory=FakeOscilloscope,
            )
            test.execute(
                {
                    "PSU": "DUT",
                    "OSC": "SCOPE",
                    "PSU_Channel": 1,
                    "LowVoltageInitialPoint": 800,
                    "LowVoltageFinalPoint": 800,
                    "OSC_Channel": 4,
                    "updatedelay": 0,
                    "ScopeRunCaptureDelay": 0,
                    "ScopeVppEnabled": True,
                    "ExcelReportEnabled": True,
                    "InkSaver": "ON",
                    "savedir": temporary_directory,
                }
            )

            report_path = (
                Path(temporary_directory)
                / "low_voltage_scope"
                / "low_voltage_scope_report_loop_001.xlsx"
            )
            workbook = load_workbook(report_path)
            worksheet = workbook["Low Voltage Capture"]

            self.assertEqual(800, worksheet["C2"].value)
            self.assertAlmostEqual(0.79, worksheet["E2"].value)
            self.assertAlmostEqual(0.81, worksheet["F2"].value)
            self.assertAlmostEqual(20.0, worksheet["G2"].value)
            self.assertEqual(1, len(worksheet._images))
            self.assertIn(
                ("vmin", "CHANNEL4"),
                FakeOscilloscope.instances[0].commands,
            )
            self.assertIn(
                ("vmax", "CHANNEL4"),
                FakeOscilloscope.instances[0].commands,
            )

    def test_optional_344xxa_dmm_records_one_measurement_per_image(self):
        worker = FakeWorker()
        with tempfile.TemporaryDirectory() as temporary_directory:
            test = LowVoltageScopeCaptureTest(
                hornbill_factory=FakeHornbill,
                oscilloscope_factory=FakeOscilloscope,
                dmm_344xxa_factory=FakeDMM344,
            )
            images = test.execute(
                {
                    "PSU": "DUT",
                    "OSC": "SCOPE",
                    "DMM_Enabled": True,
                    "DMM": "DMM",
                    "DMM_Model": "344xxA",
                    "PSU_Channel": 1,
                    "LowVoltageInitialPoint": 800,
                    "LowVoltageFinalPoint": 1000,
                    "OSC_Channel": 1,
                    "updatedelay": 0,
                    "ScopeRunCaptureDelay": 0,
                    "InkSaver": "ON",
                    "savedir": temporary_directory,
                },
                worker=worker,
            )

            csv_path = (
                Path(temporary_directory)
                / "low_voltage_scope"
                / "low_voltage_dmm_measurements_loop_001.csv"
            )
            with csv_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(len(images), 3)
        self.assertEqual([row["DIAG Point"] for row in rows], ["800", "900", "1000"])
        self.assertEqual(
            [float(row["DMM Voltage (V)"]) for row in rows],
            [0.8, 0.9, 1.0],
        )
        self.assertEqual(
            FakeDMM344.instances[0].instr.queries,
            ["MEAS:VOLT:DC?"] * 3,
        )
        self.assertTrue(FakeDMM344.instances[0].instr.closed)

    def test_optional_3458a_uses_legacy_configuration_and_measurement(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            test = LowVoltageScopeCaptureTest(
                hornbill_factory=FakeHornbill,
                oscilloscope_factory=FakeOscilloscope,
                dmm_3458a_factory=FakeDMM3458,
            )
            test.execute(
                {
                    "PSU": "DUT",
                    "OSC": "SCOPE",
                    "DMM_Enabled": True,
                    "DMM": "GPIB0::22::INSTR",
                    "DMM_Model": "3458A",
                    "PSU_Channel": 1,
                    "LowVoltageInitialPoint": 800,
                    "LowVoltageFinalPoint": 800,
                    "OSC_Channel": 1,
                    "updatedelay": 0,
                    "ScopeRunCaptureDelay": 0,
                    "InkSaver": "ON",
                    "savedir": temporary_directory,
                }
            )

        self.assertEqual(
            FakeDMM3458.instances[0].commands,
            [("dcv", "10"), ("nplc", "10"), ("azero", "ON"), ("measure",)],
        )
        self.assertTrue(FakeDMM3458.instances[0].instr.closed)

    def test_dialog_requires_unique_dmm_address_only_when_enabled(self):
        dialog = LowVoltageTestDialog()
        self.addCleanup(dialog.close)
        dialog.dut_address.setText("DUT")
        dialog.scope_address.setText("SCOPE")
        dialog.output_directory.setText("output")

        disabled_configuration = dialog._configuration()
        self.assertFalse(disabled_configuration["DMM_Enabled"])

        dialog.dmm_enabled.setChecked(True)
        self.assertTrue(dialog.dmm_address.isEnabled())
        with self.assertRaisesRegex(ValueError, "DMM address is required"):
            dialog._configuration()
        dialog.dmm_address.setText("DUT")
        with self.assertRaisesRegex(ValueError, "must be different"):
            dialog._configuration()
        dialog.dmm_address.setText("DMM")

        enabled_configuration = dialog._configuration()
        self.assertTrue(enabled_configuration["DMM_Enabled"])
        self.assertEqual(enabled_configuration["DMM_Model"], "344xxA")
        self.assertEqual(enabled_configuration["LowVoltageIncrement"], 100)
        self.assertTrue(enabled_configuration["ScopeVppEnabled"])
        self.assertTrue(enabled_configuration["ExcelReportEnabled"])


if __name__ == "__main__":
    unittest.main()
