#!/usr/bin/env python3
"""
goal_throughput.py
==================
Evaluates the goal-attainment transfer function against the goal ledger.

THE STRUCTURE THIS ENFORCES. Goal attainment from this system is not additive in
its inputs. Two of them are MULTIPLICATIVE GATES:

    Y = X1 * X3 * f(X2, X4 .. X10)

    X1  goals written down            0 or 1
    X3  a review cadence executed     0 or 1

If either is zero, Y is zero regardless of every other input. That is a
structural statement, not an empirical one: an unwritten goal cannot be advanced
by anything, and an unreviewed goal cannot be detected as stalled. So this script
checks the gates FIRST and refuses to report an attainment figure while either
is open -- reporting a low number there would imply the other inputs matter yet,
and they do not.

LITTLE'S LAW IS USED, AND IT IS A THEOREM, NOT A CITATION. For a stable system,
average WIP = average throughput x average cycle time. It follows that at fixed
throughput, raising the number of concurrently active goals raises the time each
one takes -- it does not raise how many finish. This is arithmetic, so it is
stated without a source; the empirical question of what YOUR throughput is
remains unmeasured and is not guessed.

WHAT IT WILL NOT DO. Produce a percentage of goals that will be achieved. That
needs a history of committed-versus-closed goals across completed periods. The
ledger is empty, so there is no history, and an invented rate would be the exact
failure this repository's AGENTS.md forbids.

Usage:
    python3 scripts/goal_throughput.py [ledger.md]
    python3 scripts/goal_throughput.py --self-test
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

LEDGER = "agents/analysis/goal-ledger.md"
ROW = re.compile(r"^\|\s*(G-[YQMWD]-\d+)\s*\|(.*)$")
WIP_CAP_PER_LANE = 1
WIP_CAP_TOTAL = 3


def parse(text: str) -> list[dict]:
    """A row counts as a goal only when it carries actual content."""
    goals = []
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        while len(cells) < 6:
            cells.append("")
        lane, goal, owner, nxt, agents, status = cells[:6]
        if not goal:
            continue  # an empty template row is not a goal
        goals.append({"id": m.group(1), "lane": lane, "goal": goal,
                      "owner": owner, "next": nxt, "agents": agents,
                      "status": status.upper()})
    return goals


def evaluate(goals: list[dict], cadence_executed: bool) -> dict:
    x1 = 1 if goals else 0
    x3 = 1 if cadence_executed else 0
    owned = [g for g in goals if g["owner"] and g["next"]]
    unowned = [g for g in goals if not g["owner"] or not g["next"]]
    wip = [g for g in goals if g["status"] == "MOVING"]
    by_lane: dict[str, int] = {}
    for g in wip:
        by_lane[g["lane"]] = by_lane.get(g["lane"], 0) + 1
    breaches = [(ln, n) for ln, n in by_lane.items() if n > WIP_CAP_PER_LANE]
    return {"X1": x1, "X3": x3, "goals": goals, "owned": owned,
            "unowned": unowned, "wip": wip, "by_lane": by_lane,
            "wip_breaches": breaches, "gate_open": x1 == 0 or x3 == 0}


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--self-test":
        return self_test()
    root = Path(__file__).resolve().parent.parent
    path = Path(argv[1]) if len(argv) > 1 else root / LEDGER
    if not path.exists():
        print(f"REFUSED: no ledger at {path}")
        return 2

    # Cadence cannot be read from a file; it is a fact about behaviour. Absent
    # evidence of a completed review, it is treated as NOT executed. Assuming it
    # ran would be assuming the thing being measured.
    res = evaluate(parse(path.read_text()), cadence_executed=False)

    print("=" * 74)
    print("GOAL ATTAINMENT TRANSFER FUNCTION    Y = X1 * X3 * f(X2, X4..X10)")
    print("=" * 74)
    print(f"  X1  goals written down .............. {res['X1']}"
          f"   ({len(res['goals'])} goal(s) with content)")
    print(f"  X3  review cadence executed ......... {res['X3']}"
          f"   (no completed review recorded)")
    print()

    if res["gate_open"]:
        zero = [n for n, v in (("X1", res["X1"]), ("X3", res["X3"])) if v == 0]
        print(f"  Y = {' * '.join(str(res[n]) for n in ('X1', 'X3'))} * f(...) = 0")
        print()
        print(f"GATE OPEN: {', '.join(zero)} = 0.")
        print("  Y is structurally ZERO, not merely low. Every other input is")
        print("  irrelevant until the gate closes: an unwritten goal cannot be")
        print("  advanced, and an unreviewed goal cannot be detected as stalled.")
        print()
        print("  NO ATTAINMENT PERCENTAGE IS PRODUCED. Reporting one here would")
        print("  imply the remaining inputs matter yet. They do not.")
        print()
        print("  TO CLOSE THE GATE:")
        if res["X1"] == 0:
            print(f"    X1 -> write at least one goal into {LEDGER}")
        if res["X3"] == 0:
            print("    X3 -> complete one review at any cadence and record it")
        return 1

    print(f"  goals with an owner AND one next action : {len(res['owned'])}/{len(res['goals'])}")
    if res["unowned"]:
        print("  UNOWNED - a goal with no owner is a wish:")
        for g in res["unowned"]:
            print(f"    {g['id']}  {g['goal'][:58]}")
    print()
    print(f"  WIP (status MOVING): {len(res['wip'])}   cap/lane {WIP_CAP_PER_LANE}"
          f"   cap total {WIP_CAP_TOTAL}")
    for ln, n in sorted(res["by_lane"].items()):
        print(f"    {ln or '(no lane)':<10} {n}")
    if res["wip_breaches"] or len(res["wip"]) > WIP_CAP_TOTAL:
        print()
        print("  WIP CAP BREACHED. Little's Law: WIP = throughput x cycle time.")
        print("  At fixed throughput, more concurrent goals lengthen every one of")
        print("  them. It does not finish more. Park something.")
    print()
    print("  Attainment rate and cycle time need a HISTORY of completed periods.")
    print("  None exists yet. Not estimated.")
    return 0


def self_test() -> int:
    empty = "| G-Y-01 | | | | | |"
    one = "| G-Q-01 | FORGE | Ship v1 by 2026-12-31 | Andrew | Write the spec | BUILDER | MOVING |"
    two_same_lane = one + "\n| G-Q-02 | FORGE | Patent filed by 2027-03-01 | Andrew | Draft disclosure | PRIORART | MOVING |"
    unowned = "| G-Q-03 | ABO | Win a prime contract | | | | NOT STARTED |"
    checks = [
        ("empty template row is not a goal", len(parse(empty)) == 0),
        ("a filled row is a goal", len(parse(one)) == 1),
        ("X1=0 on an empty ledger", evaluate(parse(empty), True)["X1"] == 0),
        ("gate open when no goals", evaluate(parse(empty), True)["gate_open"]),
        ("gate open when cadence not run", evaluate(parse(one), False)["gate_open"]),
        ("gate closed when both present", not evaluate(parse(one), True)["gate_open"]),
        ("unowned goal detected", len(evaluate(parse(unowned), True)["unowned"]) == 1),
        ("WIP breach detected per lane",
         len(evaluate(parse(two_same_lane), True)["wip_breaches"]) == 1),
        ("single WIP is not a breach",
         len(evaluate(parse(one), True)["wip_breaches"]) == 0),
    ]
    fails = 0
    for label, ok in checks:
        print(f"  {'ok   ' if ok else 'FAIL '} {label}")
        fails += 0 if ok else 1
    print(f"\n{len(checks)-fails}/{len(checks)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError, ValueError):
        pass
    sys.exit(main(sys.argv))
