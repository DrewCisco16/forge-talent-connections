# 02 — AGENT ROSTER

Ten agents. Each entry is a contract: charter, trigger, inputs, output shape,
Trust Tier, escalation, and the failure it is built to prevent.

**Reading the tier column:** Tier is the *starting* tier. Promotion is per
category and earned against measurement (`01-operating-model.md` §2).

| # | Agent | Lane(s) | Start tier | Cadence |
|---|---|---|---|---|
| 1 | MAILROOM | all five, isolated instances | C → B | hourly |
| 2 | SCOUT | ABO, J4V | B | nightly |
| 3 | CAPTURE | ABO, J4V | C | on demand |
| 4 | MATRIX | ABO, J4V | B | on demand |
| 5 | LIBRARIAN | DBA | B | weekly |
| 6 | PRIORART | FORGE | C | on demand |
| 7 | BUILDER | FORGE | B | event-driven |
| 8 | REVIEWER | FORGE | B | event-driven |
| 9 | NIGHTWATCH | any (one lane per run) | C | manual, cost-gated |
| 10 | STEWARD | per lane | B | weekly |

---

## 1. MAILROOM — inbox triage and draft reply

**Prevents:** the two hours a day that disappear into an inbox, and the reply you
sent at 11pm that you should not have sent.

| | |
|---|---|
| **Charter** | Read every unread thread in one mailbox. Classify. Draft replies for the drafts folder. **Never send.** |
| **Trigger** | Scheduled, hourly (the floor — see `03` §2) |
| **Inputs** | One mailbox only. Calendar read for scheduling questions. Nothing from another lane |
| **Tools** | Gmail or Superhuman connector (read, label, create draft). **Not** `send_message`, **not** `send_draft`, **not** `trash` |
| **Output** | Labels applied in-place + drafts in the drafts folder + one digest |
| **Tier** | **C at launch. B after two weeks of clean classification. A only for the narrow categories in `04` §5** |
| **Escalates when** | Anything on the never-auto-send list (`04` §4), any monetary figure, any deadline inside 48h, any sender it cannot place |

Full protocol in [`04-mailroom-sop.md`](04-mailroom-sop.md).

---

## 2. SCOUT — opportunity surveillance

**Prevents:** manually scanning federal opportunity feeds, and the far worse
failure of missing a fit because you were scanning the day it posted.

| | |
|---|---|
| **Charter** | Sweep federal opportunity sources nightly. Score every hit against a fixed, written eligibility and fit rubric. Return only what clears the gate. |
| **Trigger** | Scheduled, nightly |
| **Inputs** | SAM.gov opportunities; agency forecasts; award history for context. **All endpoint details Unverified — see `05` §2** |
| **Output** | A ranked queue. **Default output is the empty queue, and an empty queue is a good night.** |
| **Tier** | B — each entry must pass the sixty-second test |
| **Escalates when** | Response deadline < 10 business days; requires a facility clearance or certification you do not hold; a sole-source or 8(a) set-aside you are ineligible for |

**Hard rule.** SCOUT does not estimate win probability, Pwin, or an expected
value. Those are numbers, and per your standing rule a number requires a real
dataset and a shown calculation. SCOUT has neither. It emits a **fit
classification** (`STRONG FIT` / `PLAUSIBLE` / `STRETCH` / `NO`) and the
**specific reasons**, and it names what evidence would move the classification.

**Scoring rubric (fixed, versioned, auditable — edit it deliberately, not per-run):**

| Gate | Question | Fail = |
|---|---|---|
| 1. Eligibility | Set-aside, socio-economic status, size standard, registration | `NO`, immediately, no further analysis |
| 2. NAICS / PSC | Does it match a code you actually perform under? | `NO` unless a teaming path is named |
| 3. Past performance | Do you have citable, relevant past performance? | `STRETCH`, and the gap is named |
| 4. Capacity | Can the work be delivered with people you can actually field? | `STRETCH`, and the shortfall is named |
| 5. Clearance / facility | Required and held? | `NO` if required and not held |
| 6. Economics | Is the ceiling worth the bid cost? | `NO` if bid cost plausibly exceeds the realistic margin |
| 7. Deadline | Enough calendar to produce a compliant response? | Escalate |

---

## 3. CAPTURE — pre-bid intelligence

**Prevents:** bidding blind against an entrenched incumbent.

| | |
|---|---|
| **Charter** | For one opportunity that SCOUT cleared: incumbent, award history, likely competitors, teaming candidates, and the honest case *against* bidding |
| **Trigger** | On demand, one opportunity at a time. Never batch |
| **Inputs** | The solicitation; public award history; public registrations. Public sources only |
| **Output** | A capture brief that **leads with the strongest argument for NO-BID** |
| **Tier** | **C.** Bid/no-bid commits real money and real weeks. It is a Tier C decision and stays one |
| **Escalates when** | Always — that is the point. CAPTURE assembles; you decide |

**Inversion requirement.** Section 1 of every capture brief is *"The case for
no-bid"*, written at full strength before anything favorable appears. An agent
that only argues for the bid is a cheerleader, and you are paying for a
red team.

---

## 4. MATRIX — compliance matrix construction

**Prevents:** the single most expensive avoidable GovCon failure — a
non-compliant proposal thrown out before anyone reads the technical volume.

| | |
|---|---|
| **Charter** | Parse a solicitation into a complete requirement matrix. Every "shall", "must", "will provide", every Section L instruction, every Section M evaluation factor, each as a row with its source citation |
| **Trigger** | On demand, on bid decision |
| **Inputs** | The solicitation document and every amendment |
| **Output** | A spreadsheet: `ID | Source (section, page, ¶) | Requirement verbatim | Type (L/M/C/PWS) | Volume | Owner | Status | Response location` |
| **Tier** | B — but see the gate below |
| **Escalates when** | Any requirement it cannot classify, any ambiguity between an amendment and the base solicitation, any conflict between L and M |

**Mechanical gate before model judgment** (`01` §5). MATRIX runs a deterministic
extraction pass first — regex for the imperative verbs, section boundaries, page
and paragraph anchors — and the model pass may only *classify and organize* what
the mechanical pass found. **A row that the model added but the mechanical pass
did not find is flagged, not silently included.** A requirement invented into a
compliance matrix is worse than a requirement missed: it sends the proposal team
to write a response to something nobody asked for.

**Never automated:** the *adequacy* judgment. MATRIX says the row exists and
where the response lives. Whether the response is any good is a human call.

---

## 5. LIBRARIAN — literature surveillance (DBA)

**Prevents:** a fabricated or retracted citation reaching your dissertation. That
is the one error in the DBA lane with no recovery path.

| | |
|---|---|
| **Charter** | Weekly sweep of new literature in your dissertation domain. Every candidate passes the citation integrity gate before it is shown to you |
| **Trigger** | Scheduled, weekly |
| **Inputs** | Scholarly indexes only — Crossref, PubMed, Semantic Scholar, and the FT50 venue list in your standing preferences |
| **Output** | ≤5 items per week, each with a resolved DOI, a retraction/preprint status, and two sentences on why it matters to your argument |
| **Tier** | B |
| **Escalates when** | A new source materially contradicts a claim already load-bearing in your draft. **That is a finding, and it gets escalated loudly rather than buried** |

**Route into what you already have.** This repository already contains
`adjudication/citation_gate.py`, `adjudication/doi_resolver.py` and
`adjudication/quote_gate.py` (Repo-Verified). LIBRARIAN calls those. It does not
reimplement them, and it **fails closed**: a DOI that does not resolve is not
presented with a caveat, it is not presented at all.

**Hard rule.** LIBRARIAN never writes dissertation prose. It surfaces and
verifies sources. The argument is yours — that is not a workflow preference, it
is the academic integrity boundary.

---

## 6. PRIORART — IP landscape and disclosure intake

**Prevents:** spending a year and counsel's fees on a claim that a 2019 patent
already covers — and prevents the reverse, destroying a patent right by
disclosing publicly before filing.

| | |
|---|---|
| **Charter** | (a) Take an invention disclosure and assemble a prior-art packet for counsel. (b) Watch for new filings in your technology space |
| **Trigger** | On demand for (a); monthly for (b) |
| **Inputs** | USPTO full-text and assignment data, published applications, non-patent literature. **Endpoint details Unknown — verification task in `10`** |
| **Output** | A prior-art packet: references found, closest art with claim-level comparison, and the specific features that appear unanticipated |
| **Tier** | **C, permanently** |
| **Escalates when** | Always, to counsel |

**Three hard rules, and none of them are negotiable:**

1. **No patentability opinion. No probability. Ever.** Not "likely patentable,"
   not a percentage, not a confidence interval. That is a legal opinion, it
   requires a registered practitioner, and per your standing rule a probability
   requires a dataset and a shown calculation. PRIORART reports *what it found*
   and *what it did not find*, and states plainly that absence of found art is
   not evidence of novelty. **Professional verification required.**
2. **No public disclosure, by any agent, of any unfiled invention.** Not in a
   public repository, not in an issue, not in a PR description, not in a
   published artifact, not to a third-party service whose terms permit training
   on input. This is the FORGE lane's one-way door.
3. **A prior-art search is never complete.** PRIORART states its coverage — which
   databases, which date range, which classifications — so the gaps are visible
   rather than implied away.

---

## 7. BUILDER — software implementation (FORGE LINK)

**Prevents:** you personally writing the mechanical 80% of the talent
application's code and CI plumbing.

| | |
|---|---|
| **Charter** | Take a well-specified issue. Produce a **draft** PR with tests and a description tied to the issue |
| **Trigger** | Event-driven — a GitHub issue labeled `agent:build` |
| **Inputs** | One repository, one issue, the repo's own conventions |
| **Output** | A draft PR. Never a merge |
| **Tier** | B — draft PR is decision-ready and reviewable at a glance |
| **Escalates when** | The issue is underspecified (it asks, it does not guess); the change touches auth, payments, PII, or a published API contract; tests cannot be made to pass honestly |

**Hard rules.**
- **Never merges. Never pushes to `main`.** One-way door.
- **Never disables, skips, or quarantines a test to get green.** A test made to
  pass by deletion is a lie told in source control.
- **Underspecified issue → question, not guess.** The failure to design against
  is the agent that produces 600 confident lines implementing the wrong thing.

**Substrate note.** This is the one role where you have a genuine two-vendor
option — Claude Code and OpenAI Codex. `03` §4 covers how to run both without
coupling the design to either. **The Codex side is Unverified in this session.**

---

## 8. REVIEWER — adversarial verification

**Prevents:** the builder grading its own homework. This is the highest-value
agent in the roster and the one most often skipped.

| | |
|---|---|
| **Charter** | Review BUILDER's diff as a hostile reviewer. Find the failure case. Never fix it |
| **Trigger** | Event-driven — PR opened or synchronized |
| **Inputs** | The diff and the repository. **Not BUILDER's reasoning, not its session** |
| **Output** | Findings, each with a concrete failure scenario (inputs → wrong output), or an explicit "no findings" |
| **Tier** | B |
| **Escalates when** | It finds a security, data-loss, or compliance issue — those go to you directly, not into a PR comment queue |

**Why it must be a separate agent, not a second pass.** Docs-Verified
(`code.claude.com/docs/en/sub-agents`, retrieved 2026-09-14): *"Each subagent
starts with a fresh, isolated context window. It doesn't see your conversation
history, the skills you've already invoked, or the files Claude has already
read."* A model reviewing its own work in the same context is anchored on its own
reasoning and will reliably rediscover that it was right. The isolated context is
the mechanism that makes the review real.

**Hard rule: REVIEWER never edits.** Separation of proposer and checker collapses
the moment the checker starts fixing, because it then has an interest in its own
findings being correct.

---

## 9. NIGHTWATCH — hard-problem adjudication

**Prevents:** you personally grinding on a genuinely hard, high-stakes question,
and the subtler failure of one confident model answer feeling like a resolution.

| | |
|---|---|
| **Charter** | Take one hard question. Run it through the existing five-seat elimination engine. Return what survived and, more importantly, what did not close |
| **Trigger** | **Manual only, with a typed cost confirmation.** Never scheduled |
| **Inputs** | One `ask`, one lane, one cost ceiling |
| **Output** | The engine's own report: gate findings, survivors, convergence/divergence, open holes, judgment queue |
| **Tier** | C |
| **Escalates when** | Two candidates survive — the engine returns both and refuses to choose, which is correct behavior, not a defect |

**This already exists. Do not rebuild it.** Repo-Verified, `.github/workflows/adjudicate.yml`:
a `workflow_dispatch` button taking `ask`, `max_cost_usd` (default `"17.00"`) and
`confirm` (you type `SPEND`), with `concurrency: group: adjudicate` so two panels
never bill in parallel. Its own header states the reasoning: *"MANUAL ONLY... this
spends money at five vendors with real credentials. No push trigger, no schedule.
A run is something a person decided to start."*

**That constraint is correct and NIGHTWATCH inherits it.** Do not put this on a
schedule. An unattended loop against five paid vendors is how an agent system
produces a bill instead of an answer.

**When to spend on it** — see `03` §6 for the routing rule. Short version: only
when the question is *consequential*, *contested*, and *would not be settled by
one more hour of your own reading.*

---

## 10. STEWARD — the ledger

**Prevents:** the failure this whole system is most likely to suffer — running
for six months without anyone being able to say whether it worked.

| | |
|---|---|
| **Charter** | Per lane, weekly: what ran, what it produced, what you approved, what you rejected, what it got wrong, what it cost |
| **Trigger** | Scheduled, weekly (Sunday evening, so Monday starts informed) |
| **Inputs** | Run logs, approval/rejection records, the error ledger, cost data |
| **Output** | One page per lane. Trends, not events |
| **Tier** | B |
| **Escalates when** | Any agent's rejection rate rises two weeks running; any material error; cumulative spend crosses the threshold you set |

**The four numbers that matter.** Everything else is decoration:

1. **Approval rate** — Tier B artifacts approved unedited ÷ produced. Rising = the agent is learning your standard. Falling = demote it.
2. **Review minutes** — total time you spent reviewing agent output. **If this is going up, the system is failing, no matter how good the output is.**
3. **Material errors** — anything that would have caused harm if you had not caught it. Target is zero and it is not a stretch target.
4. **Cost** — vendor spend plus subscription usage drawn down.

STEWARD reports these. It does **not** report "hours saved" — that is a
calculation requiring a baseline, and `08-measurement.md` builds the baseline
before any such number is permitted to exist.

---

## Deliberately not in this roster

| Not built | Why |
|---|---|
| A cross-lane "chief of staff" | Single point of compliance failure across a government contract, a patent, a doctoral committee and your family's finances. See `01` §3 |
| An agent that sends email autonomously on day one | See `04` §4 |
| An agent that negotiates, quotes, or commits on your behalf | One-way door, permanently |
| A second research engine | You have one. Use it |
| An agent with write access to `main` | One-way door |
| A "personal assistant" agent over the HOME lane beyond mail triage | Family and financial data does not need an agent; it needs your attention. Stewardship is not a delegable function |
