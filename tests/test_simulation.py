import os
import unittest
from unittest.mock import patch

import GUI
import SCPI_Library.simulation as simulation
from SCPI_Library.instrument_errors import (
    InstrumentCommandError,
    InstrumentConnectionError,
    InstrumentTimeoutError,
)
from SCPI_Library.session_manager import (
    begin_visa_session_scope,
    close_visa_session_scope,
    get_visa_resource,
)
from SCPI_Library.simulation import (
    SIMULATED_INSTRUMENTS,
    SimulatedVisaResourceManager,
    inject_simulation_fault,
    initialize_main_thread_visa,
    create_resource_manager,
    reset_simulation,
    is_simulation_mode,
)


class SimulationTests(unittest.TestCase):
    def setUp(self):
        reset_simulation()

    def tearDown(self):
        close_visa_session_scope()

    def test_simulation_mode_is_explicitly_enabled(self):
        with patch.dict(os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False):
            self.assertTrue(is_simulation_mode())
            self.assertIsInstance(create_resource_manager(), SimulatedVisaResourceManager)

    def test_main_thread_visa_is_initialized_once(self):
        class FakeManager:
            def __init__(self):
                self.list_calls = 0

            def list_resources(self):
                self.list_calls += 1
                return ("GPIB0::22::INSTR",)

        manager = FakeManager()
        with patch.dict(os.environ, {"AUTOMATION_SIMULATION": "0"}), patch.object(
            simulation, "_main_thread_resource_manager", None
        ), patch.object(
            simulation.pyvisa, "ResourceManager", return_value=manager
        ) as resource_manager:
            first = initialize_main_thread_visa()
            second = initialize_main_thread_visa()

        self.assertIs(first, manager)
        self.assertIs(second, manager)
        self.assertEqual(manager.list_calls, 1)
        resource_manager.assert_called_once_with()

    def test_simulated_manager_exposes_expected_instrument_roles(self):
        with patch.dict(os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False):
            result = GUI.NewGetVisaSCPIResources()

        self.assertEqual(set(result.addresses), set(SIMULATED_INSTRUMENTS))
        self.assertEqual(len(result.identities), len(SIMULATED_INSTRUMENTS))
        self.assertEqual(result.roles["PSU"], "USB0::SIM::PSU::INSTR")
        self.assertEqual(result.roles["DMM"], "USB0::SIM::DMM::INSTR")
        self.assertEqual(result.roles["DMM2"], "USB0::SIM::DMM2::INSTR")
        self.assertEqual(result.roles["ELOAD"], "USB0::SIM::ELOAD::INSTR")
        self.assertEqual(result.roles["SCOPE"], "USB0::SIM::SCOPE::INSTR")
        self.assertEqual(result.roles["ACSource"], "USB0::SIM::ACSOURCE::INSTR")

    def test_session_pool_uses_shared_simulated_measurement_state(self):
        with patch.dict(os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False):
            begin_visa_session_scope()
            psu = get_visa_resource("USB0::SIM::PSU::INSTR")
            dmm = get_visa_resource("USB0::SIM::DMM::INSTR")

            psu.write("VOLT 12.5, (@1)")
            psu.write("OUTP ON")

            self.assertEqual(float(dmm.query("MEAS:VOLT:DC?")), 12.5)

    def test_simulated_output_off_returns_zero_measurement(self):
        manager = SimulatedVisaResourceManager()
        psu = manager.open_resource("USB0::SIM::PSU::INSTR")
        dmm = manager.open_resource("USB0::SIM::DMM::INSTR")

        psu.write("VOLT 8")
        psu.write("OUTP ON")
        psu.write("OUTP OFF")

        self.assertEqual(float(dmm.query("MEAS:VOLT:DC?")), 0.0)

    def test_injected_timeout_preserves_instrument_context(self):
        address = "USB0::SIM::DMM::INSTR"
        inject_simulation_fault("query", "timeout", resource_name=address)

        with patch.dict(os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False):
            dmm = get_visa_resource(address)
            with self.assertRaises(InstrumentTimeoutError) as raised:
                dmm.query("MEAS:VOLT:DC?")

        self.assertEqual(raised.exception.context["address"], address)
        self.assertEqual(raised.exception.context["command"], "MEAS:VOLT:DC?")
        self.assertEqual(raised.exception.context["operation"], "query")

    def test_injected_disconnect_is_reported_as_command_failure(self):
        address = "USB0::SIM::DMM::INSTR"
        inject_simulation_fault("query", "disconnect", resource_name=address)

        with patch.dict(os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False):
            dmm = get_visa_resource(address)
            with self.assertRaises(InstrumentCommandError) as raised:
                dmm.query("READ?")

        self.assertNotIsInstance(raised.exception, InstrumentTimeoutError)
        self.assertEqual(raised.exception.context["address"], address)

    def test_injected_connection_failure_is_normalized(self):
        address = "USB0::SIM::PSU::INSTR"
        inject_simulation_fault("connect", "disconnect", resource_name=address)

        with patch.dict(os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False):
            with self.assertRaises(InstrumentConnectionError) as raised:
                get_visa_resource(address)

        self.assertEqual(raised.exception.context["address"], address)
        self.assertEqual(raised.exception.context["operation"], "connect")


if __name__ == "__main__":
    unittest.main()
