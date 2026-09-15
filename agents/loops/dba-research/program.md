# PROGRAM — DBA falsification loop

**Lane:** `DBA` · **Type:** falsification (hybrid) · **Node:** HP Envy 17
**Prepend:** `../_LOOP-PREAMBLE.md`

---

## Why this is not an optimization loop

There is no code-computable score for argument quality. Inventing one would be
inventing a number, which the truth standard forbids outright.

**So this loop does not climb a score. It kills claims that cannot survive.**

## Objective

Take the claim set from the current draft. Attack each claim. Record what dies
and what killed it. **Stop when a full round produces no new kills.**

```
STOPPING CONDITION: one complete round, zero new kills.
NOT: "it reads well now."
```

## Use the engine you already own

`adjudication/` is a five-seat blinded elimination engine with claim gates, a cost
ceiling and a refuse path. `night_loop.py` is its unattended round shape.
**This loop dispatches into that engine. It does not reimplement it.**

Mechanical gates run **before** any model judgment — the ordering is the safety
property, stated in `night_loop.py`'s own docstring:

```
1. citation_gate.py   — DOI resolves AND the resolved record matches the citation
2. quote_gate.py      — quoted text appears in the source as quoted
3. retraction check   — nothing retracted survives
4. ONLY THEN          — the five-seat attack on what is left
```

## Diagnostics — not objectives

```
open_holes_count            → must reach 0 before a chapter goes to your chair
unresolved_citations_count  → must reach 0, always
contradicted_claims_count   → reported, never minimized
```

**These are never optimized toward.** The loop may not close a hole by deciding it
does not matter, and may not reduce `contradicted_claims_count` by dropping the
contradiction. A hole is closed by evidence or it stays open.

## What you may never do

❌ **Write dissertation prose.** Not a paragraph, not a "draft to edit". The
   argument is Andrew's — this is the academic integrity boundary
❌ Present a citation that did not pass the gates, with or without a caveat
❌ Choose the theoretical frame or interpret the data
❌ Reduce a diagnostic by weakening the claim instead of supporting it
❌ Touch `ABO`, `FORGE`, `J4V` or `HOME` data. **Absolute** — organizational or
   client data in doctoral research raises IRB, confidentiality and contractual
   questions simultaneously (`10` A6)

## Output per round

```
SURVIVED (n)   · <claim> — <attacks it withstood>
KILLED (n)     · <claim> — <the specific thing that killed it>
OPEN HOLES (n) · <hole> — <what evidence would close it>
NEW CONTRADICTIONS (n)  ← always reported first; never buried
```

## Stopping and cost

```
MAX_ROUNDS: <FILL-IN>        MAX_SPEND_USD: <FILL-IN>
```

The five-seat engine is **manual and cost-ceilinged by design** — Repo-Verified,
`adjudicate.yml`: *"A run is something a person decided to start, at a moment they
chose, with a ceiling they set."* **This loop inherits that. Do not schedule it
against the paid vendor path.**
