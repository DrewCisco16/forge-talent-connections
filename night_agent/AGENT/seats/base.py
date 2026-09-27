"""The seat contract every runtime implements."""
from dataclasses import dataclass, field
from typing import Protocol

from ..config import SeatSpec
from ..packets import Packet


@dataclass
class Reply:
    text: str = ""
    completed: bool = False          # a result arrived without error (completion_signal_observed)
    aborted: bool = False            # Dispatch terminated the slot (MAX_WAIT) or found it dead on resume
    error: str | None = None         # SDK, auth or model error text; a login page is text, not an error (FAILED)
    session_id: str = ""             # the pre-assigned slot id the runtime observed
    served_model: str = ""
    cost_usd: float | None = None
    usage: dict = field(default_factory=dict)
    started: str = ""
    ended: str = ""
    start_boundary: str = ""
    end_boundary: str = ""


class Seat(Protocol):
    spec: SeatSpec

    def send(self, packet: Packet, timeout_s: float, slot_id: str) -> Reply: ...


class Executor(Protocol):
    """The one tool-capable seat (spec 2). Everything it runs is confined to a working directory."""
    spec: SeatSpec

    def run_command(self, cmd: str, cwd: str | None = None, timeout_s: float | None = None) -> dict: ...

    def apply_mutation(self, change: str, workdir: str) -> dict: ...

    def measure(self, procedure: str, workdir: str, timeout_s: float) -> dict: ...
