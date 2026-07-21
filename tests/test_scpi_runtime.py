import unittest
from importlib import import_module

from DUT_Test_Scripts.scpi_runtime import (
    CHROMA_CLASSES,
    DOLPHIN_CLASSES,
    HORNBILL_KEYSIGHT_CLASSES,
    DictGenerator,
    DolphinDimport,
    HornbillDimport,
    VisaResourceManager,
)
from tests.fakes import FakeVisaManager


class ScpiRuntimeTests(unittest.TestCase):
    def test_dynamic_imports_preserve_expected_tuple_contracts(self):
        dolphin = DolphinDimport.getClasses("Keysight")
        hornbill = HornbillDimport.getClasses_Keysight("Keysight")
        chroma = HornbillDimport.getClasses_Chroma("Chroma")

        self.assertEqual(len(dolphin), len(DOLPHIN_CLASSES))
        self.assertEqual(len(hornbill), len(HORNBILL_KEYSIGHT_CLASSES))
        self.assertEqual(len(chroma), len(CHROMA_CLASSES))
        keysight_module = import_module("SCPI_Library.Keysight")
        chroma_module = import_module("SCPI_Library.Chroma")
        self.assertEqual(
            dolphin,
            tuple(getattr(keysight_module, name) for name in DOLPHIN_CLASSES),
        )
        self.assertEqual(
            hornbill,
            tuple(
                getattr(keysight_module, name)
                for name in HORNBILL_KEYSIGHT_CLASSES
            ),
        )
        self.assertEqual(
            chroma,
            tuple(getattr(chroma_module, name) for name in CHROMA_CLASSES),
        )

    def test_dictionary_generator_retains_legacy_contract(self):
        self.assertEqual(DictGenerator.input(voltage=5), {"voltage": 5})

    def test_resource_manager_configures_and_closes_resources(self):
        events = []
        manager = FakeVisaManager(events)
        runtime = VisaResourceManager(lambda: manager)

        connected, errors = runtime.openRM("PSU", "DMM")
        runtime.closeRM()

        self.assertEqual((connected, errors), (1, None))
        self.assertEqual(events[-1], ("manager_close",))


if __name__ == "__main__":
    unittest.main()
