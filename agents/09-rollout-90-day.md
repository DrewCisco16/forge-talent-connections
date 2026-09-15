# 09 — 90-DAY ROLLOUT

One sprint. Three gates. **Each gate has a stop condition, and the stop condition
is real — if it trips, the next 30 days do not start.**

**Sequencing principle:** deploy in order of *review cost reduction per unit of
risk*, not in order of enthusiasm. Email first because it is the largest, most
reversible drain. GovCon last in the ABO lane because it is the one with a legal
gate in front of it.

---

## DAY 0 — BEFORE ANY AGENT RUNS

These are prerequisites, not tasks. Nothing after this section starts until they
are done.

| # | Item | Why it blocks | Owner |
|---|---|---|---|
| 0.1 | **Start the two-week baseline** (`08` §2) | No baseline, no verdict at day 90 | You |
| 0.2 | **Send the four questions to contracts counsel** (`07` §2) | The ABO lane cannot touch non-public data until answered | You + counsel |
| 0.3 | **Create five lane workspaces**, separate repos/roots | Lane separation is structural | You |
| 0.4 | **Protect `main`** on every repository | Makes the one-way door platform-enforced | You |
| 0.5 | **Confirm this repository's visibility** (public/private) | Determines what may ever be committed here — see §IP rules in `06` | You |
| 0.6 | **Password manager entries** for routine tokens and per-lane credentials | Tokens are shown once | You |
| 0.7 | **Verify the Codex substrate** or formally defer it (`03` §4) | Unverified today; do not build on it blind | You |
| 0.8 | **Write the kill-switch card** and put it on your phone (`07` §7) | 2am, no laptop | You |

**Do not skip 0.1.** It is the least satisfying item on the list and the one that
determines whether any of this can be evaluated.

---

## GATE 1 — DAYS 1–30: ONE AGENT, ONE LANE, PROVEN

**Scope: MAILROOM on exactly one mailbox.** Not five. One.

Pick the lane with the highest volume and the lowest stakes per message —
probably FORGE LINK or HOME. **Not ABO**, which is still behind the counsel gate.

### Build
| Day | Task |
|---|---|
| 1–3 | Create the routine. Prune connectors with the `07` §1 checklist. Grant read/label/draft only |
| 4 | **Test the denial.** Deliberately instruct MAILROOM to send an email. Confirm it cannot. Record the result |
| 4 | **Practice the kill switch.** Pause the routine, resume it. Revoke and regenerate a token |
| 5–7 | First live runs at Tier C. Read everything. Fix the prompt against real mail, not imagined mail |
| 8–21 | Tier C → B. Drafts begin. Measure approval rate daily |
| 22–30 | Stabilize. STEWARD produces its first weekly ledger |

### Gate 1 exit criteria — all five, no partial credit
```
[ ] MAILROOM demonstrably cannot send, delete, or spam-mark. Tested, recorded.
[ ] Digest reads in <=90 seconds.
[ ] Approval rate >=80% over the final 7 days.
[ ] Zero material errors.
[ ] Review minutes for that mailbox are DOWN against the baseline.
```

**Stop condition:** if review minutes are flat or up, **do not deploy a second
agent.** You have proof the artifact shape is wrong, and duplicating it four more
times multiplies the defect. Fix the shape first.

---

## GATE 2 — DAYS 31–60: BREADTH IN SAFE LANES

**Scope: MAILROOM to the remaining mailboxes + LIBRARIAN + BUILDER/REVIEWER.**

Deliberately excluded: **ABO GovCon agents, unless counsel has answered 0.2.**

| Agent | Lane | Why now |
|---|---|---|
| MAILROOM ×4 | remaining mailboxes | Shape is proven. Replicate it, do not redesign it |
| LIBRARIAN | DBA | Rides gates you already own (`citation_gate.py`). Low build cost, high integrity value |
| BUILDER + REVIEWER | FORGE | The pair. Never BUILDER alone — an unreviewed builder is worse than no builder |
| STEWARD | all active | Per-lane ledgers begin in earnest |

### Also in this window
- Stand up `disclosure/` in a **private** repository with the `06` §B5 template.
  The habit matters more than the agent.
- If Codex was verified at 0.7, run **one** issue through both BUILDER
  implementations and compare. If it was not verified, skip and note it.

### Gate 2 exit criteria
```
[ ] All five mailboxes at Tier B, each digest <=90 seconds.
[ ] LIBRARIAN has produced >=4 weekly reports, every citation DOI-resolved.
[ ] >=5 PRs from BUILDER, every one reviewed by REVIEWER before you read it.
[ ] REVIEWER has caught >=1 real defect.  (If zero, distrust it and verify it
    is actually reading the diff.)
[ ] Zero material errors. Zero lane-separation violations.
[ ] Total review minutes DOWN against baseline, with five more agents running.
```

**Stop condition:** any lane-separation violation stops everything for a full
audit (`08` §4). Not a warning, not a note — a stop.

---

## GATE 3 — DAYS 61–90: THE GOVCON LANE, IF CLEARED

**Scope: SCOUT → CAPTURE → MATRIX. Only if counsel has answered 0.2.**

If counsel has not answered, **this gate does not open.** Use the window to
deepen Gates 1–2 instead. That is a legitimate outcome, not a delay to route
around.

| Day | Task |
|---|---|
| 61–65 | Complete `prompts/SOURCES-GOVCON.md` from each provider's own docs. Record retrieval dates. **No value written from memory** |
| 66–70 | Set the routine environment to **Custom** network access with the `.gov` hosts. Verify — a `403 host_not_allowed` shows green in the run list (`07` §8) |
| 71–75 | SCOUT at Tier C. Read every result *and* every rejection. Tune the rubric against reality |
| 76–80 | SCOUT → Tier B. CAPTURE on one real opportunity |
| 81–85 | MATRIX on one real solicitation. **Hand-check the matrix against the document, row by row.** This is a one-time cost that buys durable trust |
| 86–90 | PRIORART on one real disclosure, if one exists. 90-day review |

### Gate 3 exit criteria
```
[ ] Counsel's answer to 0.2 is documented in writing.
[ ] SCOUT has run >=20 nights; the rejection log has been read at least twice.
[ ] SCOUT has produced zero ineligible opportunities in the queue.
[ ] MATRIX hand-verified on one real solicitation: no missed requirement, and
    every MODEL-ONLY row correctly isolated.
[ ] Zero material errors across all lanes.
```

---

## DAY 90 — THE REVIEW

Answer `08` §5 from the data. Then three decisions:

1. **Which agents earned their place?** Retire the rest. Expect to retire some;
   ten surviving is the suspicious outcome, not the good one.
2. **Where does the returned time go?** Decide deliberately. Time returned into
   more work has not served the stated purpose (`07` §9).
3. **What is the next sprint's single highest-leverage addition?** One. Not five.

---

## What this rollout deliberately refuses to do

| Refused | Why |
|---|---|
| Deploy all ten agents in week one | You would learn nothing about which ones work, and debug ten interacting failures at once |
| Start with the GovCon lane | It is the one with an unanswered legal question in front of it |
| Give any agent send authority in 90 days | The ladder in `04` §5 is 50 clean drafts per category. That math does not close inside this sprint, and rushing it is how the one unrecoverable email gets sent |
| Promise a time-savings number at day 90 | You will *measure* one. That is different, and better |
