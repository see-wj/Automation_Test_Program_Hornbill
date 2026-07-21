import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.realtime_plot import RealtimeMeasurement, RealtimePlotSeries


def measurement(programming_error=0.1, readback_error=0.2):
    return RealtimeMeasurement(
        set_voltage=5.0,
        set_current=1.0,
        programming_voltage=5.1,
        readback_voltage=5.05,
        readback_current=1.0,
        programming_error=programming_error,
        readback_error=readback_error,
        programming_percent=2.0,
        readback_percent=1.0,
        programming_upper_bound=0.5,
        programming_lower_bound=-0.5,
        readback_upper_bound=0.5,
        readback_lower_bound=-0.5,
        percentage_upper_bound=100.0,
        percentage_lower_bound=-100.0,
    )


class RealtimePlotTests(unittest.TestCase):
    def test_measurement_exposes_complete_csv_row_and_status(self):
        point = measurement()

        self.assertTrue(point.passed)
        self.assertEqual(len(point.csv_values), 15)
        self.assertFalse(measurement(programming_error=0.6).passed)

    def test_series_keeps_only_latest_points(self):
        series = RealtimePlotSeries(max_points=100)

        for _ in range(105):
            series.append(measurement())

        self.assertEqual(len(series.x_data), 100)
        self.assertEqual(series.x_data[0], 6)
        self.assertEqual(series.x_data[-1], 105)


if __name__ == "__main__":
    unittest.main()
