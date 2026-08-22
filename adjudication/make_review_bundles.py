#!/usr/bin/env python3
"""
make_review_bundles.py
======================
Regenerate the paste-ready review bundles in review/.

The bundles are GENERATED, not source -- they are concatenations of the modules
with a header, and they go stale the moment any module changes. Only this
script and REVIEW-BRIEF.md are committed; run this to rebuild the bundles
against whatever the code says today.

    python make_review_bundles.py

It refuses to write a bundle containing anything that looks like a live
credential, because the entire point of the bundles is that they get pasted
into someone else's chat window.
"""

from __future__ import annotations

import pathlib
import re
import sys

BUNDLES = [
    ("bundle-1-math.txt", "THE STATISTICS AND THE RUN-TO-RHO JOIN",
     "Are the formulas correct, and is the correctness-matrix scoring defensible?\n"
     "The load-bearing judgement is: correct = (seat asserted it) == (claim is true),\n"
     "which scores a silent seat as having MISSED a verified true finding.",
     ["seat_independence.py", "correctness_matrix.py"]),
    ("bundle-2-orchestrator.txt", "GATES, BLINDING, THE FIVE PASSES, STOPPING",
     "Where does this fail OPEN instead of closed? Can the blinding be broken by any\n"
     "route, including indirect ones - shared state, ordering, error text, logs?",
     ["adjudication_orchestrator.py"]),
    ("bundle-3-io.txt", "NETWORK, SETTINGS, AUDIT LOG, CLI",
     "Where can an API key leak - a log line, an exception, a repr, a retry?\n"
     "What happens on partial failure: a torn write, a half response, a dead seat?",
     ["seat_adapter.py", "seat_profiles.py", "run_adjudication.py", "audit_log.py",
      "validation_harness.py"]),
    ("bundle-4-tests.txt", "THE TEST SUITE",
     "Which of these tests would STILL PASS if the behaviour it names were deleted?\n"
     "Name the test and name the deletion.",
     ["test_suite.py", "test_properties.py"]),
]

# A real key, not a fixture. Fixture values in the suite are plain words
# ("from-the-file", "demo-key-1"); a live key is long and high-entropy.
LIVE_SECRET = re.compile(
    r"sk-ant-[A-Za-z0-9_\-]{20,}|sk-[A-Za-z0-9]{32,}|xai-[A-Za-z0-9]{20,}"
    r"|AIza[A-Za-z0-9_\-]{30,}|ADJ_SEAT_[0-9]_API_KEY=[A-Za-z0-9_\-]{20,}"
)


def build(root: pathlib.Path, out: pathlib.Path) -> int:
    out.mkdir(exist_ok=True)
    failures = 0
    for name, title, ask, files in BUNDLES:
        parts = [
            "=" * 78,
            f"ELIMINATION PROTOCOL FIVE  --  {title}",
            "=" * 78,
            "",
            "WHAT I WANT FROM YOU:",
            ask,
            "",
            "Try to BREAK this. A reply saying it looks fine is worth nothing to me.",
            "Assume there is a defect and go find it. Read REVIEW-BRIEF.md first for",
            "the design rules and the list of things that look wrong but are deliberate.",
            "",
            f"FILES IN THIS BUNDLE ({len(files)}):",
        ]
        for f in files:
            n = len((root / f).read_text().splitlines())
            parts.append(f"  - {f}  ({n} lines)")
        parts.append("")
        for f in files:
            parts += ["", "#" * 78, f"# FILE: {f}", "#" * 78, "",
                      (root / f).read_text()]
        text = "\n".join(parts)

        leaked = LIVE_SECRET.findall(text)
        if leaked:
            print(f"REFUSING to write {name}: looks like a live credential "
                  f"({len(leaked)} match(es))", file=sys.stderr)
            failures += 1
            continue

        (out / name).write_text(text)
        print(f"{name:28} {len(text):>8,} chars  ~{len(text)//4:>6,} tokens")
    return failures


if __name__ == "__main__":
    here = pathlib.Path(__file__).parent
    raise SystemExit(1 if build(here, here / "review") else 0)
