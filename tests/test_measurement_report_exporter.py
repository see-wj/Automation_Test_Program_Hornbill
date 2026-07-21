import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from execution import measurement_report_exporter
from execution.test_worker import TestWorker


class Parameters(dict):
    __getattr__ = dict.get


def create_worker(params=None):
    return TestWorker({}, {}, params or Parameters(noofloop=1))


class MeasurementReportExporterTests(unittest.TestCase):
    def test_config_csv_uses_active_run_storage(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            raw_directory = Path(temporary_directory)
            worker = create_worker()
            worker.dict = {"PSU": "SIM::PSU", "Voltage": 5.0}
            worker.run_context = SimpleNamespace(
                storage=SimpleNamespace(raw=raw_directory)
            )

            worker.report_exporter.write_config_csv("config.csv")

            config_frame = pd.read_csv(raw_directory / "config.csv", index_col=0)

        self.assertEqual(config_frame.loc["PSU", "Value"], "SIM::PSU")
        self.assertEqual(float(config_frame.loc["Voltage", "Value"]), 5.0)

    def test_voltage_report_uses_simulation_prefix(self):
        worker = create_worker(
            Parameters(
                noofloop=1,
                unit="VOLTAGE",
                savelocation="reports",
            )
        )
        report_instances = []

        class Report:
            def __init__(self, save_directory, file_name):
                self.save_directory = save_directory
                self.file_name = file_name
                self.was_run = False
                report_instances.append(self)

            def run(self):
                self.was_run = True

        with patch.object(
            measurement_report_exporter,
            "is_simulation_mode",
            return_value=True,
        ), patch.object(measurement_report_exporter, "xlreport", Report):
            worker.report_exporter.save_voltage_report()

        self.assertEqual(len(report_instances), 1)
        self.assertEqual(report_instances[0].save_directory, "reports")
        self.assertEqual(report_instances[0].file_name, "SIMULATED_VOLTAGE")
        self.assertTrue(report_instances[0].was_run)

    def test_executor_exports_delegate_to_shared_exporter(self):
        worker = create_worker()
        measurement = (["info"], ["measured"], ["readback"])

        with patch.object(
            worker.report_exporter,
            "export_voltage_accuracy",
        ) as voltage_export, patch.object(
            worker.report_exporter,
            "export_current_accuracy",
        ) as current_export, patch.object(
            worker.report_exporter,
            "export_power_accuracy",
        ) as power_export:
            worker._export_voltage_accuracy(*measurement)
            worker._export_current_accuracy(*measurement)
            worker._export_power_accuracy(*measurement)

        voltage_export.assert_called_once_with(*measurement)
        current_export.assert_called_once_with(*measurement)
        power_export.assert_called_once_with(*measurement)

    def test_current_export_uses_snapshot_rating_and_current_meter(self):
        worker = create_worker(
            Parameters(
                noofloop=1,
                PSU="SIM::PSU",
                DMM2="SIM::CURRENT_DMM",
                ELoad="SIM::ELOAD",
                Programming_Error_Gain="0.1",
                Programming_Error_Offset="0.2",
                Readback_Error_Gain="0.3",
                Readback_Error_Offset="0.4",
                unit="CURRENT",
                Current_Rating="10",
                savelocation="reports",
                savedir="reports",
            )
        )
        worker._execute_checkpointed = lambda function, *args: function(*args)

        class Report:
            def __init__(self, **_kwargs):
                pass

            def run(self):
                pass

        with patch.object(
            measurement_report_exporter,
            "instrumentData",
        ) as instrument_data, patch.object(
            measurement_report_exporter,
            "datatoCSV_Accuracy2",
        ), patch.object(
            measurement_report_exporter,
            "datatoGraph2",
        ) as graph, patch.object(
            worker.report_exporter,
            "write_config_csv",
        ), patch.object(
            measurement_report_exporter,
            "xlreport",
            Report,
        ):
            worker.report_exporter.export_current_accuracy([], [], [])

        instrument_data.assert_called_once_with(
            "SIM::PSU",
            "SIM::CURRENT_DMM",
            "SIM::ELOAD",
        )
        graph.return_value.scatterCompareCurrent2.assert_called_once()
        self.assertEqual(
            graph.return_value.scatterCompareCurrent2.call_args.args[-1],
            10.0,
        )


if __name__ == "__main__":
    unittest.main()
