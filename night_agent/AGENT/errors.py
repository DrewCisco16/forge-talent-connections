"""Exceptions shared by the state machine and the seat layer."""


class NightStop(Exception):
    """The run stops here with a labelled reason (spec 6, 7); never for subject matter."""

    def __init__(self, reason, note):
        super().__init__(f"{reason}: {note}")
        self.reason = reason
        self.note = note
