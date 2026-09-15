# 22 — DMADV: PATENT ALLOWANCE READINESS

**Scope:** FORGE LINK's IP lane. Design a pre-filing process that removes
self-inflicted rejections before an examiner ever sees them.

> **PROFESSIONAL VERIFICATION REQUIRED throughout.** Patentability is a legal
> determination reserved to a registered practitioner. Nothing here is legal
> advice, and no agent in this design files, argues, amends, or contacts the
> USPTO.

---

## 0. The request contained a contradiction. Resolving it, once.

You asked for two things that cannot both be honoured:

| You asked for | Status |
|---|---|
| *"Do not lie, embellish, hallucinate or drift"* | **Honoured absolutely** |
| *"updated statistical probabilities of success in percentages"* | **Refused** |
| *"10 rigorously peer-reviewed scholarly articles found on Google Scholar"* | **Partially — as an unverified queue, not as references** |

**Why no percentage.** Your own `AGENTS.md`, which governs this repository:
*"No success percentage, probability, Pwin, confidence interval or expected value
without a real dataset and a shown calculation."* There is no dataset. USPTO,
PatentsView, Google Scholar and every scholarly index were unreachable from this
session. And allowance prediction is a legal opinion requiring standing I do not
have. **A percentage here would be the precise failure the whole system exists to
prevent — and it would be the one you could least afford, because you would act
on it.**

**What replaces it, and why it is better than a number I would have to invent:**

1. A **readiness score** — a real count over a real checklist, arithmetic shown,
   re-computable: `scripts/patent_readiness.py`.
2. **The procedure for obtaining a genuine base rate** from someone who can
   lawfully give you one (§5.3).
3. **Five new agents** that remove the defect classes an applicant actually
   controls.

**Why no fabricated bibliography.** You hold a doctorate in progress. A
fabricated citation in your hands is a career risk, not a formatting error. Ten
honestly labelled candidates in §6 beat ten references I cannot stand behind.

---

## 1. DEFINE

### 1.1 The problem, stated so it can be solved

**Patent allowance is not one thing.** It decomposes into rejection classes, and
they are not equally controllable:

| Rejection basis | Who controls it | Controllable pre-filing? |
|---|---|---|
| **§112(b)** definiteness, antecedent basis | **The applicant, entirely** | **Yes — fully mechanical** |
| **§112(a)** written description, enablement | The applicant, largely | **Yes — largely mechanical** |
| **§101** eligibility | Applicant drafting + examiner + case law | **Partly — by how claims are framed** |
| **§102** novelty | The prior art, which exists regardless | **No — but knowable before filing** |
| **§103** obviousness | Examiner judgement on combinations | **No — but anticipable** |
| Duty of candor (37 CFR 1.56) | **The applicant, entirely** | **Yes — and it is unforgiving** |

> **The design target is therefore not "increase the probability of allowance."
> It is: eliminate every rejection the applicant caused.** Those are the only
> ones an applicant can remove, and they are removable to zero.

### 1.2 CTQs — critical to quality

Ten, in `agents/analysis/patent-readiness-checklist.json`, 41 checkable items:
§101 · §112(a) · §112(b) · §102 · §103 · candor · claim scope · prosecution
strategy · inventorship · evidentiary record.

### 1.3 The dominant risk for *this* subject matter

FORGE LINK is a **mobile talent application with AI features** — hiring,
matching, ranking. That is squarely inside the technology where §101 bites
hardest: *organising human activity, implemented on a generic computer*.

Search reported that in USPTO TC working group 2120 (AI and simulation modelling)
**77% of office actions now include a §101 rejection**, and that post-*Alice*
allowance rates for AI-containing applications fell relative to non-AI ones.
**Both Unverified — search snippets only, USPTO unreachable.** But the direction
is consistent across independent snippets, and the design cost of assuming it is
low while the cost of ignoring it is high. **§101 is treated as the primary
CTQ.**

---

## 2. MEASURE

### 2.1 What is measurable before filing

| Measurable | How | Mechanical? |
|---|---|---|
| Claim terms lacking spec support | String resolution, claims → spec | **Yes** |
| Antecedent-basis breaks | "the X" with no prior "a X" | **Yes** |
| Functional terms with no disclosed algorithm | Pattern + spec search | **Yes** |
| Independent claim word count and count | Count | **Yes** |
| Claim elements absent from every found reference | Element-by-element matrix | Semi |
| §101 risk patterns | Result-language without mechanism | Semi |
| Public activity older than 12 months | Date inventory | **Yes** |
| Candor inventory completeness | Enumeration | **Yes** |

### 2.2 What is not measurable here, and is not guessed

```
probability of allowance ......... needs USPTO art-unit data + counsel. NOT HERE
this examiner's tendencies ....... needs examiner data. NOT HERE
whether a claim is eligible ...... legal determination. NOT MINE
whether art anticipates .......... legal determination. NOT MINE
```

### 2.3 The measurement system

```bash
python3 scripts/patent_readiness.py                # score one disclosure
python3 scripts/patent_readiness.py --probability  # prints the refusal and why
```

**Current template score: `0 / 41 = 0.000`, with 15 BLOCKING items open.** That
is correct — no disclosure has been assessed. **An empty instrument reading zero
is honest; an instrument reporting a number before it has data is not.**

The script refuses `--probability` with three reasons and one warning: **never
multiply a readiness score by a base rate.** They are not independent and the
product would mean nothing.

---

## 3. ANALYZE

### 3.1 Where allowance is actually lost

| Loss mode | Root cause | Controllable | Current coverage |
|---|---|---|---|
| §112 rejection on a self-inflicted defect | No mechanical pre-filing check | **Fully** | **NONE → SPEC-WARDEN** |
| §101 rejection on result-style claiming | Claims recite *what*, not *how* | **Largely** | **NONE → ELIGIBILITY-SCOUT** |
| §103 combination nobody anticipated | No pre-filing element matrix | Partly | **NONE → ART-DELTA** |
| Unenforceability from a candor failure | No disclosure inventory | **Fully** | **NONE → IDS-WARDEN** |
| Extra office-action rounds | Interview treated as a last resort | **Fully** | **NONE → INTERVIEW-PREP** |
| **Rights destroyed by public disclosure** | **This repository is PUBLIC** | **Fully** | Prose only — `FM-04`, still order-1 |
| Statutory bar from forgotten public activity | No dated activity inventory | **Fully** | **NONE → IDS-WARDEN** |

**Six of seven loss modes had no agent at all.** The IP lane had exactly one
agent — PRIORART — which searches. Searching is upstream of every row above.

### 3.2 The inversion

*It is three years on and the application was abandoned. Why?*

```
1  §101 final rejection: claims recited a result, never a mechanism
2  §112(a): a functional term had no algorithm; the amendment needed new matter
3  A statutory bar: a 2025 pitch deck nobody inventoried started the clock
4  A candor problem: agent search logs were never handed to counsel
5  It was never filed - the disclosure was never written down    <-- likeliest
```

**Item 5 is the same failure mode as `FM-24`** and it is again the most probable
one. `PRIORART`'s §B5 already said it: *the real IP loss is inventions never
written down.*

---

## 4. DESIGN

### 4.1 Five new agents — added, none removed

| Agent | Closes | Tier |
|---|---|---|
| **[ELIGIBILITY-SCOUT](cards/eligibility-scout.md)** | §101 result-style claiming, the dominant risk for AI/talent subject matter | C |
| **[SPEC-WARDEN](cards/spec-warden.md)** | §112(a)+(b) — the fully mechanical, fully self-inflicted class | B |
| **[ART-DELTA](cards/art-delta.md)** | §102/§103 — the element-by-element matrix, and the §103 combination written against you | C |
| **[IDS-WARDEN](cards/ids-warden.md)** | Duty of candor and the statutory-bar clock | C |
| **[INTERVIEW-PREP](cards/interview-prep.md)** | Extra prosecution rounds | B |

**Roster: 24 agents + 2 protocols → 29 agents + 2 protocols.**

### 4.2 The boundary every one of them holds

```
NEVER drafts or amends a claim ......... practice of law
NEVER opines on patentability .......... legal determination
NEVER emits a probability .............. no dataset, no standing
NEVER decides materiality .............. counsel decides
NEVER contacts the USPTO ............... counsel files, counsel calls
NEVER touches a public repository ...... FM-04 is still an order-1 cut set
```

### 4.3 The pipeline

```
disclosure written (PRIVATE store)          <- the step most often skipped
   -> IDS-WARDEN      inventory + bar-clock check    ESCALATES if >12 months
   -> PRIORART        search, coverage stated
   -> ART-DELTA       element matrix; the delta; the §103 case against you
   -> ELIGIBILITY-SCOUT   §101 flags
   -> SPEC-WARDEN     §112 mechanical gate
   -> patent_readiness.py  -> BLOCKING items open?  DO NOT FILE
   -> COUNSEL                                  <- the only path to the USPTO
   -> [office action] -> INTERVIEW-PREP -> COUNSEL runs the call
```

### 4.4 The one design change that is not an agent

**Move invention disclosures to a private repository today.** `FM-04` remains an
**order-1 cut set on prose**: one commit to this public repository can destroy a
patent right, and the redaction guard **cannot** detect an invention disclosure
because "this paragraph describes an unfiled invention" has no pattern.

**No agent closes this. A repository setting does.**

---

## 5. VERIFY

### 5.1 How each new agent gets verified

Each card carries acceptance tests, including a planted-defect test — a planted
antecedent break for SPEC-WARDEN, a planted result-style claim for
ELIGIBILITY-SCOUT. **CANARY runs them monthly.** An agent that stops catching its
planted defect is blind, and a blind IP agent is worse than none.

### 5.2 The verification that matters most

**Counsel reviews the first packet end to end**, and the honest question is put
to them: *did this save you time, or did it create work?* If it created work,
the design is wrong and no further agent fixes it.

### 5.3 How to obtain a real allowance figure — the procedure I can give you

```
1  Counsel identifies the likely art unit from the classification.
2  Counsel obtains that art unit's allowance rate from USPTO data or a
   prosecution-analytics service. THIS IS A REAL BASE RATE.
3  Counsel forms a case-specific judgement against it. THIS IS A LEGAL OPINION.
4  The readiness score stays a SEPARATE second number.
   DO NOT MULTIPLY THEM. They are not independent; the product is meaningless.
```

**That is the only honest route to a percentage, and the person at the end of it
is not me.**

---

## 6. THE TEN SOURCES — a verification queue, honestly labelled

**None of these is verified.** Google Scholar, Crossref, PubMed, arXiv, SAGE,
NeurIPS, OpenAlex, Semantic Scholar, Europe PMC, DOAJ, USPTO, PatentsView and
Federal Register were **all unreachable** from this session. Every row below is a
**search-result snippet**. Run each through `.claude/agents/citation-verifier.md`
before it informs a decision or enters a document.

**And a distinction your standard demands:** you asked for *rigorously
peer-reviewed* articles. **Most of these are not.** Law reviews are
student-edited, not peer-reviewed. NBER and USPTO Economic Working Papers are
working papers. CRS reports and USPTO reports are government documents. **By the
strict standard, only the *Research Policy* entries qualify as peer-reviewed
journal articles.** Saying so is more useful than padding the list.

| # | Candidate | Claimed finding (snippet) | Type | Label |
|---|---|---|---|---|
| **P1** | Frakes & Wasserman, *"Irrational Ignorance at the Patent Office"*, **Vanderbilt Law Review** | 1.4M applications via FOIA; as examination time roughly halves (GS-7→GS-14), grant rates rise **9–19 percentage points**; ~19 hours average examination | Law review — **not peer-reviewed** | **Unverified** |
| **P2** | Frakes & Wasserman, **NBER w20337**, *"Is the Time Allocated to Review Patent Applications Inducing Examiners to Grant Invalid Patents?"* | Micro-level application data; time allocation vs. grant behaviour | Working paper | **Unverified** |
| **P3** | Frakes & Wasserman, **NBER w27579**, evidence from pharmaceutical patent examination | Examination scrutiny and outcomes | Working paper | **Unverified** |
| **P4** | Marco, Sarnoff & deGrazia, *"Patent Claims and Patent Scope"*, **Research Policy 48(9)**; also USPTO Economic Working Paper 2016-04 | Independent claim **length** and **count** as validated scope measures; **prosecution narrows scope** on both | **Peer-reviewed journal** | **Unverified** |
| **P5** | *"Examination incentives, learning, and patent office outcomes: the use of examiner's amendments at the USPTO"*, **Research Policy** | Examiner amendments, incentives and outcomes | **Peer-reviewed journal** | **Unverified** |
| **P6** | Tu, S. S., *"Patent Examination and Examiner Interviews"*, SSRN 3725770 / WVU | ~**1.1M applications**, 2007–Jun 2020; interviewed cases ~**2.0** office actions to allowance vs ~**3.6** for the same examiners | Law review / working paper | **Unverified** |
| **P7** | USPTO Office of the Chief Economist, *"Adjusting to Alice"* | Post-*Alice* allowance rates fell in Alice-affected technologies; treatment/control design | Government report | **Unverified** |
| **P8** | USPTO, *"Patent Eligible Subject Matter: Report on Views and Recommendations"* | §101 practice and stakeholder views | Government report | **Unverified** |
| **P9** | CRS, *"Patent-Eligible Subject Matter Reform: An Overview"* (IF12563), **Congress.gov** | §101 doctrine and reform proposals | Government primary — **on your approved list** | **Unverified** |
| **P10** | Metro, Moshiri & Avery, *"Impact of Prosecution Length on Patent Litigation Outcomes"*, **Harvard JOLT v38** | Prosecution length vs. downstream litigation outcomes | Law review | **Unverified** |

**How each shaped the design** — and note that *none* was used to produce a
number:

- **P4** → the readiness checklist *records* independent claim length and count.
  It sets **no target**, because the snippet reports what prosecution *does*, not
  what an applicant *should* do.
- **P6** → INTERVIEW-PREP exists, and the interview is the **default** first
  response rather than a last resort. Cost of being wrong: one phone call.
- **P7/P8/P9** → §101 is the **primary CTQ** for this subject matter.
- **P1/P2/P3** → the sober reading: **examiner variance is real and outside your
  control.** The response is to control what you can, not to model the examiner.

---

## 7. THE HONEST BOTTOM LINE

| Question | Answer |
|---|---|
| **Updated probability of allowance?** | **None. Refused, with three reasons and a route to a real one (§5.3)** |
| **What actually improved?** | Six of seven controllable loss modes went from **no coverage** to a named agent with tests |
| **Readiness score today** | **0 / 41**, 15 BLOCKING — because no disclosure has been assessed |
| **Biggest remaining IP risk** | **`FM-04`** — this repository is public and no gate can detect a disclosure. A private repo closes it today |
| **Likeliest failure** | **The disclosure never gets written.** Same shape as `FM-24`. No agent fixes it |

**What raises the odds of allowance, in the only sense I can defend:** write the
disclosure down, put it somewhere private, inventory every public date before the
clock runs out, and take the whole packet to a registered practitioner. **The
five new agents make that packet better. They do not make it legal, and they do
not make it certain.**
