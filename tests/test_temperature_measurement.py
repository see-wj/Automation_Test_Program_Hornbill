import csv
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from External_Auxiliary_Equipment.Temperature_Measurement import TemperatureMeasurement


class FakeInstrument:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeDAQ:
    instances = []

    def __init__(self, address):
        self.address = address
        self.calls = []
        self.instr = FakeInstrument()
        self.__class__.instances.append(self)

    def __getattr__(self, name):
        if name == "readScan":
            return lambda: [20.1, 20.2, 20.3, 20.4]
        if name == "queryError":
            return lambda: '+0,"No error"'
        return lambda *args: self.calls.append((name, args))


class TemperatureMeasurementTests(unittest.TestCase):
    def setUp(self):
        FakeDAQ.instances.clear()

    def test_configures_reference_channels_and_writes_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            output_file = Path(directory) / "temperature.csv"
            monitor = TemperatureMeasurement(
                "USB::DAQ",
                output_file=output_file,
                daq_class=FakeDAQ,
            )

            sample = monitor.measure(loop_index=0)

            self.assertEqual(sample.readings[101], 20.1)
            self.assertIn("CH105=20.400 °C", sample.status_text())
            with output_file.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))
            self.assertEqual(
                rows[0],
                ["Timestamp", "Loop", "CH101_T_C", "CH103_T_C", "CH104_E_C", "CH105_E_C"],
            )
            self.assertEqual(rows[1][1:], ["1", "20.1", "20.2", "20.3", "20.4"])

    def test_close_releases_daq_resource(self):
        monitor = TemperatureMeasurement("USB::DAQ", daq_class=FakeDAQ)
        instrument = monitor.daq.instr

        monitor.close()

        self.assertTrue(instrument.closed)


if __name__ == "__main__":
    unittest.main()
