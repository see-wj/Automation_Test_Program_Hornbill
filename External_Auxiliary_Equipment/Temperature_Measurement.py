"""Optional DAQ973A thermocouple monitoring for DUT test runs."""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from SCPI_Library.Keysight import DAQ973A


DEFAULT_CHANNEL_TYPES = {
    101: "T",
    103: "T",
    104: "E",
    105: "E",
}


@dataclass(frozen=True)
class TemperatureSample:
    timestamp: datetime
    readings: dict[int, float]

    def status_text(self):
        values = ", ".join(
            f"CH{channel}={temperature:.3f} °C"
            for channel, temperature in self.readings.items()
        )
        return f"Temperature: {values}"


class TemperatureMeasurement:
    def __init__(
        self,
        visa_address,
        channel_types=None,
        output_file=None,
        daq_class=DAQ973A,
    ):
        self.channel_types = dict(channel_types or DEFAULT_CHANNEL_TYPES)
        self.channels = tuple(self.channel_types)
        self.output_file = Path(output_file) if output_file else None
        self.daq = daq_class(visa_address)
        self.configured = False

    def configure(self):
        self.daq.clearStatus()
        self.daq.reset()
        self.daq.configureThermocoupleTemperature(self.channels)

        channels_by_type = {}
        for channel, thermocouple_type in self.channel_types.items():
            channels_by_type.setdefault(str(thermocouple_type).upper(), []).append(channel)
        for thermocouple_type, channels in channels_by_type.items():
            self.daq.setThermocoupleType(thermocouple_type, channels)

        self.daq.setInternalReferenceJunction(self.channels)
        self.daq.setTemperatureNPLC(1, self.channels)
        self.daq.enableAutomaticChannelDelay(self.channels)
        self.daq.setScanChannels(self.channels)
        self._raise_for_errors()
        self.configured = True

    def measure(self, loop_index=None):
        if not self.configured:
            self.configure()
        values = self.daq.readScan()
        if len(values) != len(self.channels):
            raise RuntimeError(
                f"DAQ973A returned {len(values)} temperature value(s); "
                f"expected {len(self.channels)}"
            )
        sample = TemperatureSample(
            timestamp=datetime.now(),
            readings=dict(zip(self.channels, values)),
        )
        if self.output_file:
            self._append_csv(sample, loop_index)
        return sample

    def _raise_for_errors(self):
        for _ in range(100):
            response = str(self.daq.queryError()).strip()
            error_code = response.split(",", 1)[0].strip()
            try:
                has_error = float(error_code) != 0
            except ValueError as exception:
                raise RuntimeError(
                    f"Unrecognized DAQ973A SYST:ERR? response: {response!r}"
                ) from exception
            if not has_error:
                return
            raise RuntimeError(f"DAQ973A error: {response}")
        raise RuntimeError("DAQ973A error queue did not clear")

    def _append_csv(self, sample, loop_index):
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        new_file = not self.output_file.exists()
        with self.output_file.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            if new_file:
                writer.writerow(("Timestamp", "Loop", *(
                    f"CH{channel}_{self.channel_types[channel]}_C"
                    for channel in self.channels
                )))
            writer.writerow((
                sample.timestamp.isoformat(timespec="seconds"),
                "" if loop_index is None else int(loop_index) + 1,
                *(sample.readings[channel] for channel in self.channels),
            ))

    def close(self):
        instrument = getattr(self.daq, "instr", None)
        if instrument is not None:
            instrument.close()


def measure_temperature(visa_address, channel_types=None):
    """Configure a DAQ973A, take one scan, and close the VISA resource."""
    monitor = TemperatureMeasurement(visa_address, channel_types=channel_types)
    try:
        return monitor.measure()
    finally:
        monitor.close()
