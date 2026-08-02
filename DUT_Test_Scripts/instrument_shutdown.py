import traceback
from dataclasses import dataclass

from SCPI_Library.simulation import create_resource_manager
from SCPI_Library.visa_config import open_visa_resource


@dataclass(frozen=True)
class ShutdownFailure:
    role: str
    address: str
    action: str
    exception: Exception
    traceback_text: str

    def to_dict(self):
        details = {
            "role": self.role,
            "address": self.address,
            "action": self.action,
            "type": type(self.exception).__name__,
            "message": str(self.exception),
        }
        if hasattr(self.exception, "to_dict"):
            details["exception"] = self.exception.to_dict()
        return details


@dataclass(frozen=True)
class ShutdownResult:
    attempted_roles: tuple
    failures: tuple

    @property
    def succeeded(self):
        return not self.failures


def _commands_for_role(role, configuration):
    if role == "ELoad":
        if configuration.get("ELoad_Model") == "Chroma":
            return (("disable_load", "LOAD OFF"),)
        return (
            ("disable_output", "OUTP OFF"),
            ("set_current_zero", "CURR 0"),
        )
    if role == "PSU":
        return (
            ("disable_output", "OUTP OFF"),
            ("set_voltage_zero", "VOLT 0"),
            ("set_current_zero", "CURR 0"),
            ("disable_series_parallel", "OUTP:PAIR OFF"),
        )
    if role in {"ACSource", "ExternalSource"}:
        return (("disable_output", "OUTP OFF"),)
    if role == "OSC":
        return (("stop_acquisition", "STOP"),)
    return ()


def shutdown_instruments(configuration, resource_manager_factory=None):
    resource_manager_factory = resource_manager_factory or create_resource_manager
    failures = []
    attempted_roles = []
    resource_manager = None

    try:
        resource_manager = resource_manager_factory()
    except Exception as exception:
        failures.append(
            ShutdownFailure(
                "VISA",
                "",
                "create_resource_manager",
                exception,
                traceback.format_exc(),
            )
        )
        return ShutdownResult(tuple(attempted_roles), tuple(failures))

    try:
        for role in ("ELoad", "PSU", "ExternalSource", "ACSource", "OSC"):
            address = configuration.get(role)
            commands = _commands_for_role(role, configuration)
            if (
                not address
                or str(address).strip().lower() == "none"
                or not commands
            ):
                continue

            attempted_roles.append(role)
            try:
                resource = open_visa_resource(resource_manager, address)
            except Exception as exception:
                failures.append(
                    ShutdownFailure(
                        role,
                        str(address),
                        "connect",
                        exception,
                        traceback.format_exc(),
                    )
                )
                continue

            try:
                for action, command in commands:
                    try:
                        resource.write(command)
                    except Exception as exception:
                        failures.append(
                            ShutdownFailure(
                                role,
                                str(address),
                                action,
                                exception,
                                traceback.format_exc(),
                            )
                        )
            finally:
                try:
                    resource.close()
                except Exception as exception:
                    failures.append(
                        ShutdownFailure(
                            role,
                            str(address),
                            "close_session",
                            exception,
                            traceback.format_exc(),
                        )
                    )
    finally:
        try:
            resource_manager.close()
        except Exception as exception:
            failures.append(
                ShutdownFailure(
                    "VISA",
                    "",
                    "close_resource_manager",
                    exception,
                    traceback.format_exc(),
                )
            )

    return ShutdownResult(tuple(attempted_roles), tuple(failures))
