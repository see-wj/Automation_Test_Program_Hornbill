import os
import re
import sys
import threading
from dataclasses import dataclass, field

import pyvisa

from SCPI_Library.instrument_errors import ReportGenerationError


SIMULATION_ENVIRONMENT_VARIABLE = "AUTOMATION_SIMULATION"


def is_simulation_mode():
    value = os.getenv(SIMULATION_ENVIRONMENT_VARIABLE, "").strip().lower()
    return value in {"1", "true", "yes", "on"} or "--simulate" in sys.argv


@dataclass
class SimulationState:
    voltage: float = 0.0
    load_voltage: float = 0.0
    current: float = 0.0
    load_current: float = 0.0
    output_enabled: bool = False
    selected_channel: int = 1
    command_log: list = field(default_factory=list)
    faults: list = field(default_factory=list)


@dataclass
class SimulationFault:
    operation: str
    error: str
    resource_name: str = None
    command_pattern: str = None
    after: int = 0
    remaining: int = 1

    def matches(self, operation, resource_name=None, command=None):
        if self.operation != operation:
            return False
        if self.resource_name and self.resource_name != resource_name:
            return False
        if self.command_pattern and not re.search(
            self.command_pattern, str(command or ""), re.IGNORECASE
        ):
            return False
        return True


SIMULATED_INSTRUMENTS = {
    "USB0::SIM::PSU::INSTR": "KEYSIGHT,E36441A,SIM-PSU,1.0",
    "USB0::SIM::DMM::INSTR": "KEYSIGHT,34470A,SIM-DMM,1.0",
    "USB0::SIM::DMM2::INSTR": "KEYSIGHT,34461A,SIM-DMM2,1.0",
    "USB0::SIM::ELOAD::INSTR": "KEYSIGHT,EL33133A,SIM-ELOAD,1.0",
    "USB0::SIM::SCOPE::INSTR": "KEYSIGHT,MSO6104A,SIM-SCOPE,1.0",
    "USB0::SIM::ACSOURCE::INSTR": "KEYSIGHT,6813C,SIM-ACSOURCE,1.0",
}


_simulation_state = SimulationState()
_main_thread_resource_manager = None


def get_simulation_state():
    return _simulation_state


def reset_simulation():
    global _simulation_state
    _simulation_state = SimulationState()
    return _simulation_state


def inject_simulation_fault(
    operation,
    error,
    resource_name=None,
    command_pattern=None,
    after=0,
    repeat=1,
):
    if after < 0 or repeat < 1:
        raise ValueError("after must be non-negative and repeat must be positive")
    fault = SimulationFault(
        operation=str(operation),
        error=str(error),
        resource_name=str(resource_name) if resource_name else None,
        command_pattern=command_pattern,
        after=int(after),
        remaining=int(repeat),
    )
    get_simulation_state().faults.append(fault)
    return fault


def clear_simulation_faults():
    get_simulation_state().faults.clear()


def raise_for_simulation_fault(operation, resource_name=None, command=None):
    state = get_simulation_state()
    for fault in tuple(state.faults):
        if not fault.matches(operation, resource_name, command):
            continue
        if fault.after:
            fault.after -= 1
            continue
        fault.remaining -= 1
        if not fault.remaining:
            state.faults.remove(fault)
        if fault.error == "timeout":
            raise pyvisa.VisaIOError(pyvisa.constants.StatusCode.error_timeout)
        if fault.error == "disconnect":
            raise pyvisa.VisaIOError(pyvisa.constants.StatusCode.error_connection_lost)
        if fault.error == "report":
            raise ReportGenerationError(
                "Simulated report generation failure",
                operation=operation,
            )
        if fault.error == "cleanup":
            raise RuntimeError("Simulated cleanup failure")
        raise ValueError(f"Unknown simulation fault type: {fault.error}")


class SimulatedVisaResource:
    def __init__(self, resource_name, identity, state):
        self.resource_name = resource_name
        self.identity = identity
        self.state = state
        self.timeout = 15000
        self.baud_rate = 9600
        self.write_termination = "\n"
        self.read_termination = "\n"
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def close(self):
        raise_for_simulation_fault("close", self.resource_name)
        self.closed = True

    def clear(self):
        return None

    def write(self, message):
        command = str(message).strip()
        raise_for_simulation_fault("write", self.resource_name, command)
        self.state.command_log.append((self.resource_name, command))
        normalized = command.upper()
        value = self._programming_value(command)

        if "INST" in normalized and "NSEL" in normalized and value is not None:
            self.state.selected_channel = int(value)
        elif normalized.startswith(("VOLT", "SOUR:VOLT", "SOURCE:VOLT")) and value is not None:
            if "ELOAD" in self.resource_name:
                self.state.load_voltage = value
            else:
                self.state.voltage = value
        elif "LOAD" in self.resource_name and normalized.startswith("CURR"):
            if value is not None:
                self.state.load_current = value
        elif normalized.startswith(("CURR", "SOUR:CURR", "SOURCE:CURR")) and value is not None:
            self.state.current = value
        elif normalized.startswith(("OUTP", "OUTPUT", "LOAD")):
            self.state.output_enabled = not any(
                token in normalized for token in ("OFF", " 0")
            )
        return len(command)

    def query(self, message):
        command = str(message).strip()
        raise_for_simulation_fault("query", self.resource_name, command)
        self.state.command_log.append((self.resource_name, command))
        normalized = command.upper()

        if normalized == "*IDN?":
            return self.identity + "\n"
        if normalized in {"*OPC?", "*TST?"}:
            return "1\n" if normalized == "*OPC?" else "0\n"
        if normalized.startswith("SYST:ERR"):
            return '0,"No error"\n'
        if normalized.startswith("STAT:OPER:COND"):
            return "512\n"
        if normalized.startswith("DIAG:PEEK?"):
            selector = self._diagnostic_selector(command)
            value = self._measured_voltage() if selector in {0, 2} else self._measured_current()
            return f"{value:.9f}\n"
        if "INST" in normalized and "NSEL" in normalized:
            return f"{self.state.selected_channel}\n"
        if "VOLT" in normalized:
            return f"{self._measured_voltage():.9f}\n"
        if "CURR" in normalized:
            return f"{self._measured_current():.9f}\n"
        if any(token in normalized for token in ("FETC", "FETCH", "READ")):
            return f"{self._measured_value():.9f}\n"
        if normalized.startswith("DATE?"):
            return "2026,1,1\n"
        if "TIME?" in normalized:
            return "0,0,0\n"
        if "VERS?" in normalized:
            return "1999.0\n"
        return "0\n"

    def query_ascii_values(self, message, *args, **kwargs):
        response = self.query(message).strip().split(",")
        values = []
        for value in response:
            try:
                values.append(float(value))
            except ValueError:
                continue
        return values or [0.0]

    def query_binary_values(self, message, *args, **kwargs):
        return self.query_ascii_values(message, *args, **kwargs)

    def write_ascii_values(self, message, values, *args, **kwargs):
        payload = ",".join(str(value) for value in values)
        return self.write(f"{message} {payload}")

    def write_binary_values(self, message, values, *args, **kwargs):
        return self.write_ascii_values(message, values, *args, **kwargs)

    def read(self):
        raise_for_simulation_fault("read", self.resource_name)
        return f"{self._measured_value():.9f}\n"

    def read_raw(self):
        return self.read().encode("ascii")

    def read_ascii_values(self, *args, **kwargs):
        return [float(self.read())]

    def read_binary_values(self, *args, **kwargs):
        return self.read_ascii_values(*args, **kwargs)

    def read_bytes(self, count, *args, **kwargs):
        return self.read_raw()[:count]

    def write_raw(self, message):
        return self.write(message.decode("ascii", errors="ignore"))

    def _measured_voltage(self):
        return self.state.voltage if self.state.output_enabled else 0.0

    def _measured_current(self):
        if not self.state.output_enabled:
            return 0.0
        return self.state.load_current or self.state.current

    def _measured_value(self):
        if "DMM2" in self.resource_name:
            return self._measured_current()
        if "DMM" in self.resource_name:
            return self._measured_voltage()
        return self._measured_current()

    @staticmethod
    def _programming_value(command):
        value_text = re.sub(r"\(@[^)]*\)", "", command)
        if re.search(r"\b(?:MAXIMUM|MINIMUM|MAX|MIN)\b", value_text, re.IGNORECASE):
            return None
        matches = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?", value_text)
        return float(matches[0]) if matches else None

    @staticmethod
    def _diagnostic_selector(command):
        match = re.search(r"DIAG:PEEK\?\s*\d+\s*,\s*(\d+)", command, re.IGNORECASE)
        return int(match.group(1)) if match else None


class SimulatedVisaResourceManager:
    def __init__(self, state=None):
        self.state = state or get_simulation_state()
        self.closed = False

    def list_resources(self, query="?*::INSTR"):
        return tuple(SIMULATED_INSTRUMENTS)

    def open_resource(self, address, *args, **kwargs):
        key = str(address)
        raise_for_simulation_fault("connect", key)
        if key not in SIMULATED_INSTRUMENTS:
            raise ValueError(f"Unknown simulated VISA resource: {key}")
        resource = SimulatedVisaResource(
            key,
            SIMULATED_INSTRUMENTS[key],
            self.state,
        )
        if "timeout" in kwargs:
            resource.timeout = kwargs["timeout"]
        return resource

    def close(self):
        raise_for_simulation_fault("close_manager", "VISA ResourceManager")
        self.closed = True


def create_resource_manager():
    if is_simulation_mode():
        return SimulatedVisaResourceManager()

    import pyvisa

    return pyvisa.ResourceManager()


def initialize_main_thread_visa():
    global _main_thread_resource_manager
    if is_simulation_mode():
        return None
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("VISA must be initialized from the main thread")
    if _main_thread_resource_manager is None:
        _main_thread_resource_manager = pyvisa.ResourceManager()
        _main_thread_resource_manager.list_resources()
    return _main_thread_resource_manager
