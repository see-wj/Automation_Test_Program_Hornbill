import tempfile
import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from instruments.NoiseTestVoltageSweep import (
    NoiseVoltageSweepCaptureTest,
    NoiseVoltageSweepDialog,
    noise_voltage_points,
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

    def outputState(self, state, channel):
        self.commands.append(("output", state, channel))


class FakeOscilloscope:
    instances = []

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
        return b"#13PNG\n"


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


class NoiseVoltageSweepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        FakeHornbill.instances.clear()
        FakeOscilloscope.instances.clear()

    def test_default_sweep_uses_point_one_volt_increment(self):
        voltages = noise_voltage_points()

        self.assertEqual(53, len(voltages))
        self.assertEqual(0.8, voltages[0])
        self.assertEqual(6.0, voltages[-1])
        self.assertTrue(
            all(
                round(right - left, 10) == 0.1
                for left, right in zip(voltages, voltages[1:])
            )
        )

    def test_sweep_accepts_user_defined_increment(self):
        self.assertEqual(
            (0.8, 0.85, 0.9, 0.95, 1.0),
            noise_voltage_points(0.8, 1.0, 0.05),
        )
        self.assertEqual(
            (0.8, 0.87, 0.94, 1.0),
            noise_voltage_points(0.8, 1.0, 0.07),
        )

    def test_dialog_exposes_scpi_voltage_settings(self):
        dialog = NoiseVoltageSweepDialog()
        try:
            self.assertEqual(0.8, dialog.initial_voltage.value())
            self.assertEqual(6.0, dialog.final_voltage.value())
            self.assertEqual(0.1, dialog.voltage_increment.value())
            self.assertEqual(3.0, dialog.scope_run_delay.value())
            self.assertEqual("ON", dialog.ink_saver.currentText())
        finally:
            dialog.close()

    def test_main_test_selection_registers_noise_voltage_sweep(self):
        import GUI

        registry = GUI.MainWindow._create_dialog_registry(object())
        registration = next(
            item
            for item in registry.registrations
            if item.owner_attribute == "noise_voltage_sweep_dialog"
        )

        self.assertEqual(
            "Hornbill Noise Test Voltage Sweep",
            registration.title,
        )
        self.assertIs(registration.factory, NoiseVoltageSweepDialog)
        self.assertIn(
            "noise_voltage_sweep_dialog",
            GUI.MainWindow.TEST_SELECTION_DIALOGS,
        )

    def test_uses_scpi_voltage_command_and_captures_each_point(self):
        worker = FakeWorker()
        with tempfile.TemporaryDirectory() as temporary_directory:
            test = NoiseVoltageSweepCaptureTest(
                hornbill_factory=FakeHornbill,
                oscilloscope_factory=FakeOscilloscope,
            )
            images = test.execute(
                {
                    "PSU": "DUT",
                    "OSC": "SCOPE",
                    "PSU_Channel": 2,
                    "NoiseVoltageInitialVolts": 0.8,
                    "NoiseVoltageFinalVolts": 1.0,
                    "NoiseVoltageIncrementVolts": 0.1,
                    "OSC_Channel": 1,
                    "updatedelay": 0,
                    "ScopeRunCaptureDelay": 0,
                    "InkSaver": "OFF",
                    "savedir": temporary_directory,
                },
                loop_index=0,
                worker=worker,
            )

            self.assertEqual(3, len(images))
            self.assertTrue(
                all(Path(path).read_bytes() == b"PNG" for path in images)
            )

        dut = FakeHornbill.instances[0]
        self.assertEqual(
            [
                ("mode", "VOLTAGE", 2),
                ("voltage", 0, 2),
                ("output", "ON", 2),
                ("voltage", 0.8, 2),
                ("voltage", 0.9, 2),
                ("voltage", 1.0, 2),
                ("voltage", 0, 2),
                ("output", "OFF", 2),
            ],
            dut.commands,
        )
        self.assertNotIn(
            "poke",
            [command[0] for command in dut.commands],
        )
        self.assertEqual(["SYST:ERR?"] * 3, dut.instr.queries)
        self.assertEqual(["*CLS"], dut.instr.writes)
        self.assertTrue(dut.instr.closed)
        self.assertTrue(FakeOscilloscope.instances[0].instr.closed)
        self.assertIn(
            ("ink_saver", "OFF"),
            FakeOscilloscope.instances[0].commands,
        )
        self.assertEqual(100, worker.progress_value.values[-1])


if __name__ == "__main__":
    unittest.main()
