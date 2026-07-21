import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for import_path in (SRC, ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from DUT_Test_Scripts.DUT_screenshot import (
    GetVisaSCPIResources,
    ScreenShotDialog,
    normalize_network_visa_address,
)
from PyQt5.QtWidgets import QApplication


class FakeResource:
    def __init__(self, identity):
        self.identity = identity
        self.closed = False
        self.timeout = None

    def query(self, command):
        if command != "*IDN?":
            raise AssertionError(command)
        return self.identity

    def close(self):
        self.closed = True


class FakeManager:
    def __init__(self, listed_addresses, identities):
        self.listed_addresses = listed_addresses
        self.identities = identities
        self.resources = {}
        self.closed = False

    def list_resources(self):
        return tuple(self.listed_addresses)

    def open_resource(self, address):
        resource = FakeResource(self.identities[address])
        self.resources[address] = resource
        return resource

    def close(self):
        self.closed = True


class ScreenshotDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_normalizes_hostname_ip_and_full_visa_addresses(self):
        self.assertEqual(
            normalize_network_visa_address("scope-lab"),
            "TCPIP0::scope-lab::inst0::INSTR",
        )
        self.assertEqual(
            normalize_network_visa_address("192.0.2.10"),
            "TCPIP0::192.0.2.10::inst0::INSTR",
        )
        self.assertEqual(
            normalize_network_visa_address("TCPIP0::scope-lab::inst0::INSTR"),
            "TCPIP0::scope-lab::inst0::INSTR",
        )

    def test_discovers_listed_usb_ip_and_hostname_resources(self):
        identities = {
            "USB0::MODEL::INSTR": "VENDOR,USBMODEL,SERIAL,1.0",
            "TCPIP0::192.0.2.1::inst0::INSTR": "VENDOR,IPMODEL,SERIAL,1.0",
            "TCPIP0::scope-lab::inst0::INSTR": "VENDOR,HOSTMODEL,SERIAL,1.0",
            "GPIB0::22::INSTR": "VENDOR,GPIBMODEL,SERIAL,1.0",
        }
        manager = FakeManager(tuple(identities), identities)

        addresses, names = GetVisaSCPIResources(
            resource_manager_factory=lambda: manager
        )

        self.assertEqual(addresses, list(identities)[:3])
        self.assertEqual(len(names), 3)
        self.assertTrue(manager.closed)
        self.assertTrue(all(resource.closed for resource in manager.resources.values()))

    def test_direct_hostname_is_probed_even_when_visa_does_not_list_it(self):
        address = "TCPIP0::new-scope::inst0::INSTR"
        manager = FakeManager(
            (),
            {address: "KEYSIGHT,DSOX1204G,SERIAL,1.0"},
        )

        addresses, names = GetVisaSCPIResources(
            "new-scope",
            resource_manager_factory=lambda: manager,
        )

        self.assertEqual(addresses, [address])
        self.assertEqual(names, ["KEYSIGHT,DSOX1204G,SERIAL,1.0"])

    def test_dialog_find_button_forwards_hostname_and_populates_table(self):
        dialog = ScreenShotDialog()
        self.addCleanup(dialog.deleteLater)
        dialog.networkAddressEntry.setText("scope-lab")

        with patch(
            "DUT_Test_Scripts.DUT_screenshot.GetVisaSCPIResources",
            return_value=(
                ["TCPIP0::scope-lab::inst0::INSTR"],
                ["KEYSIGHT,DSOX1204G,SERIAL,1.0"],
            ),
        ) as discovery:
            dialog.doFind()

        discovery.assert_called_once_with("scope-lab")
        self.assertEqual(dialog.instrTable.rowCount(), 1)
        self.assertEqual(dialog.instrTable.item(0, 0).text(), "DSOX1204G")
        self.assertEqual(
            dialog.instrTable.item(0, 3).text(),
            "TCPIP0::scope-lab::inst0::INSTR",
        )
        dialog.close()


if __name__ == "__main__":
    unittest.main()
