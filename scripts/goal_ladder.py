#!/usr/bin/env python3
"""
goal_ladder.py
==============
Enforces FM-35 -- "every agent traces to a goal" -- as a rung-1 gate instead of
a sentence in a design document.

WHAT THIS CHECKS. Every card in agents/cards/ must declare:

    ### GOAL
    **<one goal sentence>**

    - **Measured by:** <a measure a person could actually compute>
    - **Rolls up to:** outcome <A|B|C|D> -- <label>
    - **Which serves:** <the ledger pointer>

and the roll-up must name one of exactly four declared outcomes. A card whose
goal rolls up to nothing is an orphan; an outcome with no agent under it is an
unserved outcome. Both are reported, both are failures.

WHY FOUR OUTCOMES AND NOT MORE. Four is the number of distinct things this
system can do that are not restatements of each other:

    A  time returned          an hour Andrew does not spend
    B  nothing irreversible   a bad act that does not happen
    C  no goal stalls unseen  a stall that is detected while it is cheap
    D  work compounds         the second instance costs less than the first

Anything a fifth outcome would hold is one of these four wearing a new word.

WHAT THIS WILL NOT DO. Assert that the ladder is CORRECT -- that the agent
goals, summed, actually produce the outcome at the top. That claim needs
outcome data across completed periods and there is none. This checks only that
the ladder is CONNECTED: no orphan agent, no unserved outcome, no missing
measure. A connected ladder can still be pointed at the wrong summit; only the
person at the top can tell you that, and he writes it himself.

THE TOP OF THE LADDER IS DELIBERATELY EMPTY. GOALKEEPER's hard rule is that no
agent authors a goal. That rule does not suspend itself for the most important
goal in the system. So this script REFUSES to synthesise the ultimate goal from
the 29 beneath it, and reports the slot as open until the ledger is filled.

Usage:
    python3 scripts/goal_ladder.py              # check, human-readable
    python3 scripts/goal_ladder.py --emit       # regenerate the ladder document
    python3 scripts/goal_ladder.py --json       # machine-readable
    python3 scripts/goal_ladder.py --self-test  # run the self-tests
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CARDS = REPO / "agents" / "cards"
LEDGER = REPO / "agents" / "analysis" / "goal-ledger.md"
LADDER = REPO / "agents" / "analysis" / "goal-ladder.md"

# The four outcomes. Fixed here so a card cannot invent a fifth by typo.
OUTCOMES = {
    "A": ("time returned", "An hour Andrew does not spend is the only unit this system produces that he cannot buy more of."),
    "B": ("nothing irreversible goes wrong", "A send, a submission, a filing, a publication, a merge. These do not have an undo, so their cost is not bounded by their frequency."),
    "C": ("no goal stalls unnoticed", "A stall detected in a week costs a week. Detected in a quarter it costs a quarter. Detection latency IS the cost."),
    "D": ("work compounds", "The second proposal, the second literature sweep, the second claim chart must cost less than the first, or this is a treadmill with better tooling."),
}

# Cards that are protocols, not agents: nothing performs them for Andrew.
PROTOCOLS = {"baseline", "smoke"}

# Cards that are not agent cards at all.
NOT_A_CARD = {"README"}

GOAL_BLOCK = re.compile(
    r"^### GOAL\s*\n+"
    r"\*\*(?P<goal>.+?)\*\*\s*\n+"
    r"- \*\*Measured by:\*\* (?P<measure>.+?)\s*\n"
    r"- \*\*Rolls up to:\*\* outcome (?P<outcome>[A-Z])(?P<outcome_tail>[^\n]*)\n"
    r"- \*\*Which serves:\*\* (?P<serves>.+?)\s*$",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class Card:
    name: str
    goal: str = ""
    measure: str = ""
    outcome: str = ""
    kind: str = "agent"          # agent | protocol
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def parse_card(path: Path) -> Card | None:
    """Parse one card. Returns None for files that are not agent cards."""
    stem = path.stem
    if stem in NOT_A_CARD:
        return None
    text = path.read_text(encoding="utf-8")
    card = Card(name=stem, kind="protocol" if stem in PROTOCOLS else "agent")

    # Isolate the GOAL section: from "### GOAL" to the next "### " heading.
    start = text.find("### GOAL")
    if start == -1:
        card.problems.append("no ### GOAL section")
        return card
    rest = text[start:]
    nxt = rest.find("\n### ", 1)
    section = rest[:nxt] if nxt != -1 else rest

    m = GOAL_BLOCK.search(section.rstrip())
    if not m:
        card.problems.append("GOAL section present but malformed (goal / Measured by / Rolls up to / Which serves)")
        return card

    card.goal = " ".join(m.group("goal").split())
    card.measure = " ".join(m.group("measure").split())
    card.outcome = m.group("outcome")

    if card.outcome not in OUTCOMES:
        card.problems.append(f"rolls up to outcome {card.outcome!r}, which is not one of {sorted(OUTCOMES)}")
    if len(card.goal) < 12:
        card.problems.append("goal sentence is too short to be a goal")
    if len(card.measure) < 12:
        card.problems.append("no usable measure")
    # A measure nobody can compute is prose wearing a measure's clothes.
    if not re.search(r"\d|zero|every|no |none|rising|falling|trend", card.measure, re.I):
        card.problems.append("measure contains no countable quantity")
    return card


def load_cards() -> list[Card]:
    cards = []
    for path in sorted(CARDS.glob("*.md")):
        card = parse_card(path)
        if card is not None:
            cards.append(card)
    return cards


# A ledger row: | G-Y-01 | lane | goal | owner | next | agents | status |
LEDGER_ROW = re.compile(r"^\|\s*(G-[A-Z]-\d+)\s*\|(?P<rest>.*)\|\s*$", re.MULTILINE)


def ledger_is_filled() -> bool:
    """The ultimate goal slot. Empty BY DESIGN until Andrew writes it.

    This must not be fooled by the ledger's own prose. The template explains at
    length why it is empty, and an earlier version of this check counted those
    explanations as content -- reporting the gate CLOSED while it stood wide
    open. A gate that reads its own instructions as evidence is worse than no
    gate, because it reports clean. So: only a filled TABLE ROW counts.
    """
    if not LEDGER.exists():
        return False
    for m in LEDGER_ROW.finditer(LEDGER.read_text(encoding="utf-8")):
        cells = [c.strip() for c in m.group("rest").split("|")]
        # Lane and Goal are cells 0 and 1. A goal needs at least a goal.
        if len(cells) >= 2 and cells[1]:
            return True
    return False


def audit(cards: list[Card]) -> dict:
    served: dict[str, list[str]] = {k: [] for k in OUTCOMES}
    orphans, malformed = [], []
    for c in cards:
        if not c.ok:
            malformed.append({"agent": c.name, "problems": c.problems})
            continue
        if c.outcome in served:
            served[c.outcome].append(c.name)
        else:
            orphans.append(c.name)
    unserved = [k for k, v in served.items() if not v]
    agents = [c for c in cards if c.kind == "agent"]
    protocols = [c for c in cards if c.kind == "protocol"]
    return {
        "cards": len(cards),
        "agents": len(agents),
        "protocols": len(protocols),
        "with_goal": sum(1 for c in cards if c.ok),
        "malformed": malformed,
        "orphans": orphans,
        "served": served,
        "unserved_outcomes": unserved,
        "ultimate_goal_written": ledger_is_filled(),
        "connected": not malformed and not orphans and not unserved,
    }


def report(a: dict) -> int:
    print("GOAL LADDER -- FM-35 gate")
    print("=" * 72)
    print(f"cards parsed        : {a['cards']}  ({a['agents']} agents + {a['protocols']} protocols)")
    print(f"carrying a goal     : {a['with_goal']} / {a['cards']}")
    print()
    for key, (label, _why) in OUTCOMES.items():
        names = a["served"][key]
        print(f"  outcome {key} -- {label:<34} {len(names):>2} card(s)")
    print()

    failed = False
    if a["malformed"]:
        failed = True
        print("FAIL -- cards without a usable goal:")
        for m in a["malformed"]:
            print(f"  {m['agent']}: {'; '.join(m['problems'])}")
        print()
    if a["orphans"]:
        failed = True
        print(f"FAIL -- orphan cards (goal rolls up to nothing): {', '.join(a['orphans'])}\n")
    if a["unserved_outcomes"]:
        failed = True
        print(f"FAIL -- outcomes no card serves: {', '.join(a['unserved_outcomes'])}\n")

    if not failed:
        print("PASS -- the ladder is CONNECTED: no orphan card, no unserved outcome,")
        print("        every goal carries a measure.")
        print()
        print("        Connected is not the same as correct. Whether these goals sum to")
        print("        the right summit is not checkable from inside the ladder.")
        print()

    if a["ultimate_goal_written"]:
        print("Top of the ladder : WRITTEN -- see agents/analysis/goal-ledger.md")
    else:
        print("Top of the ladder : OPEN.")
        print("  29 agent goals roll into 4 outcomes. The outcomes roll into one goal")
        print("  that is not written. No agent may author it -- that is GOALKEEPER's")
        print("  hard rule and it does not suspend itself for the goal that matters most.")
        print("  Until agents/analysis/goal-ledger.md carries it, X1 = 0 and so does Y.")
        print("  (scripts/goal_throughput.py holds the same gate.)")
        failed = True

    return 1 if failed else 0


# --------------------------------------------------------------------------
# Emitting the ladder document
# --------------------------------------------------------------------------

def emit(cards: list[Card]) -> str:
    a = audit(cards)
    L: list[str] = []
    w = L.append

    w("# THE GOAL LADDER")
    w("")
    w("Generated by [`scripts/goal_ladder.py`](../../scripts/goal_ladder.py). Do not hand-edit —")
    w("edit the `### GOAL` block on the card and regenerate. The script is also the")
    w("gate: it fails if any card is an orphan, if any outcome is unserved, or if any")
    w("goal carries no measure.")
    w("")
    w("Three levels. **You write the top one.**")
    w("")
    w("```")
    w("   LEVEL 0   the ultimate goal          <- Andrew's. Written 2026-09-15.")
    w("                    ^")
    w("   LEVEL 0.5 its three components       <- billionaire | philanthropist | Christian")
    w("                    ^")
    w("             ====== THE SEAM ======     <- agents stop here. Andrew crosses it.")
    w("                    ^")
    w("   LEVEL 1   four outcomes  A B C D     <- what the agent system can produce")
    w("                    ^")
    w(f"   LEVEL 2   {a['agents']} agent goals + {a['protocols']} protocols   <- one per card, each measured")
    w("```")
    w("")
    w("---")
    w("")
    w("## LEVEL 0 — the ultimate goal")
    w("")
    if a["ultimate_goal_written"]:
        w("> ### To become a Christian billionaire philanthropist, in U.S. dollars.")
        w("")
        w("**Written by Andrew Francisco, 2026-09-15.** Full entry, its three components and")
        w("what is still open: [`goal-ledger.md`](goal-ledger.md).")
        w("")
        w("`X1` is closed for the first time in this project's life. It had been zero since")
        w("the beginning, and while it was zero every other input was irrelevant by")
        w("construction. It is not zero now.")
        w("")
        w("### LEVEL 0.5 — it is three goals, and they do not share a clock")
        w("")
        w("| | Component | Starts | Served by |")
        w("|---|---|---|---|")
        w("| **1** | **Billionaire** — net worth >= $1,000,000,000 USD | decades; tail outcome | ASSET-LINE, CAPTABLE, and every hour that raises owned value |")
        w("| **2** | **Philanthropist** — deployed, not consumed | **today** | FIRSTFRUITS |")
        w("| **3** | **Christian** — the means, not only the ends | **every decision** | a gate over all of it; returns only *stop* |")
        w("")
        w("**Component 2 is not gated on component 1**, and a system that assumed otherwise")
        w("would record nothing against a third of the goal for twenty years. **Component 3 is")
        w("a gate, not a metric** — it cannot be optimised toward, only violated.")
        w("")
        w("---")
        w("")
        w("## ====== THE SEAM ======")
        w("")
        w("**This is the most important line in the document, so it is drawn explicitly rather")
        w("than left to be assumed.**")
        w("")
        w("The four outcomes below are what an agent system can produce: returned time,")
        w("prevented irreversible loss, detected stalls, compounding reuse. **None of them is")
        w("a billion dollars, and no sum of them becomes one.** The distance between")
        w("`A + B + C + D` and the summit is closed by owned equity that a market values —")
        w("`f · V >= $1e9` — and that is built by Andrew's decisions, not by this repository.")
        w("")
        w("```")
        w("   what agents produce        |    what closes the rest")
        w("   ------------------------- | -------------------------------")
        w("   hours returned            |    what is built in those hours")
        w("   losses that did not occur |    the position that was taken")
        w("   stalls surfaced early     |    the decision made on the signal")
        w("   work that got reused      |    the asset it compounded into")
        w("```")
        w("")
        w("An agent system that claimed to cross this seam would be claiming to make Andrew")
        w("wealthy, which it cannot do and must not imply. **What it can honestly claim is to")
        w("return the hours and protect the downside of whoever does cross it.**")
        w("")
        w("`Evidence label: Assumption` — that returned hours and prevented losses help at all")
        w("is reasoned, not measured. BASELINE and STEWARD exist to test it. Until they run, it")
        w("is an assumption, and it is labelled as one.")
    else:
        w("```")
        w("                                                                        ")
        w("        ________________________________________________________        ")
        w("                                                                        ")
        w("                            THIS SLOT IS OPEN                           ")
        w("        ________________________________________________________        ")
        w("                                                                        ")
        w("```")
        w("")
        w("**Status: OPEN.** It is open on purpose, not by oversight.")
        w("")
        w("I wrote all 31 goals below. I did not write this one and I will not. GOALKEEPER's")
        w("hard rule is that **no agent authors a goal** — and the rule does not get suspended")
        w("for the single goal that determines whether the other 31 point anywhere useful.")
        w("An agent that infers your summit from the rungs it built itself has closed a loop")
        w("with nothing outside it.")
        w("")
        w("So: the 31 goals below are mine. **The goal at the top is yours.** It goes in")
        w("[`goal-ledger.md`](goal-ledger.md), which is empty for exactly this reason.")
        w("")
        w("Until it is written, `X1 = 0`, and `Y = X1 · X3 · f(...)` = 0 — regardless of how")
        w("well-formed everything below is. A perfectly connected ladder against a wall you")
        w("did not choose still gets you onto the wrong roof.")
    w("")
    w("---")
    w("")
    w("## LEVEL 1 — the four outcomes")
    w("")
    w("Every agent goal rolls up to exactly one of these. Four, because four is the number")
    w("of distinct things this system can produce that are not restatements of each other.")
    w("")
    w("| | Outcome | Why it is its own outcome | Cards |")
    w("|---|---|---|---|")
    for key, (label, why) in OUTCOMES.items():
        w(f"| **{key}** | **{label}** | {why} | {len(a['served'][key])} |")
    w("")
    w("**A and B are in tension, and that is the design.** Every gate that protects B costs")
    w("time from A. The resolution is not balance, it is *asymmetry*: A's losses are bounded")
    w("and recurring (minutes), B's are unbounded and one-shot (a filed disclosure, a sent")
    w("email, a submitted price). You trade bounded cost for unbounded protection every time.")
    w("")
    w("### What the distribution itself says")
    w("")
    nA, nB, nC, nD = (len(a["served"][k]) for k in "ABCD")
    total = nA + nB + nC + nD
    w("```")
    for k, n in zip("ABCD", (nA, nB, nC, nD)):
        bar = "#" * n
        w(f"  {k}  {OUTCOMES[k][0]:<34} {n:>2}/{total}  {bar}")
    w("```")
    w("")
    w(f"**{nB} of {total} cards exist to stop a loss. {nD} exist to compound a gain.** That is not")
    w("an accident and it is not obviously wrong — an irreversible act has unbounded cost while")
    w("a missed compounding opportunity merely recurs — but it is worth naming plainly, because")
    w("a system built this way has a characteristic failure: **it becomes very safe and produces")
    w("very little.** Outcome D is the thinnest rung on this ladder.")
    w("")
    w("The check against that failure is not adding more D cards. It is outcome A's measure:")
    w("if review minutes are not falling, the B-weighted design is costing more than it saves,")
    w(f"and the {nB} defensive cards are a tax rather than insurance. STEWARD measures exactly that,")
    w("weekly, and it is the one number that can falsify this whole architecture.")
    w("")
    if a["ultimate_goal_written"]:
        w("### The misalignment this exposes, now that the summit is known")
        w("")
        w(f"**The summit is a pure outcome-D goal, and D is the thinnest rung: {nD} of {total} cards.**")
        w("Net worth of $1,000,000,000 is a compounding outcome — it is reached by owning")
        w("something that appreciates, never by hours accumulated. Yet this system devotes")
        w(f"{nB} cards to preventing loss and {nD} to compounding.")
        w("")
        w("**That is a real misalignment and adding cards does not fix it.** It cannot be fixed")
        w("inside this repository at all, because compounding toward the summit happens on the")
        w("far side of the seam — in what Andrew builds and owns, not in what agents produce.")
        w("The honest reading of this distribution is:")
        w("")
        w("```")
        w("  the system is correctly shaped to PROTECT a billion-dollar outcome")
        w("  the system is NOT shaped to PRODUCE one, and cannot be")
        w("```")
        w("")
        w("Which is the right division of labour, provided it is stated. **Stated, it is a")
        w("design. Unstated, it is a system that looks like progress while producing none.**")
        w("")
    w("---")
    w("")

    for key, (label, _why) in OUTCOMES.items():
        names = a["served"][key]
        w(f"## LEVEL 2 — outcome {key}: {label}  ({len(names)} cards)")
        w("")
        w("| Card | Its goal | Measured by |")
        w("|---|---|---|")
        for n in names:
            c = next(c for c in cards if c.name == n)
            tag = " *(protocol)*" if c.kind == "protocol" else ""
            w(f"| **{n.upper()}**{tag} | {c.goal} | {c.measure} |")
        w("")

    w("---")
    w("")
    w("## What this ladder does NOT establish")
    w("")
    w("```")
    w("CHECKED    every card has a goal          CHECKED    every goal has a measure")
    w("CHECKED    every goal names an outcome    CHECKED    every outcome has cards under it")
    w("")
    w("NOT CHECKED  that these goals, achieved, produce the outcome above them")
    w("NOT CHECKED  that the four outcomes, achieved, produce the goal above them")
    w("NOT CHECKED  that any of it is the right thing to want")
    w("```")
    w("")
    w("The first two are empirical and need outcome data across completed periods. There is")
    w("none, so no number is offered for either. The third is not an empirical question at")
    w("all — it is yours, and it is answered by writing Level 0.")
    w("")
    w("**Evidence labels.** The goals and their measures: `Stated` — mine, by design, derived")
    w("from each card's existing contract. The connectivity audit above: `Repo-Verified` —")
    w("this script, run against the cards. The claim that achieving these goals produces the")
    w("summit: `Unverified`, and it stays that way until there are completed periods to measure.")
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------
# Self-tests
# --------------------------------------------------------------------------

def selftest() -> int:
    import tempfile
    passed = failed = 0

    def check(name, cond):
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")

    def card_text(goal="Do the one thing well.",
                  measure="Zero escapes across 10 runs.",
                  outcome="B", complete=True):
        block = f"### GOAL\n**{goal}**\n\n- **Measured by:** {measure}\n"
        if complete:
            block += (f"- **Rolls up to:** outcome {outcome} — label\n"
                      "- **Which serves:** the goal Andrew writes.\n")
        return "# TEST — agent card\n\n" + block + "\n### INPUTS\nnothing\n"

    with tempfile.TemporaryDirectory() as d:
        def write(name, text):
            p = Path(d) / f"{name}.md"
            p.write_text(text, encoding="utf-8")
            return p

        c = parse_card(write("good", card_text()))
        check("well-formed card parses", c is not None and c.ok)
        check("goal captured", c.goal == "Do the one thing well.")
        check("outcome captured", c.outcome == "B")

        c = parse_card(write("nogoal", "# X — agent card\n\n### INPUTS\nnothing\n"))
        check("missing GOAL fails", not c.ok and "no ### GOAL section" in c.problems[0])

        c = parse_card(write("partial", card_text(complete=False)))
        check("truncated GOAL block fails", not c.ok)

        c = parse_card(write("badout", card_text(outcome="Z")))
        check("a fifth outcome is rejected", not c.ok)

        c = parse_card(write("vague", card_text(measure="It should generally feel better.")))
        check("uncountable measure is rejected", not c.ok)

        c = parse_card(write("short", card_text(goal="Win.")))
        check("goal too short is rejected", not c.ok)

        check("README is not a card", parse_card(write("README", "# index\n")) is None)

        # A protocol card is still a card and still needs a goal.
        c = parse_card(write("baseline", card_text()))
        check("protocol classified as protocol", c.kind == "protocol")

        # Audit-level failures.
        cards = [Card("a", "g" * 20, "zero defects", "A"), Card("b", "g" * 20, "zero defects", "A")]
        res = audit(cards)
        check("unserved outcomes are reported", set(res["unserved_outcomes"]) == {"B", "C", "D"})
        check("unserved ladder is not connected", res["connected"] is False)

        cards = [Card(k.lower(), "g" * 20, "zero defects", k) for k in OUTCOMES]
        res = audit(cards)
        check("fully served ladder is connected", res["connected"] is True)

        cards.append(Card("broken", problems=["no ### GOAL section"]))
        res = audit(cards)
        check("a malformed card breaks connectivity", res["connected"] is False)

    # REGRESSION (E-02, this session): the first ledger check counted the
    # ledger's own explanatory prose as content and reported the X1 gate CLOSED
    # while it was open. Only a filled table ROW may count.
    with tempfile.TemporaryDirectory() as d:
        led = Path(d) / "goal-ledger.md"
        global LEDGER
        _saved = LEDGER
        try:
            LEDGER = led

            led.write_text("# GOAL LEDGER\n\nIt cannot make you accomplish your goals.\n"
                           "Everything else is yours.\n\n| ID | Lane | Goal | Owner |\n"
                           "|---|---|---|---|\n| G-Y-01 |  |  |  |\n", encoding="utf-8")
            check("ledger prose does not count as a written goal", ledger_is_filled() is False)

            led.write_text("| G-Y-01 |  |  |  |\n| G-Q-01 |  |  |  |\n", encoding="utf-8")
            check("empty template rows do not count", ledger_is_filled() is False)

            led.write_text("| G-Y-01 | ABO | Win one prime award by 2027-06-30. | Andrew |\n",
                           encoding="utf-8")
            check("one filled row does count", ledger_is_filled() is True)

            led.unlink()
            check("a missing ledger is not filled", ledger_is_filled() is False)
        finally:
            LEDGER = _saved

    # Was: "the live ledger is still open". Andrew wrote the summit on 2026-09-15,
    # so this now guards the opposite direction -- that the summit is not silently
    # lost by an edit or a bad merge, which would reopen X1 without anyone noticing.
    check("the live ledger carries the summit (X1 = 1)", ledger_is_filled() is True)

    # The real repository must pass its own gate on connectivity.
    real = load_cards()
    res = audit(real)
    check("every real card carries a goal", res["with_goal"] == res["cards"])
    check("no real orphans", not res["orphans"])
    check("every outcome is served by a real card", not res["unserved_outcomes"])
    check("the four outcomes are exactly four", len(OUTCOMES) == 4)
    # The refusal is load-bearing and must NOT go slack now that the slot is filled.
    # Point the script at an empty ledger and confirm it still refuses to invent a
    # summit from the 34 goals beneath it -- the case it will face again on any new
    # repository, and the one a "goal written" short-circuit would quietly break.
    with tempfile.TemporaryDirectory() as d:
        led = Path(d) / "goal-ledger.md"
        led.write_text("# GOAL LEDGER\n\n| G-Y-01 |  |  |  |\n", encoding="utf-8")
        _saved = LEDGER
        try:
            LEDGER = led
            out = emit(real)
            check("with an empty ledger, emit() still refuses to invent a summit",
                  "THIS SLOT IS OPEN" in out)
            check("the refusal names whose job it is",
                  "no agent authors a goal" in out)
        finally:
            LEDGER = _saved

    # And with the real ledger, the summit is rendered rather than synthesised:
    # it must appear together with its attribution, never as a bare assertion.
    out = emit(real)
    check("the written summit is rendered with its author",
          "Written by Andrew Francisco" in out)
    check("the seam between agent outcomes and the summit is drawn",
          "THE SEAM" in out)
    check("no probability is emitted anywhere in the ladder",
          not re.search(r"\b\d{1,3}(\.\d+)?%\s*(chance|probability|likelihood)", out, re.I))

    total = passed + failed
    print(f"goal_ladder: {passed}/{total} passed")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="FM-35 gate: every agent traces to a goal.")
    ap.add_argument("--emit", action="store_true", help="regenerate agents/analysis/goal-ladder.md")
    ap.add_argument("--json", action="store_true", help="machine-readable audit")
    # The repository convention is --self-test; --selftest stays as an alias.
    ap.add_argument("--self-test", "--selftest", dest="self_test",
                    action="store_true", help="run self-tests")
    ap.add_argument(
        "--gate", action="store_true",
        help="connectivity only, quiet on success: for the pre-commit hook. "
             "Deliberately IGNORES whether the ultimate goal is written -- that "
             "slot is Andrew's and blocking every commit on it would only teach "
             "him to pass --no-verify, which would also disable the redaction guard.",
    )
    args = ap.parse_args()

    if args.self_test:
        return selftest()

    cards = load_cards()
    if args.emit:
        LADDER.write_text(emit(cards), encoding="utf-8")
        print(f"wrote {LADDER.relative_to(REPO)}")
        return 0
    a = audit(cards)
    if args.json:
        print(json.dumps(a, indent=2, sort_keys=True))
        return 0 if a["connected"] else 1
    if args.gate:
        if a["connected"]:
            return 0
        print("COMMIT BLOCKED -- FM-35: an agent card traces to no goal.", file=sys.stderr)
        for m in a["malformed"]:
            print(f"  {m['agent']}: {'; '.join(m['problems'])}", file=sys.stderr)
        for o in a["orphans"]:
            print(f"  {o}: rolls up to no declared outcome", file=sys.stderr)
        for u in a["unserved_outcomes"]:
            print(f"  outcome {u} ({OUTCOMES[u][0]}): no card serves it", file=sys.stderr)
        print("\nFix the card's ### GOAL block, then re-run:", file=sys.stderr)
        print("  python3 scripts/goal_ladder.py --emit", file=sys.stderr)
        return 1
    return report(a)


if __name__ == "__main__":
    try:
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError):
        pass
    sys.exit(main())
