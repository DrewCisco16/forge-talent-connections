"""Night Agent v11.4 SDK runtime: a deterministic Dispatch that executes DISPATCH.md.

The runtime is not a thinker. The only model calls it makes are the sends DISPATCH.md
names; CHECK is its own code. Seats are driven through the Claude Agent SDK, one fresh
session per send (seats/sdk_seat.py), or by deterministic fake seats for rehearsal and
CI (seats/fake_seat.py). Every stage and every send is guarded by TESTS/na_gate.py.
"""
import json
import os

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME_VERSION = "11.4.0"


def schema_version():
    with open(os.path.join(PKG, "SCHEMA.json"), encoding="utf-8") as f:
        return json.load(f)["schema_version"]
