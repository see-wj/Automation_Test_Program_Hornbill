import tempfile
import unittest
from datetime import datetime
from execution.preflight import validate_preflight
from execution.run_storage import create_run_storage


def valid_voltage_parameters(output_directory):
    return {
        "savedir": output_directory,
        "noofloop": 1,
        "updatedelay": 0,
        "minVoltage": 0,
        "maxVoltage": 5,
        "minCurrent": 0,
        "maxCurrent": 1,
        "voltage_step_size": 1,
        "current_step_size": 0.1,
        "Programming_Error_Gain": 0,
        "Programming_Error_Offset": 0,
        "Readback_Error_Gain": 0,
        "Readback_Error_Offset": 0,
        "PSU_Channel": [1],
        "ELoad_Channel": 1,
        "PSU": "TCPIP0::PSU::INSTR",
        "DMM": "TCPIP0::DMM::INSTR",
        "ELoad": "TCPIP0::LOAD::INSTR",
    }


class PreflightTests(unittest.TestCase):
    def test_accepts_valid_voltage_accuracy_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            errors, requirements = validate_preflight(
                valid_voltage_parameters(directory),
                {"VoltageAccuracy": True},
            )

        self.assertEqual(errors, [])
        self.assertEqual(requirements, {"PSU", "DMM", "ELoad"})

    def test_rejects_duplicate_instrument_addresses(self):
        with tempfile.TemporaryDirectory() as directory:
            parameters = valid_voltage_parameters(directory)
            parameters["DMM"] = parameters["PSU"]
            errors, _ = validate_preflight(
                parameters,
                {"VoltageAccuracy": True},
            )

        self.assertTrue(any("same VISA address" in error for error in errors))

    def test_requires_an_actual_test_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            errors, requirements = validate_preflight(
                valid_voltage_parameters(directory),
                {"DataReport": True},
            )

        self.assertIn("Select at least one test", errors)
        self.assertEqual(requirements, set())

    def test_hornbill_scope_capture_requires_oscilloscope(self):
        with tempfile.TemporaryDirectory() as directory:
            parameters = valid_voltage_parameters(directory)
            errors, requirements = validate_preflight(
                parameters,
                {
                    "VoltageAccuracy": True,
                    "CurrentStatic(VoltageChange)withOscilloscope": True,
                },
            )

        self.assertIn("OSC", requirements)
        self.assertTrue(any("OSC" in error for error in errors))

    def test_temperature_option_requires_daq_address(self):
        with tempfile.TemporaryDirectory() as directory:
            parameters = valid_voltage_parameters(directory)
            errors, requirements = validate_preflight(
                parameters,
                {"VoltageAccuracy": True, "Temperature": True},
            )

        self.assertIn("DAQ", requirements)
        self.assertTrue(any("DAQ VISA address is required" in error for error in errors))

    def test_temperature_option_accepts_distinct_daq_address(self):
        with tempfile.TemporaryDirectory() as directory:
            parameters = valid_voltage_parameters(directory)
            parameters["DAQ"] = "USB0::DAQ::INSTR"
            errors, requirements = validate_preflight(
                parameters,
                {"VoltageAccuracy": True, "Temperature": True},
            )

        self.assertEqual(errors, [])
        self.assertIn("DAQ", requirements)


class RunStorageTests(unittest.TestCase):
    def test_creates_isolated_sanitized_run_tree(self):
        started_at = datetime(2026, 7, 14, 10, 11, 12, 345678)
        with tempfile.TemporaryDirectory() as directory:
            storage = create_run_storage(directory, "Hornbill / DUT 1", started_at)

            self.assertEqual(
                storage.root.name,
                "20260714_101112_345678_Hornbill_DUT_1",
            )
            for path in (
                storage.raw,
                storage.charts,
                storage.reports,
                storage.logs,
            ):
                self.assertTrue(path.is_dir())
            self.assertTrue(storage.log_file.is_file())
            self.assertTrue(storage.diagnostics_file.is_file())
            self.assertIn("DUT: Hornbill / DUT 1", storage.log_file.read_text())

    def test_rejects_duplicate_run_directory(self):
        started_at = datetime(2026, 7, 14, 10, 11, 12, 345678)
        with tempfile.TemporaryDirectory() as directory:
            create_run_storage(directory, "Hornbill", started_at)
            with self.assertRaises(FileExistsError):
                create_run_storage(directory, "Hornbill", started_at)


if __name__ == "__main__":
    unittest.main()
