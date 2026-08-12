import unittest
from unittest.mock import Mock, call, patch

from DUT_Test_Scripts.Hornbill.Hornbill_DUT_Test_With_ELoad import (
    _measure_hornbill_readback,
)
from SCPI_Library.Keysight import (
    DMM_344XXA,
    DMM_3458A,
    ELOAD_E367XXA,
    ELOAD_N3300A,
    Excavator,
    Hornbill,
)


class FakeInstrument:
    def __init__(self, query_response="1.25"):
        self.writes = []
        self.queries = []
        self.query_response = query_response
        self.write_termination = None
        self.read_termination = None
        self.read_buffer_size = None

    def write(self, command):
        self.writes.append(command)

    def query(self, command):
        self.queries.append(command)
        return self.query_response


class HornbillMeasurementTests(unittest.TestCase):
    def setUp(self):
        self.instrument = FakeInstrument()
        resource_patch = patch(
            "SCPI_Library.Keysight.get_visa_resource",
            return_value=self.instrument,
        )
        self.addCleanup(resource_patch.stop)
        resource_patch.start()
        self.hornbill = Hornbill("TCPIP0::hornbill::inst0::INSTR")

    def test_voltage_dc_uses_channel_aware_measurement(self):
        result = self.hornbill.measureVoltageDC(1)

        self.assertEqual(result, "1.25")
        self.assertEqual(self.instrument.writes, [])
        self.assertEqual(self.instrument.queries, ["MEAS:VOLT:DC? (@1)"])

    def test_array_voltage_uses_requested_sample_count(self):
        result = self.hornbill.measureVoltageArray(2, sample=512000)

        self.assertEqual(result, "1.25")
        self.assertEqual(
            self.instrument.writes,
            ["SENSe:SWEep:POINts 512000, (@2)"],
        )
        self.assertEqual(
            self.instrument.queries,
            ["SYST:ERR?", "MEAS:ARR:VOLT? (@2)"],
        )

    def test_setting_voltage_sample_count_uses_requested_value(self):
        self.hornbill.setVoltageSweepPoints(3, sample=250)

        self.assertEqual(
            self.instrument.writes,
            ["SENSe:SWEep:POINts 250, (@3)"],
        )
        self.assertEqual(self.instrument.queries, ["SYST:ERR?"])

    def test_voltage_sense_source_uses_hornbill_command_hierarchy(self):
        self.hornbill.senseVoltageSource("EXT", 2)

        self.assertEqual(
            self.instrument.writes,
            ["SOURce:VOLTage:SENSe:SOURce EXT,(@2)"],
        )

    def test_sample_count_above_instrument_limit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 512000"):
            self.hornbill.setVoltageSweepPoints(1, sample=512001)

        self.assertEqual(self.instrument.writes, [])
        self.assertEqual(self.instrument.queries, [])

    def test_e367xxa_translates_zero_current_to_minimum(self):
        eload = ELOAD_E367XXA("USB0::eload::INSTR")

        eload.setOutputCurrent(0)

        self.assertEqual(self.instrument.writes, ["CURR MIN"])

    def test_e367xxa_preserves_positive_current(self):
        eload = ELOAD_E367XXA("USB0::eload::INSTR")

        eload.setOutputCurrent(1.5)

        self.assertEqual(self.instrument.writes, ["CURR 1.5"])

    def test_e367xxa_translates_cc_to_current_function(self):
        eload = ELOAD_E367XXA("USB0::eload::INSTR")

        eload.setMode("CC")

        self.assertEqual(self.instrument.writes, ["FUNCtion CURRent"])

    def test_n3300a_translates_cc_to_current_function(self):
        eload = ELOAD_N3300A("GPIB1::1::INSTR")

        eload.set_Mode("CC")

        self.assertEqual(
            self.instrument.writes,
            ["SOURce:FUNCtion CURR"],
        )

    def test_excavator_power_study_eload_sequence(self):
        excavator = Excavator("USB0::excavator::INSTR")

        excavator.clearStatus()
        excavator.setSYSTEMEMULationMode("ELOAD")
        excavator.setMode("CURRent")
        excavator.setOutputCurrent(20)
        excavator.setOutputState("ON")

        self.assertEqual(
            self.instrument.writes,
            [
                "*CLS",
                "SYSTem:EMULation ELOAD",
                "SOURce:FUNCtion CURRent",
                "SOURce:CURRent:LEVel:IMMediate:AMPLitude 20",
                "OUTPut:STATe ON",
            ],
        )

    def test_344xxa_advanced_settings_use_valid_scpi(self):
        dmm = DMM_344XXA("USB0::dmm::INSTR")

        dmm.setNPLC("10")
        dmm.setAutoZeroMode("OFF")
        dmm.setAutoImpedanceMode("ON")

        self.assertEqual(
            self.instrument.writes,
            [
                "SENSe:VOLTage:DC:NPLCycles 10",
                "SENSe:VOLTage:DC:ZERO:AUTO OFF",
                "SENSe:VOLTage:DC:IMPedance:AUTO ON",
            ],
        )

    def test_3458a_advanced_settings_use_legacy_commands(self):
        dmm = DMM_3458A("GPIB0::22::INSTR")

        dmm.setDCV("10")
        dmm.setNPLC("100")
        dmm.setAutoZeroMode("OFF")

        self.assertEqual(
            self.instrument.writes,
            ["DCV 10", "NPLC 100", "AZERO OFF"],
        )

    def test_non_numeric_sample_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            self.hornbill.setVoltageSweepPoints(1, sample="invalid")

        self.assertEqual(self.instrument.writes, [])

    def test_diag_readback_uses_requested_precision_adc_inputs(self):
        voltage = self.hornbill.measureReadbackVoltage(2, mode="DIAG")
        current = self.hornbill.measureReadbackCurrent(
            2,
            mode="DIAG",
            diagnostic_input="200uA",
        )

        self.assertEqual(voltage, 1.25)
        self.assertEqual(current, 1.25)
        self.assertEqual(
            self.instrument.queries,
            [
                "DIAG:PEEK? 21,0,100000",
                "DIAG:PEEK? 21,1,100000",
            ],
        )

    def test_diag_voltage_input_can_measure_vloc(self):
        result = self.hornbill.measureReadbackVoltage(
            3,
            mode="DIAG",
            diagnostic_input="VLOC",
            sample=250,
        )

        self.assertEqual(result, 1.25)
        self.assertEqual(self.instrument.queries, ["DIAG:PEEK? 22,2,250"])

    def test_invalid_diag_voltage_input_is_rejected_before_io(self):
        with self.assertRaisesRegex(ValueError, "Use: VMON, VLOC"):
            self.hornbill.measureReadbackVoltage(
                1,
                mode="DIAG",
                diagnostic_input="unknown",
            )

        self.assertEqual(self.instrument.queries, [])

    def test_legacy_diag_helpers_are_channel_aware(self):
        voltage = self.hornbill.diagVoltageReadback_VLOC_100k(4)
        current = self.hornbill.diagCurrentReadback_IMON_FULL_100k(4)

        self.assertEqual(voltage, b"1.25")
        self.assertEqual(current, b"1.25")
        self.assertEqual(
            self.instrument.queries,
            ["DIAG:PEEK? 23,2,100000", "DIAG:PEEK? 23,7,100000"],
        )

    def test_scpi_readback_uses_channel_aware_measurement_commands(self):
        voltage = self.hornbill.measureReadbackVoltage(2, mode="SCPI")
        current = self.hornbill.measureReadbackCurrent(2, mode="SCPI")

        self.assertEqual(voltage, 1.25)
        self.assertEqual(current, 1.25)
        self.assertEqual(
            self.instrument.writes,
            [
                "SENSe:SWEep:POINts 100000, (@2)",
                "SENSe:SWEep:POINts 100000, (@2)",
            ],
        )
        self.assertEqual(
            self.instrument.queries,
            [
                "SYST:ERR?",
                "MEAS:VOLT:DC? (@2)",
                "SYST:ERR?",
                "MEASure:CURRent:DC? (@2)",
            ],
        )

    def test_invalid_readback_mode_is_rejected_before_io(self):
        with self.assertRaisesRegex(ValueError, "either DIAG or SCPI"):
            self.hornbill.measureReadbackVoltage(1, mode="unknown")

        self.assertEqual(self.instrument.writes, [])
        self.assertEqual(self.instrument.queries, [])

    def test_hornbill_test_point_captures_vmon_imon_and_vloc(self):
        power_supply = Mock()
        power_supply.measureReadbackVoltage.side_effect = [12.1, 12.0]
        power_supply.measureReadbackCurrent.return_value = 0.5

        result = _measure_hornbill_readback(
            power_supply,
            {"Hornbill_Measurement_Command": "SCPI", "SweepPoints": 250},
            2,
        )

        self.assertEqual(result, (12.1, 0.5, 12.0))
        self.assertEqual(
            power_supply.measureReadbackVoltage.call_args_list,
            [
                call(2, mode="SCPI", diagnostic_input="VMON", sample=250),
                call(2, mode="DIAG", diagnostic_input="VLOC", sample=250),
            ],
        )
        power_supply.measureReadbackCurrent.assert_called_once_with(
            2,
            mode="SCPI",
            diagnostic_input="FULL",
            sample=250,
        )


if __name__ == "__main__":
    unittest.main()
