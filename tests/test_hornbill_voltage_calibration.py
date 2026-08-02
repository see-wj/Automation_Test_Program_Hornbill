import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from instruments.TestVolt_HB_3458 import CalWorker, normalize_visa_address
from instruments.TestVolt_HB_3458 import VoltageCalibrationDialog
from instruments.TestVolt_HB_34470A import CalWorker as CalWorker34470A
from instruments.TestVolt_HB_34470A import (
    VoltageCalibrationDialog as VoltageCalibration34470ADialog,
)


class FakeInstrument:
    def __init__(self, readings=()):
        self.commands = []
        self.readings = iter(readings)
        self.timeout = None
        self.closed = False

    def write(self, command):
        self.commands.append(("write", command))

    def query(self, command):
        self.commands.append(("query", command))
        if command == "SYST:ERR?":
            return '+0,"No error"'
        return next(self.readings)

    def close(self):
        self.closed = True


class FakeResourceManager:
    def __init__(self, instruments):
        self.instruments = instruments
        self.closed = False

    def open_resource(self, address):
        return self.instruments[address]

    def list_resources(self):
        return tuple(self.instruments)

    def close(self):
        self.closed = True


class NoOpenResourceManager(FakeResourceManager):
    def open_resource(self, address):
        raise AssertionError(f"Worker reopened preconnected resource: {address}")


class HornbillVoltageCalibrationTests(unittest.TestCase):
    def create_worker(self, psu, dmm, resource_manager):
        return CalWorker(
            "TCPIP0::PSU::INSTR",
            "GPIB0::22",
            "PP8000A",
            1,
            ["P1", "P2"],
            resource_manager_factory=lambda: resource_manager,
            command_delay=0,
            settling_delay=0,
        )

    def test_3458a_sequence_saves_both_calibration_points(self):
        psu = FakeInstrument()
        dmm = FakeInstrument(["1.23456789", "59.8765432"])
        resource_manager = FakeResourceManager({
            "TCPIP0::PSU::inst0::INSTR": psu,
            "GPIB0::22::INSTR": dmm,
        })
        worker = self.create_worker(psu, dmm, resource_manager)
        errors = []
        worker.error.connect(errors.append)

        worker.run()

        self.assertEqual(errors, [])
        psu_writes = [command for operation, command in psu.commands if operation == "write"]
        self.assertIn('CAL:STAT ON,"PP8000A"', psu_writes)
        self.assertIn("CAL:VOLT 60,(@1)", psu_writes)
        self.assertIn("CAL:LEV P1", psu_writes)
        self.assertIn("CAL:DATA 1.23456789", psu_writes)
        self.assertIn("CAL:LEV P2", psu_writes)
        self.assertIn("CAL:DATA 59.8765432", psu_writes)
        self.assertIn("CAL:SAVE", psu_writes)
        self.assertIn("CAL:STAT OFF", psu_writes)
        self.assertEqual(psu_writes[-1], "OUTPUT:STATE OFF,(@1)")
        self.assertIn(("write", "DCV 10"), dmm.commands)
        self.assertIn(("write", "DCV 100"), dmm.commands)
        self.assertEqual(
            dmm.commands.count(("query", "TARM SGL,1")),
            2,
        )
        self.assertTrue(psu.closed)
        self.assertTrue(dmm.closed)
        self.assertTrue(resource_manager.closed)

    def test_measurement_failure_exits_calibration_mode_and_disables_output(self):
        psu = FakeInstrument()
        dmm = FakeInstrument(["not-a-number"])
        resource_manager = FakeResourceManager({
            "TCPIP0::PSU::inst0::INSTR": psu,
            "GPIB0::22::INSTR": dmm,
        })
        worker = self.create_worker(psu, dmm, resource_manager)
        errors = []
        worker.error.connect(errors.append)

        worker.run()

        self.assertEqual(len(errors), 1)
        self.assertIn("Invalid 3458A reading", errors[0])
        psu_writes = [command for operation, command in psu.commands if operation == "write"]
        self.assertIn("CAL:STAT OFF", psu_writes)
        self.assertEqual(psu_writes[-1], "OUTPUT:STATE OFF,(@1)")
        self.assertNotIn("CAL:SAVE", psu_writes)

    def test_34470a_sequence_uses_modern_scpi_and_saves_both_points(self):
        psu = FakeInstrument()
        dmm = FakeInstrument(["1.23456789", "59.8765432"])
        dmm_address = "USB0::0x2A8D::0x0501::MY57702180::0::INSTR"
        resource_manager = FakeResourceManager({
            "TCPIP0::PSU::inst0::INSTR": psu,
            dmm_address: dmm,
        })
        worker = CalWorker34470A(
            "TCPIP0::PSU::INSTR",
            dmm_address,
            "PP8000A",
            1,
            ["P1", "P2"],
            resource_manager_factory=lambda: resource_manager,
            command_delay=0,
            settling_delay=0,
        )
        errors = []
        worker.error.connect(errors.append)

        worker.run()

        self.assertEqual(errors, [])
        dmm_writes = [
            command
            for operation, command in dmm.commands
            if operation == "write"
        ]
        self.assertIn("*RST", dmm_writes)
        self.assertIn("CONF:VOLT:DC 10", dmm_writes)
        self.assertIn("SENS:VOLT:DC:NPLC 100", dmm_writes)
        self.assertIn("SENS:VOLT:DC:RANG 10", dmm_writes)
        self.assertIn("SENS:VOLT:DC:RANG 100", dmm_writes)
        self.assertEqual(dmm.commands.count(("query", "READ?")), 2)
        psu_writes = [
            command
            for operation, command in psu.commands
            if operation == "write"
        ]
        self.assertIn("CAL:DATA 1.23456789", psu_writes)
        self.assertIn("CAL:DATA 59.8765432", psu_writes)
        self.assertIn("CAL:SAVE", psu_writes)
        self.assertEqual(psu_writes[-1], "OUTPUT:STATE OFF,(@1)")

    def test_short_gpib_address_is_canonicalized(self):
        self.assertEqual(
            normalize_visa_address("GPIB0::22"),
            "GPIB0::22::INSTR",
        )

    def test_worker_uses_resources_opened_by_gui_thread(self):
        psu = FakeInstrument()
        dmm = FakeInstrument(["1.23456789", "59.8765432"])
        resource_manager = NoOpenResourceManager({})
        worker = CalWorker(
            "TCPIP0::PSU::INSTR",
            "GPIB0::22::INSTR",
            "PP8000A",
            1,
            ["P1", "P2"],
            command_delay=0,
            settling_delay=0,
            resource_manager=resource_manager,
            psu=psu,
            dmm=dmm,
        )
        errors = []
        worker.error.connect(errors.append)

        worker.run()

        self.assertEqual(errors, [])
        self.assertTrue(resource_manager.closed)

    def test_gui_launcher_uses_3458a_calibration_dialog(self):
        import GUI

        owner = object()
        registry = GUI.MainWindow._create_dialog_registry(owner)
        registration = next(
            item
            for item in registry.registrations
            if item.owner_attribute == "voltage_calibration_dialog"
        )

        self.assertEqual(registration.title, "Voltage Calibration - 3458A")
        self.assertIs(registration.factory, VoltageCalibrationDialog)

    def test_gui_launcher_includes_34470a_calibration_dialog(self):
        import GUI

        registry = GUI.MainWindow._create_dialog_registry(object())
        registration = next(
            item
            for item in registry.registrations
            if item.owner_attribute == "voltage_calibration_34470a_dialog"
        )

        self.assertEqual(registration.title, "Voltage Calibration - 34470A")
        self.assertIs(registration.factory, VoltageCalibration34470ADialog)

    def test_test_selection_exposes_approved_hornbill_dialogs(self):
        import GUI

        registry = GUI.MainWindow._create_dialog_registry(object())
        options = registry.indexed_selection_options(
            GUI.MainWindow.TEST_SELECTION_DIALOGS
        )

        self.assertEqual(
            [title for _index, title, _description in options],
            [
                "Voltage Calibration - 3458A",
                "Voltage Calibration - 34470A",
                "Hornbill Low Voltage Scope Capture",
                "Hornbill Noise Test Voltage Sweep",
                "DAQ973A Temperature Measurement",
                "Waveform Image Anomaly Analyzer",
            ],
        )


if __name__ == "__main__":
    unittest.main()
