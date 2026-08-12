"""Non-blocking Blynk Cloud publisher for live test monitoring."""

import math
import os
import threading
from time import monotonic
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from PyQt5.QtCore import QObject, pyqtSignal


DEFAULT_SERVER = "blynk.cloud"
DEFAULT_UPDATE_INTERVAL = 5.0
DEFAULT_ERROR_EVENT_CODE = "test_error"
DEFAULT_START_EVENT_CODE = "test_start"
DEFAULT_COMPLETION_EVENT_CODE = "test_complete"
DEFAULT_EVENT_COOLDOWN = 60.0


def _windows_user_environment(name):
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _value_type = winreg.QueryValueEx(key, name)
            return value
    except (FileNotFoundError, OSError):
        return None


def environment_setting(name, default=None):
    value = os.getenv(name)
    if value is None or not str(value).strip():
        value = _windows_user_environment(name)
    if value is None or not str(value).strip():
        return default
    return value


def normalize_server(server):
    value = str(server or DEFAULT_SERVER).strip()
    for prefix in ("https://", "http://"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):]
            break
    return value.rstrip("/")


def build_batch_update_url(token, values, server=DEFAULT_SERVER):
    parameters = {"token": token}
    parameters.update(values)
    return (
        f"https://{normalize_server(server)}/external/api/batch/update?"
        f"{urlencode(parameters)}"
    )


def build_event_url(token, event_code, description, server=DEFAULT_SERVER):
    parameters = {
        "token": token,
        "code": event_code,
        "description": str(description)[:300],
    }
    return (
        f"https://{normalize_server(server)}/external/api/logEvent?"
        f"{urlencode(parameters)}"
    )


def _valid_value(value):
    if value is None:
        return False
    if isinstance(value, float):
        return math.isfinite(value)
    return isinstance(value, (str, int, bool))


class BlynkPublisher(QObject):
    """Coalesce live values and publish them outside the GUI/test threads."""

    status_changed = pyqtSignal(str)
    notification_status_changed = pyqtSignal(str)

    def __init__(
        self,
        token=None,
        server=DEFAULT_SERVER,
        update_interval=DEFAULT_UPDATE_INTERVAL,
        request_timeout=3.0,
        error_event_code=DEFAULT_ERROR_EVENT_CODE,
        start_event_code=DEFAULT_START_EVENT_CODE,
        completion_event_code=DEFAULT_COMPLETION_EVENT_CODE,
        opener=urlopen,
        parent=None,
    ):
        super().__init__(parent)
        self.token = str(token or "").strip()
        self.server = normalize_server(server)
        self.update_interval = max(1.0, float(update_interval))
        self.request_timeout = max(0.1, float(request_timeout))
        self.error_event_code = str(
            error_event_code or DEFAULT_ERROR_EVENT_CODE
        ).strip()
        self.start_event_code = str(
            start_event_code or DEFAULT_START_EVENT_CODE
        ).strip()
        self.completion_event_code = str(
            completion_event_code or DEFAULT_COMPLETION_EVENT_CODE
        ).strip()
        self._opener = opener
        self._condition = threading.Condition()
        self._pending = {}
        self._events = []
        self._last_event_times = {}
        self._force_send = False
        self._stop_requested = False
        self._thread = None
        self._last_status = None
        self._signals_enabled = True
        self._unsupported_pins = set()

    @classmethod
    def from_environment(cls, parent=None):
        interval_text = environment_setting(
            "BLYNK_UPDATE_INTERVAL",
            str(DEFAULT_UPDATE_INTERVAL),
        )
        try:
            interval = float(interval_text)
        except ValueError:
            interval = DEFAULT_UPDATE_INTERVAL
        return cls(
            token=environment_setting("BLYNK_AUTH_TOKEN"),
            server=environment_setting("BLYNK_SERVER", DEFAULT_SERVER),
            update_interval=interval,
            error_event_code=environment_setting(
                "BLYNK_ERROR_EVENT_CODE",
                DEFAULT_ERROR_EVENT_CODE,
            ),
            start_event_code=environment_setting(
                "BLYNK_START_EVENT_CODE",
                DEFAULT_START_EVENT_CODE,
            ),
            completion_event_code=environment_setting(
                "BLYNK_COMPLETION_EVENT_CODE",
                DEFAULT_COMPLETION_EVENT_CODE,
            ),
            parent=parent,
        )

    @property
    def configured(self):
        return bool(self.token and self.server)

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())

    @property
    def unsupported_pins(self):
        with self._condition:
            return tuple(sorted(self._unsupported_pins))

    def start(self):
        if not self.configured:
            self._emit_status("Not configured: set BLYNK_AUTH_TOKEN")
            return False
        if self.running:
            return True
        with self._condition:
            self._stop_requested = False
            self._signals_enabled = True
        self._thread = threading.Thread(
            target=self._run,
            name="Blynk-Live-Publisher",
            daemon=True,
        )
        self._thread.start()
        self._emit_status("Ready")
        return True

    def publish(self, values, force=False):
        if not self.running and not self.start():
            return False
        with self._condition:
            clean_values = {
                str(pin).lower(): value
                for pin, value in values.items()
                if (
                    str(pin).lower().startswith("v")
                    and _valid_value(value)
                    and str(pin).lower() not in self._unsupported_pins
                )
            }
            if not clean_values:
                return False
            self._pending.update(clean_values)
            self._force_send = self._force_send or bool(force)
            self._condition.notify()
        return True

    def notify_error(self, description, cooldown=DEFAULT_EVENT_COOLDOWN):
        return self.notify(
            self.error_event_code,
            description,
            cooldown=cooldown,
        )

    def notify_start(self, description):
        return self.notify(
            self.start_event_code,
            description,
            cooldown=0,
        )

    def notify_completion(self, description):
        return self.notify(
            self.completion_event_code,
            description,
            cooldown=0,
        )

    def notify(self, event_code, description, cooldown=DEFAULT_EVENT_COOLDOWN):
        if not self.running and not self.start():
            return False
        code = str(event_code or "").strip()
        if not code:
            return False
        now = monotonic()
        with self._condition:
            last_sent = self._last_event_times.get(code)
            if last_sent is not None and now - last_sent < max(
                0.0, float(cooldown)
            ):
                return False
            self._last_event_times[code] = now
            self._events.append((code, str(description)[:300]))
            self._condition.notify()
        return True

    def stop(self, flush=False, timeout=None):
        thread = self._thread
        if not thread:
            return
        with self._condition:
            self._stop_requested = True
            self._signals_enabled = False
            self._force_send = self._force_send or bool(flush)
            if not flush:
                self._pending.clear()
                self._events.clear()
            self._condition.notify()
        if timeout is None:
            timeout = self.request_timeout + 0.5
        thread.join(timeout=max(0.0, float(timeout)))
        if not thread.is_alive():
            self._thread = None

    def _run(self):
        next_send_time = 0.0
        while True:
            with self._condition:
                while (
                    not self._pending
                    and not self._events
                    and not self._stop_requested
                ):
                    self._condition.wait()
                if (
                    self._stop_requested
                    and not self._pending
                    and not self._events
                ):
                    return

                if self._events:
                    event = self._events.pop(0)
                    values = None
                else:
                    event = None

                if event is not None:
                    pass
                else:
                    now = monotonic()
                    delay = next_send_time - now
                    if delay > 0 and not self._force_send:
                        self._condition.wait(timeout=delay)
                        continue

                    values = dict(self._pending)
                    self._pending.clear()
                    self._force_send = False

            if event is not None:
                try:
                    self._send_event(*event)
                    self._emit_notification_status(
                        f"Notification sent: {event[0]}"
                    )
                except Exception as exception:
                    self._emit_notification_status(
                        "Notification failed: "
                        f"{self._safe_error_text(exception)}"
                    )
                continue

            try:
                rejected_pins = self._send(values)
                if rejected_pins:
                    with self._condition:
                        self._unsupported_pins.update(rejected_pins)
                    names = ", ".join(
                        pin.upper() for pin in rejected_pins
                    )
                    self._emit_status(
                        "Connected; skipped unavailable pins: " + names
                    )
                else:
                    self._emit_status("Connected")
            except Exception as exception:
                with self._condition:
                    if self._stop_requested:
                        return
                    values.update(self._pending)
                    self._pending = values
                self._emit_status(
                    f"Offline: {self._safe_error_text(exception)}"
                )
            next_send_time = monotonic() + self.update_interval

    def _send(self, values):
        try:
            self._send_update_request(values)
            return ()
        except HTTPError as exception:
            if exception.code != 400 or len(values) <= 1:
                raise

        accepted = []
        rejected = []
        for pin, value in values.items():
            try:
                self._send_update_request({pin: value})
                accepted.append(pin)
            except HTTPError as exception:
                if exception.code != 400:
                    raise
                rejected.append(pin)
        if not accepted:
            raise RuntimeError(
                "Blynk rejected every virtual pin in the update batch"
            )
        return tuple(rejected)

    def _send_update_request(self, values):
        url = build_batch_update_url(self.token, values, self.server)
        with self._opener(url, timeout=self.request_timeout) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise RuntimeError(f"HTTP {status}")

    def _send_event(self, event_code, description):
        url = build_event_url(
            self.token,
            event_code,
            description,
            self.server,
        )
        with self._opener(url, timeout=self.request_timeout) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise RuntimeError(f"HTTP {status}")

    def _emit_status(self, status):
        if not self._signals_enabled:
            return
        if status == self._last_status:
            return
        self._last_status = status
        self.status_changed.emit(status)

    def _emit_notification_status(self, status):
        if self._signals_enabled:
            self.notification_status_changed.emit(status)

    def _safe_error_text(self, exception):
        reason = getattr(exception, "reason", None)
        text = str(reason if reason is not None else exception)
        if self.token:
            text = text.replace(self.token, "***")
        return text[:160]
