"""Measured progress and ETA calculations for active test runs."""

import math
import time
from dataclasses import dataclass


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _inclusive_values(start, stop, step):
    if step <= 0 or stop < start:
        return []
    count = int(math.floor(((stop - start) / step) + 1e-9)) + 1
    return [min(stop, start + index * step) for index in range(count)]


def _channel_count(channels):
    if isinstance(channels, range):
        return len(channels)
    if isinstance(channels, (list, tuple, set)):
        return max(1, len(channels))
    return 1


def expected_measurement_points(configuration, selections):
    loops = max(1, int(_number(configuration.get("noofloop"), 1)))
    channels = _channel_count(configuration.get("PSU_Channel"))

    if selections.get("VoltageAccuracy"):
        currents = _inclusive_values(
            _number(configuration.get("minCurrent")),
            _number(configuration.get("maxCurrent")),
            _number(configuration.get("current_step_size")),
        )
        voltages = _inclusive_values(
            _number(configuration.get("minVoltage")),
            _number(configuration.get("maxVoltage")),
            _number(configuration.get("voltage_step_size")),
        )
        power_limit = _number(configuration.get("power"), math.inf)
        points = sum(
            1
            for current in currents
            for voltage in voltages
            if voltage * current <= power_limit
        )
        return points * loops * channels

    if selections.get("CurrentAccuracy"):
        currents = _inclusive_values(
            _number(configuration.get("minCurrent")),
            _number(configuration.get("maxCurrent")),
            _number(configuration.get("current_step_size")),
        )
        return len(currents) * loops * channels

    return 0


def format_duration(seconds):
    seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


@dataclass(frozen=True)
class ProgressSnapshot:
    completed: int
    total: int
    percent: int
    elapsed_seconds: float
    remaining_seconds: float | None


class MeasurementProgressTracker:
    def __init__(self, total_points, initial_seconds_per_point=1.0, clock=None):
        self.total_points = max(0, int(total_points))
        self.initial_seconds_per_point = max(0.0, float(initial_seconds_per_point))
        self.clock = clock or time.monotonic
        self.started_at = self.clock()
        self.completed_points = 0
        self.paused_at = None
        self.paused_seconds = 0.0
        self.completed = False

    def record_measurement(self):
        if not self.completed:
            self.completed_points += 1

    def pause(self):
        if self.paused_at is None:
            self.paused_at = self.clock()

    def resume(self):
        if self.paused_at is not None:
            self.paused_seconds += self.clock() - self.paused_at
            self.paused_at = None

    def mark_complete(self):
        self.completed = True

    def snapshot(self):
        now = self.clock()
        current_pause = now - self.paused_at if self.paused_at is not None else 0.0
        elapsed = max(0.0, now - self.started_at - self.paused_seconds - current_pause)

        if self.completed:
            percent = 100
            remaining = 0.0
        elif self.total_points > 0:
            percent = min(99, int(self.completed_points * 100 / self.total_points))
            seconds_per_point = (
                elapsed / self.completed_points
                if self.completed_points
                else self.initial_seconds_per_point
            )
            remaining_points = max(0, self.total_points - self.completed_points)
            remaining = remaining_points * seconds_per_point
        else:
            percent = 0
            remaining = None

        return ProgressSnapshot(
            completed=self.completed_points,
            total=self.total_points,
            percent=percent,
            elapsed_seconds=elapsed,
            remaining_seconds=remaining,
        )
