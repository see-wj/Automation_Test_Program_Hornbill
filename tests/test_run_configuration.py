import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from configuration.test_configuration import (
    build_test_parameters,
    prepare_run_submission,
    snapshot_parameters,
)


class Parameters(dict):
    __getattr__ = dict.get


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.parameters = Parameters({
            "DUT": "Dolphin",
            "savelocation": "output",
            "Voltage_Rating": "20",
            "Current_Rating": "5",
            "Power_Rating": "100",
            "Power": "100",
            "estimatetime": 1,
            "updatedelay": 0,
            "readbackvoltage": True,
            "readbackcurrent": True,
            "noofloop": 1,
            "DMM_Instrument": "Keysight",
            "Programming_Error_Gain": 1,
            "Programming_Error_Offset": 0,
            "Readback_Error_Gain": 1,
            "Readback_Error_Offset": 0,
            "unit": "unit",
            "minCurrent": 0,
            "maxCurrent": 1,
            "current_step_size": 1,
            "minVoltage": 0,
            "maxVoltage": 1,
            "voltage_step_size": 1,
            "selected_text": "Dolphin",
            "PSU": "PSU",
            "DMM": "DMM",
            "ELoad": "ELoad",
            "DAQ": "USB::DAQ",
            "ELoad_Channel": 1,
            "PSU_Channel": [1],
            "VoltageSense": "2-wire",
            "VoltageRes": 0.1,
            "setFunction": "Voltage",
            "SPOperationMode": "CV",
            "DMM_Model": "DMM",
            "ELoad_Model": "ELoad",
            "Hornbill_Measurement_Command": "SCPI",
            "Relay_Control": "Voltage Relay (Channel 3)",
            "Range": "Auto",
            "Aperture": 1,
            "AutoZero": "ON",
            "inputZ": "Auto",
            "UpTime": 0,
            "DownTime": 0,
            "rshunt": 0.1,
            "DMM2": "DMM2",
            "OSC": "OSC",
            "OSC_Channel": 1,
            "Channel_CouplingMode": "DC",
            "Trigger_Mode": "EDGE",
            "Trigger_CouplingMode": "DC",
            "Trigger_SweepMode": "AUTO",
            "Trigger_SlopeMode": "POS",
            "Probe_Setting": 10,
            "Acq_Type": "NORM",
            "TimeScale": 0.001,
            "VerticalScale": 1,
            "V_Settling_Band": 1,
            "T_Settling_Band": 1,
        })

    def test_builds_base_configuration(self):
        result = build_test_parameters(self.parameters, {})

        self.assertEqual(result["DUT"], "Dolphin")
        self.assertEqual(result["InputZ"], "Auto")
        self.assertEqual(result["Hornbill_Measurement_Command"], "SCPI")
        self.assertEqual(result["Relay_Control"], "Voltage Relay (Channel 3)")
        self.assertNotIn("DMM2", result)

    def test_adds_current_only_fields(self):
        result = build_test_parameters(self.parameters, {"Current_Test": True})

        self.assertEqual(result["DMM2"], "DMM2")
        self.assertEqual(result["rshunt"], 0.1)

    def test_adds_scope_fields_for_hornbill_capture_mode(self):
        result = build_test_parameters(
            self.parameters,
            {
                "VoltageAccuracy": True,
                "CurrentStatic(VoltageChange)withOscilloscope": True,
            },
        )

        self.assertEqual(result["OSC"], "OSC")
        self.assertEqual(result["OSC_Channel"], 1)

    def test_includes_optional_daq_address(self):
        result = build_test_parameters(self.parameters, {"Temperature": True})

        self.assertEqual(result["DAQ"], "USB::DAQ")

    def test_snapshot_is_independent_from_gui_parameters(self):
        self.parameters["PSU_Channel"] = [1]

        snapshot = snapshot_parameters(self.parameters)
        snapshot.PSU_Channel.append(2)

        self.assertEqual(self.parameters.PSU_Channel, [1])
        self.assertEqual(snapshot.PSU_Channel, [1, 2])

    def test_prepares_snapshot_and_label_for_submission(self):
        selections = {
            "Voltage_Test": True,
            "VoltageAccuracy": True,
            "DataReport": True,
            "DataImage": False,
        }

        submission = prepare_run_submission(self.parameters, selections)
        self.parameters.noofloop = 9
        selections["VoltageAccuracy"] = False

        self.assertEqual(submission.parameters.noofloop, 1)
        self.assertTrue(submission.selections["VoltageAccuracy"])
        self.assertEqual(
            submission.label,
            "Dolphin: Voltage_Test, VoltageAccuracy",
        )
        self.assertEqual(submission.configuration["DUT"], "Dolphin")


if __name__ == "__main__":
    unittest.main()
