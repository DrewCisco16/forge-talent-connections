# 20 — FMEA · FTA · FMEDA

**Question asked:** are 25 agents too many, too few, or right — and will everything
that needs to be done actually get done?

**Answer, up front:** **25 is right. A 26th agent would not close a single open
failure path.** The four highest-ranked unprotected risks in this system cannot be
closed by any agent — they are closed by four human acts. Two of the 25 exist only
as cards and need to be *built*, not re-specified.

Register: [`analysis/failure-register.json`](analysis/failure-register.json) ·
Calculator: [`../scripts/fmeda_coverage.py`](../scripts/fmeda_coverage.py)
(re-run it; the numbers move with the register)

---

## 0. What each method can honestly do here

| Method | Needs | Status |
|---|---|---|
| **FMEA** | Ordinal severity / occurrence / detection ranks | **Done in full.** 32 modes |
| **FTA** | System structure and logic | **Done in full.** Minimal cut sets below — this is where the real finding is |
| **FMEDA** | **A failure rate (λ, in FIT) per component**, from field data or a reliability handbook | **Cannot be done. Half of it is done and labelled as half** |

**On FMEDA, plainly.** A real FMEDA per IEC 61508 assigns λ to every component,
classifies each mode safe/dangerous × detected/undetected, and computes **Safe
Failure Fraction** and **PFH** to verify a SIL. **There is no failure-rate data
for LLM agents** — not in this repository, and not in any source reachable from
this session. **Any λ I wrote would be invented, so I wrote none, and there is no
SFF and no PFH in this document.**

What *is* computed is FMEDA's structural half: the safe/dangerous ×
detected/undetected classification, and **diagnostic coverage as a count over the
register** — which is a real measurement, because the register is a real dataset
and the arithmetic is shown.

**On RPN, plainly.** S, O and D are **ordinal judgement scales, not
probabilities.** Their product has no units. RPN is used here **only to sort**,
which is the one thing it can honestly do. Two modes with equal RPN are not
equally risky, and a 450 is not "three times" a 150.

---

## 1. FMEA — the top of the ranking

Full table: `python3 scripts/fmeda_coverage.py`. The head of it:

| Rank | ID | Mode | S | O | D | RPN | Control rung |
|---|---|---|---|---|---|---|---|
| 1 | **FM-06** | FIU AI-use policy violated because nobody checked it | 10 | 5 | 9 | **450** | **PROSE** |
| 2 | **FM-31** | Cloudflare Pages serves repo markdown as web pages | 8 | 6 | 8 | **384** | **PROSE** |
| 3 | **FM-12** | REVIEWER goes blind and reports clean | 7 | 6 | 9 | **378** | TEST |
| 4 | **FM-09** | An agent claims work it did not do | 8 | 7 | 6 | **336** | TEST |
| 5 | **FM-04** | Unfiled invention disclosure committed to a public repo | 10 | 4 | 8 | **320** | **PROSE** |
| 6 | FM-10 | Evidence label silently upgraded across a handoff | 8 | 6 | 6 | 288 | TEST |
| 7 | FM-21 | J4V client data processed against unread contract terms | 8 | 5 | 7 | **280** | **PROSE** |

**Read the detection column, not the severity column.** The gated modes — PII,
keys, CUI, runaway loops, weakened tests, stale price ceilings — have fallen to
the *bottom* of this ranking, not because their consequences shrank but because
**D dropped when a gate replaced a rule.** That is the entire mechanism by which
this ranking improves.

---

## 2. FTA — minimal cut sets

### Top event TE-1: irreversible harm to Andrew's interests

```
                      TE-1  IRREVERSIBLE HARM
                               [ OR ]
      ┌─────────────┬────────────┴──────────┬──────────────────┐
   G1 DISCLOSURE  G2 EXTERNAL COMMITMENT  G3 INTEGRITY      G4 LEGAL
     [ OR ]           [ OR ]                [ OR ]           [ OR ]
      │                │                     │                │
  FM-01 PII x GUARD   FM-14 email sent      FM-05 citation   FM-20 ABO
  FM-03 CUI x GUARD   (x no-send scope)      x GATE           x GATE
  FM-04 PATENT ───┐   submission to portal  FM-06 FIU ─────┐ FM-21 J4V ──┐
  FM-31 PAGES ────┤   USPTO filing          POLICY         │  TERMS      │
                  │   money movement                       │             │
                  └──────── ORDER-1 CUT SETS ──────────────┴─────────────┘
```

**Minimal cut sets of order 1 — a single failure is sufficient:**

| Cut set | Why it stands alone | Rung |
|---|---|---|
| **{FM-06}** FIU policy | One violation, one integrity finding. Nothing else must also fail | **PROSE** |
| **{FM-04}** patent disclosure | One commit to a public repo. The right dies | **PROSE** |
| **{FM-31}** Pages serving docs | If true, *every* document commit is already a publication | **PROSE** |
| **{FM-21}** J4V terms | One processing act against unread terms | **PROSE** |

**Every order-1 cut set in this system sits on prose. That is the finding.**

**Cut sets raised to order 2 by a gate** — two things must now fail together:

| Cut set | Gate that raised it |
|---|---|
| {FM-01, redaction_guard bypassed or blind} | `redaction_guard.py`, 35 tests, denial live-tested |
| {FM-03, redaction_guard bypassed or blind} | same |
| {FM-05, citation_gate bypassed} | `citation_gate.py`, fail closed |
| {FM-20, loop_guard bypassed} | `counsel_cleared: false` refusal |
| {FM-14, send tool granted} | no send tool in MAILROOM's scope |

> **This is what a gate buys, stated precisely: it does not reduce severity. It
> raises the order of the cut set.** Before the redaction guard, one tired
> mistake published third-party PII — order 1. It now takes a mistake *and* a
> gap in the guard — order 2. That is the whole argument for moving rules from
> prose to code, and it is measurable rather than rhetorical.

**One compound path deserves naming.** **FM-31 × FM-04**: if Pages serves the
repository's markdown, then the redaction guard is the *only* barrier between a
document and the open web — and the guard **cannot detect an invention
disclosure**, because "this paragraph describes an unfiled invention" has no
pattern. FM-31 does not merely add risk; **it amplifies FM-04 from a repository
problem into a publication problem.**

### Top event TE-2: the system delivers no value

```
              TE-2  NO VALUE DELIVERED
                       [ OR ]
   ┌────────────┬──────────┴─────┬──────────────┐
FM-24          FM-25          FM-26          FM-27
never started  review minutes  no baseline    too many at once
[ORDER-1,      rise            (cannot tell   (nothing
 O = 9]                         success)       attributable)
```

**{FM-24} is an order-1 cut set with the highest occurrence rank in the entire
register (O = 9).** The single likeliest way this system fails is not a bad
agent. It is that **no agent is ever run.** `START-HERE.md`, `STATE.md` and the
2026-10-14 kill date exist against exactly this cut set.

---

## 3. FMEDA-adapted — computed, with the arithmetic shown

```
total failure modes ....... 32
  dangerous ............... 24        safe .................... 8
  dangerous DETECTED ...... 17        dangerous UNDETECTED .... 7

Diagnostic coverage (structural):
  DC = DD / (DD + DU) = 17 / (17 + 7) = 17/24 = 0.708

Coverage by CODE rather than by human memory:
  gated_dangerous / dangerous = 9 / 24 = 0.375
  gated_all / all             = 10 / 32 = 0.312

Rung distribution:
  rung 1  GATE  (blocks, tested) .... 10/32   31.2%
  rung 2  TEST  (declared, unrun) ... 16/32   50.0%
  rung 3  PROSE (human memory) ......  6/32   18.8%
```

**How to read 0.708 honestly.** It means 17 of 24 dangerous failure modes have
*some* detection behind them. It does **not** mean a 70.8% chance of catching a
failure — that would require the λ data this document does not have. **And the
harder number is 0.375:** only nine of twenty-four dangerous modes are caught by
code rather than by someone remembering.

**The seven undetected dangerous modes, in rank order — this is the work queue:**

| ID | RPN | Mode | What closes it |
|---|---|---|---|
| FM-06 | 450 | FIU AI-use policy unchecked | **Ask your program. Not an agent** |
| FM-31 | 384 | Pages may serve the docs | **Open one URL. Not an agent** |
| FM-12 | 378 | REVIEWER goes blind | **Build CANARY's seeded-defect probe** |
| FM-09 | 336 | Agent claims work it did not do | **Build ATTESTOR's artifact check** |
| FM-04 | 320 | Invention disclosure published | **A private repository. Not an agent** |
| FM-21 | 280 | J4V terms unread | **Read the 1099 agreement. Not an agent** |
| FM-23 | 210 | SCOUT silently returns zero | **Implement the FILL-IN refusal** |

---

## 4. Is 25 the right number?

### The count, by role

| Role | n | Agents |
|---|---|---|
| **Control / assurance** | 8 | ROUTER · REVIEWER · ATTESTOR · CANARY · REDACTOR · BASELINE · STEWARD · SENTINEL |
| **Production** | 14 | BRIEFER · MAILROOM · SCOUT · CAPTURE · MATRIX · LIBRARIAN · TRACKER · PRIORART · BUILDER · SYNTH-QA · DILIGENCE · HARVESTER · ORCHESTRATOR · NIGHTWATCH |
| **Infrastructure** | 3 | SMOKE · PARKING · OPTIMIZER |

### The argument

**Every production agent added imports the same four shared failure modes** —
FM-09 (false claim), FM-10 (label drift), FM-11 (invented number), FM-13
(injection). They are not independent risks per agent; they are one risk surface
that every new agent widens.

**Control agents do not widen it. They detect on it.** One ATTESTOR covers FM-09
for all fourteen production agents. One CANARY covers FM-12 and FM-13 for all of
them. **That is why the control:production ratio matters more than the total.**

**8 : 14 is defensible.** Drop below roughly one control agent per two production
agents and the shared surface outruns detection.

### Verdict

| Question | Answer |
|---|---|
| **Too many?** | **No — to specify.** A card is a contract, not a process; 25 cards cost nothing to hold. **Yes — to deploy.** Zero are running; deploying more than one at a time is FM-27 |
| **Too few?** | **No.** I looked for a 26th and could not find one that closes an open cut set. **Four of the seven undetected dangerous modes are not agent-shaped at all** |
| **Any to remove?** | **None.** Two are already correctly deferred: ORCHESTRATOR (the Playbook says the swarm is not the pilot) and NIGHTWATCH (demoted to a calibration instrument by your own `one_model.py` finding) |
| **Will everything get done?** | **Not on the current trajectory.** FM-24 — never started, O = 9 — is the dominant path, and no amount of further specification touches it |

### The honest shape of the answer

> **You do not have an agent-count problem. You have two build items
> (ATTESTOR, CANARY), four human acts (FIU, Pages, private repo, J4V terms), and
> one start (BRIEFER).** Adding a twenty-sixth agent would move none of those.

---

## 5. Literature — a verification queue, not a bibliography

**Every scholarly host was blocked from this session:** `api.crossref.org` (403
through the proxy), `pubmed.ncbi.nlm.nih.gov`, `arxiv.org`,
`journals.sagepub.com`, `neurips.cc` — all `EGRESS_BLOCKED`.

**So there are no verified citations in this document, and I will not write one
from memory.** What follows is a **verification queue**: candidates seen only in
search-result snippets, with exactly what was seen, for you to run through the
gate you already own.

> **Run them through your own gate before any of this enters a dissertation, a
> proposal, or a decision:**
> `.claude/agents/citation-verifier.md` · `adjudication/citation_gate.py` ·
> `adjudication/doi_resolver.py`

| # | Candidate | What the snippet claimed | Label |
|---|---|---|---|
| **L1** | Cemri, Pan, Yang et al., *"Why Do Multi-Agent LLM Systems Fail?"*, arXiv:2503.13657; NeurIPS 2025 poster | MAST taxonomy; 1,600+ annotated traces across 7 MAS frameworks; 150 traces for taxonomy development; inter-annotator κ = 0.88; **14 failure modes in 3 categories**; MAS failure rates **41%–86.7%**; gains often minimal vs. single-agent | **Unverified — snippet only. Verify every number** |
| **L2** | Onnasch, Wickens, Li & Manzey (2014), *Human Factors* 56(3), 476–488; DOI 10.1177/0018720813501549; PMID 24930170 | Meta-analysis of **18 experiments**; higher degree of automation improves **routine** performance but degrades **failure-mode** performance and situation awareness | **Unverified — snippet only** |
| **L3** | IEC 61508 FMEDA practice (vendor FMEDA reports; Emerson, Pepperl+Fuchs, Yokogawa, Turck) | FMEDA assigns a failure rate per component and classifies safe/dangerous × detected/undetected to compute SFF and PFH | **Unverified — snippet only.** Used only to justify §0's refusal to produce SFF/PFH |

**If L1 and L2 verify, they converge with something already measured inside your
own repository**, which is worth more than either alone:

- `adjudication/one_model.py` (**Repo-Verified**): Stage 0 baselines **0.968** and
  **1.000** against a 0.45 threshold → *"DO NOT BUILD THE ENSEMBLE."*
- `adjudication/accuracy.py` (**Repo-Verified**): SOP 7.1 — *"overall mean
  multi-agent improvement across six benchmarks was 0.0%."*

Three independent lines — your Stage 0 measurement, your SOP's benchmark note,
and (if it verifies) L1's failure-rate range — point the same way: **more agents
in a chain is not more capability. It is more failure surface.** That is the
strongest available support for the §4 verdict, and it is **the reason the
control:production ratio, not the headcount, is the number to manage.**

**What I could not do:** produce the "as many scholarly articles with empirical
data as possible" you asked for. The network in this session does not permit it.
Three candidates, honestly labelled, beat twenty citations I cannot stand behind.
