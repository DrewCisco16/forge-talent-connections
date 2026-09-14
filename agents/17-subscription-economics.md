# 17 — SUBSCRIPTION ECONOMICS (v2.1 amendment)

**Amends [`14-panel-economics.md`](14-panel-economics.md) §3 and
[`16-agent-roster-v2.md`](16-agent-roster-v2.md) §11.**

**New fact, Stated 2026-09-14:** Andrew holds **$200/month Max-tier subscriptions
for both ChatGPT (GPT-5.6 Sol) and Claude (Opus 5).**

---

## 1. What this changes

The two most expensive seats on your rate card are the two you already own
outright.

| Seat | Model | Metered $/MTok out | Now |
|---|---|---|---|
| 1 | `gpt-5.6-sol` | **20.00** | **$0 marginal** — ChatGPT Max |
| 5 | `claude-opus-5` | **25.00** | **$0 marginal** — Claude Max |
| 2 | `gemini-3.1-pro-preview` | 12.00 | metered |
| 3 | Mistral Medium 3.5 | 7.50 | metered |
| 4 | `grok-4.6` | 6.00 | metered |

**45.00 of the panel's 70.50 output rate — 63.8% — is now a fixed cost you have
already committed**, not a variable one you pay per question.

`14` §5 listed "drop the two priciest seats" as a 63.8% saving. **You no longer
have to drop them.** You keep all five and take the same cut. That is a strictly
better outcome than the one I recommended.

---

## 2. CORRECTION: the Tier 1 default seat

**`14` §3 said `grok-4.6`. That is now wrong.**

The reasoning was sound under metered pricing — grok has the cheapest output at
$6.00/MTok. Under subscription, the comparison is not $6.00 vs $25.00. It is
**$6.00 vs $0.00**, and the $0.00 option is also the more capable model.

| | Old (v2) | **New (v2.1)** |
|---|---|---|
| **Tier 1 default** | `grok-4.6` via API | **`claude-opus-5` via Claude Code on Max** |
| Marginal cost/question | $0.42 – $0.68 | **$0.00** |
| Capability | cheapest seat | most capable seat on the card |

**Second Tier 1 seat:** `gpt-5.6-sol` through the ChatGPT/Codex surface, also
$0 marginal. Two subscription-funded Tier 1 engines means you can run a
**two-seat cross-vendor check at zero marginal cost** — which is corroboration,
the exact thing `one_model.py` says n=1 gives up.

**That is the single biggest gain from this fact.** You recover the main weakness
of the one-model architecture without reintroducing the panel's bill.

---

## 3. Recomputed cascade

```
TIER 0  gates                                   $0.00     free, always
TIER 1  Opus 5 (Max) + gates                    $0.00     ◀ THE DEFAULT
TIER 1b Opus 5 + GPT-5.6 Sol cross-check        $0.00     corroboration, free
TIER 2  window swarm, 5 vendors                 $0.00-$1.80  depends on composition
TIER 3  paid API panel                          $4.96-$16.82  rare, calibration
```

**30 deep questions per month:**

```
24 x TIER 1   (Max subscriptions)        $0.00
 4.5 x TIER 2 (2 subs + 3 metered)       $8.08     = 4.5 x $1.80
 1.5 x TIER 3 (full paid panel)          $7.44 - $25.23
                                         ─────────────────
                             TOTAL       $15.52 - $33.31 / month
```

Tier 2 metered share: seats 2+3+4 = (12.00+7.50+6.00) ÷ 70.50 = **36.2%** of a
panel run → 0.362 × $4.96 = **$1.80**.

| Version | Monthly | Annual | vs v1 |
|---|---|---|---|
| v1 (all Tier 3) | $148.80 – $504.60 | $1,786 – $6,055 | — |
| v2 (metered cascade) | $17.52 – $41.55 | $210 – $499 | −88% |
| **v2.1 (subscription cascade)** | **$15.52 – $33.31** | **$186 – $400** | **−90% to −93%** |

**Label: Inference**, on the Repo-Verified $4.96/$16.82 anchors and `rates.json`
rate shares, with the 80/15/5 split still an Assumption until ROUTER's log
replaces it.

**Stated honestly: the $400/month of subscriptions is real money.** It is a
**fixed** cost you have already committed and would pay with or without this
system. Every figure above is *marginal* cost against that. The system's job is
to extract more from $400 you are already spending, not to pretend it is free.

---

## 4. The constraint is no longer dollars. It is rate limits.

**This is the strategic reframe, and it is bigger than the cost saving.**

On metered API, spending more buys more thinking. On a Max subscription it does
not — you hit usage limits instead, and limits do not negotiate.

Docs-Verified, `code.claude.com/docs/en/routines` and `/claude-code-on-the-web`
(retrieved 2026-09-14):

> "routines... draw down subscription usage the same way interactive sessions do."

> "In addition to the standard subscription limits, routines have a daily cap on
> how many runs can start per account."

> "Claude Code on the web shares rate limits with all other Claude and Claude Code
> usage within your account. **Running multiple tasks in parallel consumes more
> rate limits proportionately.**"

**Therefore your agents compete with you.** A nightly swarm on four machines, five
MAILROOM routines, SENTINEL, HARVESTER and STEWARD all draw from the same pool
that funds your Tuesday afternoon session.

### The objective changes

```
v2  :  minimise   cost_per_resolved_correct
v2.1:  maximise   resolved_correct_per_week  SUBJECT TO  staying inside the limit
                  and leaving headroom for interactive work
```

**Corresponding changes:**

| Where | Change |
|---|---|
| `loops/panel-economics/loop.json` | Objective becomes usage-draw per resolved-correct. Dollar cost stays a secondary term for the metered seats |
| **ROUTER** (`16` §11) | Adds a **usage budget**, not just a cost rule. See §5 |
| **STEWARD** (`08` §3) | Number 4 becomes *"usage drawn, and how much headroom remained"* — not just dollars |
| **Overage** | `claude.ai/settings/usage` can enable usage credits for metered overage. **Decide deliberately whether you want that on.** Off means agents stop; on means they keep going and bill |

### ROUTER's usage budget

```
RESERVED FOR INTERACTIVE WORK    >= 40% of daily allowance, never spent by agents
AGENT CEILING                     <= 60%, allocated:
    MAILROOM x5 (hourly)          highest frequency, smallest calls
    SENTINEL (daily)              small
    ORCHESTRATOR swarm (nightly)  largest single consumer
    OPTIMIZER loops               capped per loop.json
    STEWARD/HARVESTER (weekly)    small

WHEN THE AGENT CEILING IS REACHED: agents stop. Interactive work does not.
```

**If you hit limits and your own session is throttled, the system has failed
regardless of what it produced.** That is the same principle as review minutes in
`08` §3 — an agent that consumes the resource it was meant to protect is a tax.

---

## 5. Swarm composition — and do not buy more subscriptions

The swarm wants five vendors (`15` §2). You have two confirmed.

| Seat | Subscription? |
|---|---|
| Claude Opus 5 | **Yes — Max, Stated** |
| GPT-5.6 Sol | **Yes — Max, Stated** |
| Gemini | **Unknown** |
| Grok | **Unknown** |
| Mistral | **Unknown** |

**The arithmetic on buying three more:**

```
Three subscriptions at ~$25/month each        = $75/month fixed
Metered seats 2+3+4 per swarm run             = $1.80
Break-even                                    = $75 / $1.80 = 41.7 runs/month
                                               ~1.4 swarm runs PER DAY
```

**Recommendation: do not buy them yet.** At the 4.5 Tier 2 runs/month the cascade
projects, three more subscriptions would cost **$75/month to save $8.08/month.**

**Revisit when ROUTER's log shows you actually running the swarm more than ~1.4
times a day.** That is a measured trigger, not a guess — and it is exactly the
kind of question the ROUTER log exists to answer.

**Until then, run the swarm as: 2 subscription windows + 3 metered API seats**, or
**2 subscription windows + free-tier windows** where a vendor offers one and its
terms permit it (**Unknown per vendor — check once, record the date**).

---

## 6. Mixed-transport panel — an option, with a real caveat

You could run seats 1 and 5 through subscription surfaces and seats 2–4 through
the API, getting all five seats for **~36% of the metered cost** (the $1.80
figure in §3).

**The caveat is not cost, it is instrumentation.** `adjudication/` reaches every
seat by HTTP through `seat_adapter.py` and `profiles.json`, and `cost_ledger.py`
prices calls from **vendor-reported token counts**. A browser-window seat reports
no token usage block, so:

- The ledger's total becomes a **lower bound** with unmeasured calls stated — the
  ledger already handles this correctly and says so, which is why it is trustworthy
- Blinding through a chat window is weaker than blinding through an API call
- **Any rho computed across mixed transports is not defensible**, and a number you
  cannot defend is not a number

**So: mixed transport is fine for Tier 2 production work, labeled `SWARM`,
qualitative divergence only. Keep Tier 3 pure API when the point of the run is to
measure rho.** That is the whole reason Tier 3 still exists.

---

## 7. What Max unlocks — verified, and one open question closes

Docs-Verified 2026-09-14. All four require the plan you now have:

| Capability | Requirement | Status |
|---|---|---|
| **Claude in Chrome / `claude --chrome`** | *"A direct Anthropic plan (Pro, Max, Team, or Enterprise)"* + `/login` | ✅ available |
| **Routines** | *"available on Pro, Max, Team, and Enterprise plans"* | ✅ available |
| **Claude Code on the web** | *"research preview for Pro, Max, and Team users"* | ✅ available |
| **Cloud environment API credentials** | *"in Anthropic-hosted environments **on Pro and Max plans**, keys you add to a cloud environment stay outside the sandbox"* | ✅ available |

**`10-open-questions.md` B10 closes.** You have API credentials, so the metered
keys for seats 2–4 go there — outside the sandbox, never in environment variables,
which are *"visible to anyone who uses the environment."*

**Note the one thing Chrome integration refuses:** *"If you authenticate with an
API key or a long-lived token... Claude Code keeps Chrome integration off, even
when you pass `--chrome`."* The swarm dispatcher must run on your **Max login**,
not on an API key.

---

## 8. Revised first moves

```
1. Re-point Tier 1 to Opus 5 via Claude Code on Max.     $0 marginal.   [15 min]
2. Stand up Tier 1b: Opus 5 + GPT-5.6 Sol cross-check.
   Free corroboration, which is what n=1 was missing.     [1 hour]
3. Set ROUTER's usage budget: 40% reserved interactive,
   60% agent ceiling. Agents stop at the ceiling; you do not.  [30 min]
4. calibrate.py — five calls. STILL THE HIGHEST-VALUE 30 MINUTES.       [30 min]
5. Clear seat_3's Mistral id. Unblocks Tier 3 and the loop.    [2 min]
6. Decide usage-credit overage ON or OFF, deliberately.        [5 min]
7. DO NOT buy three more subscriptions. Revisit at 1.4 swarm runs/day.
```

**Step 4 does not change.** Subscriptions make the panel cheaper to *run*; they
say nothing about whether its five seats are independent. If rho is high, Tier 3
is still five correlated opinions — now merely a cheaper waste. **Free is not a
reason to run something that does not work.**
