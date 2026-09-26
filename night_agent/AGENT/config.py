"""Run configuration and seat specifications for the SDK runtime."""
import json
import os
from dataclasses import dataclass, field

from . import PKG

DEFAULT_MODEL = "claude-opus-5"
GENERATORS = ["G1", "G2", "G3", "G4"]
ROLE_OF = {"CLOSER": "closer", "REVIEWER": "reviewer", "VERIFIER": "verifier", "EXECUTOR": "executor"}


@dataclass
class SeatSpec:
    id: str
    role: str
    model: str = DEFAULT_MODEL
    effort: str = "high"
    provider: str = "anthropic"
    runtime: str = "sdk"          # browser|sdk|fake (SCHEMA seat_record.runtime)
    url: str = ""

    def __post_init__(self):
        if not self.url:
            if self.runtime == "fake":
                self.url = f"fake://fake/{self.id}"
            else:
                self.url = f"sdk://{self.provider}/{self.model}/{self.id}"


@dataclass
class RunConfig:
    root: str
    ask_path: str = ""
    seats_mode: str = "live"          # live|fake
    model: str = DEFAULT_MODEL
    model_overrides: dict = field(default_factory=dict)
    effort: str = "high"
    documents_dir: str | None = None
    sandbox_dir: str | None = None
    hard_stop: str | None = None      # HH:MM local clock
    max_wait_s: float = 600.0
    net: bool = True
    faults: dict = field(default_factory=dict)   # Layer B knobs for fake seats: {"B1": {"seat": "G2", "stage": "GENERATE"}}
    profile: str | None = None
    resume: str | None = None         # runs/na-NNN
    stop_after: str | None = None     # test hook: stop once this run-relative file exists
    per_send_budget_usd: float = 2.0
    per_experiment_budget_usd: float = 5.0
    executor_turns: int = 40
    cli_path: str | None = None
    generators: int = 4
    fixed_clock: str | None = None    # test hook: ISO timestamp used for every record


def load_schema():
    with open(os.path.join(PKG, "SCHEMA.json"), encoding="utf-8") as f:
        return json.load(f)


def default_seats(cfg: RunConfig) -> list[SeatSpec]:
    runtime = "fake" if cfg.seats_mode == "fake" else "sdk"
    provider = "fake" if runtime == "fake" else "anthropic"

    def spec(sid, role):
        return SeatSpec(id=sid, role=role, model=cfg.model_overrides.get(sid, cfg.model), effort=cfg.effort,
                        provider=provider, runtime=runtime)

    seats = [spec(g, "generator") for g in GENERATORS[: cfg.generators]]
    seats += [spec("CLOSER", "closer"), spec("REVIEWER", "reviewer"), spec("VERIFIER", "verifier")]
    if cfg.sandbox_dir:
        seats.append(spec("EXECUTOR", "executor"))
    return seats
