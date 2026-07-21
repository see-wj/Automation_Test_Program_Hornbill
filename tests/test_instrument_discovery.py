import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from instruments.instrument_discovery import (
    DiscoveryResult,
    get_all_visa_resources,
    get_configured_visa_resources,
    get_visa_gpib_resources,
    get_visa_hostname_resources,
    get_visa_tcpip_resources,
    load_model_role_map,
    _query_identity,
)
from SCPI_Library.instrument_errors import InstrumentTimeoutError


class DiscoveryResource:
    def __init__(self, identity):
        self.identity = identity
        self.closed = False
        self.last_command = None

    def query(self, _command):
        return self.identity

    def clear(self):
        return None

    def write(self, command):
        self.last_command = command

    def read(self):
        return self.identity

    def close(self):
        self.closed = True


class DiscoveryManager:
    def __init__(self, identities):
        self.identities = identities
        self.resources = {}
        self.closed = False

    def list_resources(self):
        return tuple(self.identities)

    def open_resource(self, address, **_options):
        resource = DiscoveryResource(self.identities[address])
        self.resources[address] = resource
        return resource

    def close(self):
        self.closed = True


class LegacyGpibResource:
    def __init__(self):
        self.commands = []

    def query(self, command):
        self.commands.append(command)
        raise InstrumentTimeoutError()

    def clear(self):
        self.commands.append("clear")

    def write(self, command):
        self.commands.append(command)

    def read(self):
        self.commands.append("read")
        return "HP3458A\r\n"


class InstrumentDiscoveryTests(unittest.TestCase):
    def test_discovery_result_combines_scans(self):
        result = DiscoveryResult(
            addresses=["USB0::MODEL::INSTR"],
            identities=["VENDOR,MODEL-USB,SERIAL,1.0"],
            roles={"PSU": "USB0::MODEL::INSTR"},
        )

        result.extend(
            DiscoveryResult(
                addresses=["TCPIP0::scope-lab::inst0::INSTR"],
                identities=["VENDOR,MODEL-HOST,SERIAL,1.0"],
                roles={"SCOPE": "TCPIP0::scope-lab::inst0::INSTR"},
            )
        )

        self.assertEqual(len(result.addresses), 2)
        self.assertEqual(len(result.identities), 2)
        self.assertEqual(set(result.roles), {"PSU", "SCOPE"})

    def test_load_model_role_map_ignores_comments_and_normalizes_models(self):
        with tempfile.TemporaryDirectory() as directory:
            role_map = Path(directory) / "roles.txt"
            role_map.write_text(
                "# comment\n// comment\nmodel-a: PSU\ninvalid line\n",
                encoding="utf-8",
            )
            roles = load_model_role_map(role_map)

        self.assertEqual(roles, {"MODEL-A": "PSU"})

    def test_tcpip_scans_classify_addresses_and_close_resources(self):
        identities = {
            "TCPIP0::192.0.2.1::inst0::INSTR": "VENDOR,MODEL-IP,SERIAL,1.0",
            "TCPIP0::scope-lab::inst0::INSTR": "VENDOR,MODEL-HOST,SERIAL,1.0",
            "USB0::MODEL::INSTR": "VENDOR,MODEL-USB,SERIAL,1.0",
        }
        managers = []

        def factory():
            manager = DiscoveryManager(identities)
            managers.append(manager)
            return manager

        with tempfile.TemporaryDirectory() as directory:
            role_map = Path(directory) / "roles.txt"
            role_map.write_text(
                "MODEL-IP: PSU\nMODEL-HOST: SCOPE\n",
                encoding="utf-8",
            )
            ip_result = get_visa_tcpip_resources(factory, role_map)
            host_result = get_visa_hostname_resources(factory, role_map)

        self.assertEqual(
            ip_result.addresses, ["TCPIP0::192.0.2.1::inst0::INSTR"]
        )
        self.assertEqual(ip_result.roles, {"PSU": ip_result.addresses[0]})
        self.assertEqual(
            host_result.addresses, ["TCPIP0::scope-lab::inst0::INSTR"]
        )
        self.assertEqual(host_result.roles, {"SCOPE": host_result.addresses[0]})
        self.assertTrue(all(manager.closed for manager in managers))
        self.assertTrue(
            all(
                resource.closed
                for manager in managers
                for resource in manager.resources.values()
            )
        )

    def test_serial_specific_role_overrides_generic_duplicate_model(self):
        identities = {
            "USB0::OTHER::INSTR": "KEYSIGHT,E36731A,MY62100065,1.0",
            "USB0::ELOAD::INSTR": "KEYSIGHT,E36731A,MY62100043,1.0",
        }
        with tempfile.TemporaryDirectory() as directory:
            role_map = Path(directory) / "roles.txt"
            role_map.write_text(
                "E36731A: ELOAD\nMY62100043: ELOAD\n",
                encoding="utf-8",
            )
            result = get_all_visa_resources(
                lambda: DiscoveryManager(identities),
                role_map,
            )

        self.assertEqual(result.roles["ELOAD"], "USB0::ELOAD::INSTR")

    def test_gpib_identity_uses_legacy_fallback_after_guarded_timeout(self):
        resource = LegacyGpibResource()

        with patch("instruments.instrument_discovery.time.sleep") as sleep:
            identity = _query_identity(
                resource,
                "GPIB0::22::INSTR",
                gpib_fallback=True,
            )

        self.assertEqual(identity, "HP3458A")
        self.assertEqual(
            resource.commands,
            ["*IDN?", "clear", "ID?", "read"],
        )
        self.assertEqual(resource.write_termination, "\n")
        self.assertEqual(resource.read_termination, "\n")
        self.assertEqual(sleep.call_count, 2)

    def test_gpib_scan_discovers_legacy_3458a(self):
        class LegacyGpibManager:
            def __init__(self):
                self.resource = LegacyGpibResource()

            def list_resources(self):
                return ("GPIB0::22::INSTR",)

            def open_resource(self, _address, **_options):
                return self.resource

            def close(self):
                return None

        with tempfile.TemporaryDirectory() as directory:
            role_map = Path(directory) / "roles.txt"
            role_map.write_text("HP3458A: DMM\n", encoding="utf-8")
            result = get_visa_gpib_resources(LegacyGpibManager, role_map)

        self.assertEqual(result.addresses, ["GPIB0::22::INSTR"])
        self.assertEqual(result.identities, ["HP3458A"])
        self.assertEqual(result.roles, {"DMM": "GPIB0::22::INSTR"})

    def test_configured_gpib_uses_3458a_id_query_handshake(self):
        class ConfiguredGpibManager:
            def __init__(self):
                self.resource = LegacyGpibResource()

            def open_resource(self, _address, **_options):
                return self.resource

            def close(self):
                return None

        manager = ConfiguredGpibManager()
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.txt"
            config.write_text("DMM = GPIB0::22::INSTR\n", encoding="utf-8")
            with patch("instruments.instrument_discovery.time.sleep") as sleep:
                result = get_configured_visa_resources(
                    config,
                    lambda: manager,
                    enabled_transports={"gpib"},
                )

        self.assertEqual(result.identities, ["HP3458A"])
        self.assertEqual(manager.resource.commands, ["clear", "ID?", "read"])
        self.assertEqual(manager.resource.timeout, 10000)
        self.assertEqual(manager.resource.write_termination, "\n")
        self.assertEqual(manager.resource.read_termination, "\n")
        self.assertEqual(sleep.call_count, 2)

    def test_configured_gpib_never_sends_modern_idn_query(self):
        class FailingLegacyResource(LegacyGpibResource):
            def read(self):
                self.commands.append("read")
                raise InstrumentTimeoutError()

        class ConfiguredGpibManager:
            def __init__(self):
                self.resource = FailingLegacyResource()

            def open_resource(self, _address, **_options):
                return self.resource

            def close(self):
                return None

        manager = ConfiguredGpibManager()
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.txt"
            config.write_text("DMM = GPIB0::22::INSTR\n", encoding="utf-8")
            with patch("instruments.instrument_discovery.time.sleep"):
                result = get_configured_visa_resources(
                    config,
                    lambda: manager,
                    enabled_transports={"gpib"},
                )

        self.assertEqual(result.addresses, [])
        self.assertEqual(manager.resource.commands, ["clear", "ID?", "read"])
        self.assertNotIn("*IDN?", manager.resource.commands)

    def test_configured_discovery_probes_available_addresses_and_assigns_roles(self):
        identities = {
            "TCPIP0::hornbill::inst0::INSTR": "KEYSIGHT,LINUXGEN,SERIAL,1.0",
            "GPIB0::22::INSTR": "HP3458A",
        }

        class ConfiguredManager(DiscoveryManager):
            def open_resource(self, address, **options):
                if address not in self.identities:
                    raise RuntimeError("not connected")
                return super().open_resource(address, **options)

        manager = ConfiguredManager(identities)
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.txt"
            config.write_text(
                "PSU = TCPIP0::hornbill::inst0::INSTR\n"
                "DMM = GPIB0::22::INSTR\n"
                "ELoad = USB0::missing::INSTR\n",
                encoding="utf-8",
            )
            result = get_configured_visa_resources(
                config,
                lambda: manager,
                enabled_transports={"tcpip_hostname", "gpib", "usb"},
            )

        self.assertEqual(
            result.addresses,
            ["TCPIP0::hornbill::inst0::INSTR", "GPIB0::22::INSTR"],
        )
        self.assertEqual(
            result.roles,
            {
                "PSU": "TCPIP0::hornbill::inst0::INSTR",
                "DMM": "GPIB0::22::INSTR",
            },
        )
        self.assertTrue(manager.closed)
        self.assertTrue(all(resource.closed for resource in manager.resources.values()))

    def test_configured_discovery_respects_transport_filters(self):
        manager = DiscoveryManager(
            {"USB0::DMM::INSTR": "KEYSIGHT,34470A,SERIAL,1.0"}
        )
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.txt"
            config.write_text(
                "PSU = TCPIP0::hornbill::inst0::INSTR\n"
                "DMM = USB0::DMM::INSTR\n",
                encoding="utf-8",
            )
            result = get_configured_visa_resources(
                config,
                lambda: manager,
                enabled_transports={"usb"},
            )

        self.assertEqual(result.addresses, ["USB0::DMM::INSTR"])
        self.assertEqual(result.roles, {"DMM": "USB0::DMM::INSTR"})


if __name__ == "__main__":
    unittest.main()
