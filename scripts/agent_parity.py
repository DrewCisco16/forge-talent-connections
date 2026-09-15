#!/usr/bin/env python3
"""
agent_parity.py -- the card and its runnable form must not drift apart.

THE FAILURE THIS PREVENTS. A card says MAILROOM never sends. The runnable
definition is what Claude Code actually loads. If someone edits one and not the
other, the contract Andrew reviewed is not the contract that runs -- and the
difference is invisible, because both files look fine on their own.

This gate checks three things:

    1  every agent card has a runnable definition          (no unbuilt agent)
    2  every runnable definition has a card                (no orphan agent)
    3  the definition is byte-identical to a fresh build    (no silent drift)

WHAT IT DELIBERATELY DOES NOT CHECK. Whether the tool grants are CORRECT. That
those are the right tools for MAILROOM is a human judgement made once in
build_agents.py's SPEC table and reviewed there. This gate only ensures nobody
changed them afterwards without saying so.

PROTOCOLS ARE EXEMPT. baseline and smoke are protocols: nothing performs them for
Andrew, so they have no runnable form and must not acquire one.

THREE AGENTS ARE HAND-WRITTEN. reviewer, librarian and matrix were built by hand
under different names before the generator existed. They are exempt from the
byte-identical check and only checked for existence -- a generated file would
throw away better hand-written prose.

Usage:
    python3 scripts/agent_parity.py              # check
    python3 scripts/agent_parity.py --gate       # quiet on success, for the hook
    python3 scripts/agent_parity.py --self-test
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import build_agents as ba  # noqa: E402

CARDS = REPO / "agents" / "cards"
RUNNABLE = REPO / "agents" / "runnable"
LIVE = REPO / ".claude" / "agents"


def audit() -> dict:
    cards = {p.stem for p in CARDS.glob("*.md")} - ba.SKIP - ba.PROTOCOLS
    # ba.SKIP excludes README, which is this directory's index, not an agent.
    # Caught by this gate's own first run, which is the correct way to find it.
    built = ({p.stem for p in RUNNABLE.glob("*.md")} - ba.SKIP) if RUNNABLE.exists() else set()
    live = ({p.stem for p in LIVE.glob("*.md")} - ba.SKIP) if LIVE.exists() else set()

    handwritten = set(ba.ALREADY)                      # reviewer, librarian, matrix
    expected = cards - handwritten
    live_handwritten = set(ba.ALREADY.values())

    missing = sorted(expected - built)
    orphans = sorted(built - expected)
    no_spec = sorted(c for c in expected if c not in ba.SPEC)

    drift = []
    for name in sorted(expected & built):
        try:
            fresh = ba.build(name)
        except Exception as exc:                        # a card the builder cannot parse
            drift.append((name, f"cannot rebuild: {exc}"))
            continue
        if (RUNNABLE / f"{name}.md").read_text(encoding="utf-8") != fresh:
            drift.append((name, "differs from a fresh build of its card"))

    # Hand-written three: existence only.
    hand_missing = sorted(n for n, f in ba.ALREADY.items()
                          if not (LIVE / f"{f}.md").exists())

    # Protocols must NOT have a runnable form.
    protocol_leak = sorted(p for p in ba.PROTOCOLS
                           if (RUNNABLE / f"{p}.md").exists() or (LIVE / f"{p}.md").exists())

    installed = sorted((built | live_handwritten) & live)
    not_installed = sorted(built - live)

    return {
        "cards": len(cards), "built": len(built), "live": len(live),
        "missing": missing, "orphans": orphans, "no_spec": no_spec,
        "drift": drift, "hand_missing": hand_missing, "protocol_leak": protocol_leak,
        "installed": installed, "not_installed": not_installed,
        "ok": not (missing or orphans or no_spec or drift or hand_missing or protocol_leak),
    }


def report(a: dict) -> int:
    print("AGENT PARITY -- card <-> runnable definition")
    print("=" * 70)
    print(f"agent cards                : {a['cards']}")
    print(f"runnable definitions built : {a['built']}  (agents/runnable/)")
    print(f"installed and live         : {a['live']}  (Claude Code agents dir)")
    print()

    bad = False
    for key, label in (("missing", "cards with NO runnable definition"),
                       ("orphans", "runnable definitions with NO card"),
                       ("no_spec", "cards with no tools spec in build_agents.SPEC"),
                       ("hand_missing", "hand-written agents that have gone missing"),
                       ("protocol_leak", "PROTOCOLS that wrongly acquired a runnable form")):
        if a[key]:
            bad = True
            print(f"FAIL -- {label}: {', '.join(a[key])}")
    if a["drift"]:
        bad = True
        print("FAIL -- definition no longer matches its card:")
        for name, why in a["drift"]:
            print(f"    {name}: {why}")
            print("      fix: edit the CARD, then `python3 scripts/build_agents.py`")

    if not bad:
        print("PASS -- every card has a runnable form, every form matches its card,")
        print("        and no protocol has acquired one.")
    print()

    if a["not_installed"]:
        print(f"NOT YET INSTALLED: {len(a['not_installed'])} definition(s) are built but not live.")
        print("  They are specified, generated, reviewed -- and cannot run until installed.")
        print("  See agents/runnable/README.md. This is NOT a parity failure; it is FM-47.")
    return 1 if bad else 0


def selftest() -> int:
    p = f = 0

    def check(name, cond):
        nonlocal p, f
        if cond:
            p += 1
        else:
            f += 1
            print(f"  FAIL: {name}")

    a = audit()
    check("no card is missing a runnable form", not a["missing"])
    check("no runnable form is an orphan", not a["orphans"])
    check("every card has a tools spec", not a["no_spec"])
    check("no definition has drifted from its card", not a["drift"])
    check("the three hand-written agents still exist", not a["hand_missing"])
    check("protocols have NOT acquired a runnable form", not a["protocol_leak"])
    check("baseline is still a protocol", "baseline" in ba.PROTOCOLS)
    check("smoke is still a protocol", "smoke" in ba.PROTOCOLS)

    # The load-bearing safety property: MAILROOM must never hold a send tool.
    m = (RUNNABLE / "mailroom.md")
    if m.exists():
        txt = m.read_text(encoding="utf-8")
        head = txt.split("---")[1]
        tools = next(l for l in head.splitlines() if l.startswith("tools:"))
        banned = next(l for l in head.splitlines() if l.startswith("disallowedTools:"))
        for verb in ("send_message", "send_draft", "reply", "forward"):
            check(f"MAILROOM is not granted {verb}", verb not in tools)
        check("MAILROOM explicitly disallows send_message", "send_message" in banned)
    else:
        check("mailroom definition exists", False)

    print(f"agent_parity: {p}/{p + f} passed")
    return 1 if f else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="card <-> runnable definition parity")
    ap.add_argument("--gate", action="store_true", help="quiet on success, for the hook")
    ap.add_argument("--self-test", "--selftest", dest="self_test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return selftest()
    a = audit()
    if args.gate:
        if a["ok"]:
            return 0
        print("COMMIT BLOCKED -- an agent card and its runnable form disagree.", file=sys.stderr)
        for name, why in a["drift"]:
            print(f"  {name}: {why}", file=sys.stderr)
        for n in a["missing"]:
            print(f"  {n}: card has no runnable definition", file=sys.stderr)
        for n in a["orphans"]:
            print(f"  {n}: runnable definition has no card", file=sys.stderr)
        for n in a["protocol_leak"]:
            print(f"  {n}: is a PROTOCOL and must not have a runnable form", file=sys.stderr)
        print("\n  fix: edit the card, then python3 scripts/build_agents.py", file=sys.stderr)
        return 1
    return report(a)


if __name__ == "__main__":
    try:
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError):
        pass
    sys.exit(main())
