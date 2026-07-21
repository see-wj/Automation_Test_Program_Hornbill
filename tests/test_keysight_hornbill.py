import unittest
from unittest.mock import patch

from SCPI_Library.Keysight import ELOAD_E367XXA, Hornbill


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

    def test_non_numeric_sample_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            self.hornbill.setVoltageSweepPoints(1, sample="invalid")

        self.assertEqual(self.instrument.writes, [])

    def test_diag_readback_uses_requested_precision_adc_inputs(self):
        voltage = self.hornbill.measureReadbackVoltage(1, mode="DIAG")
        current = self.hornbill.measureReadbackCurrent(
            1,
            mode="DIAG",
            diagnostic_input="200uA",
        )

        self.assertEqual(voltage, 1.25)
        self.assertEqual(current, 1.25)
        self.assertEqual(
            self.instrument.queries,
            [
                "DIAG:PEEK? 20,0,100000",
                "DIAG:PEEK? 20,1,100000",
            ],
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


if __name__ == "__main__":
    unittest.main()
