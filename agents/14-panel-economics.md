# 14 — PANEL ECONOMICS

Making deep thinking cheap without making it worse. All rates **Repo-Verified**
from `adjudication/rates.json`, verified by you against vendor pages 2026-09-09.

---

## 1. The verified rate card

| Seat | Vendor | Model | In $/MTok | Out $/MTok |
|---|---|---|---|---|
| 1 | OpenAI | `gpt-5.6-sol` | 4.00 | 20.00 |
| 2 | Google | `gemini-3.1-pro-preview` | 2.00 | 12.00 |
| 3 | Mistral | Medium 3.5 — **id UNVERIFIED** | 1.50 | 7.50 |
| 4 | xAI | `grok-4.6` | 2.00 | **6.00** ← cheapest output |
| 5 | Anthropic | `claude-opus-5` | 5.00 | 25.00 |
| | | **PANEL TOTAL** | **14.50** | **70.50** |

**Measured cost of a five-round panel run: $4.96. Planned bound: $16.82**
(Repo-Verified, `adjudicate.yml` and `accuracy.py`).

**Output dominates.** The panel's output rate is 4.9× its input rate
(70.50 ÷ 14.50), and reasoning runs are output-heavy. **Optimize output, ignore
input.** That single observation drives every choice below.

---

## 2. What one seat actually costs — arithmetic shown

**Method.** Each seat's share of panel cost is its rate ÷ the panel total, taken
separately for input and output. That brackets the true share without needing the
token split, which is not recorded in any file I read.

```
seat share (input)  = seat_in  / 14.50
seat share (output) = seat_out / 70.50
cost range          = [min(share) , max(share)] x panel run cost
```

**Applied to the $4.96 measured run and the $16.82 bound:**

| Single seat | Share range | vs $4.96 measured | vs $16.82 bound |
|---|---|---|---|
| **grok-4.6** | 8.51% – 13.79% | **$0.42 – $0.68** | $1.43 – $2.32 |
| Mistral Medium 3.5 | 10.34% – 10.64% | $0.51 – $0.53 | $1.74 – $1.79 |
| gemini-3.1-pro | 13.79% – 17.02% | $0.68 – $0.84 | $2.32 – $2.86 |
| gpt-5.6-sol | 27.59% – 28.37% | $1.37 – $1.41 | $4.64 – $4.77 |
| claude-opus-5 | 34.48% – 35.46% | $1.71 – $1.76 | $5.80 – $5.96 |

**Label: Inference, with two stated assumptions.**
1. A single-seat run sends comparable token volume to one panel seat.
2. It runs a comparable number of rounds.

**Assumption 2 is conservative** — a one-model run has no cross-seat rounds, so
real cost is likely *below* these figures. **The exact answer is already
instrumented:** `cost_ledger.py` records actuals per call. Run one and read the
ledger; it beats any estimate here, including mine.

**Consistency check on the method.** `accuracy.py` states 30 questions is "on the
order of $150 measured, $500 bounded." 30 × $4.96 = **$148.80**; 30 × $16.82 =
**$504.60**. The method reproduces your own documented figure, which is the only
evidence I have that it is sound.

---

## 3. The cascade

```
TIER 0  GATES                      $0.00      always, first, on everything
TIER 1  one_model.py + gates       ~$0.55     the default
TIER 2  window swarm (5 LLMs)      ~$0.00     subscription-funded breadth
TIER 3  paid API panel             $4.96+     rare, and mainly for calibration
```

### Tier 0 — gates. Free, and the most valuable layer.

Your own SOP, via `one_model.py`: *"SOP 2.2 calls it the most valuable part of
the system, and the reason is that its errors are UNCORRELATED with the model's:
a calculator does not make the mistake a language model makes, and a DOI either
resolves or it does not."*

Gates you already own: `citation_gate.py` · `doi_resolver.py` · `quote_gate.py` ·
`predicate.py` · `option_set.py` · arithmetic self-refutation · the compliance
extractor from `05` §4.

**Self-refutation survives at n=1** — `one_model.py`: *"An option is removed when
its own formula, with its own inputs, fails to produce its own figure... It is
also the only mechanism that ever removed anything correctly in this project."*

**Read that last clause again.** The mechanism that actually did the work needs
**one** seat. You have been paying for five.

### Tier 1 — one model plus gates. The default.

`one_model.py` exists and is the measured-correct architecture for your two task
classes. **What you lose at n=1, stated in your own file:** corroboration
("two seats who wrote blind independently give the same different value"), and
all panel diagnostics — rho, effective seat count, per-pass divergence, the
collapse flag. *"At n=1 they are undefined, not zero."*

**Seat choice:** `grok-4.6` at $6.00/MTok output is the cheapest and the obvious
Tier 1 default. Use `claude-opus-5` when the task is long-context or
instruction-dense and you will accept ~3× the cost for it.

### Tier 2 — the window swarm. Breadth at zero marginal API cost.

Five different LLMs in five Chrome tabs, driven by a dispatcher, **billed against
subscriptions you already pay for rather than per-token API calls.**

This buys back most of what n=1 gives up — five genuinely different model
families, so corroboration and divergence become observable again — **without the
per-token bill.** Full design in [`15-window-swarm.md`](15-window-swarm.md).

**What it does not buy:** *measured* rho. Blinding in a browser swarm is weaker
than in the API panel, and a number you cannot defend is not a number. Tier 2
gives you **qualitative** divergence — seats disagreed, here is how — which is
most of the decision value. **Quantitative rho stays a Tier 3 product.**

### Tier 3 — the paid panel. Rare, and mostly an instrument.

Keep it for: measuring rho, running the accuracy harness, and the occasional
decision where blind independence genuinely matters and the consequence justifies
$5–$17.

**Do not schedule it.** `adjudicate.yml`'s own header: *"A run is something a
person decided to start, at a moment they chose, with a ceiling they set."*

---

## 4. What the cascade saves — arithmetic shown

**Scenario: 30 deep questions per month.**

| Strategy | Monthly | Annual |
|---|---|---|
| All Tier 3 (v1 behavior) | $148.80 – $504.60 | **$1,786 – $6,055** |
| All Tier 1 (grok) | $12.60 – $20.40 | $151 – $245 |
| **Cascade 80/15/5** | **$17.52 – $41.55** | **$210 – $499** |

```
Cascade: 24 questions Tier 1, 4.5 Tier 2, 1.5 Tier 3
  24 x $0.42 = $10.08      24 x $0.68 = $16.32
   4.5 x $0.00 = $0.00      4.5 x $0.00 = $0.00
   1.5 x $4.96 =  $7.44     1.5 x $16.82 = $25.23
                 -------                   -------
                 $17.52                    $41.55
```

**Reduction vs all-Tier-3: 88.2% at the measured end, 91.8% at the bound.**

**Label: Inference** — built on the Repo-Verified $4.96/$16.82 anchors and the
§2 rate shares, with the 80/15/5 split as an **Assumption**. Your real split is
unknown until you run the cascade and count. The loop in §6 measures it.

---

## 5. Five more cost reductions, cheapest first

| # | Change | Saves | Effort |
|---|---|---|---|
| **1** | **Early stop on convergence.** `convergence.py` already computes the decay curve and `Orchestrator.should_stop` applies the four-condition conjunction. Stop at round 3 when yields have decayed instead of always running 5 | up to **40%** of a panel run | Wiring — the estimators exist |
| **2** | **Prompt caching.** `rates.json` seat_5: *"Cache reads are 0.1x input if caching is ever enabled."* Rounds 2–5 resend a large shared merged text | up to **90% of input** on cached seats | Per-vendor, small |
| **3** | **Drop the two priciest seats from routine panels.** Removing `claude-opus-5` and `gpt-5.6-sol` cuts panel output rate from 70.50 to 25.50 — **a 63.8% cut** | **~64%** of a panel run | Config |
| **4** | **Cap `max_tokens` harder.** `rates.json` records measured output multipliers of 0.24x–2.9x against caps set at 2.0–7.0 for headroom. Headroom is bought with money | proportional | Measure, then tighten |
| **5** | **Local seat on the ProArt** for round-1 breadth. RTX 5070, 8GB VRAM — small models only, which is fine for generating candidate options that gates will filter anyway | one seat's cost | Setup, then free |

**Do #1 and #3 first.** Together they are roughly a 4× reduction on any panel run
you still choose to make, and neither requires new code.

---

## 6. Optimize it with a Karpathy loop — the metric already exists

This is the part that answers *"we still need to iterate and optimize that."*

**`accuracy.py` is already a `val_bpb`.** It runs a fixed question set with known
answers and returns three outcomes — `RESOLVED CORRECT`, `RESOLVED WRONG`,
`NOT RESOLVED`. Combine with `cost_ledger.py` and you have a real objective:

```
objective = cost_per_resolved_correct       (lower is better)
subject to:  resolved_correct_rate must not fall below the current baseline
             not_resolved_rate must not rise
```

**The search space** — every knob in §5, plus panel composition:

```
seat_count · which seats · round_count · early-stop threshold
max_tokens per seat · caching on/off · gate ordering · Tier-1 seat choice
```

**The G2 problem, and its solution.** A full accuracy eval is 30 five-round runs
— **$148.80–$504.60 and hours.** Far too expensive per iteration.

So the loop splits the metric exactly the way the Measurability Gate prescribes:

| | Per iteration (cheap) | Held out (expensive, rare) |
|---|---|---|
| **What** | `calibrate.py` rho (**5 calls total**, not 5 runs) · convergence yield · gate-refutation counts · ledger cost · a 6-question smoke set | Full `accuracy.py` on 30 questions |
| **Cost** | cents | $148.80 – $504.60 |
| **Cadence** | every iteration | **once per 20 iterations, and at the end** |
| **Loop sees it?** | yes | **never** — this is G6 |

**That is not a compromise. It is the correct structure**, and your repository
already contains both halves.

Spec: [`loops/panel-economics/`](loops/panel-economics/). Guard-checked.

**The cheat path this loop will find, named in advance (G4):** drive
`cost_per_resolved_correct` down by resolving *fewer* questions — a panel that
answers nothing costs little per answer. **Defence:** `not_resolved_rate` is a
hard constraint, not a term, and a run that raises it is rejected before its cost
is scored.

---

## 7. Do this first, before any of it

```bash
cd adjudication && python3 calibrate.py     # five calls. Not five runs.
```

**`calibrate.py` costs one call per seat** — its own header: *"the whole
calibration is five API calls, not five times the item count."* It returns **rho**,
your measured seat independence.

**Why this thirty minutes outranks everything else here:** if rho is high, your
five seats are five correlated opinions billing five times, Tier 3's only unique
product is worthless, and you should retire it rather than optimize it. If rho is
low, Tier 3 is a real instrument worth keeping for rare use.

**You cannot decide the architecture without that number, and it costs cents.**

---

## 8. Blocker on any Tier 3 run

`rates.json`, **Repo-Verified**, seat_3: *"MAGISTRAL IS RETIRED AND THIS IS NOT
MAGISTRAL... Confirm both on Mistral's own pages before the next paid run; a
ceiling computed from an unchecked price bounds nothing."*

Two minutes in the Mistral console. Until then a Tier 3 ceiling bounds nothing,
and `loop_guard.py` blocks the panel-economics loop.

**Rate staleness:** verified 2026-09-09, re-check window 90 days → **due
2026-12-08.** SENTINEL carries the date.
