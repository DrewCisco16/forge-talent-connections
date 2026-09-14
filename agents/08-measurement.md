# 08 — MEASUREMENT

**You cannot know whether this worked. Not yet. That is the first problem to
solve, and it is solved before any agent runs, not after.**

---

## 1. Why there is no number in this document set

You will find no claim in this design that agents will save you N hours a week.
There is no such number available, for a reason that is not modesty:

- **You have no baseline.** Nobody knows how many hours a week you currently
  spend on email, opportunity scanning, or literature triage. Without that, any
  "hours saved" figure is subtraction from an invented minuend.
- **A vendor benchmark is not your baseline.** Published productivity figures
  measure other people doing other work with other tooling.
- **Your own standing rule forbids it.** A number requires a real dataset and a
  shown calculation. There is no dataset. So there is no number.

**The instrument comes first. The claim comes after, if the data supports it.**

---

## 2. The two-week baseline — do this before Gate 1

Two weeks, five categories, a phone tap per entry. Crude is fine; **consistent is
what matters.**

| Category | What counts |
|---|---|
| **MAIL** | Reading, deciding, replying, re-reading. Across all five mailboxes |
| **SCAN** | Looking for opportunities, literature, prior art, competitive information |
| **MECHANICAL** | Matrices, formatting, citation cleanup, status reports, reconciliation |
| **BUILD** | Writing and reviewing code and specifications |
| **JUDGMENT** | Deciding things only you can decide. **This is the number you want to go UP** |

Record per category: **minutes**, **time of day**, **lane**.

```
baseline/2026-09-DD.csv
date,category,lane,minutes,start_time,note
```

Time of day matters more than it looks. If MAIL is consuming 45 minutes at 10pm,
the problem is not volume — it is that the decisions queued all day and landed
when your judgment is worst. That is a scheduling fix, and an agent would have
hidden it rather than solved it.

**Fourteen days, unmodified.** Do not start optimizing during the baseline; you
will measure the optimization instead of the problem.

---

## 3. The four numbers STEWARD reports weekly

Per lane, per agent. Nothing else.

### 3.1 Approval rate
```
Tier B artifacts you approved unedited  ÷  Tier B artifacts produced
```
- **Rising** → the agent is learning your standard. Consider promotion.
- **Flat and low (<70%)** → the agent is mis-specified, not undertrained. Fix the
  prompt or retire it. More runs will not help.
- **Falling** → demote now; something changed.

### 3.2 Review minutes — **the number that matters most**
```
total minutes you spent reading and acting on agent output
```
> **If this goes up and stays up, the system is failing — no matter how good the
> output is.**

This is the whole thesis of `01` §2 rendered as a measurement. An agent producing
brilliant work you must read for twenty minutes has converted your time into
different time, not returned it.

### 3.3 Material errors
```
count of outputs that would have caused harm had you not caught them
```
Harm = money, a relationship, a legal position, a right, a deadline, your
integrity. **Target zero.** Not a stretch target — the tiers exist so that zero is
achievable, because a Tier B error stops at your desk by construction.

Every material error gets a one-line entry: what, which agent, which guard should
have caught it, what changed as a result. **The error ledger is the most valuable
artifact this system produces**, because it is the only thing that tells you where
the design is wrong.

### 3.4 Cost
```
vendor API spend  +  routine runs consumed  +  subscription usage drawn down
```
Docs-Verified: routines *"draw down subscription usage the same way interactive
sessions do"* and carry a daily run cap. **Your agents compete with your own
interactive Claude Code use.** If your Tuesday afternoon session starts hitting
limits, your nightly routines are the reason, and that trade-off should be
deliberate rather than discovered.

---

## 4. Demotion — automatic, not discretionary

| Trigger | Consequence |
|---|---|
| One material error | **Immediate demotion one tier.** Not a conversation |
| Two consecutive weeks of falling approval rate | Demote one tier; review the prompt |
| Approval rate below 70% for three weeks | **Retire the agent.** It is mis-specified |
| Any outward-facing error | **Permanent return to Tier C for that category** |
| Any lane-separation violation | **Stop everything. Full audit before restart.** |

Demotion is automatic because the moment it becomes a judgment call, it stops
happening. You will be busy, the agent will have been useful, and you will let it
ride. Make the rule mechanical now, while it costs nothing.

---

## 5. The 90-day question

At day 90 you answer one question with the data, not with your impression:

> **Did JUDGMENT minutes go up while MAIL + SCAN + MECHANICAL minutes went down,
> with zero material errors?**

| Result | Verdict | Action |
|---|---|---|
| Judgment up, mechanical down, zero errors | **Working** | Extend to the next lane |
| Mechanical down, judgment flat | **Partially working** — time returned but not redeployed | Decide deliberately where the time goes (`07` §9) |
| Mechanical flat | **Not working** | The agents are producing, not replacing. Re-scope or cut |
| Review minutes up | **Failing** | Tighten Tier B artifacts to the sixty-second test, or cut agents |
| Any material error | **Stop on that agent** | Error ledger, root cause, guard, then restart |

**Retiring an agent is a normal outcome, not a failure of the system.** Ten agents
of which four survive contact with reality is a better result than ten that all
"work" and nobody measured.

---

## 6. What deliberately is not measured

| Not measured | Why |
|---|---|
| Tokens, runs, or "tasks completed" | Activity metrics. An agent can maximize all three while returning nothing |
| Words or pages produced | Output volume is a cost, not a benefit |
| "Hours saved" as a standalone figure | Not computable without the §2 baseline, and not asserted until it is |
| Agent "accuracy" as a percentage | No test set, no labels, no calculation. It would be a fabricated number |
