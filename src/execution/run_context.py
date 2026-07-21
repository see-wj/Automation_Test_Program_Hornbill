"""Per-run storage, output paths, and realtime CSV ownership."""

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from execution.run_storage import RunStorage, create_run_storage


REALTIME_COLUMNS = (
    "Index",
    "Set_Voltage",
    "Set_Current",
    "Programming_Voltage",
    "Readback_Voltage",
    "Readback_Current",
    "Programming_Voltage_Error",
    "Readback_Voltage_Error",
    "Programming_Voltage_Percentage_Error",
    "Readback_Voltage_Percentage_Error",
    "Programming_Upper_Limit_Boundary",
    "Programming_Lower_Limit_Boundary",
    "Readback_Upper_Limit_Boundary",
    "Readback_lower_Limit_Boundary",
    "Percentage_Upper_Limit_Boundary",
    "Percentage_Lower_Limit_Boundary",
)


@dataclass
class RunContext:
    run_id: str
    storage: RunStorage
    output_root: Path
    configuration: dict
    parameters: object
    checkbox_states: dict
    simulation_mode: bool = False
    csv_file: object = field(default=None, init=False, repr=False)
    csv_writer: object = field(default=None, init=False, repr=False)
    data_index: int = field(default=0, init=False)

    @classmethod
    def create(
        cls,
        run_id,
        output_root,
        dut_name,
        configuration,
        parameters,
        checkbox_states,
        simulation_mode=False,
    ):
        storage_name = f"{dut_name or 'DUT'}_SIMULATION" if simulation_mode else dut_name
        storage = create_run_storage(output_root, storage_name)
        context = cls(
            run_id=run_id,
            storage=storage,
            output_root=Path(output_root),
            configuration=configuration,
            parameters=parameters,
            checkbox_states=dict(checkbox_states),
            simulation_mode=simulation_mode,
        )
        context._configure_paths()
        context._write_metadata()
        return context

    @property
    def voltage_chart(self):
        return self.storage.charts / "Chart.png"

    @property
    def voltage_percentage_chart(self):
        return self.storage.charts / "Chart2.png"

    @property
    def power_chart(self):
        return self.storage.charts / "powerChart.png"

    def open_realtime_csv(self, timestamp):
        path = self.storage.raw / f"realtime_voltage_data_{timestamp}.csv"
        self.csv_file = path.open("w", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(REALTIME_COLUMNS)
        self.csv_file.flush()
        return path

    def write_realtime_row(self, values):
        if not self.csv_writer:
            return
        values = tuple(values)
        expected_values = len(REALTIME_COLUMNS) - 1
        if len(values) != expected_values:
            raise ValueError(
                f"Realtime row requires {expected_values} values, got {len(values)}"
            )
        self.data_index += 1
        self.csv_writer.writerow((self.data_index, *values))
        self.csv_file.flush()

    def activate_data_paths(self):
        from reporting import data as data_module

        data_module.configure_run_storage(self.storage.raw, self.storage.charts)

    def close(self):
        if self.csv_file:
            self.csv_file.flush()
            self.csv_file.close()
        self.csv_file = None
        self.csv_writer = None

    def restore_parameter_paths(self):
        self.parameters.savelocation = str(self.output_root)
        self.parameters.savedir = str(self.output_root)
        self.parameters.rawdir = None

    def _configure_paths(self):
        report_directory = str(self.storage.reports)
        raw_directory = str(self.storage.raw)
        self.parameters.savelocation = report_directory
        self.parameters.savedir = report_directory
        self.parameters.rawdir = raw_directory
        self.parameters.run_context = self
        self.configuration.update({
            "savedir": report_directory,
            "savelocation": report_directory,
            "rawdir": raw_directory,
            "simulation_mode": self.simulation_mode,
            "run_id": self.run_id,
        })

    def _write_metadata(self):
        with (self.storage.raw / "parameters.json").open(
            "w", encoding="utf-8"
        ) as parameter_file:
            json.dump(self.configuration, parameter_file, indent=2, default=str)
        if self.simulation_mode:
            (self.storage.root / "SIMULATION_RUN.txt").write_text(
                "This run contains simulated measurements and must not be used "
                "as hardware validation evidence.\n",
                encoding="utf-8",
            )
