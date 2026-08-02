"""Deterministic simulation executor for approved integration blueprints."""

import csv
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import monotonic, sleep
from types import SimpleNamespace

from analysis.blueprint_execution import enrich_blueprint_execution_metadata
from SCPI_Library.simulation import SimulatedVisaResourceManager, reset_simulation
from execution.run_context import RunContext


SIMULATION_ADDRESS_BY_ROLE = {
    "DUT/Hornbill": "USB0::SIM::PSU::INSTR",
    "DMM": "USB0::SIM::DMM::INSTR",
    "ELOAD": "USB0::SIM::ELOAD::INSTR",
    "OSCILLOSCOPE": "USB0::SIM::SCOPE::INSTR",
    "EXTERNALSOURCE": "USB0::SIM::ACSOURCE::INSTR",
}


class BlueprintSimulationCancelled(RuntimeError):
    pass


class BlueprintExecutionControl:
    def __init__(self):
        self._condition = threading.Condition()
        self._paused = False
        self._aborted = False

    def pause(self):
        with self._condition:
            self._paused = True

    def resume(self):
        with self._condition:
            self._paused = False
            self._condition.notify_all()

    def abort(self):
        with self._condition:
            self._aborted = True
            self._paused = False
            self._condition.notify_all()

    def checkpoint(self):
        with self._condition:
            while self._paused and not self._aborted:
                self._condition.wait(timeout=0.1)
            if self._aborted:
                raise BlueprintSimulationCancelled("Simulation aborted by user")

    def interruptible_sleep(self, seconds):
        deadline = monotonic() + max(0.0, float(seconds))
        while True:
            self.checkpoint()
            remaining = deadline - monotonic()
            if remaining <= 0:
                return
            sleep(min(0.05, remaining))


@dataclass(frozen=True)
class BlueprintSimulationResult:
    rows: tuple[dict, ...]
    command_log: tuple[tuple[str, str], ...]
    csv_path: Path
    run_directory: Path


class BlueprintSimulationExecutor:
    def __init__(
        self,
        blueprint,
        configuration,
        *,
        output_root,
        control=None,
        progress_callback=None,
        honor_settling_delay=False,
    ):
        blueprint_data = (
            blueprint.to_dict() if hasattr(blueprint, "to_dict") else dict(blueprint)
        )
        self.blueprint = enrich_blueprint_execution_metadata(blueprint_data)
        self.configuration = dict(configuration)
        self.output_root = Path(output_root)
        self.control = control or BlueprintExecutionControl()
        self.progress_callback = progress_callback
        self.honor_settling_delay = bool(honor_settling_delay)
        self.commands = {
            int(command["line"]): command
            for command in self.blueprint.get("commands", [])
        }
        self.resources = {}
        self.manager = None
        self.run_context = None
        self.rows = []
        self.completed_points = 0
        self.total_points = 0

    def run(self):
        self._validate()
        reset_simulation()
        self.run_context = self._create_run_context()
        self.manager = SimulatedVisaResourceManager()
        self._open_resources()
        plan = self.blueprint["execution_plan"]
        failure = None
        csv_path = None
        try:
            self._execute_lines(plan.get("setup_command_lines", ()), {})
            phases = plan.get("phases", ())
            self.total_points = self._count_points(phases)
            if phases:
                self._run_no_load_phase(phases[0])
            self._execute_lines(plan.get("transition_command_lines", ()), {})
            if len(phases) > 1:
                self._run_loaded_phase(phases[1])
        except BaseException as exception:
            failure = exception
        finally:
            self._guaranteed_shutdown(plan.get("shutdown_command_lines", ()))
            self._close_resources()
            csv_path = self._write_results()
            self.run_context.close()
        if failure is not None:
            raise failure
        state = self.manager.state
        result = BlueprintSimulationResult(
            rows=tuple(self.rows),
            command_log=tuple(state.command_log),
            csv_path=csv_path,
            run_directory=self.run_context.storage.root,
        )
        return result

    def _validate(self):
        if self.blueprint.get("status") != "approved":
            raise ValueError("Simulation requires an approved blueprint.")
        if not self.configuration.get("simulation_mode"):
            raise ValueError("Blueprint executor is restricted to simulation mode.")
        plan = self.blueprint.get("execution_plan") or {}
        if plan.get("template") != "cv_voltage_current_sweep_v1":
            raise ValueError("Blueprint has no supported reviewed CV execution plan.")
        parameters = self.configuration.get("parameters", {})
        for name in ("curr_start", "curr_step", "volt_start", "volt_step"):
            if name not in parameters:
                raise ValueError(f"Missing generated parameter: {name}")
            parameters[name] = float(parameters[name])
        if parameters["curr_start"] < 0 or parameters["volt_start"] < 0:
            raise ValueError("Sweep start values must be non-negative.")
        if parameters["curr_step"] <= 0 or parameters["volt_step"] <= 0:
            raise ValueError("Sweep step values must be greater than zero.")

    def _create_run_context(self):
        parameters = SimpleNamespace(
            savelocation=str(self.output_root),
            savedir=str(self.output_root),
            rawdir=None,
            run_context=None,
        )
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        configuration = dict(self.configuration)
        return RunContext.create(
            run_id=run_id,
            output_root=self.output_root,
            dut_name=self.blueprint.get("test_name", "Generated_Test"),
            configuration=configuration,
            parameters=parameters,
            checkbox_states={},
            simulation_mode=True,
        )

    def _open_resources(self):
        role_by_variable = {
            item["variable"]: item["role"]
            for item in self.blueprint.get("instruments", [])
        }
        for variable, role in role_by_variable.items():
            address = SIMULATION_ADDRESS_BY_ROLE.get(role)
            if not address:
                raise ValueError(f"No simulated instrument is registered for role {role}")
            self.resources[variable] = self.manager.open_resource(address)

    def _run_no_load_phase(self, phase):
        parameters = self.configuration["parameters"]
        loop = phase["loops"][0]
        for voltage in _float_range(
            parameters[loop["sweep"]["start"]],
            float(loop["sweep"]["stop"]),
            parameters[loop["sweep"]["step"]],
        ):
            values = {"v": voltage, **phase.get("fixed_values", {})}
            if not self._within_power_limit(values):
                break
            self._execute_point(phase["point_command_lines"], values)

    def _run_loaded_phase(self, phase):
        parameters = self.configuration["parameters"]
        current_loop, voltage_loop = phase["loops"]
        for current in _float_range(
            parameters[current_loop["sweep"]["start"]],
            float(current_loop["sweep"]["stop"]),
            parameters[current_loop["sweep"]["step"]],
        ):
            outer_values = {"i": round(current, 9)}
            self._execute_lines(phase.get("outer_setup_command_lines", ()), outer_values)
            for voltage in _float_range(
                parameters[voltage_loop["sweep"]["start"]],
                float(voltage_loop["sweep"]["stop"]),
                parameters[voltage_loop["sweep"]["step"]],
            ):
                values = {**outer_values, "v": voltage}
                if not self._within_power_limit(values):
                    break
                self._execute_point(phase["point_command_lines"], values)

    def _execute_point(self, command_lines, values):
        measurements = self._execute_lines(command_lines, values)
        row = {
            "Current Load (A)": float(values.get("i", 0.0)),
            "Set Voltage (V)": float(values.get("v", 0.0)),
            "Output Voltage (V)": measurements.get("fetch", 0.0),
            "VMON (V)": measurements.get("diagnostic_0", 0.0),
            "VLOC (V)": measurements.get("diagnostic_2", 0.0),
        }
        self.rows.append(row)
        self.completed_points += 1
        self._notify_progress(
            f"Point {self.completed_points}/{self.total_points}: "
            f"{row['Set Voltage (V)']:g} V, {row['Current Load (A)']:g} A"
        )

    def _execute_lines(self, command_lines, values):
        measurements = {}
        for line in command_lines:
            self.control.checkpoint()
            command = self.commands[int(line)]
            resource = self.resources[command["receiver"]]
            rendered = _render_command(command["command"], values)
            normalized = rendered.upper()
            operation = command["operation"]
            if "STAT" in normalized and "OPER" in normalized and "?" in normalized:
                self._poll_operation_complete(resource, rendered)
            elif operation in {"query", "query_ascii_values", "socket_query"}:
                response = resource.query_ascii_values(rendered)[0]
                if "FETC" in normalized:
                    measurements["fetch"] = float(response)
                elif "DIAG:PEEK?" in normalized:
                    selector = _diagnostic_selector(rendered)
                    measurements[f"diagnostic_{selector}"] = float(response)
            else:
                resource.write(rendered)
                if self.honor_settling_delay and _programs_voltage(rendered):
                    self.control.interruptible_sleep(
                        self.blueprint["safety"]["settling_delay_seconds"]
                    )
            self.control.checkpoint()
        return measurements

    def _poll_operation_complete(self, resource, command):
        timeout = float(self.blueprint["safety"]["polling_timeout_seconds"])
        deadline = monotonic() + timeout
        while True:
            self.control.checkpoint()
            status = int(resource.query_ascii_values(command)[0])
            if status == 512:
                return
            if monotonic() >= deadline:
                raise TimeoutError(f"DMM polling exceeded {timeout:g} seconds")
            self.control.interruptible_sleep(0.05)

    def _within_power_limit(self, values):
        voltage = float(values.get("v", 0.0))
        current = float(values.get("i", 0.0))
        return voltage * current <= float(self.blueprint["safety"]["maximum_power"])

    def _count_points(self, phases):
        parameters = self.configuration["parameters"]
        total = 0
        for phase in phases:
            loops = phase.get("loops", ())
            if len(loops) == 1:
                total += len(
                    _float_range(
                        parameters[loops[0]["sweep"]["start"]],
                        float(loops[0]["sweep"]["stop"]),
                        parameters[loops[0]["sweep"]["step"]],
                    )
                )
            elif len(loops) == 2:
                currents = _float_range(
                    parameters[loops[0]["sweep"]["start"]],
                    float(loops[0]["sweep"]["stop"]),
                    parameters[loops[0]["sweep"]["step"]],
                )
                voltages = _float_range(
                    parameters[loops[1]["sweep"]["start"]],
                    float(loops[1]["sweep"]["stop"]),
                    parameters[loops[1]["sweep"]["step"]],
                )
                total += sum(
                    1
                    for current in currents
                    for voltage in voltages
                    if current * voltage <= float(self.blueprint["safety"]["maximum_power"])
                )
        return total

    def _guaranteed_shutdown(self, command_lines):
        for line in command_lines:
            try:
                command = self.commands[int(line)]
                self.resources[command["receiver"]].write(command["command"])
            except Exception:
                continue

    def _close_resources(self):
        for resource in self.resources.values():
            try:
                resource.close()
            except Exception:
                continue
        if self.manager is not None:
            try:
                self.manager.close()
            except Exception:
                pass

    def _write_results(self):
        csv_path = self.run_context.storage.raw / "blueprint_simulation_results.csv"
        fields = list(self.blueprint.get("data_fields", ()))
        with csv_path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self.rows)
        return csv_path

    def _notify_progress(self, message):
        if self.progress_callback:
            self.progress_callback(
                message,
                self.completed_points,
                self.total_points,
            )


def _float_range(start, stop, step):
    start = float(start)
    stop = float(stop)
    step = float(step)
    if step <= 0:
        raise ValueError("Sweep step must be greater than zero")
    values = []
    index = 0
    while True:
        value = start + index * step
        if value >= stop - 1e-12:
            break
        values.append(round(value, 12))
        index += 1
    return values


def _render_command(command, values):
    rendered = str(command)
    for name, value in values.items():
        rendered = rendered.replace("{" + name + "}", f"{value:g}")
    if re.search(r"\{[^}]+\}", rendered):
        raise ValueError(f"Unresolved command expression: {rendered}")
    return rendered


def _diagnostic_selector(command):
    match = re.search(r"DIAG:PEEK\?\s*\d+\s*,\s*(\d+)", command, re.I)
    return int(match.group(1)) if match else -1


def _programs_voltage(command):
    return bool(re.match(r"\s*(?:SOUR(?:CE)?:)?VOLT", command, re.I))


__all__ = [
    "BlueprintExecutionControl",
    "BlueprintSimulationCancelled",
    "BlueprintSimulationExecutor",
    "BlueprintSimulationResult",
]
