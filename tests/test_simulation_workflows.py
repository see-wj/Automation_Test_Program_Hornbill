import os
import tempfile
import unittest
from unittest.mock import patch

import GUI
from DUT_Test_Scripts.Dolphin import DUT_Test as dut_measurements
from DUT_Test_Scripts.Hornbill import Hornbill_DUT_Test_With_ELoad as hornbill_measurements
from SCPI_Library.session_manager import (
    begin_visa_session_scope,
    close_visa_session_scope,
)
from SCPI_Library.session_manager import get_visa_resource
from SCPI_Library.simulation import get_simulation_state, reset_simulation
from SCPI_Library.simulation import inject_simulation_fault
from SCPI_Library.instrument_errors import CleanupError, ReportGenerationError


class Parameters(dict):
    __getattr__ = dict.get


class SimulationWorkflowTests(unittest.TestCase):
    def setUp(self):
        reset_simulation()

    def tearDown(self):
        close_visa_session_scope()

    def _measurement_configuration(self):
        return {
            "Instrument": "Keysight",
            "PSU": "USB0::SIM::PSU::INSTR",
            "DMM": "USB0::SIM::DMM::INSTR",
            "DMM2": "USB0::SIM::DMM2::INSTR",
            "ELoad": "USB0::SIM::ELOAD::INSTR",
            "ELoad_Channel": 1,
            "VoltageRes": "MIN",
            "OperationMode": "OFF",
            "VoltageSense": "INT",
            "Aperture": 1,
            "AutoZero": "ON",
            "InputZ": "AUTO",
            "Range": "Auto",
            "Programming_Error_Gain": 0.001,
            "Programming_Error_Offset": 0.001,
            "Readback_Error_Gain": 0.001,
            "Readback_Error_Offset": 0.001,
            "unit": "V",
            "updatedelay": 0,
            "power": 100,
            "minCurrent": 1,
            "maxCurrent": 1,
            "current_step_size": 1,
            "minVoltage": 5,
            "maxVoltage": 5,
            "voltage_step_size": 1,
            "DownTime": 0,
            "rshunt": 1,
            "DMM_Model": "344xxA",
            "ELoad_Model": "E367XXA",
        }

    def test_real_dolphin_voltage_accuracy_measurement(self):
        configuration = self._measurement_configuration()

        with patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(dut_measurements, "sleep", lambda *_: None):
            begin_visa_session_scope()
            info, measured, readback = (
                dut_measurements.NewVoltageMeasurement().Execute_Voltage_Accuracy_Current_Static(
                    configuration, 1
                )
            )

        self.assertEqual(info, [[5.0, 1.0, 0]])
        self.assertEqual(measured, [[5.0, 0]])
        self.assertEqual(readback, [[5.0, 1.0]])

    def test_real_dolphin_current_accuracy_measurement(self):
        configuration = self._measurement_configuration()
        configuration.update(minCurrent=2, maxCurrent=2)

        with patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(dut_measurements, "sleep", lambda *_: None):
            begin_visa_session_scope()
            info, measured, readback = (
                dut_measurements.NewCurrentMeasurement().executeCurrentMeasurementA(
                    configuration, 1
                )
            )

        self.assertEqual(info, [[5.0, 2.0, 0]])
        self.assertEqual(measured, [[0, 2.0]])
        self.assertEqual(readback, [[0.0, 2.0]])

    def test_real_hornbill_voltage_accuracy_measurement(self):
        configuration = self._measurement_configuration()

        with patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(hornbill_measurements, "sleep", lambda *_: None):
            begin_visa_session_scope()
            info, measured, readback = (
                hornbill_measurements.HornbillVoltageMeasurementwithELoad().Execute_Voltage_Accuracy_Current_Static(
                    configuration, 1
                )
            )

        self.assertEqual(info, [[5.0, 1.0, 0]])
        self.assertEqual(measured, [[5.0, 0]])
        self.assertEqual(readback, [[5.0, 0.9]])

    def test_hornbill_voltage_accuracy_respects_zero_initial_current(self):
        configuration = self._measurement_configuration()
        configuration.update(minCurrent=0, maxCurrent=1)

        with patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(hornbill_measurements, "sleep", lambda *_: None):
            begin_visa_session_scope()
            info, _, _ = (
                hornbill_measurements.HornbillVoltageMeasurementwithELoad().Execute_Voltage_Accuracy_Current_Static(
                    configuration, 1
                )
            )

        command_log = get_simulation_state().command_log
        load_commands = [
            command
            for address, command in command_log
            if address == configuration["ELoad"]
        ]

        self.assertEqual(info, [[5.0, 0.0, 0], [5.0, 1.0, 1]])
        self.assertLess(load_commands.index("CURR MIN"), load_commands.index("OUTP ON"))

    def test_hornbill_current_change_does_not_program_negative_load(self):
        configuration = self._measurement_configuration()
        configuration.update(minCurrent=0, maxCurrent=1)

        with patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(hornbill_measurements, "sleep", lambda *_: None):
            begin_visa_session_scope()
            hornbill_measurements.HornbillVoltageMeasurementwithELoad().Execute_Voltage_Accuracy_Current_Change(
                configuration, 1
            )

        commands = [command for _, command in get_simulation_state().command_log]
        self.assertFalse(any(command.startswith("CURR -") for command in commands))

    def test_real_hornbill_voltage_accuracy_can_use_scpi_readback(self):
        configuration = self._measurement_configuration()
        configuration["Hornbill_Measurement_Command"] = "SCPI"

        with patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(hornbill_measurements, "sleep", lambda *_: None):
            begin_visa_session_scope()
            info, measured, readback = (
                hornbill_measurements.HornbillVoltageMeasurementwithELoad().Execute_Voltage_Accuracy_Current_Static(
                    configuration, 1
                )
            )

        commands = [command for _, command in get_simulation_state().command_log]
        self.assertEqual(info, [[5.0, 1.0, 0]])
        self.assertEqual(measured, [[5.0, 0]])
        self.assertEqual(readback, [[5.0, 0.9]])
        self.assertIn("MEAS:VOLT:DC? (@1)", commands)
        self.assertIn("MEASure:CURRent:DC? (@1)", commands)
        self.assertFalse(any(command.startswith("DIAG:PEEK?") for command in commands))

    def test_real_hornbill_current_accuracy_measurement(self):
        configuration = self._measurement_configuration()
        configuration.update(minCurrent=2, maxCurrent=2)

        with patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(hornbill_measurements, "sleep", lambda *_: None):
            begin_visa_session_scope()
            info, measured, readback = (
                hornbill_measurements.HornbillCurrentMeasurementwithELoad_IMON_FULL().Execute_Current_Accuracy_Current_Static(
                    configuration, 1
                )
            )

        self.assertEqual(info, [[5.0, 2.0, 0]])
        self.assertEqual(measured, [[0, 2.0]])
        self.assertEqual(readback, [[0.0, 2.0]])

    def _run_workflow(self, dut, mode):
        voltage_mode = mode == "voltage"
        checkbox_states = {
            "Voltage_Test": voltage_mode,
            "Current_Test": not voltage_mode,
        }
        parameters = Parameters(
            DUT=dut,
            noofloop=1,
            PSU="USB0::SIM::PSU::INSTR",
            DMM="USB0::SIM::DMM::INSTR",
            ELoad="USB0::SIM::ELOAD::INSTR",
        )
        worker = GUI.TestWorker(checkbox_states, parameters, parameters)
        terminal_signals = []
        measurements = []
        worker.finished.connect(lambda: terminal_signals.append("finished"))
        worker.aborted.connect(lambda: terminal_signals.append("aborted"))
        worker.error.connect(lambda *_: terminal_signals.append("error"))

        def execute_measurement(loop_index):
            psu = get_visa_resource(parameters["PSU"])
            dmm = get_visa_resource(parameters["DMM"])
            if voltage_mode:
                psu.write("VOLT 5.0, (@1)")
                psu.write("OUTP ON, (@1)")
                measurements.append(float(dmm.query("MEAS:VOLT:DC?")))
            else:
                load = get_visa_resource(parameters["ELoad"])
                psu.write("CURR 2.0, (@1)")
                load.write("CURR 2.0")
                psu.write("OUTP ON, (@1)")
                measurements.append(float(dmm.query("MEAS:CURR:DC?")))

        handler_name = f"_run_{dut.lower()}_{mode}_tests"
        with patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(worker, handler_name, side_effect=execute_measurement):
            worker.run()

        expected_measurement = 5.0 if voltage_mode else 2.0
        self.assertEqual(measurements, [expected_measurement])
        self.assertEqual(terminal_signals, ["finished"])
        self.assertEqual(worker.state, GUI.TestState.COMPLETED)

        state = get_simulation_state()
        self.assertFalse(state.output_enabled)
        self.assertEqual(state.voltage, 0.0)
        self.assertEqual(state.current, 0.0)
        self.assertEqual(state.load_current, 0.0)

    def test_dolphin_voltage_workflow(self):
        self._run_workflow("Dolphin", "voltage")

    def test_dolphin_current_workflow(self):
        self._run_workflow("Dolphin", "current")

    def test_hornbill_voltage_workflow(self):
        self._run_workflow("Hornbill", "voltage")

    def test_hornbill_current_workflow(self):
        self._run_workflow("Hornbill", "current")

    def test_report_failure_emits_failed_only_after_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            parameters = Parameters(
                DUT="Dolphin",
                noofloop=1,
                PSU="USB0::SIM::PSU::INSTR",
                DMM="USB0::SIM::DMM::INSTR",
                ELoad="USB0::SIM::ELOAD::INSTR",
                ELoad_Model="E367XXA",
                unit="V",
                savelocation=directory,
            )
            worker = GUI.TestWorker(
                {"Voltage_Test": True, "Current_Test": False},
                parameters,
                parameters,
            )
            events = []
            errors = []
            worker.error.connect(lambda exception, _: errors.append(exception))
            worker.warning.connect(lambda *_: events.append("warning"))
            worker.failed.connect(lambda: events.append("failed"))
            inject_simulation_fault("report", "report")

            with patch.dict(
                os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
            ), patch.object(
                worker,
                "_dispatch_dut_tests",
                side_effect=lambda _: worker.report_exporter.save_voltage_report(),
            ):
                worker.run()

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ReportGenerationError)
        self.assertEqual(events[-1], "failed")
        self.assertEqual(worker.state, GUI.TestState.FAILED)

    def test_cleanup_failure_warns_and_still_disables_outputs(self):
        parameters = Parameters(
            DUT="Dolphin",
            noofloop=1,
            PSU="USB0::SIM::PSU::INSTR",
            ELoad="USB0::SIM::ELOAD::INSTR",
            ELoad_Model="E367XXA",
        )
        worker = GUI.TestWorker(
            {"Voltage_Test": True, "Current_Test": False},
            parameters,
            parameters,
        )
        warnings = []
        worker.warning.connect(lambda exception, _: warnings.append(exception))

        def enable_output(_):
            psu = get_visa_resource(parameters["PSU"])
            psu.write("VOLT 5")
            psu.write("OUTP ON")
            inject_simulation_fault(
                "close", "cleanup", resource_name=parameters["PSU"]
            )

        with patch.dict(
            os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False
        ), patch.object(worker, "_dispatch_dut_tests", side_effect=enable_output):
            worker.run()

        self.assertTrue(any(isinstance(item, CleanupError) for item in warnings))
        self.assertFalse(get_simulation_state().output_enabled)
        self.assertEqual(worker.state, GUI.TestState.COMPLETED)


if __name__ == "__main__":
    unittest.main()
