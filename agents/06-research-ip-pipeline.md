# 06 — RESEARCH AND IP PIPELINE

Two lanes with one thing in common: **an error here is not recoverable by doing
more work later.** A fabricated citation in a defended dissertation and a patent
right destroyed by premature disclosure are both permanent.

---

## PART A — DBA LANE (LIBRARIAN)

### A1. What is actually being automated

Not the thinking. **The argument is yours** — that is the academic integrity
boundary and no agent crosses it. What is automated is the mechanical layer
underneath it:

| Automated | Not automated |
|---|---|
| Finding new literature in your domain | Deciding what it means for your argument |
| Resolving and verifying every DOI | Writing any dissertation prose |
| Checking retraction and preprint status | Choosing your theoretical frame |
| Checking a quote against the source text | Interpreting your data |
| Formatting APA 7 from verified metadata | Defending anything |
| Flagging a source that contradicts your draft | Deciding how to answer it |

### A2. Fail-closed, using code you already own

This repository contains `adjudication/citation_gate.py`,
`adjudication/doi_resolver.py` and `adjudication/quote_gate.py` (Repo-Verified).
**LIBRARIAN calls them. It does not reimplement them and it does not substitute
model judgment for them.**

The gate sequence, in order, all deterministic:

```
candidate source
   │
   ├─ resolve DOI against Crossref / PubMed / publisher ──── fails ──▶ DISCARD
   ├─ resolved record matches cited authors/year/title/venue ─ no ──▶ DISCARD
   ├─ retraction check ───────────────────────────── retracted ──▶ DISCARD (report separately)
   ├─ preprint status ──────────────────────────── preprint ──▶ label PREPRINT
   ├─ venue against your FT50 + primary-source list ── outside ──▶ DISCARD unless seminal, and say why
   └─ recency ladder: 12mo → 24mo → older only with justification
   │
   ▼
present to Andrew  (≤5 per week)
```

**"Fails closed" means discarded, not caveated.** A source that does not resolve
is not shown with a warning label — it is not shown. A caveat you read at 11pm is
a caveat you will forget by the time you cite it.

### A3. Weekly output

```
LIBRARIAN — week of <date>

CONTRADICTS YOUR DRAFT (n)              ← always first; this is the valuable part
  · <APA 7 reference>
    Contradicts: <the claim in your draft, quoted>
    What it says: <2 sentences>
    DOI resolved <date> · not retracted · <venue tier>

NEW AND RELEVANT (<=5)
  · <APA 7 reference>
    Why it matters to your argument: <2 sentences>
    DOI resolved <date> · not retracted · <venue tier>

DISCARDED (n)  — count only, with reason codes. Not a reading list.

RETRACTION WATCH
  · <any source already in your reference list that has since been retracted
     or had an expression of concern issued>
```

**The retraction watch is the quietly indispensable part.** A source you cited
correctly in 2025 can be retracted in 2027, and nothing will tell you unless
something is watching.

### A4. Hard rules

1. **Never writes dissertation prose.** Not a paragraph, not a literature review
   section, not a "draft you can edit." The line is bright because a blurry line
   here is a career risk.
2. **Never presents an unresolved citation.** No exceptions, no caveats.
3. **Never reports a source it did not retrieve this week.** No citing from
   memory — that is the precise failure the gate exists to catch.
4. **Contradicting evidence is promoted, not buried.** An agent that only returns
   supporting literature is building you a confirmation-bias machine with a
   doctoral committee waiting at the end of it.
5. **Cross-lane prohibition is absolute.** DBA work does not touch ABO, FORGE, or
   J4V data. Using client or contract data in doctoral research raises IRB,
   confidentiality, and contractual questions all at once. **If your research
   genuinely requires organizational data, that is an IRB and counsel
   conversation before it is a workflow.**

---

## PART B — FORGE IP LANE (PRIORART)

### B1. The asymmetry that sets the design

| Failure | Cost | Recoverable? |
|---|---|---|
| Prior-art search misses something | Counsel finds it; you lose time and fees | Yes, painfully |
| Agent publicly discloses an unfiled invention | Patent rights may be destroyed | **No** |
| Agent gives a patentability opinion you act on | Unauthorized practice; you act on a fabrication | **No** |

The design is therefore weighted entirely toward the second and third.

### B2. The disclosure pipeline

```
invention disclosure (you write it — in a PRIVATE repository)
   │
   ▼
PRIORART assembles:
   · classification guesses (CPC/USPC) with reasoning
   · patent + published-application search, coverage stated
   · non-patent literature search, coverage stated
   · closest art, compared claim element by claim element
   · features for which no anticipating reference was found
   · COVERAGE GAPS: what was not searched and why
   │
   ▼
packet → registered patent practitioner       ← the only next step
   │
   ▼
counsel decides.  Filing is a one-way door and a human hand is on it.
```

### B3. Three rules, none negotiable

**1. No patentability opinion, no probability, ever.**
Not "likely patentable." Not "strong claim." Not a percentage, not a confidence
interval, not a Six Sigma figure, not an MTBE. Two independent reasons:
patentability is a legal opinion requiring a registered practitioner, and a
probability without a dataset and a shown calculation is a fabricated number.
PRIORART reports what it found and what it did not find, and states explicitly:
**absence of found art is not evidence of novelty.** **Professional verification
required.**

**2. No public disclosure of an unfiled invention, by any agent, anywhere.**
Not a public repository. Not an issue, PR title, or commit message. Not a
published artifact. Not a third-party service whose terms permit training on
input. **Not this repository** — check whether it is public before any disclosure
touches it. Concretely:

- Invention disclosures live in a **private** repository, or encrypted locally
- PRIORART's routine runs against that private repository only
- No PRIORART output is ever posted to a public PR or issue
- Before pointing any agent at disclosure material, confirm that vendor's data
  handling terms in writing. **Unknown for every vendor until you check.**

**3. Coverage is always stated.** Which databases, which date range, which
classifications, which languages. A search whose coverage is unstated reads as
complete and never is.

### B4. What PRIORART is genuinely good for

Honest framing: it will not replace a professional search. What it does well is
**kill bad ideas early and cheaply**. If a thirty-minute automated sweep finds
art that plainly anticipates your concept, you have saved counsel's fees and
weeks of your own time. If it finds nothing, you have learned almost nothing —
and it must say so in exactly those terms rather than implying a clear field.

### B5. Invention capture — the part that actually returns time

The real IP loss in a founder's week is not search cost. It is **inventions that
were never written down.** A `disclosure/` folder in a private repository, with a
fixed template and a routine that reminds you when one is stale, is low-effort
and high-consequence:

```
disclosure/YYYY-MM-DD-short-name.md
  · Problem
  · What is new (one paragraph, plain language)
  · How it works (enough that an engineer could build it)
  · First conceived (date) · First written (date) · Disclosed to (names, dates)
  · Public disclosure to date: NONE | <describe — and note that this may have
    started a bar clock. COUNSEL, immediately.>
  · Related work known to you
```

That dated record is evidence. Building the habit is worth more than any agent
in this file.
