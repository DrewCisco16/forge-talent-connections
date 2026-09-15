# 13 — VERSION ANALYSIS: v1 → v2

What v1 got wrong, what changes, and why. **Defect register first.**

**v1:** 2026-09-14 (`agents/01`–`12`) · **v2:** 2026-09-14, this file forward.

---

## 0. The headline

**v1 routed hard problems to the five-seat paid panel. Your own repository
already measured that as the wrong call, and I did not read that file before
designing around it.**

`adjudication/one_model.py` header, **Repo-Verified**:

> ```
> governance requirements   baseline 0.968   95% CI [0.838, 0.994]
> capture / talent / P&L    baseline 1.000   95% CI [0.890, 1.000]
> threshold 0.45            DO NOT BUILD THE ENSEMBLE
> ```
>
> "SOP 8.1 step 5: *If baseline > 0.45: STOP. Build one model plus gates. You
> just saved months.* Both whole intervals sit above the threshold, so that is
> not a close reading — it is the instruction."

And, from the same file:

> "SOP 2.2 calls [the gate layer] *the most valuable part of the system*, and
> the reason is that its errors are UNCORRELATED with the model's: a calculator
> does not make the mistake a language model makes, and a DOI either resolves or
> it does not."

And from `accuracy.py`:

> "SOP 7.1: *overall mean multi-agent improvement across six benchmarks was
> 0.0%*. If the panel does not beat one model on your own questions, that is the
> finding."

**You were right that the panel burns money, and you were right for a reason
stronger than cost: on your own two task classes, measured, it was not
justified.** The expensive part was never the valuable part. The **gates** are the
valuable part, and gates are nearly free.

**v2 inverts the engine hierarchy accordingly.** Full economics in
[`14-panel-economics.md`](14-panel-economics.md).

---

## 1. Defect register

| # | Defect in v1 | Severity | Fix in v2 |
|---|---|---|---|
| **D1** | Routed hard problems to the 5-seat paid panel as the default deep engine, ignoring `one_model.py`'s measured verdict | **Critical** | Three-tier cascade. One model + gates is the **default**; panel is a rare escalation (`14`) |
| **D2** | Treated the browser window swarm as a footnote when it is the cost-free breadth tier | **Critical** | Swarm promoted to a first-class engine (`15`) |
| **D3** | Said Codex/GPT-5.6 was unverifiable. **Your own `rates.json` carries it, verified 2026-09-09, with a source URL** | **High** | Corrected in §2. A5 partially closed |
| **D4** | Karpathy loops were bolted on at `11` instead of being the execution model for improvement | **High** | Loops become how every agent improves, not a separate feature (`16`) |
| **D5** | Roster of 10 had no agent that **compounds** — every run started from zero | **High** | HARVESTER added. Reuse libraries are the largest GovCon time win available (`16`) |
| **D6** | No agent optimized the agent system itself | **High** | PANEL-OPTIMIZER loop, using the accuracy harness you already own (`loops/panel-economics/`) |
| **D7** | Deadlines tracked per lane with no unified surface; a missed deadline is the failure mode that actually hurts | **Medium** | SENTINEL, metadata-only, no cross-lane content (`16`) |
| **D8** | Hedged repeatedly on the same points rather than stating a constraint once and building | **Medium** | Each constraint stated once, in `07`. Not repeated |
| **D9** | 90-day rollout deployed one agent in 30 days — too slow for hardware that is already sitting there | **Medium** | Compressed: parallel across four machines from week 1 (`16` §6) |
| **D10** | `rates.json` flags that seat_3's Mistral model id is **unverified** and Magistral is retired. v1 never surfaced this | **Medium** | Raised to a blocking item on any paid panel run (§4) |

---

## 2. Correction: GPT-5.6-sol is real and you already priced it

I said last turn I could not verify a "GPT-5.6" model and would not assert it.
**Your own repository verifies it.** `adjudication/rates.json`, **Repo-Verified**:

```json
"seat_1": {
  "_vendor": "OpenAI",
  "_model": "gpt-5.6-sol",
  "_source": "https://developers.openai.com/api/docs/models",
  "input_per_mtok": 4.0, "output_per_mtok": 20.0,
  "verified_on": "2026-09-09",
  "max_input_tokens": 1050000
}
```

You read it off the vendor's page on 2026-09-09 and stamped the date. That is
exactly the discipline this system asks for, and it beats my blocked proxy.
**`10-open-questions.md` A5 is now partially closed:** the model id and pricing are
Repo-Verified. What remains open is Codex's *sandbox, network, and scheduling*
behavior — not the model's existence.

**The full verified panel, from your own `rates.json` (verified 2026-09-09,
standard tier, prompts ≤200k):**

| Seat | Vendor | Model | In $/MTok | Out $/MTok |
|---|---|---|---|---|
| 1 | OpenAI | `gpt-5.6-sol` | 4.00 | 20.00 |
| 2 | Google | `gemini-3.1-pro-preview` | 2.00 | 12.00 |
| 3 | Mistral | Medium 3.5 — **id UNVERIFIED** | 1.50 | 7.50 |
| 4 | xAI | `grok-4.6` | 2.00 | **6.00** |
| 5 | Anthropic | `claude-opus-5` | 5.00 | 25.00 |
| | | **Panel totals** | **14.50** | **70.50** |

---

## 3. The v2 architecture

```
                        ┌───────────────────────────┐
                        │  TIER 0 — GATES (free)    │
                        │  DOI · quote · arithmetic │
                        │  self-refutation · compliance
                        │  ALWAYS RUN FIRST         │
                        └─────────────┬─────────────┘
                                      │ what survives
                        ┌─────────────▼─────────────┐
                        │  TIER 1 — ONE MODEL       │
                        │  one_model.py + gates     │
                        │  ~$0.42-$0.68 / question  │
                        │  ◀── THE DEFAULT ──▶      │
                        └─────────────┬─────────────┘
                          escalate only if ↓
              (gates disagree · seats needed for corroboration
               · genuinely contested · high consequence)
                        ┌─────────────▼─────────────┐
                        │  TIER 2 — WINDOW SWARM    │
                        │  5 LLMs in Chrome tabs    │
                        │  subscription-funded      │
                        │  MARGINAL API COST: $0    │
                        └─────────────┬─────────────┘
                          escalate only if ↓
                 (blind independence genuinely required,
                  AND the decision justifies the spend)
                        ┌─────────────▼─────────────┐
                        │  TIER 3 — PAID API PANEL  │
                        │  5 blinded seats, rho      │
                        │  $4.96 measured / $16.82   │
                        │  RARE. Typed SPEND.        │
                        └───────────────────────────┘
```

**The change from v1 in one line:** v1 made Tier 3 the deep engine. **v2 makes
Tier 0+1 the deep engine and Tier 3 a measuring instrument you reach for
deliberately.**

**Why Tier 3 still exists at all.** It produces something no other tier can:
**rho** — measured seat independence — and the panel diagnostics. `one_model.py`
says so itself: *"Error correlation, effective seat count, per-pass divergence
and the collapse flag are all properties of a PANEL. At n=1 they are undefined,
not zero."* You need those numbers occasionally to know whether Tiers 1 and 2 are
still trustworthy. That is a **calibration** use, not a production use — and
`calibrate.py` costs **one call per seat**, not a five-round run.

---

## 4. What v2 blocks that v1 did not

**Seat 3's model id is unverified and this blocks paid panel runs.**
`rates.json`, **Repo-Verified**:

> "MAGISTRAL IS RETIRED AND THIS IS NOT MAGISTRAL... Mistral documents the id as
> `mistral-medium-3504` and does not list `-latest` aliases, and the prices could
> not be re-verified against the pricing page on 2026-09-09... Confirm both on
> Mistral's own pages before the next paid run; a ceiling computed from an
> unchecked price bounds nothing."

Your file says it. v1 never surfaced it. **v2 treats it as a blocker on Tier 3**,
and the loop guard enforces it. Two minutes in the Mistral console clears it.

**Rates go stale.** `rates.json`: *"Re-check every 90 days."* Verified 2026-09-09
→ **due 2026-12-08.** SENTINEL carries that date (`16`).

---

## 5. What v1 got right and v2 keeps unchanged

Not everything moved. These held:

| Kept | Why |
|---|---|
| **Trust Tiers and the sixty-second artifact** | Review capacity is still the binding constraint. Nothing about cheaper engines changes that |
| **Lane separation, enforced by connector scope and now by machine** | One compromised agent must see one lane |
| **One-way doors** | No agent sends, submits, files, merges, publishes, or moves money. This does not relax with confidence |
| **Gates before model judgment** | Your own architecture, and `one_model.py` calls it the most valuable part of the system |
| **Per-lane Chrome profiles; browser control off for HOME** | The login-state exposure is real and it is one configuration step to contain |
| **Counsel gate on ABO non-public data** | Stated once, in `07` §2. Not repeated further |
| **Measurement before claims** | No hours-saved number until the baseline exists |

---

## 6. Migration — what to actually do

```
1. Re-point the deep-thinking path from Tier 3 to Tier 0+1.
   one_model.py already exists. This is configuration, not building.        [1 hour]

2. Stand up the window swarm as Tier 2 on the HP Envy, Windows side.
   Your night-agent skill already drives this shape.                        [1 evening]

3. Clear seat_3's model id in the Mistral console. Unblocks Tier 3.         [2 minutes]

4. Run calibrate.py — 5 calls, not a five-round run — to get current rho.
   That tells you whether the panel is even worth keeping as Tier 3.        [minutes, ~cents]

5. Start the FORGE autoresearch loop. It is already cleared by loop_guard.  [same day]

6. Start the PANEL-ECONOMICS loop. It optimizes cost-per-resolved-correct
   against the accuracy harness you already own.                            [week 2]
```

**Step 4 is the highest-value thirty minutes in this document.** `calibrate.py`
costs five calls and answers the question the whole cost argument turns on: are
your five seats actually independent? If rho is high, the panel is five
correlated seats billing five times for one opinion, and Tier 3 should be retired
outright rather than merely demoted.
