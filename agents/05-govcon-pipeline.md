# 05 — GOVCON PIPELINE

The ABO and Just4Veterans lanes. Opportunity → gate → capture → compliance.

> **Two standing warnings before anything below is used.**
>
> 1. **All API details in this file are Unverified.** `open.gsa.gov` returned
>    `EGRESS_BLOCKED` from this session's proxy, so I could not confirm endpoint
>    shapes, key requirements, parameter formats, or rate limits. Every one is a
>    `FILL-IN` to be completed from the source, in exactly the discipline your
>    `adjudication/profiles.example.json` already demands (Repo-Verified): *"Do
>    not write one from memory or from another project."*
> 2. **Nothing here is legal or acquisition advice.** Eligibility, set-aside
>    qualification, size standards, affiliation, joint-venture structure, and
>    anything touching CUI are matters for counsel. **Professional verification
>    required.**

---

## 1. The pipeline

```
  SCOUT (nightly)                 ┌── NO ──▶ logged with reason, never shown
    sweep → 7 eligibility gates ──┤
                                  └── clears ──▶ ranked queue (Tier B, 60 sec)
                                                    │
                                          you say GO │
                                                    ▼
  CAPTURE (on demand, one at a time)
    incumbent · award history · competitors · teaming · CASE FOR NO-BID FIRST
                                                    │
                                        bid decision │  ← Tier C. Yours.
                                                    ▼
  MATRIX (on bid decision)
    deterministic extraction  →  model classification  →  requirement matrix
                                                    │
                                                    ▼
  YOU + your team write the proposal.  No agent writes proposal prose. (§5)
```

---

## 2. Sources — all Unverified, all to be confirmed at the source

| Source | Purpose | Status |
|---|---|---|
| **SAM.gov** Get Opportunities | Active solicitations | **Unverified.** Confirm base URL, whether an api.data.gov key is required, date-range parameter format and span limit, rate limits |
| **SAM.gov** Entity Management | Registration, socio-economic status, size | **Unverified.** Confirm whether sensitive data requires a separate role/agreement |
| **FPDS** | Award history, incumbency | **Unverified** |
| **USASpending** | Award values, subaward relationships | **Unverified** |
| **Agency forecasts** | Pre-solicitation visibility | **Unknown** — varies by agency; identify your target agencies first |
| **Acquisition.gov** (FAR/DFARS) | Clause lookup | **Unverified** |

**Before SCOUT runs even once**, complete `agents/prompts/SOURCES-GOVCON.md`
(committed as a `FILL-IN` stub) from each provider's own published documentation,
and record the retrieval date beside each value. A stale endpoint that returns
200 with a changed response shape produces *"a seat that had nothing to say
rather than a seat that was never asked"* — your own words, and the exact failure
this convention prevents.

**Network note:** a Claude Code routine's environment must allow these hosts. The
Default environment's **Trusted** network access permits only a default allowlist
and *"Requests on that path to hosts outside the allowlist fail with `403` and
`x-deny-reason: host_not_allowed`"* (Docs-Verified, `code.claude.com/docs/en/cloud-environments`
via the routines page, retrieved 2026-09-14). Set the routine's environment to
**Custom** with the `.gov` hosts listed, rather than **Full**.

---

## 3. SCOUT output — the sixty-second artifact

One card per opportunity that cleared. **An empty queue is the expected output
most nights and is reported as a success, not a failure.**

```
[STRONG FIT]  <title>
  Solicitation  <number>          Agency  <agency>
  NAICS <code>  ·  Set-aside <type>  ·  Response due <date>  (<n> business days)
  Ceiling/value <as stated in the notice, verbatim — never estimated>

  WHY IT CLEARED   <=3 bullets, each tied to a gate in 02 §2
  WHY IT MIGHT NOT <the strongest objection, always present>
  UNKNOWN          <what SCOUT could not determine>

  [ CAPTURE ]   [ PASS ]   [ ASK: ______ ]
```

**Rules SCOUT operates under:**

- **No Pwin. No win probability. No expected value. No score out of 100.** A
  probability requires a dataset and a shown calculation, and SCOUT has neither.
  It classifies and gives reasons.
- **Ceiling and value are quoted verbatim from the notice or omitted.** Never
  interpolated, never "approximately."
- **A gate failure ends the analysis.** Ineligible means `NO` at gate 1; SCOUT
  does not spend tokens analyzing fit for work you cannot legally bid.
- **Every rejection is logged with its reason.** The rejection log is how you
  find out the rubric is wrong — if genuinely good opportunities keep dying at
  gate 3, the rubric needs editing, and you can only see that from the log.

---

## 4. MATRIX — the compliance matrix

The highest-leverage automation in this lane. A technically excellent proposal
thrown out for non-compliance is the most expensive avoidable failure in
government contracting, and the work of preventing it is almost entirely
mechanical.

**Two passes, in this order, and the order is the safety property:**

**Pass 1 — deterministic extraction (code, not a model).**
Section boundaries; every imperative ("shall", "must", "will provide", "is
required to"); every Section L instruction; every Section M factor and subfactor;
page/paragraph anchors; amendment deltas against the base document. Output is a
row set with provenance. **A model is not consulted in this pass.**

**Pass 2 — model classification (organizes; never adds).**
Assigns each extracted row a type, a proposal volume, an owner, and a suggested
response location. Flags conflicts between L and M, and between an amendment and
the base.

**The gate between them:**

> **A requirement the model believes exists but Pass 1 did not find is emitted to
> a `MODEL-ONLY` sheet, never merged into the matrix.**

A missed requirement is a known, recoverable risk that a human review pass will
catch. A *hallucinated* requirement is worse: it silently directs a proposal team
to write a response to something nobody asked for, and nobody catches it because
it looks exactly like the real rows. The `MODEL-ONLY` sheet makes that class of
error visible instead of invisible.

**Matrix schema:**

| Column | Source |
|---|---|
| `ID` | Generated, stable |
| `Source` | Section, page, ¶ — from Pass 1 provenance |
| `Requirement` | **Verbatim.** Never paraphrased |
| `Type` | L / M / C / PWS / SOW / Attachment |
| `Volume` | Pass 2 |
| `Owner` | You assign |
| `Status` | Not started / Drafted / Reviewed / Complete |
| `Response location` | Volume, section, page |
| `Provenance` | `EXTRACTED` or `MODEL-ONLY` |

**Never automated:** whether a response is *adequate*. MATRIX confirms a row is
addressed somewhere. Whether what is written will win is a human judgment and
stays one.

---

## 5. What no agent does in this lane

| Never | Why |
|---|---|
| **Submit anything to SAM.gov or any Government portal** | One-way door to the Government |
| **Write proposal prose that goes out under your name** | It is a representation to the Government, and your past performance narrative must be true in a way only you can certify |
| **Represent size, socio-economic status, or eligibility** | A false certification is a False Claims Act exposure. **Counsel.** |
| **Contact a CO, COR, or agency personnel** | See `04` §4 |
| **Handle CUI or source-selection-sensitive material through a vendor cloud agent** | `07` §2. **Legal question, not a hardware question. Contracts counsel, before the first run.** |
| **Negotiate or agree terms with a teaming partner** | Pre-contractual and binding sooner than people think |
| **Produce a win probability** | No dataset, no calculation, no number |

---

## 6. Just4Veterans — a different duty

Work in the J4V lane is performed as a **1099 Chief Business Development Officer
for another company** (Stated, resume). Two consequences the ABO lane does not
have:

1. **Their pipeline data is not yours.** It does not enter ABO's workspace, an
   ABO agent's context, or any shared store. Separate lane, separate everything.
2. **Your 1099 agreement may restrict tooling, data handling, or disclosure.**
   **Read it before pointing an agent at their data.** If it is silent, ask them
   in writing. An agent processing a client's pipeline through a third-party
   cloud service is a conversation to have *before* it happens, not after.
