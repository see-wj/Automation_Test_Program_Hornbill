"""Infer reviewed command bindings and execution plans from blueprint metadata."""

from copy import deepcopy
import re
from types import SimpleNamespace


def enrich_blueprint_execution_metadata(blueprint):
    data = deepcopy(blueprint)
    commands = [SimpleNamespace(**command) for command in data.get("commands", [])]
    data["command_bindings"] = build_command_bindings(commands)
    data["execution_plan"] = build_execution_plan(
        commands,
        data.get("sweeps", []),
    )
    data["schema_version"] = max(2, int(data.get("schema_version", 1)))
    return data


def build_command_bindings(commands):
    return [
        {
            "line": command.line,
            "mapping": command.selected_mapping,
            "arguments": _infer_arguments(
                command.command,
                command.selected_mapping,
                command.receiver,
            ),
        }
        for command in commands
    ]


def build_execution_plan(commands, sweeps):
    command_lines = {command.line: command for command in commands}
    voltage_sweeps = [
        sweep for sweep in sweeps if _sweep_quantity(sweep) == "voltage"
    ]
    current_sweeps = [
        sweep for sweep in sweeps if _sweep_quantity(sweep) == "current"
    ]
    if len(voltage_sweeps) < 2 or not current_sweeps:
        return {
            "template": "linear_reviewed_commands",
            "command_lines": sorted(command_lines),
            "shutdown_command_lines": _shutdown_lines(commands),
        }

    first_voltage = voltage_sweeps[0]
    current_sweep = current_sweeps[0]
    loaded_voltage = voltage_sweeps[1]
    shutdown_lines = _shutdown_lines(commands)
    shutdown_start = min(shutdown_lines) if shutdown_lines else float("inf")

    setup_lines = [
        command.line
        for command in commands
        if command.line < first_voltage["line"]
        and not _is_shutdown_command(command.command)
    ]
    no_load_lines = [
        command.line
        for command in commands
        if first_voltage["line"] < command.line < current_sweep["line"]
    ]
    transition_lines = [
        command.line
        for command in commands
        if current_sweep["line"] - 6 <= command.line < current_sweep["line"]
    ]
    no_load_lines = [line for line in no_load_lines if line not in transition_lines]
    outer_setup_lines = [
        command.line
        for command in commands
        if current_sweep["line"] < command.line < loaded_voltage["line"]
    ]
    loaded_point_lines = [
        command.line
        for command in commands
        if loaded_voltage["line"] < command.line < shutdown_start
    ]
    return {
        "template": "cv_voltage_current_sweep_v1",
        "power_limit_source": "safety.maximum_power",
        "setup_command_lines": setup_lines,
        "transition_command_lines": transition_lines,
        "shutdown_command_lines": shutdown_lines,
        "phases": [
            {
                "name": "no_load_voltage_sweep",
                "fixed_values": {"i": 0.0},
                "loops": [{"variable": "v", "sweep": dict(first_voltage)}],
                "point_command_lines": no_load_lines,
            },
            {
                "name": "loaded_current_voltage_sweep",
                "loops": [
                    {"variable": "i", "sweep": dict(current_sweep)},
                    {"variable": "v", "sweep": dict(loaded_voltage)},
                ],
                "outer_setup_command_lines": outer_setup_lines,
                "point_command_lines": loaded_point_lines,
            },
        ],
        "measurement_fields": {
            "current": "Current Load (A)",
            "voltage": "Set Voltage (V)",
            "fetch": "Output Voltage (V)",
            "diagnostic_0": "VMON (V)",
            "diagnostic_2": "VLOC (V)",
        },
    }


def _infer_arguments(command, mapping, receiver):
    normalized = str(command).strip()
    channel_match = re.search(r"\(@\s*(\d+)\s*\)", normalized, re.IGNORECASE)
    channel = channel_match.group(1) if channel_match else None
    arguments = []

    def add(name, expression, source="literal"):
        arguments.append(
            {"name": name, "expression": str(expression), "source": source}
        )

    if mapping == "DMM_344XXA.setConfiguration":
        mode = re.sub(r"^:?(?:CONFIGURE|CONF):?", "", normalized, flags=re.I)
        add("mode", mode)
    elif mapping == "DMM_344XXA.setTriggerSource":
        add("source", normalized.split()[-1])
    elif mapping.endswith(".setOutputState") or mapping.endswith(".outputState"):
        state_match = re.search(r"\b(ON|OFF|0|1)\b", normalized, re.IGNORECASE)
        add("state", state_match.group(1).upper() if state_match else "OFF")
        if channel:
            add("ChannelNumber", channel)
    elif mapping.endswith(".senseVoltageSource"):
        mode_match = re.search(r"SOUR(?:CE)?\s+([^,\s]+)", normalized, re.I)
        add("Mode", mode_match.group(1) if mode_match else "EXT")
        if channel:
            add("ChannelNumber", channel)
    elif mapping.endswith(".sourVoltageLevelImmediateAmplitude"):
        value = _programming_expression(normalized)
        add("Value", value, "loop" if value in {"v", "i"} else "literal")
        if channel:
            add("ChannelNumber", channel)
    elif mapping.endswith(".setOutputCurrent"):
        value = _programming_expression(normalized)
        add("value", value, "loop" if value in {"v", "i"} else "literal")
        if channel:
            add("ChannelNumber", channel)
    elif mapping == "IEEEStandard.TRG":
        add("VISA_ADDRESS", receiver, "instrument_address")
    elif mapping.endswith(".measureReadbackVoltage"):
        diagnostic_match = re.search(
            r"DIAG:PEEK\?\s*(\d+)\s*,\s*(\d+)", normalized, re.I
        )
        if diagnostic_match:
            bank = int(diagnostic_match.group(1))
            selector = int(diagnostic_match.group(2))
            add("ChannelNumber", max(1, bank - 19))
            add("mode", "DIAG")
            add("diagnostic_input", "VLOC" if selector == 2 else "VMON")
            add("sample", 100000)
    return arguments


def _programming_expression(command):
    without_channel = re.sub(r",?\s*\(@[^)]*\)", "", command).strip()
    parts = without_channel.split(None, 1)
    if len(parts) < 2:
        return "0"
    return parts[1].strip().strip("{}").strip()


def _sweep_quantity(sweep):
    description = " ".join(str(value) for value in sweep.values()).lower()
    if "curr" in description:
        return "current"
    if "volt" in description or "sweep_values" in description:
        return "voltage"
    return None


def _shutdown_lines(commands):
    lines_by_receiver = {}
    for command in commands:
        if _is_shutdown_command(command.command):
            lines_by_receiver.setdefault(command.receiver, []).append(command.line)
    result = []
    for lines in lines_by_receiver.values():
        result.append(lines[-2] if len(lines) >= 2 else lines[-1])
    return sorted(result)


def _is_shutdown_command(command):
    return bool(re.match(r"\s*OUTP(?:UT)?\s+OFF", str(command), re.IGNORECASE))


__all__ = [
    "build_command_bindings",
    "build_execution_plan",
    "enrich_blueprint_execution_metadata",
]
