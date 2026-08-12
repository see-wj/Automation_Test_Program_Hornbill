import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
for import_path in (PROJECT_ROOT, SRC_DIR):
    path_text = str(import_path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from execution.ac_source_controller import (
    ACSourceController,
    set_ac_source_voltage,
    uses_ac_source,
)
from SCPI_Library.session_manager import (
    begin_visa_session_scope,
    close_visa_session_scope,
)
from SCPI_Library.simulation import get_simulation_state, reset_simulation
from DUT_Test_Scripts.Dolphin.DUT_Test import LineRegulation


class ACSourceControllerTests(unittest.TestCase):
    def setUp(self):
        self.configuration = {
            "AC_Supply_Type": "AC Source",
            "ACSource": "USB0::SIM::ACSOURCE::INSTR",
            "AC_CurrentLimit": 2,
            "AC_VoltageOutput": 230,
            "Frequency": 50,
        }

    def test_plug_mode_does_not_use_programmable_source(self):
        self.assertFalse(uses_ac_source({"AC_Supply_Type": "Plug"}))
        with self.assertRaisesRegex(RuntimeError, "requires AC Supply Type"):
            set_ac_source_voltage({"AC_Supply_Type": "Plug"}, 230)

    def test_start_programs_source_and_stop_disables_output(self):
        driver = Mock()
        driver.queryError.return_value = '0,"No error"'
        controller = ACSourceController(
            self.configuration,
            driver_factory=Mock(return_value=driver),
        )

        controller.start()
        controller.stop()

        driver.clearStatus.assert_called_once_with()
        self.assertEqual(
            driver.setOutputState.call_args_list,
            [unittest.mock.call("OFF"), unittest.mock.call("ON"), unittest.mock.call("OFF")],
        )
        driver.setOutputCurrent.assert_called_once_with(2.0)
        driver.setOutputVoltage.assert_called_once_with(230.0)
        driver.setFrequency.assert_called_once_with(50.0)

    def test_simulation_uses_new_68xx_commands(self):
        reset_simulation()
        with patch.dict(os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False):
            begin_visa_session_scope()
            try:
                controller = ACSourceController(self.configuration)
                controller.start()
                controller.set_voltage(207)
                controller.stop()
            finally:
                close_visa_session_scope()

        commands = [command for _, command in get_simulation_state().command_log]
        self.assertIn("SOURce:CURRent:LEVel:IMMediate 2.0", commands)
        self.assertIn("SOURce:VOLTage:LEVel:IMMediate:AMPLitude 230.0", commands)
        self.assertIn("SOURce:FREQuency:IMMediate 50.0", commands)
        self.assertIn("SOURce:VOLTage:LEVel:IMMediate:AMPLitude 207.0", commands)
        self.assertEqual(commands[-2:], ["OUTPut:STATe OFF", "SYSTem:ERRor?"])

    def test_nonzero_instrument_error_stops_startup(self):
        driver = Mock()
        driver.queryError.return_value = '-200,"Execution error"'
        controller = ACSourceController(
            self.configuration,
            driver_factory=Mock(return_value=driver),
        )

        with self.assertRaisesRegex(RuntimeError, "AC source error"):
            controller.start()

    def test_active_voltage_and_current_line_regulation_paths_run(self):
        configuration = dict(self.configuration)
        configuration.update(
            Instrument="Keysight",
            PSU="USB0::SIM::PSU::INSTR",
            DMM="USB0::SIM::DMM::INSTR",
            DMM2="USB0::SIM::DMM2::INSTR",
            ELoad="USB0::SIM::ELOAD::INSTR",
            PSU_Channel=1,
            ELoad_Channel=1,
            updatedelay=0,
            Line_Reg_Range=[100],
            VoltageSense="EXT",
            OperationMode="Independent",
            Aperture=1,
            AutoZero="ON",
            InputZ="ON",
            Range="Auto",
            VoltageRes="SLOW",
            V_Rating=30,
            I_Rating=10,
            P_Rating=50,
            power=50,
            maxVoltage=10,
            maxCurrent=5,
            Load_Programming_Error_Gain=0.001,
            Load_Programming_Error_Offset=0.001,
            rshunt=0.01,
        )

        reset_simulation()
        with patch.dict(os.environ, {"AUTOMATION_SIMULATION": "1"}, clear=False):
            begin_visa_session_scope()
            try:
                controller = ACSourceController(configuration)
                controller.start()
                with patch(
                    "DUT_Test_Scripts.Dolphin.DUT_Test.sleep",
                    lambda *_: None,
                ):
                    voltage_results = LineRegulation().executeCV_LoadRegulation(
                        configuration
                    )
                    current_results = LineRegulation().executeCC_LoadRegulation(
                        configuration
                    )
                controller.stop()
            finally:
                close_visa_session_scope()

        self.assertEqual(len(voltage_results), 3)
        self.assertEqual(len(current_results), 3)


if __name__ == "__main__":
    unittest.main()
