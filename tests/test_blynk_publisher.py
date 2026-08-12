import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from integrations.blynk_publisher import (
    BlynkPublisher,
    build_batch_update_url,
    build_event_url,
    environment_setting,
    normalize_server,
)


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class BlynkPublisherTests(unittest.TestCase):
    def test_normalizes_server_address(self):
        self.assertEqual(
            normalize_server("https://sgp1.blynk.cloud/"),
            "sgp1.blynk.cloud",
        )

    def test_builds_batched_virtual_pin_request(self):
        url = build_batch_update_url(
            "secret",
            {"v0": 5.0, "v7": "Running"},
            "sgp1.blynk.cloud",
        )

        self.assertEqual(
            url,
            "https://sgp1.blynk.cloud/external/api/batch/update?"
            "token=secret&v0=5.0&v7=Running",
        )

    def test_builds_encoded_event_request(self):
        url = build_event_url(
            "secret",
            "test_error",
            "Voltage error: 0.25 V",
            "sgp1.blynk.cloud",
        )

        self.assertEqual(
            url,
            "https://sgp1.blynk.cloud/external/api/logEvent?"
            "token=secret&code=test_error&"
            "description=Voltage+error%3A+0.25+V",
        )

    def test_publisher_requires_authentication_token(self):
        publisher = BlynkPublisher(token="")

        self.assertFalse(publisher.start())
        self.assertFalse(publisher.publish({"v0": 5.0}))

    def test_environment_setting_falls_back_to_windows_user_value(self):
        with (
            patch("integrations.blynk_publisher.os.getenv", return_value=None),
            patch(
                "integrations.blynk_publisher._windows_user_environment",
                return_value="persisted-value",
            ),
        ):
            self.assertEqual(
                environment_setting("BLYNK_AUTH_TOKEN"),
                "persisted-value",
            )

    def test_send_uses_configured_timeout(self):
        requests = []

        def opener(url, timeout):
            requests.append((url, timeout))
            return FakeResponse()

        publisher = BlynkPublisher(
            token="secret",
            server="blynk.cloud",
            request_timeout=1.5,
            opener=opener,
        )

        publisher._send({"v0": 5.0})

        self.assertEqual(requests[0][1], 1.5)
        self.assertIn("token=secret", requests[0][0])
        self.assertIn("v0=5.0", requests[0][0])

    def test_bad_optional_pin_does_not_block_valid_updates(self):
        requests = []

        def opener(url, timeout):
            requests.append((url, timeout))
            if "v16=" in url:
                raise HTTPError(url, 400, "Bad Request", {}, None)
            return FakeResponse()

        publisher = BlynkPublisher(
            token="secret",
            server="blynk.cloud",
            opener=opener,
        )

        rejected = publisher._send({"v0": 5.0, "v16": 25.0})

        self.assertEqual(rejected, ("v16",))
        self.assertTrue(any("v0=5.0" in url for url, _timeout in requests))

    def test_discovered_unsupported_pin_is_skipped_on_future_publish(self):
        publisher = BlynkPublisher(token="secret")
        publisher._thread = type(
            "RunningThread",
            (),
            {"is_alive": lambda self: True},
        )()
        publisher._unsupported_pins.add("v16")

        self.assertTrue(publisher.publish({"v0": 5.0, "v16": 25.0}))

        self.assertEqual(publisher._pending, {"v0": 5.0})

    def test_event_send_uses_configured_code_and_description(self):
        requests = []

        def opener(url, timeout):
            requests.append((url, timeout))
            return FakeResponse()

        publisher = BlynkPublisher(
            token="secret",
            server="blynk.cloud",
            request_timeout=1.5,
            opener=opener,
        )

        publisher._send_event("test_error", "Boundary failure")

        self.assertEqual(requests[0][1], 1.5)
        self.assertIn("code=test_error", requests[0][0])
        self.assertIn("description=Boundary+failure", requests[0][0])

    def test_completion_notification_uses_separate_event_code(self):
        publisher = BlynkPublisher(
            token="secret",
            completion_event_code="test_complete",
        )
        calls = []
        publisher.notify = lambda code, description, cooldown: calls.append(
            (code, description, cooldown)
        )

        publisher.notify_completion("Test completed")

        self.assertEqual(
            calls,
            [("test_complete", "Test completed", 0)],
        )

    def test_start_notification_uses_separate_event_code(self):
        publisher = BlynkPublisher(
            token="secret",
            start_event_code="test_start",
        )
        calls = []
        publisher.notify = lambda code, description, cooldown: calls.append(
            (code, description, cooldown)
        )

        publisher.notify_start("Test started")

        self.assertEqual(
            calls,
            [("test_start", "Test started", 0)],
        )


if __name__ == "__main__":
    unittest.main()
