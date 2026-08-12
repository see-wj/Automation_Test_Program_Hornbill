"""Live temperature plotting for Bundle Test runs."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

import pyqtgraph as pg


class TemperaturePlotWidget(QWidget):
    """Plot DAQ temperature channels as samples arrive from the worker."""

    CHANNEL_COLORS = (
        "#e74c3c",
        "#3498db",
        "#2ecc71",
        "#f39c12",
        "#9b59b6",
        "#1abc9c",
        "#e67e22",
        "#34495e",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sample_numbers = []
        self.elapsed_seconds = []
        self.channel_data = {}
        self.channel_curves = {}
        self.first_timestamp = None
        self.run_state = "IDLE"
        self._last_sample_text = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.status_label = QLabel(
            "Temperature monitoring disabled. Enable Measure Temperature to collect data."
        )
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(self._status_style("#404040"))
        layout.addWidget(self.status_label)

        self.plot = pg.PlotWidget(title="DAQ973A Temperature Monitoring")
        self.plot.addLegend(offset=(10, 10))
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.setLabel("bottom", "Elapsed Time", units="s")
        self.plot.setLabel("left", "Temperature", units="°C")
        layout.addWidget(self.plot)

    @staticmethod
    def _status_style(background):
        return (
            "QLabel { "
            f"background:{background}; color:white; padding:8px; "
            "font-weight:bold; border-radius:4px; }"
        )

    def reset(self, enabled=False):
        self.sample_numbers.clear()
        self.elapsed_seconds.clear()
        self.channel_data.clear()
        self.first_timestamp = None
        self.run_state = "IDLE"
        self._last_sample_text = None
        for curve in self.channel_curves.values():
            self.plot.removeItem(curve)
        self.channel_curves.clear()
        if enabled:
            message = "Temperature monitoring ready; waiting for the first DAQ scan."
        else:
            message = (
                "Temperature monitoring disabled. Enable Measure Temperature "
                "to collect data."
            )
        self.status_label.setText(message)
        self.status_label.setStyleSheet(self._status_style("#404040"))

    def update_test_state(self, state):
        self.run_state = str(state).upper()
        if self._last_sample_text:
            self.status_label.setText(
                f"{self.run_state} | {self._last_sample_text}"
            )
        else:
            self.status_label.setText(
                f"Status: {self.run_state} | Waiting for temperature data"
            )
        if self.run_state in {"PAUSED", "PAUSING", "STOPPING"}:
            color = "#b36b00"
        elif self.run_state in {"FAILED", "ABORTED"}:
            color = "#b22222"
        elif self.run_state == "COMPLETED":
            color = "#1b7f3a"
        else:
            color = "#404040"
        self.status_label.setStyleSheet(self._status_style(color))

    def add_sample(self, sample, loop_index):
        if not sample.readings:
            return

        if self.first_timestamp is None:
            self.first_timestamp = sample.timestamp
        elapsed = max(
            0.0,
            (sample.timestamp - self.first_timestamp).total_seconds(),
        )
        self.sample_numbers.append(int(loop_index) + 1)
        self.elapsed_seconds.append(elapsed)

        for channel, temperature in sample.readings.items():
            channel = int(channel)
            if channel not in self.channel_curves:
                color = self.CHANNEL_COLORS[
                    len(self.channel_curves) % len(self.CHANNEL_COLORS)
                ]
                self.channel_curves[channel] = self.plot.plot(
                    pen=pg.mkPen(color, width=3),
                    symbol="o",
                    symbolSize=7,
                    name=f"CH{channel}",
                )
                self.channel_data[channel] = [float("nan")] * (
                    len(self.elapsed_seconds) - 1
                )

        for channel in self.channel_curves:
            value = sample.readings.get(channel, float("nan"))
            self.channel_data[channel].append(float(value))
            self.channel_curves[channel].setData(
                self.elapsed_seconds,
                self.channel_data[channel],
            )

        readings = " | ".join(
            f"CH{channel}: {temperature:.3f} °C"
            for channel, temperature in sample.readings.items()
        )
        self._last_sample_text = (
            f"Loop {int(loop_index) + 1} | Elapsed {elapsed:.1f} s | {readings}"
        )
        self.status_label.setText(f"{self.run_state} | {self._last_sample_text}")
        self.status_label.setStyleSheet(self._status_style("#1b7f3a"))
