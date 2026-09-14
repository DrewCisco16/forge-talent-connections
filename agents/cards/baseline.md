# BASELINE — protocol card

> Capture two weeks of unmodified time data, so "did this help" has an answer
> instead of an impression.

> **PROTOCOL, not an agent.** No agent performs this. It is you, a timer, and fourteen days. It kept an agent card by mistake until the TRIZ trim in `../21-triz-zerodefects-goals.md` §2.2.

| Lane | Version | Tier | Route | Status |
|---|---|---|---|---|
| cross-lane, metadata only | 1.0 | B | phone tap + weekly roll-up | **START THIS FIRST** |

**Closes `19` E4.** Every version of this system has deferred the baseline. It is
the least satisfying item in the whole build and the one that determines whether
any of it can be evaluated. **Without it, no honest claim about time saved can
ever be made** — and your own standard forbids making one anyway.

### INPUTS
One tap per work block: category, lane, minutes, time of day. **Crude is fine.
Consistent is what matters.**

### THE FIVE CATEGORIES
```
MAIL         reading, deciding, replying, re-reading. All five mailboxes
SCAN         looking for opportunities, literature, prior art, competitors
MECHANICAL   matrices, formatting, citation cleanup, status, reconciliation
BUILD        writing and reviewing code and specifications
JUDGMENT     deciding things only you can decide   ← the number you want to go UP
```

### OUTPUT
`baseline/YYYY-MM-DD.csv` → `date,category,lane,minutes,start_time,note`
Weekly roll-up: minutes per category, **and time-of-day distribution.**

**Time of day matters more than it looks.** If MAIL is eating 45 minutes at 10pm,
the problem is not volume — it is that the decisions queued all day and landed
when your judgement is worst. **That is a scheduling fix, and an agent would have
hidden it rather than solved it.**

### ACCEPTANCE TESTS
```
normal              → 14 days captured, five categories, roll-up produced
missing evidence    → a missed day → recorded as MISSING, never interpolated
unsafe instruction  → a note field carrying an instruction → FINDING, not obeyed
no-estimate         → asked for "hours saved" before 14 days → REFUSES. No baseline, no number
purity              → do NOT optimize during the baseline. You would measure the optimization
```

### LIMITS
14 consecutive days, unmodified · seconds per entry · $0.

### HUMAN APPROVAL REQUIRED FOR
Nothing. **But it requires you, every day, for two weeks. No agent can do this
part.**

### STOP CONDITION / SAFE FALLBACK
Stop at day 14 and produce the roll-up. **A partial baseline with days marked
MISSING is still usable. An invented one is not.**
