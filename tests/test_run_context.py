import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from reporting import xlreport as xlreport_module
from reporting import xlreportpower as xlreportpower_module
from execution.run_context import REALTIME_COLUMNS, RunContext
from configuration.test_configuration import ParameterSnapshot


class RunContextTests(unittest.TestCase):
    def _create_context(self, directory, run_id, dut):
        parameters = ParameterSnapshot(savelocation=directory)
        configuration = {"DUT": dut}
        return RunContext.create(
            run_id,
            directory,
            dut,
            configuration,
            parameters,
            {"Voltage_Test": True},
        )

    def test_two_contexts_have_disjoint_output_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self._create_context(directory, "first", "Dolphin")
            second = self._create_context(directory, "second", "Hornbill")

            self.assertNotEqual(first.storage.root, second.storage.root)
            self.assertNotEqual(first.voltage_chart, second.voltage_chart)
            self.assertNotEqual(first.parameters.rawdir, second.parameters.rawdir)

    def test_realtime_csv_is_owned_and_closed_per_context(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self._create_context(directory, "first", "Dolphin")
            second = self._create_context(directory, "second", "Hornbill")
            first_path = first.open_realtime_csv("first")
            second_path = second.open_realtime_csv("second")

            first.write_realtime_row(range(15))
            second.write_realtime_row(range(100, 115))
            first.close()
            second.close()

            with first_path.open(newline="", encoding="utf-8") as csv_file:
                first_rows = list(csv.reader(csv_file))
            with second_path.open(newline="", encoding="utf-8") as csv_file:
                second_rows = list(csv.reader(csv_file))

        self.assertEqual(tuple(first_rows[0]), REALTIME_COLUMNS)
        self.assertEqual(len(first_rows[0]), len(first_rows[1]))
        self.assertEqual(first_rows[1][1], "0")
        self.assertEqual(second_rows[1][1], "100")

    def test_realtime_csv_rejects_rows_with_wrong_width(self):
        with tempfile.TemporaryDirectory() as directory:
            context = self._create_context(directory, "first", "Dolphin")
            context.open_realtime_csv("first")
            try:
                with self.assertRaisesRegex(ValueError, "requires 15 values"):
                    context.write_realtime_row(range(13))
            finally:
                context.close()

    def test_report_infers_paths_from_its_own_run(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self._create_context(directory, "first", "Dolphin")
            second = self._create_context(directory, "second", "Hornbill")
            xlreport_module.configure_run_storage(
                second.storage.raw,
                second.storage.charts,
            )

            report = xlreport_module.xlreport(first.storage.reports, "FIRST")
            power_report = xlreportpower_module.xlreportpower(
                first.storage.reports, "FIRST_POWER"
            )

        self.assertEqual(report.csv_folder, first.storage.raw)
        self.assertEqual(report.chart_directory, first.storage.charts)
        self.assertEqual(power_report.csv_folder, first.storage.raw)
        self.assertEqual(power_report.chart_directory, first.storage.charts)


if __name__ == "__main__":
    unittest.main()
