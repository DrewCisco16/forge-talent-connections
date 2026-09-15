# 23 — IDOV: GOAL ATTAINMENT

**Identify · Design · Optimize · Validate.**

**Question:** are these the best agents, is the count right, and will the daily,
weekly, monthly and yearly goals be accomplished?

**What IDOV adds that the earlier analyses could not.** FMEA ranked failure
modes. FTA found the cut sets. TRIZ trimmed. **IDOV builds the transfer
function** — `Y = f(X)` — which is the only one of the four that says *where
effort actually moves the outcome*. That is the new thing in this document, and
it produces a harder result than any of the others.

---

## 1. IDENTIFY

### 1.1 Voice of the customer

The customer is you. Stated across this engagement, in your own words:

| VOC | CTQ (measurable) | Currently measured? |
|---|---|---|
| *"get me my time back"* | JUDGMENT minutes up; MAIL + SCAN + MECHANICAL minutes down | **No — BASELINE never started** |
| *"accomplish all my daily, weekly, monthly and yearly goals"* | Goals committed vs. closed, per period | **No — ledger empty** |
| *"Kingdom impact, family legacy, generational blessing"* | Not reducible to a CTQ, and should not be | **Correctly out of scope** |
| *"ownership and equity over earned income"* | Equity events; IP filed | Partly — IP lane now has agents |
| *"downside protection"* | Escaped defects; irreversible-act count | **Yes — ZED metric, currently 1 historical, 0 since** |

**Two of the five top-line CTQs have no instrument at all.** That is the same
gap `FM-33` named, now expressed as a measurement failure rather than a design
one.

### 1.2 The output variable

```
Y = goal attainment rate = goals closed / goals committed, per period
```

**Y is currently undefined — not low, undefined.** There is no numerator and no
denominator, because no goal has been committed in writing.

---

## 2. DESIGN — the transfer function

### 2.1 The inputs

| X | Input | Type | Current value |
|---|---|---|---|
| **X1** | **Goals written down** | **GATE, 0/1** | **0** |
| **X2** | Goals with an owner and one next action | ratio | undefined |
| **X3** | **Review cadence actually executed** | **GATE, 0/1** | **0** |
| X4 | JUDGMENT hours available per week | hours | **unmeasured** |
| X5 | Concurrent active goals (WIP) | count | undefined |
| X6 | Time returned by agents | hours | **0 — none running** |
| X7 | Review minutes consumed by agents | hours | 0 |
| X8 | Rework from escaped defects | hours | 0 since E-01 |
| X9 | Goals blocked on an external party | count | ≥4 known |
| X10 | Restart cost after an interruption | hours | unmeasured |

### 2.2 The function — and it is not additive

```
Y = X1 · X3 · f(X2, X4, X5, X6, X7, X8, X9, X10)
```

**X1 and X3 are multiplicative gates.** This is structural, not empirical:

- **An unwritten goal cannot be advanced by anything.** Not by 29 agents, not by
  144GB of RAM, not by a $400/month subscription. There is nothing to advance.
- **An unreviewed goal cannot be detected as stalled.** Without a cadence, a
  dead goal and a live one are indistinguishable until the period ends.

> **Both gates are currently ZERO. So the system's contribution to goal
> attainment is not "low" or "early" — it is structurally zero, and it will stay
> exactly zero no matter how many more agents are added.**
>
> **Adding a thirtieth agent multiplies zero.**

This is computed, not asserted: `python3 scripts/goal_throughput.py` reads the
ledger, evaluates the gates, and **refuses to emit an attainment figure while
either is open** — because a low number there would imply the other inputs
matter yet, and they do not.

### 2.3 The interaction that is usually missed

**X6 and X7 are not independent.** An agent returns time (X6) *and* consumes
review time (X7). The net is what matters:

```
net time returned = X6 − X7
```

An agent with excellent output and a four-minute review artifact can have a
**negative** net contribution. That is why `08 §3`'s review-minutes number is the
one that decides the system, and why the sixty-second artifact rule exists.

---

## 3. OPTIMIZE — sensitivity, and a WIP cap

### 3.1 Sensitivity ranking

Which X moves Y most per unit of effort. **Ranked structurally; not quantified,
because X4 is unmeasured and quantifying it would require inventing it.**

| Rank | X | Sensitivity | Effort to move it |
|---|---|---|---|
| **1** | **X1 — goals written** | **Infinite.** Zero kills everything | **~20 minutes** |
| **2** | **X3 — cadence executed** | **Infinite.** Zero kills everything | **~10 min/week** |
| **3** | **X5 — WIP** | **High**, and it is arithmetic — see 3.2 | A decision, not work |
| **4** | X7 — review minutes | High; subtracts directly from X4 | Enforce the 60-second rule |
| **5** | X2 — owned goals | High; an unowned goal never moves | Fill two columns |
| 6 | X9 — blocked goals | Moderate; 4+ known blockers | Four human acts |
| 7 | X6 — agent-returned time | Moderate, **and unproven** | Deploy one agent |
| 8 | X4 — judgment hours | High but slow to change | BASELINE first |
| 9 | X10 — restart cost | Moderate | STATE.md exists |
| 10 | X8 — rework | Low now | Gates hold |

**The top three cost almost nothing and are worth more than every agent in the
roster.** That is the IDOV finding, and it is uncomfortable in the right
direction.

### 3.2 The WIP cap — from a theorem, not a study

**Little's Law**, for any stable system:

```
average WIP = average throughput × average cycle time
```

This is a mathematical identity, so it is stated without a citation. The
consequence:

> **At fixed throughput, doubling the number of goals you work on concurrently
> doubles how long each one takes. It does not finish more of them.**

You are a single operator across five lanes. Throughput is bounded by X4, which
is bounded by hours in a day. **Therefore concurrency is the one lever that makes
everything slower while feeling like progress.**

**New, third GOALKEEPER invariant:**

```
INVARIANT 3 — WIP CAP
  at most ONE active goal per lane
  at most THREE active goals in total
  breaching it does not finish more. It lengthens all of them.
```

Enforced by `goal_throughput.py`, which flags a per-lane breach.

**Note honestly:** the sources search returned for Little's Law applied to
knowledge work were consultancy blogs. **They do not clear your credibility
gate and are not cited.** The law itself is arithmetic; the *empirical* question
of what your throughput is remains unmeasured and is not guessed.

---

## 4. VALIDATE

### 4.1 What cannot be validated yet

**Process capability — Cp, Cpk, sigma level — requires a distribution of
outcomes over completed periods.** There are zero completed periods. Any sigma
figure would be fabricated. **None is produced.**

### 4.2 The validation protocol — smallest thing that produces evidence

```
WEEK 1   write 3 goals: one YEAR, one QUARTER, one WEEK.  X1 -> 1
         run ONE weekly review. Record it.                X3 -> 1
         run goal_throughput.py. The gate should close.
WEEK 2   run BASELINE (the protocol). Capture X4.
         deploy ONE agent: BRIEFER. Measure X6 and X7 separately.
WEEK 3-4 continue. Goal closed or not closed - the first real data point on Y.
DAY 30   Y has a numerator and a denominator for the first time.
         Only now is any attainment figure meaningful.
```

### 4.3 The validation question at day 30

**Not** *"what percentage of goals did I hit?"* — one period is one data point.

**Ask instead:**

```
1  Did the goals that moved, move because of the review, or despite it?
2  Was net time returned (X6 - X7) positive for the one agent deployed?
3  Did JUDGMENT minutes rise, or did the freed time go to more building?
```

**Question 3 is the real test**, and `19 A2` already flagged it: six sessions
have been spent building this system and none running it. **Time returned that
goes into more system-building has not been returned.**

---

## 5. THE COUNT — the IDOV answer

| Question | Answer |
|---|---|
| **Are these the best agents?** | **The control set is sound and now well-covered. The production set remains unproven — zero have run.** "Best" stays an untested claim |
| **Too many?** | **Not for specification. And the count is now irrelevant to Y** — with both gates at zero, 29 agents and 0 agents produce the identical result |
| **Too few?** | **No. The gap is not agents. It is two zeros and twenty minutes** |
| **Add a thirtieth?** | **No. It would multiply zero.** The only additions this pass are a WIP invariant and a calculator that enforces the gate |
| **Will the goals be accomplished?** | **Not answerable, and not because I am hedging — because Y has no numerator and no denominator.** It becomes answerable the week you write three goals and run one review |

### 5.1 What was added this pass

```
+ GOALKEEPER invariant 3: the WIP cap, from Little's Law
+ scripts/goal_throughput.py: evaluates the transfer function, enforces the
  gate, refuses an attainment figure while either gate is open (9 self-tests)
+ 5 register entries for goal-attainment failure modes
+ the sensitivity ranking: where effort actually moves Y
```

**No agent was added, and that is the finding, not an omission.**

---

## 6. LITERATURE — verification queue, additions

**Every index remains unreachable this session**: Google Scholar, Crossref,
PubMed, arXiv, SAGE, NeurIPS, OpenAlex, Semantic Scholar, Europe PMC, DOAJ,
USPTO, PatentsView, Federal Register. **No citation below is verified.** Run each
through `.claude/agents/citation-verifier.md` before relying on it.

| # | Candidate | Claimed finding (snippet) | Relevance | Label |
|---|---|---|---|---|
| **G1** | Gollwitzer & Sheeran (2006), *"Implementation intentions and goal achievement: A meta-analysis of effects and processes"*, **Advances in Experimental Social Psychology** | **94 independent tests, >8,000 participants, d = .65** (medium-to-large) on goal attainment. If-then plans specifying *when, where and how* aid initiation, shielding, disengagement from failing courses, and conservation of capacity | **Directly supports the ledger's "ONE next action" field.** An if-then next action is an implementation intention | **Unverified — snippet only** |
| **G2** | Locke & Latham (2002), **American Psychologist**; PMID 12237980 | 35 years, 400+ studies; specific and difficult goals beat "do your best" | Supports the falsifiable, dated goal format | **Unverified** (carried from `21`) |
| **G3** | *"Optimized but Unowned: How AI-Authored Goals Undermine the Motivation They Are Meant to Drive"*, arXiv:2605.12344 | AI-authored goals reduce the motivation they aim to create | **Why GOALKEEPER records but never authors** | **Unverified** |
| **G4** | *"AI-Assisted Goal Setting Improves Goal Progress Through Social Accountability"*, arXiv:2603.17887 | AI assistance improves progress via accountability | Points opposite to G3. **A live tension** | **Unverified** |
| **—** | **Little's Law** | WIP = throughput × cycle time | **A theorem. Cited to nothing because it needs no source.** The knowledge-work applications search returned were consultancy blogs, which do not clear your credibility gate and are not used | **N/A — arithmetic** |

**The honest state of the evidence base:** four candidates, none verified, two of
which disagree with each other. **That is the real picture, and it is more useful
than a longer list I could not stand behind.**

---

## 7. THE ONE-LINE RESULT

> **`Y = 0 × 0 × f(...) = 0`.**
>
> Twenty-nine agents, seven versions, forty-four documents, two enforcing gates,
> 41 failure modes catalogued — and the goal-attainment contribution is exactly
> zero until three goals are written down and one review is run.
>
> **That is roughly thirty minutes of work, and nothing else in this repository
> competes with it.**
