import csv
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from External_Auxiliary_Equipment.Temperature_Measurement import TemperatureMeasurement
from instruments.TemperatureMeasurement import (
    TemperatureMeasurementDialog,
    TemperatureMeasurementWorker,
    parse_channel_types,
)


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

    def test_parses_editable_channel_and_thermocouple_types(self):
        self.assertEqual(
            parse_channel_types("101:t, 103:T, 104:e"),
            {101: "T", 103: "T", 104: "E"},
        )

    def test_main_test_selection_registers_temperature_dialog(self):
        import GUI

        registry = GUI.MainWindow._create_dialog_registry(object())
        registration = next(
            item
            for item in registry.registrations
            if item.owner_attribute == "temperature_measurement_dialog"
        )

        self.assertIs(registration.factory, TemperatureMeasurementDialog)
        self.assertIn(
            "temperature_measurement_dialog",
            GUI.MainWindow.TEST_SELECTION_DIALOGS,
        )

    def test_recording_worker_collects_samples_until_stop_requested(self):
        collected = []
        monitor = Mock()
        sample = SimpleNamespace(timestamp=datetime(2026, 8, 2, 12, 0, 0))
        worker = TemperatureMeasurementWorker(
            "USB::DAQ",
            {101: "T"},
            None,
            interval_seconds=0.01,
        )

        def measure(loop_index):
            self.assertEqual(loop_index, 0)
            worker.request_stop()
            return sample

        monitor.measure.side_effect = measure
        worker.sample_ready.connect(
            lambda current_sample, count, elapsed: collected.append(
                (current_sample, count, elapsed)
            )
        )

        with patch(
            "instruments.TemperatureMeasurement.TemperatureMeasurement",
            return_value=monitor,
        ):
            worker.run()

        self.assertEqual(collected[0][0], sample)
        self.assertEqual(collected[0][1], 1)
        self.assertGreaterEqual(collected[0][2], 0)
        monitor.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
