import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from SCPI_Library.Keysight import DAQ973A


class RecordingInstrument:
    def __init__(self):
        self.writes = []
        self.queries = []
        self.responses = {
            "*IDN?": "KEYSIGHT TECHNOLOGIES,DAQ973A,MY59010677,1.0",
            "READ?": "21.1,22.2,23.3,24.4",
            "SYST:ERR?": '+0,"No error"',
        }

    def write(self, command):
        self.writes.append(command)

    def query(self, command):
        self.queries.append(command)
        return self.responses[command]


class DAQ973ATests(unittest.TestCase):
    def setUp(self):
        self.instrument = RecordingInstrument()
        self.daq = DAQ973A.__new__(DAQ973A)
        self.daq.instr = self.instrument

    def test_generates_reference_temperature_configuration_commands(self):
        channels = (101, 103, 104, 105)
        self.daq.clearStatus()
        self.daq.reset()
        self.daq.configureThermocoupleTemperature(channels)
        self.daq.setThermocoupleType("T", (101, 103))
        self.daq.setThermocoupleType("E", (104, 105))
        self.daq.setInternalReferenceJunction(channels)
        self.daq.setTemperatureNPLC(1, channels)
        self.daq.enableAutomaticChannelDelay(channels)
        self.daq.setScanChannels(channels)

        self.assertEqual(self.instrument.writes, [
            "*CLS",
            "*RST",
            "CONF:TEMP TC,DEF,(@101,103,104,105)",
            "SENS:TEMP:TRAN:TC:TYPE T,(@101,103)",
            "SENS:TEMP:TRAN:TC:TYPE E,(@104,105)",
            "SENS:TEMP:TRAN:TC:RJUN:TYPE INT,(@101,103,104,105)",
            "SENS:TEMP:NPLC 1,(@101,103,104,105)",
            "ROUT:CHAN:DELAY:AUTO ON,(@101,103,104,105)",
            "ROUT:SCAN (@101,103,104,105)",
        ])

    def test_reads_temperature_scan_as_floats(self):
        self.assertEqual(self.daq.readScan(), [21.1, 22.2, 23.3, 24.4])
        self.assertEqual(self.instrument.queries, ["READ?"])

    def test_accepts_single_channel_for_command_checker_preview(self):
        self.daq.configureThermocoupleTemperature(101)

        self.assertEqual(
            self.instrument.writes,
            ["CONF:TEMP TC,DEF,(@101)"],
        )


if __name__ == "__main__":
    unittest.main()
