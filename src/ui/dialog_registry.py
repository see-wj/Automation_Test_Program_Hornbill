"""Named dialog registry used by the legacy application launcher."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DialogRegistration:
    title: str
    description: str
    owner_attribute: str
    factory: object


class DialogRegistry:
    def __init__(self, registrations, message_sink=None):
        self.registrations = tuple(registrations)
        self.message_sink = message_sink or (lambda _message: None)

    @property
    def selection_options(self):
        return tuple(
            (registration.title, registration.description)
            for registration in self.registrations[2:]
        )

    def open(self, owner, index):
        if index < 0 or index >= len(self.registrations):
            self.message_sink(f"Invalid dialog index: {index}")
            return None
        registration = self.registrations[index]
        dialog = registration.factory()
        setattr(owner, registration.owner_attribute, dialog)
        dialog.show()
        return dialog
