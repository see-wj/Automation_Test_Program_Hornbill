import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
for import_path in (PROJECT_ROOT, SRC_DIR):
    path_text = str(import_path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from instruments.TestVolt_HB_3458 import CalWorker


class FakeResourceManager:
    def close(self):
        return None


class FakeInstrument:
    def __init__(self, error_sequence=None):
        self.error_sequence = list(error_sequence or [])
        self.writes = []
        self.queries = []
        self.closed = False
        self.timeout = None

    def write(self, command):
        self.writes.append(command)

    def query(self, command):
        self.queries.append(command)
        if command == "SYST:ERR?":
            if self.error_sequence:
                return self.error_sequence.pop(0)
            return '+0,"No error"'
        return "0"

    def close(self):
        self.closed = True


class TestVoltHB3458Tests(unittest.TestCase):
    def test_retries_transient_psu_errors_and_uses_requested_cal_point(self):
        psu = FakeInstrument(error_sequence=['-100,"Execution error"', '+0,"No error"'])
        dmm = FakeInstrument()
        errors = []

        worker = CalWorker(
            "TCPIP0::psu::instr",
            "GPIB0::22::INSTR",
            "PP8000A",
            1,
            ["P2"],
            command_delay=0,
            settling_delay=0,
            calibration_time=0,
            resource_manager=FakeResourceManager(),
            psu=psu,
            dmm=dmm,
        )
        worker.error.connect(errors.append)

        worker.run()

        self.assertEqual(errors, [])
        self.assertIn("CAL:LEV P2", psu.writes)
        self.assertTrue(psu.closed)
        self.assertTrue(dmm.closed)


if __name__ == "__main__":
    unittest.main()
