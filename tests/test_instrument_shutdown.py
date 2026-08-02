import unittest

from DUT_Test_Scripts.instrument_shutdown import shutdown_instruments
from tests.fakes import FakeVisaManager


class InstrumentShutdownTests(unittest.TestCase):
    def test_continues_after_command_and_connection_failures(self):
        events = []
        manager = FakeVisaManager(
            events,
            connect_fails={"AC"},
            command_failures={
                "LOAD": {"CURR 0"},
                "PSU": {"VOLT 0"},
            },
        )
        configuration = {
            "ELoad": "LOAD",
            "ELoad_Model": "E367XXA",
            "PSU": "PSU",
            "ACSource": "AC",
            "OSC": "SCOPE",
        }

        result = shutdown_instruments(configuration, lambda: manager)

        self.assertEqual(
            result.attempted_roles,
            ("ELoad", "PSU", "ACSource", "OSC"),
        )
        self.assertEqual(
            [failure.action for failure in result.failures],
            ["set_current_zero", "set_voltage_zero", "connect"],
        )
        self.assertIn(("write", "PSU", "OUTP OFF"), events)
        self.assertIn(("write", "PSU", "CURR 0"), events)
        self.assertIn(("write", "SCOPE", "STOP"), events)
        self.assertEqual(events[-1], ("manager_close",))

    def test_chroma_load_uses_load_off_only(self):
        events = []
        result = shutdown_instruments(
            {"ELoad": "CHROMA", "ELoad_Model": "Chroma"},
            lambda: FakeVisaManager(events),
        )

        self.assertTrue(result.succeeded)
        self.assertIn(("write", "CHROMA", "LOAD OFF"), events)
        self.assertNotIn(("write", "CHROMA", "CURR 0"), events)

    def test_external_source_output_is_disabled(self):
        events = []
        result = shutdown_instruments(
            {"ExternalSource": "SOURCE"},
            lambda: FakeVisaManager(events),
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(result.attempted_roles, ("ExternalSource",))
        self.assertIn(("write", "SOURCE", "OUTP OFF"), events)

    def test_resource_manager_failure_is_reported(self):
        def fail_manager_creation():
            raise RuntimeError("VISA unavailable")

        result = shutdown_instruments(
            {"PSU": "PSU"},
            fail_manager_creation,
        )

        self.assertFalse(result.succeeded)
        self.assertEqual(result.failures[0].action, "create_resource_manager")

    def test_none_eload_is_not_opened_during_shutdown(self):
        events = []
        result = shutdown_instruments(
            {"ELoad": "None", "PSU": "PSU"},
            lambda: FakeVisaManager(events),
        )

        self.assertTrue(result.succeeded)
        self.assertEqual(result.attempted_roles, ("PSU",))
        self.assertFalse(any(event[1:2] == ("None",) for event in events))


if __name__ == "__main__":
    unittest.main()
