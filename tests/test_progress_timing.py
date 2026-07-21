import unittest

from execution.progress_timing import (
    MeasurementProgressTracker,
    expected_measurement_points,
    format_duration,
)


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class ProgressTimingTests(unittest.TestCase):
    def test_counts_voltage_points_across_loops_and_channels(self):
        configuration = {
            "minCurrent": 0,
            "maxCurrent": 1,
            "current_step_size": 1,
            "minVoltage": 5,
            "maxVoltage": 10,
            "voltage_step_size": 5,
            "power": 100,
            "noofloop": 2,
            "PSU_Channel": [1, 2],
        }

        total = expected_measurement_points(
            configuration,
            {"VoltageAccuracy": True},
        )

        self.assertEqual(total, 16)

    def test_power_limit_excludes_unreachable_voltage_current_points(self):
        configuration = {
            "minCurrent": 1,
            "maxCurrent": 2,
            "current_step_size": 1,
            "minVoltage": 5,
            "maxVoltage": 10,
            "voltage_step_size": 5,
            "power": 10,
            "noofloop": 1,
            "PSU_Channel": [1],
        }

        total = expected_measurement_points(
            configuration,
            {"VoltageAccuracy": True},
        )

        self.assertEqual(total, 3)

    def test_eta_uses_measured_instrument_and_delay_time(self):
        clock = FakeClock()
        tracker = MeasurementProgressTracker(10, initial_seconds_per_point=3, clock=clock)

        self.assertEqual(tracker.snapshot().remaining_seconds, 30)

        clock.advance(5)
        tracker.record_measurement()
        first = tracker.snapshot()
        self.assertEqual(first.percent, 10)
        self.assertEqual(first.remaining_seconds, 45)

        clock.advance(7)
        tracker.record_measurement()
        second = tracker.snapshot()
        self.assertEqual(second.percent, 20)
        self.assertEqual(second.remaining_seconds, 48)

    def test_paused_time_is_excluded_from_eta(self):
        clock = FakeClock()
        tracker = MeasurementProgressTracker(2, clock=clock)
        clock.advance(2)
        tracker.pause()
        clock.advance(100)
        tracker.resume()
        tracker.record_measurement()

        snapshot = tracker.snapshot()

        self.assertEqual(snapshot.elapsed_seconds, 2)
        self.assertEqual(snapshot.remaining_seconds, 2)

    def test_complete_snapshot_reaches_one_hundred_percent(self):
        tracker = MeasurementProgressTracker(5, clock=FakeClock())

        tracker.mark_complete()
        snapshot = tracker.snapshot()

        self.assertEqual(snapshot.percent, 100)
        self.assertEqual(snapshot.remaining_seconds, 0)

    def test_measurement_progress_stays_below_complete_until_run_finishes(self):
        tracker = MeasurementProgressTracker(1, clock=FakeClock())

        tracker.record_measurement()
        snapshot = tracker.snapshot()

        self.assertEqual(snapshot.percent, 99)
        self.assertEqual(snapshot.completed, snapshot.total)

    def test_formats_short_and_long_durations(self):
        self.assertEqual(format_duration(65), "01:05")
        self.assertEqual(format_duration(3661), "1:01:01")


if __name__ == "__main__":
    unittest.main()
