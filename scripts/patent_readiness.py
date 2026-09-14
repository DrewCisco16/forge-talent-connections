#!/usr/bin/env python3
"""
patent_readiness.py
===================
Scores a pre-filing patent readiness checklist. Refuses to output an allowance
probability, and says why.

WHAT THIS COMPUTES. A count: checkable pre-filing defects closed, over the count
applicable, overall and per CTQ. The arithmetic is shown. Edit the checklist and
the score moves.

WHAT THIS REFUSES TO COMPUTE, AND WHY. A probability of allowance. Three
independent reasons, any one of which is sufficient:

  1. NO DATASET. An allowance probability needs art-unit or examiner base-rate
     data from the USPTO. None is in this repository and USPTO was unreachable
     from the session that wrote this file.
  2. NO STANDING. Patentability is a legal determination. It requires a
     registered practitioner. A script is not one and neither is a model.
  3. A READINESS COUNT IS NOT A PROBABILITY. Closing every item here cannot make
     an unpatentable idea patentable. It removes SELF-INFLICTED rejections,
     which are the only kind an applicant controls. Reporting the count as a
     probability would confuse the two, and that confusion is exactly the error
     the operator's standing rules forbid.

So: `--probability` exists only to print that refusal, because a reader who
wants the number should meet the reason rather than the silence.

Usage:
    python3 scripts/patent_readiness.py [checklist.json]
    python3 scripts/patent_readiness.py --probability
    python3 scripts/patent_readiness.py --self-test
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULT = "agents/analysis/patent-readiness-checklist.json"
SEV_ORDER = {"BLOCKING": 0, "MATERIAL": 1, "ADVISORY": 2}


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def score(doc: dict) -> dict:
    """PASS counts as closed. FAIL and UNKNOWN do not. NA leaves the denominator."""
    per_ctq, blocking_open, material_open = [], [], []
    closed = applicable = 0
    for c in doc["ctqs"]:
        items = [i for i in c["items"] if i["status"] != "NA"]
        p = [i for i in items if i["status"] == "PASS"]
        closed += len(p)
        applicable += len(items)
        for i in items:
            if i["status"] != "PASS":
                (blocking_open if i["severity"] == "BLOCKING" else
                 material_open if i["severity"] == "MATERIAL" else []).append((c, i))
        per_ctq.append({"id": c["id"], "name": c["name"],
                        "closed": len(p), "applicable": len(items)})
    return {"closed": closed, "applicable": applicable, "per_ctq": per_ctq,
            "blocking_open": blocking_open, "material_open": material_open}


def refusal() -> str:
    return (
        "REFUSED: no probability of allowance is produced.\n"
        "  1. No dataset. Art-unit base rates come from the USPTO; none is here.\n"
        "  2. No standing. Patentability is a legal determination reserved to a\n"
        "     registered practitioner.\n"
        "  3. A readiness count is not a probability. Closing every item cannot\n"
        "     make an unpatentable idea patentable; it removes self-inflicted\n"
        "     rejections, which are the only kind an applicant controls.\n\n"
        "  To obtain a real figure: ask counsel for the art unit's allowance rate\n"
        "  from USPTO data, and treat this readiness score as a separate, second\n"
        "  number. Never multiply them together -- they are not independent and\n"
        "  the product would mean nothing."
    )


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--probability":
        print(refusal()); return 1
    if len(argv) > 1 and argv[1] == "--self-test":
        return self_test()

    root = Path(__file__).resolve().parent.parent
    path = Path(argv[1]) if len(argv) > 1 else root / DEFAULT
    doc = load(path)
    s = score(doc)

    print("=" * 76)
    print(f"PATENT PRE-FILING READINESS  --  disclosure: {doc.get('disclosure_id')}")
    print("=" * 76)
    print(f"{'CTQ':<16}{'NAME':<44}{'CLOSED':>10}")
    for c in s["per_ctq"]:
        bar = f"{c['closed']}/{c['applicable']}"
        print(f"{c['id']:<16}{c['name'][:43]:<44}{bar:>10}")

    print()
    print("READINESS SCORE, shown:")
    print(f"  closed / applicable = {s['closed']} / {s['applicable']}"
          f" = {s['closed']/s['applicable']:.3f}" if s["applicable"] else "  no applicable items")
    print("  This is a COUNT OF DEFECTS CLOSED. It is not a probability of allowance.")

    print()
    if s["blocking_open"]:
        print(f"DO NOT FILE -- {len(s['blocking_open'])} BLOCKING item(s) open:")
        for c, i in s["blocking_open"]:
            print(f"  [{i['id']:<8}] {c['id']:<14} {i['check'][:78]}")
    else:
        print("No BLOCKING items open.")

    if s["material_open"]:
        print()
        print(f"{len(s['material_open'])} MATERIAL item(s) open -- close, or record a "
              "counsel-approved reason:")
        for c, i in s["material_open"][:12]:
            print(f"  [{i['id']:<8}] {c['id']:<14} {i['check'][:78]}")
        if len(s["material_open"]) > 12:
            print(f"  ... and {len(s['material_open']) - 12} more")

    base = (doc.get("art_unit_base_rate") or {}).get("value")
    print()
    print(f"Art-unit base rate on file: {base if base is not None else 'NONE -- obtain from counsel or USPTO data'}")
    print()
    print("PROFESSIONAL VERIFICATION REQUIRED. A registered patent practitioner")
    print("decides everything in this checklist. This output organises evidence")
    print("for that person and substitutes for none of their judgement.")
    return 1 if s["blocking_open"] else 0


def self_test() -> int:
    doc = {"disclosure_id": "T", "ctqs": [{"id": "C1", "name": "n", "items": [
        {"id": "a", "severity": "BLOCKING", "check": "x", "status": "PASS"},
        {"id": "b", "severity": "BLOCKING", "check": "y", "status": "UNKNOWN"},
        {"id": "c", "severity": "MATERIAL", "check": "z", "status": "FAIL"},
        {"id": "d", "severity": "ADVISORY", "check": "w", "status": "NA"},
    ]}]}
    s = score(doc)
    checks = [
        ("NA leaves the denominator", s["applicable"] == 3),
        ("PASS counts as closed", s["closed"] == 1),
        ("UNKNOWN is not closed", len(s["blocking_open"]) == 1),
        ("FAIL is not closed", len(s["material_open"]) == 1),
        ("refusal text names all three reasons",
         all(k in refusal() for k in ("No dataset", "No standing", "not a probability"))),
        ("refusal forbids multiplying", "Never multiply them" in refusal()),
    ]
    fails = 0
    for label, ok in checks:
        print(f"  {'ok   ' if ok else 'FAIL '} {label}")
        fails += 0 if ok else 1
    print(f"\n{len(checks)-fails}/{len(checks)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    # A tool that traces back when piped into `head` is a tool people stop
    # piping. Restore default SIGPIPE so the shell handles a closed pipe.
    try:
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError, ValueError):
        pass  # Windows has no SIGPIPE
    sys.exit(main(sys.argv))
