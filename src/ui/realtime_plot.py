"""Realtime measurement values and bounded plot-series state."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RealtimeMeasurement:
    set_voltage: float
    set_current: float
    programming_voltage: float
    readback_voltage: float
    readback_current: float
    programming_error: float
    readback_error: float
    programming_percent: float
    readback_percent: float
    programming_upper_bound: float
    programming_lower_bound: float
    readback_upper_bound: float
    readback_lower_bound: float
    percentage_upper_bound: float
    percentage_lower_bound: float

    @property
    def passed(self):
        return (
            self.programming_lower_bound
            <= self.programming_error
            <= self.programming_upper_bound
            and self.readback_lower_bound
            <= self.readback_error
            <= self.readback_upper_bound
        )

    @property
    def csv_values(self):
        return (
            self.set_voltage,
            self.set_current,
            self.programming_voltage,
            self.readback_voltage,
            self.readback_current,
            self.programming_error,
            self.readback_error,
            self.programming_percent,
            self.readback_percent,
            self.programming_upper_bound,
            self.programming_lower_bound,
            self.readback_upper_bound,
            self.readback_lower_bound,
            self.percentage_upper_bound,
            self.percentage_lower_bound,
        )


@dataclass
class RealtimePlotSeries:
    max_points: int = 100
    counter: int = 0
    x_data: list = field(default_factory=list)
    programming_data: list = field(default_factory=list)
    readback_data: list = field(default_factory=list)
    upper_bound_data: list = field(default_factory=list)
    lower_bound_data: list = field(default_factory=list)

    def append(self, measurement):
        self.counter += 1
        self.x_data.append(self.counter)
        self.programming_data.append(measurement.programming_error)
        self.readback_data.append(measurement.readback_error)
        self.upper_bound_data.append(measurement.programming_upper_bound)
        self.lower_bound_data.append(measurement.programming_lower_bound)

        if len(self.x_data) > self.max_points:
            self.x_data = self.x_data[-self.max_points :]
            self.programming_data = self.programming_data[-self.max_points :]
            self.readback_data = self.readback_data[-self.max_points :]
            self.upper_bound_data = self.upper_bound_data[-self.max_points :]
            self.lower_bound_data = self.lower_bound_data[-self.max_points :]
