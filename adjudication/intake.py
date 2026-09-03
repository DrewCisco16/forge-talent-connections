"""
intake.py
=========
Turns a problem into the three things the engine needs: an artifact, competing
candidates, and claims carrying mechanically checkable warrants.

This is the layer the tool was missing. The engine has always been sound; the
friction was that a real question -- "should we raise placement fees?" -- is
not an artifact with candidates, and writing candidates.json by hand, with
warrants in the exact form "<expression> = <result>", is the part nobody wants
to do at 11pm.

TWO REFUSALS THAT ARE NOT SKIPPABLE.

  No disproof test  ->  stop. A question nobody can be wrong about cannot be
                        eliminated against. It produces five essays and a bill.
  One candidate     ->  stop. One candidate is a thesis looking for support.
                        Elimination needs something to eliminate.

Both refusals happen before a single token is spent, which is the only place
they are worth anything.

NEVER INVENTS A WARRANT. If the operator cannot say where a number came from,
the claim is recorded as judgment and says so. A fabricated expression that
happens to evaluate true manufactures an EARNED kill -- a false verification
written into a hash-chained record that may later be cited as evidence. That
is worse than no claim at all.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

from domains import ALL, Domain

RUNS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs")


# ---------------------------------------------------------------------------
# small console helpers
# ---------------------------------------------------------------------------

def _p(s: str = "") -> None:
    print(s)


def ask(prompt: str, allow_blank: bool = False) -> str:
    while True:
        v = input(f"{prompt} ").strip()
        if v or allow_blank:
            return v
        _p("  (needed)")


def ask_yes(prompt: str) -> bool:
    return input(f"{prompt} [y/N] ").strip().lower() in ("y", "yes")


def ask_multiline(prompt: str) -> str:
    _p(prompt)
    _p("  (paste as much as you like; a single line containing only END finishes)")
    lines: list[str] = []
    while True:
        try:
            ln = input()
        except EOFError:
            break
        if ln.strip() == "END":
            break
        lines.append(ln)
    return "\n".join(lines).strip()


def slugify(s: str, n: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return (s[:n] or "run").rstrip("-")


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------

def choose_domain() -> Domain:
    _p("What kind of problem is this?")
    _p()
    for i, d in enumerate(ALL, 1):
        _p(f"  {i}  {d.title}")
        _p(f"     {d.blurb}")
    _p()
    while True:
        raw = ask(f"Choose 1-{len(ALL)}:")
        if raw.isdigit() and 1 <= int(raw) <= len(ALL):
            return ALL[int(raw) - 1]
        _p("  not a choice")


def red_gate(d: Domain) -> bool:
    """Returns True if it is safe to proceed. Refuses rather than redacts."""
    if not d.red_gate:
        return True
    _p()
    _p("=" * 68)
    _p("  CONFIDENTIALITY CHECK")
    _p("=" * 68)
    _p(d.red_prompt)
    _p()
    if not ask_yes("Is EVERY word of your artifact already published?"):
        _p()
        _p("  Stopped. That material is out of scope for this tool, because the")
        _p("  tool sends it to five outside vendors.")
        _p("  Use a channel that does not call external providers.")
        return False
    return True


def disproof_test() -> str | None:
    _p()
    _p("-" * 68)
    _p("  THE QUESTION THAT DECIDES WHETHER THIS RUN IS WORTH PAYING FOR")
    _p("-" * 68)
    _p("  What evidence would prove a candidate WRONG?")
    _p("  A recomputed total, a DOI that does not resolve, a test that fails.")
    _p()
    v = ask("Disproof test (or 'none'):")
    if v.lower() in ("none", "n", "-", "idk", "i dont know", "i don't know"):
        _p()
        _p("  Stopped, and nothing was spent.")
        _p("  A question nobody can be wrong about cannot be eliminated against.")
        _p("  It produces five essays. Come back when there is something checkable.")
        return None
    return v


def collect_artifact(d: Domain) -> str:
    _p()
    _p("-" * 68)
    _p("  THE ARTIFACT -- the thing the five seats will examine")
    _p("-" * 68)
    _p(f"  {d.artifact_is}")
    _p("  For example:")
    for ex in d.artifact_examples:
        _p(f"    - {ex}")
    _p()
    if ask_yes("Is it already in a file?"):
        while True:
            path = ask("Path:")
            path = os.path.expanduser(path)
            if os.path.isfile(path):
                with open(path, encoding="utf-8", errors="replace") as fh:
                    return fh.read()
            _p("  no file there")
    return ask_multiline("Paste the artifact:")


def collect_claims(d: Domain, cand_id: str) -> list[dict[str, Any]]:
    """One candidate's claims. Warrants are asked for, never invented."""
    claims: list[dict[str, Any]] = []
    _p(f"  Claims for {cand_id}. What does this position STAND ON?")
    _p(f"  (this domain leans on: {', '.join(d.primary_claim_kinds)})")
    while True:
        text = ask("    Claim (blank to finish):", allow_blank=True)
        if not text:
            break
        _p("      1 arithmetic   2 unit   3 citation   4 code_behavior   5 judgment")
        k = ask("      Kind 1-5:")
        kind = {"1": "arithmetic", "2": "unit", "3": "citation",
                "4": "code_behavior", "5": "judgment"}.get(k, "judgment")

        warrant = None
        if kind == "arithmetic":
            _p("      The expression that produces the number, and the number itself.")
            _p("      Example: expression '3 * 18500'   result '55500'")
            expr = ask("      Expression (blank if you cannot derive it):", allow_blank=True)
            if expr:
                res = ask("      Result it should equal:")
                warrant = f"{expr} = {res}"
            else:
                _p("      -> recorded as JUDGMENT. A number with no derivation is")
                _p("         an opinion, and inventing an expression for it would")
                _p("         manufacture a false verification.")
                kind = "judgment"
        elif kind == "unit":
            _p("      Example: '5 km = 5000 m'")
            warrant = ask("      Conversion:") or None
            if not warrant:
                kind = "judgment"
        elif kind == "citation":
            _p("      A DOI resolves and is field-matched. A bare title does not.")
            warrant = ask("      DOI or https URL (blank -> judgment):", allow_blank=True) or None
            if not warrant:
                kind = "judgment"
        elif kind == "code_behavior":
            _p("      A command YOU wrote and approved. Never one a model suggested.")
            warrant = ask("      Command (blank -> judgment):", allow_blank=True) or None
            if not warrant:
                kind = "judgment"

        claims.append({"kind": kind, "text": text,
                       **({"warrant": warrant} if warrant else {})})
        tag = "judgment (escalates to you)" if kind == "judgment" else kind
        _p(f"      recorded as {tag}")
    return claims


def collect_candidates(d: Domain) -> list[dict[str, Any]] | None:
    _p()
    _p("-" * 68)
    _p("  CANDIDATES -- the competing answers, 2 to 5")
    _p("-" * 68)
    _p(f"  {d.candidate_is}")
    _p("  For example:")
    for ex in d.candidate_examples:
        _p(f"    - {ex}")
    _p()
    cands: list[dict[str, Any]] = []
    while len(cands) < 5:
        n = len(cands) + 1
        content = ask(f"  Candidate {n} (blank to finish):", allow_blank=True)
        if not content:
            break
        cid = ask(f"    Short id [c{n}]:", allow_blank=True) or f"c{n}"
        cands.append({"id": slugify(cid, 24), "content": content,
                      "claims": collect_claims(d, cid)})
    if len(cands) < 2:
        _p()
        _p("  Stopped, and nothing was spent.")
        _p("  One candidate is a thesis looking for support. Elimination needs")
        _p("  something to eliminate. Come back with at least two.")
        return None
    return cands


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def run_intake() -> dict[str, Any] | None:
    """Walks the operator through formulation. Returns a run spec, or None."""
    _p()
    _p("=" * 68)
    _p("  NEW PROBLEM")
    _p("=" * 68)
    _p()
    d = choose_domain()
    if not red_gate(d):
        return None

    _p()
    question = ask("In one sentence, what are you deciding?")

    dis = disproof_test()
    if dis is None:
        return None

    prior = ask("What do you currently believe the answer is? (recorded, not sent):",
                allow_blank=True)
    extra: list[tuple[str, str]] = []
    for q in d.extra_questions:
        extra.append((q, ask(f"{q}", allow_blank=True)))

    artifact = collect_artifact(d)
    if not artifact.strip():
        _p("  Empty artifact. Stopped.")
        return None

    cands = collect_candidates(d)
    if cands is None:
        return None

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = f"{stamp}-{slugify(question)}"
    run_dir = os.path.join(RUNS_DIR, slug)
    if os.path.exists(run_dir):
        _p(f"  {run_dir} already exists. Append-only means append-only. Stopped.")
        return None
    os.makedirs(run_dir)

    art_path = os.path.join(run_dir, "artifact.txt")
    cand_path = os.path.join(run_dir, "candidates.json")
    with open(art_path, "w", encoding="utf-8") as fh:
        fh.write(artifact.rstrip() + "\n")
    with open(cand_path, "w", encoding="utf-8") as fh:
        json.dump(cands, fh, indent=2)

    # PROBLEM.md is not sent to any seat. It records what the operator believed
    # going in, so the run can be checked against the prior instead of quietly
    # confirming it.
    with open(os.path.join(run_dir, "PROBLEM.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# {question}\n\n")
        fh.write(f"- Domain: {d.title}\n- Formulated: {stamp}\n\n")
        fh.write(f"## Disproof test\n{dis}\n\n")
        if prior:
            fh.write(f"## Prior belief (not sent to any seat)\n{prior}\n\n")
        for q, a in extra:
            if a:
                fh.write(f"## {q}\n{a}\n\n")
        fh.write("## Candidates\n")
        for c in cands:
            fh.write(f"- **{c['id']}** — {c['content']}\n")
            for cl in c["claims"]:
                w = cl.get("warrant", "(no warrant — escalates)")
                fh.write(f"    - [{cl['kind']}] {cl['text']}  `{w}`\n")

    # what the operator is actually about to buy
    total = sum(len(c["claims"]) for c in cands)
    gateable = sum(1 for c in cands for cl in c["claims"]
                   if cl["kind"] != "judgment" and cl.get("warrant"))
    _p()
    _p("=" * 68)
    _p("  READY")
    _p("=" * 68)
    _p(f"  folder      : runs/{slug}")
    _p(f"  candidates  : {len(cands)}")
    _p(f"  claims      : {total}  ({gateable} checkable, "
       f"{total - gateable} will escalate to you)")
    if gateable == 0:
        _p()
        _p("  WARNING: not one claim can be checked mechanically.")
        _p("  Five seats will discuss it and nothing will be refuted. That is a")
        _p("  consensus run. Consider adding derivations before you spend.")
    _p()
    return {"run_dir": run_dir, "artifact": art_path, "candidates": cand_path,
            "domain": d.key, "gates": ",".join(d.gates),
            "resolve_dois": d.resolve_dois, "slug": slug, "gateable": gateable}


if __name__ == "__main__":  # pragma: no cover
    spec = run_intake()
    print(json.dumps(spec, indent=2) if spec else "no run created")
