"""METHOD command: only the EXECUTOR seat runs anything (spec 2). The RETRIEVED value is the tool output the
runtime observed, never the seat's prose."""
import re

CMD_RE = re.compile(r"`([^`]+)`|\b((?:python3?|pytest|npm|make|go|cargo|bash|sh)\s[^\s].*?)(?:\)|$)")


def command_of(text: str) -> str:
    m = CMD_RE.search(text)
    if not m:
        return ""
    return (m.group(1) or m.group(2) or "").strip().rstrip(".")


def check_command(claim, executor, allowed_commands: list, workdir: str | None = None, on_execution=None) -> dict:
    cmd = command_of(claim.text)
    if not cmd:
        return {"result": "NOT TESTABLE", "retrieved": "", "settle": "state the exact command to run", "action": "no command named"}
    if executor is None:
        return {"result": "NOT TESTABLE", "retrieved": "", "settle": f"register an EXECUTOR seat and run: {cmd}", "action": "no EXECUTOR registered"}
    if allowed_commands and not any(cmd == a or cmd.startswith(a.split()[0] + " ") for a in allowed_commands):
        return {"result": "BLOCKED", "retrieved": "", "settle": f"the command is not one of the gate's procedures; add it to the gate or run it by hand: {cmd}",
                "action": f"refused {cmd}: not in the gate procedures"}
    run = executor.run_command(cmd, cwd=workdir)
    if on_execution:
        on_execution({"command": cmd, "cwd": workdir or "", "returncode": run.get("returncode"), "error": run.get("error"),
                      "output_head": (run.get("output") or "")[:500], "elapsed_s": run.get("elapsed_s")})
    if run.get("error"):
        return {"result": "BLOCKED", "retrieved": "", "settle": f"rerun when the executor can run it ({run['error']})", "action": f"asked EXECUTOR to run {cmd}"}
    out = (run.get("output") or "").strip()
    rc = run.get("returncode")
    if rc == 0:
        return {"result": "PASSED", "retrieved": f"exit 0; output: {out[:300]}", "settle": "", "action": f"EXECUTOR ran {cmd}"}
    return {"result": "FAILED", "retrieved": f"exit {rc}; output: {out[:300]}", "settle": "", "action": f"EXECUTOR ran {cmd}"}
