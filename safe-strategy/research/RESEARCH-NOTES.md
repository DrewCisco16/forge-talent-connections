# Karpathy-Style Autoresearch Log — SAFE Strategy for Forgelink LLC

**Run date:** 2026-09-14
**Operator:** Andrew (andrew@forgetalentconnections.com)
**Method label:** "Karpathy Autoresearch" is the user's term. I could not verify a
published, formalized research protocol under that name. I am therefore treating it
as an *interpretation*: an autonomous, iterative, self-critiquing retrieval loop
(broad sweep -> targeted verification -> adversarial re-read -> gap statement).
**Evidence label for the method name itself: Assumption.**

---

## RETRIEVAL CONSTRAINT (must be disclosed in the deliverable)

This session's egress policy **blocked full-document WebFetch** on:
- `www.ecfr.gov` (CFR full text)
- `www.investor.gov` (SEC investor bulletins)
- `www.sec.gov` (SEC pages)
- `www.sbir.gov`, `www.sba.gov`
- `www.minnesotalawreview.org`

Search-engine retrieval against those domains **did** work and returned substantive
extracts. So: claims below are grounded in **retrieved search extracts of real,
named primary documents**, not in model memory — but I could **not** read the full
text of the underlying regulations end-to-end in this session.

**Consequence:** every regulatory citation in the deliverable is marked
"verify at source before relying on it." This is a real limitation, not boilerplate.

---

## FINDING 1 — The LLC / SAFE structural mismatch  [CRITICAL]

SAFEs were drafted for C-corporations that issue **stock**. An LLC issues
**membership units/interests**, not stock. Standard SAFE conversion language
("Preferred Stock") has no referent in an LLC.

- Retrieved: Polsky Center (Univ. of Chicago) SAFE FAQ; multiple practitioner sources.
- Investor-side consequence retrieved: LLC pass-through means investors receive
  **Schedule K-1**, which many institutional funds refuse.
- Label: **Evidence-Based Inference** (structural claim is consistently reported
  across retrieved sources; exact drafting fix is jurisdiction-specific).
- **Professional verification required (counsel).**

## FINDING 2 — SBIR/STTR ownership is tested on a FULLY DILUTED basis  [CRITICAL]

Retrieved from SBIR.gov eligibility material and 13 CFR 121.702 search extracts:
- Concern must be **>50% directly owned and controlled** by one or more
  **individuals** who are US citizens or permanent resident aliens (or by other
  qualifying small business concerns).
- "Individual" means an actual human, not an entity.
- **"SBA reviews equity ownership on a fully diluted basis."**
- Awardee + affiliates must not exceed **500 employees**.

**Why this is the hinge of the whole strategy:** SAFEs are convertible instruments.
On a fully diluted analysis they are counted. Raising too much SAFE money, or
routing ownership through the Wyoming holdco (an *entity*, not an individual),
can break the >50%-individual test and **disqualify the company from SBIR/STTR** —
the exact non-dilutive money that would stop the founder burning personal cash.
- Label: **PDF-Supported / regulation-grounded**, pending full-text verification.

## FINDING 3 — SBA affiliation (13 CFR 121.103)

- Affiliation exists where one party **controls or has the power to control** another;
  it does not matter whether control is exercised.
- Power to control presumed at **50%+ ownership**; can exist with **considerably less**
  via contractual arrangement.
- SBA considers ownership, management, prior relationships, contractual relationships.
- Size = the concern **plus all domestic and foreign affiliates**.
- Implication: investor consent/veto rights in a SAFE side letter can create
  **negative control** -> affiliation -> size/eligibility loss.
- Label: **PDF-Supported**, pending full-text verification.

## FINDING 4 — Securities law: a SAFE IS a security

- SEC Office of Investor Education & Advocacy, *Investor Bulletin: Be Cautious of
  SAFEs in Crowdfunding*: a SAFE is **not** common stock and **not** a current
  equity stake; it converts **only if** a triggering event occurs; triggers may
  **never** occur, "leaving you with nothing"; "despite its name, a SAFE may not
  be 'simple' or 'safe.'"
- Exemption paths retrieved (SEC small-business resources):
  - **Rule 506(b)**: unlimited raise; **no general solicitation**; unlimited
    accredited investors + up to **35** non-accredited *sophisticated* investors
    per 90 days; issuer needs **reasonable belief** of accreditation.
  - **Rule 506(c)**: general solicitation **permitted**; **all** purchasers must be
    accredited AND issuer must take **reasonable steps to verify** (income via IRS
    forms, net worth via documentation dated within prior 3 months, or written
    confirmation from a registered broker-dealer, SEC-registered investment adviser,
    licensed attorney, or CPA).
  - **Form D** due within **15 days after first sale**; no SEC filing fee.
  - **Reg CF**: offering limit **$5,000,000** / 12 months; non-accredited aggregate
    investment cap **$124,000**; accredited investor limits removed.
  - **Reg A Tier 2**: up to **$75,000,000**; secondary sales up to $22.5M.
- **NSMIA** preempts state blue-sky *registration* for Rule 506 covered securities,
  but states retain **anti-fraud authority** and may require **notice filings and fees**.
- Label: **PDF-Supported**, pending full-text verification.

## FINDING 5 — Non-dilutive ladder: SBIR/STTR

- SBIR/STTR = "America's Seed Fund," coordinated by SBA, **11 participating agencies**;
  described by SBIR.gov as awarding **non-dilutive** funding.
- Eligibility: for-profit, US-located, **<500 employees**, >50% US-individual owned/controlled.
- STTR additionally requires a research-institution partner; small business performs
  **>=40%**, research institution **>=30%** of work.
- Phase I: **$50,000–$275,000**, 6–12 months (proof of concept).
- Phase II: **$750,000–$1,800,000**, ~24 months.
- Label: **PDF-Supported**, pending full-text verification. Agency-specific ceilings vary.

## FINDING 6 — Federal contracting mechanics

- **UEI** = 12-character alphanumeric, obtained at SAM.gov. Free.
- Registration required at offer, at award, and **throughout contract life**;
  **renew every 365 days**.
- UEI-only option exists (name + physical address) without full registration.
- **Current thresholds (effective Oct 1, 2025)** — FAR 2.101 inflation adjustment:
  - **Micro-purchase threshold: $15,000**
  - **Simplified acquisition threshold: $250,000** (non-commercial)
  - **$2,000,000** for commercial products/services **through Sept 30, 2027**
- ANTI-DRIFT NOTE: an early search returned **$3,500 / $150,000**. Those are
  **STALE**. Rejected. Current figures above are from acquisition.gov threshold-change
  material and GSA SmartPay bulletin.
- **Rule of Two** (FAR 19.502-2): set-aside when reasonable expectation of offers from
  **two or more** responsible small business concerns at fair market prices.
- **GSA MAS**: long-term governmentwide contract; **Cooperative Purchasing** lets
  **state and local** governments buy from MAS — this is the bridge to "city contracts."
- Size standard **NAICS 541511 (Custom Computer Programming Services): $34.0 million**
  receipts (retrieved; **verify against SBA table of size standards — this changes**).
- Label: mixed PDF-Supported / needs verification (size standard especially).

## FINDING 7 — Scholarly empirical base

1. **Coyle, J. F., & Green, J. M. (2018). The SAFE, the KISS, and the Note: A Survey
   of Startup Seed Financing Contracts.** *Minnesota Law Review Headnotes, 103*, 42.
   - Method: online survey with Thomson Reuters Practical Law, spring/summer 2018.
   - Sample: **300+ startup lawyers**, **32 US states + 4 Canadian provinces**.
   - First systematic documentation of the spread of the deferred equity agreement
     across the US and Canada; findings cast doubt on the traditional
     "East Coast vs West Coast" startup-lawyering distinction.
   - Label: **Empirical Finding**.

2. **Green, J. M., & Coyle, J. F. (2016). Crowdfunding and the Not-So-Safe SAFE.**
   *Virginia Law Review Online, 102*, 168. SSRN abstract 2830213.
   - Core argument: widespread SAFE use in crowdfunding may **frustrate investors'
     ability to share in upside**, because many issuers will **never raise
     institutional VC** — so the conversion trigger never fires.
   - **Directly on point for Forgelink**: a govtech company selling to cities and
     agencies may never do a classic priced VC round. Retrieved via Virginia Law
     Review + SSRN + Harvard Law School Forum on Corporate Governance.
   - Label: **Empirical/Doctrinal Finding**.

3. **Coyle & Green, Contract as Swag**, *Penn State Law Review* (p. 353). Retrieved,
   not yet substantively mined. Lower priority.

## FINDING 8 — Business survival base rates (US BLS, Business Employment Dynamics)

- ~**20%** of new establishments do not survive year 1.
- ~**32%** do not survive 2 years (i.e., **66%** still exist after 2 years).
- ~**44%** still operating after 4 years.
- ~**50%** do not survive 5 years.
- Largest single drop in the **first six months** (~13% gone).
- Sector variation across 2-digit NAICS: **53%** (educational services) to **74%** (utilities).
- Label: **Empirical Finding** (US government statistical program).
- Use: sets the honest base rate for the Summer-2027 plan. NOT a prediction about
  Forgelink specifically.

## FINDING 9 — Tax / entity

- IRS default classification: single-member LLC = **disregarded entity**;
  multi-member LLC = **partnership**; **Form 8832** elects corporate treatment.
- Form 8832 effective date: no more than **75 days before** filing, no more than
  **12 months after** filing.
- **IRC Section 1202 (QSBS)**: requires a **C corporation**; stock acquired at
  **original issuance**; held **more than 5 years**; anti-churning redemption rules.
  Retrieved from IRS and govinfo USC text.
- Implication: staying an LLC forecloses QSBS. Converting starts the 5-year clock.
- Label: **PDF-Supported**. **Professional verification required (CPA + tax counsel).**
- SAFE tax characterization is **unsettled** — commonly analyzed as a variable
  prepaid forward contract (VPFC) or as equity; characterization affects holding
  period and QSBS. Retrieved from accounting-firm commentary (does NOT clear the
  user's source gate) + Polsky Center FAQ. Label: **Unknown / contested**.

---

## SOURCES EXCLUDED BY THE USER'S OWN SOURCE GATE

- **Carta** (state-of-pre-seed / valuation-cap benchmarks): proprietary vendor data,
  not peer-reviewed, not .gov. Does **not** clear the HBR/WSJ-equivalent bar.
  EXCLUDED from load-bearing claims.
  *What is missing:* a peer-reviewed or government dataset of current SAFE
  valuation-cap benchmarks. I am not aware of one. Stated as a gap, not filled.
- Law-firm blogs, accounting-firm insight posts, LinkedIn, Medium, arXiv preprints:
  EXCLUDED or used only as pointers to primary documents.
- Y Combinator SAFE documents: **used as the primary instrument source only**
  (YC authored the SAFE; ycombinator.com/documents is the authoritative location of
  the form itself). Not used as evidence for any empirical or legal claim.

---

## THINGS I DO NOT KNOW ABOUT FORGELINK (must be user-supplied)

- State of formation of Forgelink LLC; operating agreement terms; existing members.
- Whether Deterministic Governance LLC (WY) currently OWNS Forgelink or merely
  licenses IP to it. **This single fact changes the entire SBIR eligibility analysis.**
- The license terms between the WY holdco and Forgelink (exclusivity, field of use,
  royalty, termination, change-of-control).
- Current revenue, employee count, cap table, burn rate, runway.
- Which software products exist at what TRL; what "sole licenses" covers.
- Target city/agency, NAICS codes, whether any past performance exists.
- Whether Andrew is a US citizen/permanent resident (assumed yes; must be confirmed
  for SBIR).
- Any socioeconomic certification eligibility (8(a), HUBZone, SDVOSB, WOSB).

**These are Unknowns, not assumptions to paper over. The deliverable captures each
as a fillable field rather than inventing a value.**

---

## PREMISE CORRECTION REQUIRED IN DELIVERABLE

User asked for a strategy that will "ensure that I get city and federal contracts
within the year." **No strategy can ensure a contract award.** Award depends on
competition, agency budget, evaluation, and protest risk — none controllable by the
offeror. The deliverable states this plainly and converts the goal into
**controllable leading indicators** (registrations completed, capability statement
delivered, solicitations responded to, past performance created via micro-purchase
and SAT-range work) rather than a promised outcome.

---

## FINDING 10 — SBIR Phase III sole-source authority  [STRATEGICALLY DECISIVE]

Retrieved from SBIR.gov data-rights tutorials and acquisition.gov:
- A Phase III award must **derive from, extend, or complete** prior SBIR/STTR effort
  and is funded with **non-SBIR funds**.
- **An agency funding a Phase III award "is not required to conduct another
  competition ... in order to satisfy statutory competition requirements."**
- Authority cited: **15 U.S.C. 638(r)(4)**.
- "The government must award a Phase III to the SBIR firm that developed the
  Phase III technology **to the greatest extent practicable**."
- There is **no dollar limit and no phase limit** on Phase III (agency-dependent).
- Label: **PDF-Supported**, pending full-text verification of 15 U.S.C. 638(r)(4)
  and the SBA SBIR/STTR Policy Directive.

**Why this reframes the whole plan:** the user asked how to "ensure" city and federal
contracts. Competitive award cannot be ensured. But SBIR Phase I -> II -> III is the
one federal pathway with an explicit statutory basis for **sole-source** follow-on
award to the developing firm. That is the closest legitimate thing to the user's goal,
and it is non-dilutive at Phases I and II.

## FINDING 11 — SBIR/STTR data rights  [PROTECTS THE IP HOLDCO THESIS]

- SBA set a uniform **20-year** SBIR/STTR data protection period **beginning at date
  of award**, effective **May 2, 2019**.
- During the protection period the government receives a **limited, nonexclusive
  license**; it **cannot disclose SBIR data outside the government**.
- On expiration, the government obtains **government purpose rights**, which **do not
  expire**.
- Protections apply across **Phase I, II, and III**.
- Data must be **properly marked** with the SBIR/STTR data rights legend to be protected.
- Relevant FAR/DFARS: FAR 52.227-20; DFARS 252.227-7018; DFARS 227.7104-2.
- Label: **PDF-Supported**, pending full-text verification.
- Strategic read: SBIR funding is compatible with — not hostile to — a Wyoming IP
  holding company thesis, PROVIDED marking discipline is maintained from day one.
  Failure to mark is the standard way firms lose these rights.

## FINDING 12 — UNRESOLVED CONFLICT: Simplified Acquisition Threshold

Three retrievals disagreed:
  (a) acquisition.gov threshold material -> SAT **$250,000**; commercial **$2,000,000**
      through 9/30/2027.
  (b) Federal Register 2025-16412 summary -> SAT **increased from $250,000 to $350,000**;
      commercial **$2,000,000 -> $2,500,000**.
  (c) A further FR extract referenced removing "$15,000" / adding "$20,000" — which may
      relate to a different threshold entirely.

**RESOLUTION: NOT RESOLVED. I am not asserting a SAT figure.**
Corroborated twice and asserted: **micro-purchase threshold = $15,000**, effective
Oct 1, 2025 (GSA SmartPay bulletin is explicitly titled to that effect).
The deliverable instructs the reader to confirm SAT at
https://www.acquisition.gov/threshold-changes before relying on it.
Label: **Unknown** (deliberately left unknown rather than guessed).

## FINDING 13 — Socioeconomic certifications (SBA)

- **8(a)**: majority owned/controlled by socially disadvantaged individuals; certain
  groups presumed socially disadvantaged; others case-by-case on a showing of
  chronic and substantial bias.
- **HUBZone**: >=51% owned/controlled by US citizens (or listed entity types);
  **principal office** in a designated HUBZone; employ staff residing in a HUBZone.
- **WOSB / EDWOSB**: owned and controlled by one or more women; EDWOSB adds a
  personal-assets test (retrieved figure: $6.5 million or less — verify).
- **SDVOSB/VOSB**: >=51% owned and controlled by veterans; SDVOSB requires VA
  service-disabled rating.
- Apply at certifications.sba.gov.
- Label: **PDF-Supported**, pending verification. Eligibility for Forgelink is
  **Unknown** — depends on facts I do not have.
