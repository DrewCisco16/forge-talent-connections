# 11 — AUTORESEARCH LOOPS

Four lane-scoped autonomous research loops. What a Karpathy loop actually is,
which of your four lanes can support a real one, and which must be hybrids.

**Version 1.0 · 2026-09-14**

---

## 1. What AutoResearch actually is

**Docs-Verified** — retrieved from the primary source, `github.com/karpathy/autoresearch`,
2026-09-14:

| Element | Verbatim from the repository |
|---|---|
| **The loop** | The agent iteratively modifies `train.py`, trains for exactly 5 minutes, evaluates the result, then **retains or discards** the change, and repeats |
| **The file agents edit** | `train.py` — "the sole file agents modify", containing architecture, optimizer, and training loop |
| **The file humans edit** | `program.md` — "baseline instructions for one agent", "intentionally kept as a bare bones baseline" |
| **The metric** | `val_bpb` — validation bits per byte. "lower is better, and vocab-size-independent so architectural changes are fairly compared" |
| **The agent** | "Claude/Codex or whatever you want" — the loop is agent-agnostic |
| **The compute** | A single NVIDIA GPU, tested on an H100. Python 3.10+ |
| **The budget** | 5 minutes "wall clock, excluding startup/compilation" |
| **Stated limit** | Results are "not comparable to other people running on other compute platforms" because the budget is fixed in time, not in FLOPs |

**A note on sourcing.** Search surfaced write-ups on Fortune, DataCamp, MarkTechPost,
Verdent and similar. **None of those clear your credibility gate**, so they were
used for discovery only and every fact in the table above was then read at the
primary repository. Widely-repeated figures — ~700 experiments, 20 kept changes,
an 11% reduction from 2.02 to 1.80 hours — come from those secondary write-ups
and **were not confirmed at the primary source in this session.** Treat them as
**Unverified**. They are not load-bearing for anything below.

---

## 2. The one thing that makes the loop work

Strip the loop to its mechanism and this is what is left:

```
propose  →  evaluate  →  KEEP or ROLL BACK  →  repeat
                            ▲
                            └── a cheap, automatic, objective number
```

**`val_bpb` is the entire reason it can run unattended for two days.** The
keep-or-discard decision is *mechanical*. No human judges anything. No model is
asked "was that better?" A number goes down or it does not.

**Therefore the design question for your four lanes is not "can an agent research
this." It is: *what is `val_bpb` here, and can a script compute it in minutes?***

Where that number exists, you get a real Karpathy loop.
Where it does not, **an optimization loop is not merely hard — it is the wrong
shape**, and running one anyway produces confident motion in a random direction.
Those lanes get a **falsification loop** instead, which improves by killing wrong
answers rather than by climbing a score. You already own one of those.

---

## 3. THE MEASURABILITY GATE

**No loop runs unattended until all six pass. Fail one → it is a hybrid, not a
Karpathy loop, and it is labeled as such.**

| # | Gate | Why it is here |
|---|---|---|
| **G1** | **The metric is computed by code.** No model judgment anywhere in the scoring path | A model scoring its own output is a loop that converges on what the model likes |
| **G2** | **One evaluation completes in under N minutes**, N fixed in advance | Karpathy's N is 5. A loop with a 3-hour eval gets ~8 experiments a day and learns nothing |
| **G3** | **The evaluation is deterministic, or seeded and averaged** | Noise gets banked as improvement. You then build on it |
| **G4** | **The metric cannot be satisfied by a degenerate solution** — and you have written down the three cheapest ways to cheat it | See §4. This is the gate people skip and then get burned by |
| **G5** | **Rollback is automatic and complete.** Version-controlled, one command, no residue | A loop that cannot cleanly revert accumulates damage instead of improvements |
| **G6** | **A held-out check exists that the loop cannot see or optimize against** | The only defense against G4 that survives a clever optimizer |

**G4 and G6 are not optional and they are not paperwork.** An optimization loop
is a search for *anything* that moves the number. It does not know or care what
you meant. It will find the cheap path if a cheap path exists.

---

## 4. Reward hacking — plan for it, it is not a hypothetical

Write down, before the loop runs, the three cheapest ways to move your metric
without doing the work. Then defend each one.

| Lane | The cheap path the loop will find | Defense |
|---|---|---|
| Software | Weaken or delete the failing test; loosen an assertion; special-case the benchmark input | Test files are **read-only to the loop**. Test-file changes in the diff = automatic rollback + escalation |
| GovCon | Keyword-stuff the response so the compliance script matches every shall-statement | Held-out human-written rubric on a sample of rows (G6); a length ceiling; verbatim-quote checks |
| Research | Cite more sources; raise counts without raising quality | Citation gate is a *filter*, never a score. Count of sources is not the metric and must never become one |
| Personal | **No metric. No loop.** | See §5.4 |

**The standing rule:** if the loop's metric improves and you cannot explain *why*
in one sentence that would survive a hostile reader, **assume it cheated and
check.** That instinct is the actual skill in loop engineering.

---

## 5. The four lanes

### 5.1 FORGE LINK (software) — **TRUE optimization loop.** Gates: all six pass.

This is the lane AutoResearch was built for, and the mapping is close to exact.

| Karpathy | Yours |
|---|---|
| `train.py` | Source files in the talent application, **excluding tests** |
| 5-minute training run | Your test suite + a benchmark harness |
| `val_bpb` | A composite score (below) |
| keep / roll back | `git commit` / `git reset --hard` |
| `program.md` | `agents/loops/forge-software/program.md` |

**The composite metric — every term computed by a script:**

```
score = w1·(1 - test_pass_rate)        # correctness. HARD GATE: any failure = reject
      + w2·(p95_latency_ms / baseline)
      + w3·(bundle_size_kb / baseline)
      + w4·(1 - coverage_of_changed_lines)
```

Correctness is a **gate, not a term** — a change that fails any test is rejected
before its score is computed. You cannot trade correctness for latency.

**G4 defenses:** tests are read-only to the loop; any diff touching a test path is
an automatic rollback and an escalation. **G6:** a weekly `adversarial-reviewer`
pass on the accumulated diff, which the loop never sees.

**Honest scope:** this loop is good at *local* optimization — performance, size,
dead code, test coverage, dependency pruning. **It will not design your product.**
Point it at a bounded module with a real benchmark, never at "make the app
better."

---

### 5.2 ABO (GovCon) — **TRUE optimization loop, and this is the surprise.**

Most people assume GovCon cannot support a Karpathy loop because win/loss
feedback takes months and the sample is tiny. That is true of *bid outcomes*. It
is **not** true of **compliance**, which is mechanically checkable in seconds.

| Karpathy | Yours |
|---|---|
| `train.py` | One proposal response document |
| 5-minute run | The compliance script from `05-govcon-pipeline.md` §4 |
| `val_bpb` | Unaddressed-requirement count (below) |
| keep / roll back | Git on the response document |

**The metric — lower is better, all mechanical:**

```
score = 3·(shall_statements_with_no_mapped_response)
      + 2·(section_M_factors_with_no_mapped_response)
      + 2·(section_L_instructions_violated)     # page limits, format, order
      + 1·(cross_reference_errors)
```

Every term comes from the **deterministic Pass-1 extraction** that already refuses
to trust model-invented rows (`05` §4). The loop proposes an edit to the response,
the script recomputes, the change is kept only if the count went down.

**This is a genuine unattended loop on a real objective**, and it attacks the most
expensive avoidable failure in your GovCon lane.

**What it is emphatically NOT:** a loop that makes the proposal *persuasive*.
It drives **unaddressed requirements toward zero.** Whether the response is any
good is a human judgment and stays one.

**G4 defenses — this metric is the most gameable of the four.** Keyword stuffing
moves it without addressing anything. Defenses: a per-section length ceiling; a
verbatim-quote check; and **G6 — a human reads a random 10% sample of mapped rows
and asks "does this actually respond?"** If the sample fails, the run is void.

> **GATE BEFORE THIS LOOP EXISTS AT ALL:** a proposal in progress is very
> plausibly procurement-sensitive. **This loop does not run on any non-public
> document until contracts counsel has answered the four questions in `07` §2.**
> That is `10-open-questions.md` item A1 and it blocks this lane entirely.
> **Professional verification required.**

---

### 5.3 DBA (dissertation) — **HYBRID. Falsification loop.** Gates G1, G3, G4 fail.

There is no scalar for "argument quality." Any number you invent for it would be
a fabricated number, which your own standing rule forbids outright.

**So this loop does not climb. It kills.**

```
claim set from your draft
   │
   ├─ each claim → attacked from five analytical lenses
   ├─ mechanical gates run FIRST: DOI resolution, quote fidelity, retraction
   ├─ claims that survive carry forward; claims that die are recorded WITH the killer
   └─ repeat until a round produces no new kills
   │
   ▼
output: surviving claims · killed claims and why · OPEN HOLES
```

**"No new kills" is the stopping condition — not "it sounds good now."**

**You already own this.** `adjudication/` is a five-seat blinded elimination
engine with claim gates, a cost ceiling and a refuse path, and `night_loop.py`
is its unattended round shape. **Do not build a second one.** This lane's loop is
`adjudication/` pointed at your claim set on a weekly cadence.

**The closest thing to a metric — and it is a diagnostic, not an objective:**
`open_holes_count` and `unresolved_citations_count`. Both are mechanically
computable. Both must reach zero before a chapter goes to your chair. Neither is
ever *optimized toward* — the loop is not permitted to close a hole by deciding
it does not matter.

**Never:** writes prose, chooses your frame, or interprets your data. The
argument is yours.

---

### 5.4 HOME (personal, family, investment) — **HYBRID. Deliberately NOT a loop.**

**I am going to push back on this one, and then build you what will actually
help.**

An optimization loop over investment decisions fails every gate that matters:

| Gate | Why it fails |
|---|---|
| **G1** | There is no code-computable measure of a *good decision*. Returns measure outcomes, and outcome ≠ decision quality |
| **G2** | The feedback horizon is years. Not minutes |
| **G3** | Markets are the opposite of deterministic. Sample size across your real decisions is tiny |
| **G4** | **Catastrophic.** A loop optimizing backtested return will find leverage, concentration and survivorship bias — the three cheapest paths to a great backtest and a destroyed balance sheet |
| **G6** | You cannot hold out the future |

Run an optimization loop here and you build a machine that produces
confident, quantitative, *fabricated* justifications for financial decisions —
against your explicit standing rules on invented numbers and downside protection,
and against the stewardship frame the whole enterprise is built on.

**What this lane gets instead — and it is more valuable:**

```
DECISION JOURNAL LOOP  (weekly, falsification, never executes anything)

For each open decision:
  1. Restate it as a falsifiable claim with a date
  2. State the base rate — or state that you do not know it, and stop
  3. PRE-MORTEM: it is 3 years on and this failed. Write why
  4. INVERSION: what would have to be true for the opposite to be right?
  5. Name the ONE fact that would change your mind, and where it would come from
  6. Record: decision, reasoning, expected outcome, review date
  7. On review dates: compare what happened to what you wrote.
     Score the REASONING, never the outcome

Hard rules:
  · Never recommends a specific security, allocation, or transaction
  · Never produces a return estimate, probability, or expected value
  · Never touches a brokerage, bank, or payment surface (07 §6)
  · Reads only what you give it
```

**The metric that actually matters here is calibration** — how often your
recorded reasoning turns out to have been right for the reason you wrote down.
That takes years to accumulate, and it is the only honest number in this lane.

This is not a smaller version of the other three. It is the right shape for
decisions that are few, slow, irreversible and consequential — which is exactly
what family and capital decisions are.

---

## 6. Summary — what you actually get

| Lane | Loop type | Metric | Unattended? | Blocker |
|---|---|---|---|---|
| **FORGE** software | **True optimization** | composite, mechanical | **Yes** | none |
| **ABO** GovCon | **True optimization** | unaddressed-requirement count | **Yes, after counsel** | **A1 — contracts counsel** |
| **DBA** research | Falsification | open holes → 0 (diagnostic) | Yes, cost-gated | none |
| **HOME** decisions | Decision journal | calibration, over years | **No, by design** | none |

**Two real Karpathy loops, two honest hybrids.** You asked for four "even if they
are hybrid versions" — that instinct was right, and this is where the line
actually falls.

---

## 7. Hardware — you do have enough, with three caveats

One lane per machine. **Physical separation is the strongest lane isolation
available to you**, and it costs nothing because you already own the hardware.

| Lane | Node | Why this one | RAM |
|---|---|---|---|
| **DBA** research | **HP Envy 17** | Heaviest context: long documents, many sources, the five-seat loop. Already your designated overnight host | 64GB |
| **FORGE** software | **ASUS ProArt 16** | Builds, benchmarks, and the only GPU if a loop ever goes GPU-bound | 32GB |
| **ABO** GovCon | **Surface Pro 8** | 32GB is sufficient for a document loop, and a physically separate machine is the cleanest CUI boundary if counsel permits anything at all | 32GB |
| **HOME** decisions | **MacBook Air 15 M4** | Lightest loop by far — weekly, document-only, no browser swarm | 16GB |

**Caveat 1 — WSL cannot drive Chrome.** Docs-Verified: *"Chrome integration isn't
supported in Windows Subsystem for Linux (WSL)"* (`code.claude.com/docs/en/chrome`,
retrieved 2026-09-14). Your HP Envy's WSL2 Ubuntu is where you run bash-heavy
work; **any browser-driving loop on that machine must run from Claude Code on the
Windows side, not inside WSL.**

**Caveat 2 — the MacBook Air is the fleet bottleneck at 16GB** (Stated, your
fleet pack §1.4). It can run the HOME decision-journal loop comfortably. Do not
put a five-window browser swarm on it.

**Caveat 3 — the literal nanochat autoresearch wants an NVIDIA GPU, tested on an
H100** (Docs-Verified, primary repo). Your RTX 5070 has 8GB VRAM (Stated). The
repo notes recommendations for smaller machines "but no guarantee of success."
**You can run the original as a learning exercise on the ProArt. Your results will
not be comparable to anyone else's**, which the repo says outright. None of the
four lane loops above are GPU-bound, so this limits only the ML-training case.

---

## 8. The cost constraint, stated before you find it the hard way

Four loops running continuously is **four times the spend and four times the
rate-limit draw**, against pools that also fund your interactive work.

- Routines *"draw down subscription usage the same way interactive sessions do"*
  and carry a **daily run cap** (Docs-Verified, `code.claude.com/docs/en/routines`).
- Your own five-seat engine is bounded under **$17 per run** with a typed `SPEND`
  confirmation (Repo-Verified, `.github/workflows/adjudicate.yml`).

**Rules, adopted from your own engine's design:**

1. **Every loop declares a per-run ceiling and a per-week ceiling before it runs.**
2. **Every loop has a maximum iteration count.** A loop with no stopping condition
   is a bill with no stopping condition.
3. **Start one loop.** FORGE software — it is the only one with no blocker and the
   cleanest metric. Prove the mechanism, then add the second.
4. **STEWARD reports loop spend weekly** alongside the other four numbers (`08` §3).
