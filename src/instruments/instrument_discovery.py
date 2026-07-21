"""VISA instrument discovery and model-to-role assignment."""

import ipaddress
import time
from dataclasses import dataclass, field
from pathlib import Path

import pyvisa

from configuration.configuration_service import load_configuration
from common.output_logging import print_console_safe
from common.path import config_folder
from SCPI_Library.instrument_errors import InstrumentTimeoutError
from SCPI_Library.simulation import create_resource_manager
from SCPI_Library.visa_config import configure_visa_resource


IGNORED_VISA_ERROR_CODES = {-1073807343, -1073807339, -1073807298}
DEFAULT_ROLE_MAP = config_folder / "instrument_role.txt"
CONFIGURED_INSTRUMENT_ROLES = {
    "PSU": "PSU",
    "DMM": "DMM",
    "DMM2": "DMM2",
    "ELoad": "ELOAD",
    "OSC": "SCOPE",
    "ACSource": "ACSOURCE",
    "DAQ": "DAQ",
}


@dataclass
class DiscoveryResult:
    addresses: list[str] = field(default_factory=list)
    identities: list[str] = field(default_factory=list)
    roles: dict[str, str] = field(default_factory=dict)

    def extend(self, other: "DiscoveryResult") -> None:
        self.addresses.extend(other.addresses)
        self.identities.extend(other.identities)
        self.roles.update(other.roles)


def load_model_role_map(path=None):
    role_map_path = Path(path) if path else DEFAULT_ROLE_MAP
    model_roles = {}
    try:
        for line in role_map_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            model, role = (value.strip() for value in line.split(":", 1))
            model_roles[model.upper()] = role
    except OSError as exception:
        print_console_safe(f"Error reading {role_map_path}: {exception}")
    return model_roles


def get_visa_scpi_resources(resource_manager_factory=None, role_map_path=None):
    return _discover_resources(
        resource_manager_factory,
        role_map_path,
        prefixes=("USB", "GPIB"),
        timeout_ms=5000,
        gpib_fallback=True,
    )


def get_visa_usb_resources(resource_manager_factory=None, role_map_path=None):
    return _discover_resources(
        resource_manager_factory,
        role_map_path,
        prefixes=("USB",),
        timeout_ms=5000,
    )


def get_visa_gpib_resources(resource_manager_factory=None, role_map_path=None):
    return _discover_resources(
        resource_manager_factory,
        role_map_path,
        prefixes=("GPIB",),
        timeout_ms=5000,
        gpib_fallback=True,
    )


def get_all_visa_resources(resource_manager_factory=None, role_map_path=None):
    return _discover_resources(
        resource_manager_factory,
        role_map_path,
        timeout_ms=2000,
        gpib_fallback=True,
        serial_access=True,
    )


def get_visa_tcpip_resources(resource_manager_factory=None, role_map_path=None):
    return _discover_resources(
        resource_manager_factory,
        role_map_path,
        prefixes=("TCPIP",),
        timeout_ms=10000,
        address_kind="ip",
        require_comma=True,
    )


def get_visa_hostname_resources(resource_manager_factory=None, role_map_path=None):
    return _discover_resources(
        resource_manager_factory,
        role_map_path,
        prefixes=("TCPIP",),
        timeout_ms=10000,
        address_kind="hostname",
    )


def get_configured_visa_resources(
    configuration_file,
    resource_manager_factory=None,
    enabled_transports=None,
    timeout_ms=2000,
):
    """Probe only instrument addresses declared by a DUT configuration file."""
    configured_values = load_configuration(configuration_file)
    allowed_transports = (
        set(enabled_transports) if enabled_transports is not None else None
    )
    configured_instruments = []
    for config_key, role in CONFIGURED_INSTRUMENT_ROLES.items():
        address = configured_values.get(config_key, "").strip()
        if not address:
            continue
        transport = _address_transport(address)
        if allowed_transports is not None and transport not in allowed_transports:
            continue
        configured_instruments.append((role, address))

    result = DiscoveryResult()
    if not configured_instruments:
        return result

    factory = resource_manager_factory or create_resource_manager
    manager = factory()
    identities_by_address = {}
    try:
        for role, address in configured_instruments:
            if address in identities_by_address:
                result.roles[role] = address
                continue
            instrument = None
            try:
                instrument_timeout = (
                    max(timeout_ms, 10000)
                    if str(address).upper().startswith("GPIB")
                    else timeout_ms
                )
                instrument = configure_visa_resource(
                    manager.open_resource(address),
                    instrument_timeout,
                )
                identity = _query_identity(
                    instrument,
                    address,
                    gpib_fallback=True,
                    prefer_legacy_gpib=True,
                )
                if not identity:
                    continue
                identities_by_address[address] = identity
                result.addresses.append(address)
                result.identities.append(identity)
                result.roles[role] = address
            except Exception as exception:
                print_console_safe(
                    f"Configured {role} unavailable at {address}: {exception}"
                )
            finally:
                if instrument is not None:
                    try:
                        instrument.close()
                    except Exception:
                        pass
    finally:
        try:
            manager.close()
        except Exception:
            pass
    return result


def _discover_resources(
    resource_manager_factory,
    role_map_path,
    *,
    prefixes=None,
    timeout_ms=15000,
    address_kind=None,
    gpib_fallback=False,
    serial_access=False,
    require_comma=False,
):
    factory = resource_manager_factory or create_resource_manager
    manager = factory()
    result = DiscoveryResult()
    model_roles = load_model_role_map(role_map_path)
    role_specificity = {}
    try:
        for address in manager.list_resources():
            if prefixes and not str(address).startswith(prefixes):
                continue
            if not _matches_address_kind(address, address_kind):
                continue
            instrument = None
            try:
                open_options = {}
                if serial_access and str(address).startswith("ASRL"):
                    open_options = {"timeout": timeout_ms, "access_mode": 1}
                instrument = configure_visa_resource(
                    manager.open_resource(address, **open_options),
                    timeout_ms,
                )
                identity = _query_identity(
                    instrument,
                    address,
                    gpib_fallback=gpib_fallback,
                )
                if not identity or (require_comma and "," not in identity):
                    continue
                result.addresses.append(address)
                result.identities.append(identity)
                _assign_role(
                    result.roles,
                    model_roles,
                    identity,
                    address,
                    role_specificity,
                )
            except pyvisa.errors.VisaIOError as exception:
                if exception.error_code not in IGNORED_VISA_ERROR_CODES:
                    print_console_safe(f"VISA error on {address}: {exception}")
            except Exception as exception:
                print_console_safe(f"Unexpected error on {address}: {exception}")
            finally:
                if instrument is not None:
                    try:
                        instrument.close()
                    except Exception:
                        pass
    finally:
        try:
            manager.close()
        except Exception:
            pass
    return result


def _query_identity(
    instrument,
    address,
    *,
    gpib_fallback,
    prefer_legacy_gpib=False,
):
    is_gpib = str(address).upper().startswith("GPIB")
    if prefer_legacy_gpib and is_gpib:
        return _query_legacy_gpib_identity(instrument)
    try:
        return instrument.query("*IDN?").strip().upper()
    except (pyvisa.errors.VisaIOError, InstrumentTimeoutError):
        if not gpib_fallback or not is_gpib:
            raise
        return _query_legacy_gpib_identity(instrument)


def _query_legacy_gpib_identity(instrument):
    instrument.write_termination = "\n"
    instrument.read_termination = "\n"
    instrument.clear()
    time.sleep(0.5)
    instrument.write("ID?")
    time.sleep(0.5)
    return instrument.read().strip().upper()


def _matches_address_kind(address, address_kind):
    if address_kind is None:
        return True
    parts = str(address).split("::")
    if len(parts) < 2:
        return False
    try:
        ipaddress.ip_address(parts[1])
        actual_kind = "ip"
    except ValueError:
        actual_kind = "hostname"
    return actual_kind == address_kind


def _address_transport(address):
    normalized = str(address).upper()
    if normalized.startswith("USB"):
        return "usb"
    if normalized.startswith("GPIB"):
        return "gpib"
    if normalized.startswith("TCPIP"):
        return f"tcpip_{_tcpip_address_kind(address)}"
    if normalized.startswith("ASRL"):
        return "serial"
    return "other"


def _tcpip_address_kind(address):
    parts = str(address).split("::")
    if len(parts) < 2:
        return "hostname"
    try:
        ipaddress.ip_address(parts[1])
        return "ip"
    except ValueError:
        return "hostname"


def _assign_role(roles, model_roles, identity, address, role_specificity=None):
    matches = [
        (len(model), role)
        for model, role in model_roles.items()
        if model in identity
    ]
    if not matches:
        return
    specificity, role = max(matches)
    specificity_by_role = role_specificity if role_specificity is not None else {}
    if specificity > specificity_by_role.get(role, -1):
        roles[role] = address
        specificity_by_role[role] = specificity
