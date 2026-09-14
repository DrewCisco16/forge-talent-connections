#!/usr/bin/env python3
"""
loop_guard.py
=============
Fail-closed gate in front of every autonomous research loop.

WHY THIS EXISTS. An autonomous optimization loop is a search for anything that
moves a number. It does not know what you meant. If the number can be moved
cheaply, it will be, and the loop will report success while producing nothing --
or worse, while quietly damaging the thing it was pointed at.

The defence is not vigilance during the run. Nobody is watching at 3am; that is
the point of the loop. The defence is refusing to start a loop whose objective
cannot survive being optimised against.

So this refuses BEFORE anything runs, in the same shape as the cost ceiling in
adjudicate.yml: plan first, refuse before spending, and say exactly what is
missing.

SIX GATES (agents/11-autoresearch-loops.md section 3):
  G1  metric computed by code, no model judgement in the scoring path
  G2  one evaluation bounded in wall clock
  G3  evaluation deterministic, or seeded and averaged
  G4  three cheapest cheat paths written down in advance
  G5  rollback automatic and complete
  G6  a held-out check the loop cannot see

BLOCKERS. A spec may declare `blockers`: [{id, what, clear_by, resolved}].
Any entry not explicitly resolved=true refuses the loop. A blocker you can
run past is a note, not a blocker.

A HYBRID IS NOT A FAILED LOOP. Falsification and journal loops legitimately have
no optimisable metric. They are held to different checks, and they are FORBIDDEN
from declaring an optimisation metric -- claiming one you cannot compute is the
failure this file exists to catch.

Usage:
    python3 loop_guard.py <loop.json>       0 = may run, non-zero = may not
    python3 loop_guard.py --self-test
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

VALID_TYPES = ("optimization", "falsification", "journal")
MIN_CHEAT_PATHS = 3


class Refusal(Exception):
    """Raised with the reason a loop may not run."""


def _require(cond: object, gate: str, msg: str, findings: list[str]) -> bool:
    if not cond:
        findings.append(f"{gate}: {msg}")
        return False
    return True


def check(spec: dict) -> list[str]:
    """Return a list of findings. Empty list means the loop may run."""
    f: list[str] = []

    lane = spec.get("lane")
    _require(lane, "SPEC", "no 'lane' declared -- a loop with no lane has no boundary", f)

    loop_type = spec.get("loop_type")
    if not _require(loop_type in VALID_TYPES, "SPEC",
                    f"'loop_type' must be one of {VALID_TYPES}, got {loop_type!r}", f):
        return f  # nothing further is meaningful

    # ---- limits: every loop, every type. A loop with no stopping condition
    # ---- is a bill with no stopping condition.
    limits = spec.get("limits") or {}
    for key in ("max_iterations", "max_wall_clock_hours", "max_spend_usd"):
        val = limits.get(key)
        _require(isinstance(val, (int, float)) and val > 0,
                 "LIMITS", f"'{key}' must be a positive number (got {val!r})", f)

    # ---- rollback (G5): every type. Even a journal must be revertible.
    rb = spec.get("rollback") or {}
    _require(rb.get("automatic") is True, "G5",
             "rollback.automatic must be true -- a loop that cannot cleanly revert "
             "accumulates damage instead of improvements", f)
    _require(bool(rb.get("command")), "G5", "rollback.command not declared", f)

    # ---- immutable paths: the loop must not be able to move its own goalposts.
    immutable = spec.get("immutable_paths") or []
    _require(isinstance(immutable, list) and immutable, "SPEC",
             "immutable_paths is empty -- at minimum the metric script and this "
             "spec must be unwritable by the loop", f)
    if isinstance(immutable, list):
        _require(any("program.md" in str(p) for p in immutable), "SPEC",
                 "program.md is not in immutable_paths -- a loop that can rewrite "
                 "its own objective has no objective", f)

    if loop_type == "optimization":
        f.extend(_check_optimization(spec))
    else:
        f.extend(_check_hybrid(spec, loop_type))

    # ---- declared blockers: any unresolved entry stops the loop.
    # ---- A blocker you can run past is a note, not a blocker.
    for b in spec.get("blockers") or []:
        if isinstance(b, dict) and b.get("resolved") is not True:
            f.append(
                f"BLOCKED: {b.get('id', '?')} -- {b.get('what', 'no description')}"
                + (f" | clear it by: {b['clear_by']}" if b.get("clear_by") else "")
            )

    # ---- lane-specific hard blocks
    if lane == "ABO" and spec.get("counsel_cleared") is not True:
        f.append(
            "BLOCKED: lane ABO requires counsel_cleared=true. A proposal in progress "
            "is plausibly procurement-sensitive. See agents/07-guardrails.md section 2 "
            "and agents/10-open-questions.md A1. Professional verification required."
        )
    if lane == "HOME":
        _require(spec.get("browser_control") is False, "HOME",
                 "browser_control must be explicitly false -- an agent in a profile "
                 "authenticated to family finances has unbounded downside "
                 "(agents/12-browser-and-remote-control.md section 3)", f)
        _require(spec.get("executes_transactions") is False, "HOME",
                 "executes_transactions must be explicitly false -- money movement "
                 "is a one-way door", f)

    return f


def _check_optimization(spec: dict) -> list[str]:
    f: list[str] = []
    metric = spec.get("metric") or {}

    # G1 -- the whole reason the loop can run unattended
    _require(metric.get("computed_by") == "script", "G1",
             "metric.computed_by must be 'script'. A model scoring its own output "
             "is a loop that converges on what the model likes", f)
    _require(bool(metric.get("script")), "G1", "metric.script path not declared", f)
    _require(metric.get("direction") in ("lower_is_better", "higher_is_better"), "G1",
             "metric.direction must be declared so keep/rollback is mechanical", f)

    # G2
    ev = spec.get("evaluation") or {}
    secs = ev.get("max_seconds")
    _require(isinstance(secs, (int, float)) and secs > 0, "G2",
             "evaluation.max_seconds must be a positive number -- an unbounded "
             "evaluation yields too few experiments to learn anything", f)

    # G3
    deterministic = ev.get("deterministic")
    seeded = ev.get("seeded_runs")
    ok = deterministic is True or (isinstance(seeded, int) and seeded >= 3)
    _require(ok, "G3",
             "evaluation must be deterministic=true, or seeded_runs>=3 and averaged. "
             "Otherwise noise gets banked as improvement and you build on it", f)

    # G4 -- the gate people skip and then get burned by
    cheats = spec.get("cheat_paths") or []
    _require(isinstance(cheats, list) and len(cheats) >= MIN_CHEAT_PATHS, "G4",
             f"declare at least {MIN_CHEAT_PATHS} cheapest ways this metric can be "
             "moved without doing the work. If you cannot name three, you do not "
             "understand the metric well enough to optimise against it", f)
    if isinstance(cheats, list):
        for i, c in enumerate(cheats):
            if not (isinstance(c, dict) and c.get("path") and c.get("defence")):
                f.append(f"G4: cheat_paths[{i}] needs both 'path' and 'defence'")

    # G6 -- the only defence against G4 that survives a clever optimiser
    ho = spec.get("held_out") or {}
    _require(ho.get("exists") is True, "G6",
             "a held-out check is required for any optimisation loop", f)
    _require(ho.get("visible_to_loop") is False, "G6",
             "held_out.visible_to_loop must be false -- a held-out check the loop "
             "can see is not held out", f)
    _require(bool(ho.get("description")), "G6", "held_out.description not declared", f)

    return f


def _check_hybrid(spec: dict, loop_type: str) -> list[str]:
    f: list[str] = []
    # A hybrid must not smuggle in an optimisation objective it cannot compute.
    metric = spec.get("metric") or {}
    if metric.get("direction") in ("lower_is_better", "higher_is_better"):
        f.append(
            f"HYBRID: loop_type '{loop_type}' declares an optimisation direction. "
            "A hybrid has no optimisable metric -- claiming one you cannot compute "
            "is the failure this guard exists to catch. Use 'diagnostics' instead, "
            "which are reported and never optimised toward."
        )
    _require(bool(spec.get("stopping_condition")), "HYBRID",
             "stopping_condition must be declared in words "
             "(e.g. 'one full round with zero new kills')", f)
    if loop_type == "falsification":
        _require(bool(spec.get("mechanical_gates")), "HYBRID",
                 "falsification loops must declare the mechanical gates that run "
                 "BEFORE model judgement -- the ordering is the safety property", f)
    return f


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) != 2:
        print(__doc__.strip())
        return 2

    path = Path(argv[1])
    if not path.exists():
        print(f"REFUSED: no such spec: {path}")
        return 2
    try:
        spec = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        print(f"REFUSED: {path} is not valid JSON: {exc}")
        return 2

    findings = check(spec)
    name = spec.get("name", path.stem)
    if findings:
        print(f"REFUSED: {name} ({spec.get('lane', '?')}) may not run.\n")
        for finding in findings:
            print(f"  - {finding}")
        print(f"\n{len(findings)} unmet condition(s). Nothing was started.")
        return 1

    print(f"CLEARED: {name} ({spec.get('lane')}, {spec.get('loop_type')}) may run.")
    lim = spec["limits"]
    print(f"  ceilings: {lim['max_iterations']} iterations, "
          f"{lim['max_wall_clock_hours']}h wall clock, "
          f"${lim['max_spend_usd']} spend")
    print("  a green run is not a good run -- read the iteration log, not the status.")
    return 0


def self_test() -> int:
    """Prove the guard refuses what it should. Failing closed is the whole point."""
    good_opt = {
        "name": "t", "lane": "FORGE", "loop_type": "optimization",
        "metric": {"computed_by": "script", "script": "m.py", "direction": "lower_is_better"},
        "evaluation": {"max_seconds": 300, "deterministic": True},
        "cheat_paths": [{"path": f"p{i}", "defence": f"d{i}"} for i in range(3)],
        "rollback": {"automatic": True, "command": "git reset --hard"},
        "held_out": {"exists": True, "visible_to_loop": False, "description": "d"},
        "immutable_paths": ["tests/**", "program.md", "m.py"],
        "limits": {"max_iterations": 100, "max_wall_clock_hours": 8, "max_spend_usd": 25},
    }
    cases: list[tuple[str, dict, bool]] = [
        ("valid optimisation loop clears", good_opt, True),
        ("model-scored metric refused",
         {**good_opt, "metric": {**good_opt["metric"], "computed_by": "model"}}, False),
        ("unbounded evaluation refused",
         {**good_opt, "evaluation": {"deterministic": True}}, False),
        ("nondeterministic, unseeded refused",
         {**good_opt, "evaluation": {"max_seconds": 60, "deterministic": False}}, False),
        ("too few cheat paths refused", {**good_opt, "cheat_paths": [
            {"path": "a", "defence": "b"}]}, False),
        ("visible held-out refused",
         {**good_opt, "held_out": {"exists": True, "visible_to_loop": True,
                                   "description": "d"}}, False),
        ("no rollback refused",
         {**good_opt, "rollback": {"automatic": False, "command": "x"}}, False),
        ("mutable program.md refused",
         {**good_opt, "immutable_paths": ["tests/**"]}, False),
        ("missing spend ceiling refused",
         {**good_opt, "limits": {"max_iterations": 1, "max_wall_clock_hours": 1}}, False),
        ("ABO without counsel refused",
         {**good_opt, "lane": "ABO"}, False),
        ("ABO with counsel clears",
         {**good_opt, "lane": "ABO", "counsel_cleared": True}, True),
        ("HOME with browser control refused",
         {**good_opt, "lane": "HOME", "loop_type": "journal",
          "stopping_condition": "weekly", "metric": {},
          "browser_control": True, "executes_transactions": False}, False),
        ("hybrid claiming an optimisation direction refused",
         {**good_opt, "loop_type": "falsification", "stopping_condition": "no new kills",
          "mechanical_gates": ["citation_gate"]}, False),
        ("unresolved blocker refused",
         {**good_opt, "blockers": [{"id": "B1", "what": "stale rate", "resolved": False}]}, False),
        ("resolved blocker clears",
         {**good_opt, "blockers": [{"id": "B1", "what": "stale rate", "resolved": True}]}, True),
        ("valid falsification loop clears",
         {**good_opt, "loop_type": "falsification", "metric": {},
          "stopping_condition": "one full round, zero new kills",
          "mechanical_gates": ["citation_gate.py", "quote_gate.py"]}, True),
    ]
    failures = 0
    for label, spec, should_clear in cases:
        cleared = not check(spec)
        if cleared != should_clear:
            print(f"  FAIL  {label}: expected "
                  f"{'clear' if should_clear else 'refuse'}, got "
                  f"{'clear' if cleared else 'refuse'}")
            failures += 1
        else:
            print(f"  ok    {label}")
    print(f"\n{len(cases) - failures}/{len(cases)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
