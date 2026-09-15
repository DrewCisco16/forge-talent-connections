# 10 — OPEN QUESTIONS

Everything this design needs and does not know. **Unresolved by design: a guess
recorded here would be worse than a gap, because a gap gets closed and a guess
gets built on.**

Rule for any agent reading this file: **if your task depends on an item below,
stop and ask. Do not substitute a plausible value.**

---

## A. Blocking — must be answered before the dependent work starts

| # | Question | Blocks | Ask |
|---|---|---|---|
| A1 | Which contracts/agreements impose data-handling duties (DFARS 252.204-7012, CUI marking, FedRAMP, NDA terms), and may contract material be processed by a commercial cloud AI service? | **All ABO agents on non-public data.** Gate 3 entirely | **Contracts counsel.** Professional verification required |
| A2 | What records must be retained if a CO asks how AI was used in preparing a submission? | MATRIX, CAPTURE | Contracts counsel |
| A3 | Does your Just4Veterans 1099 agreement restrict tooling, data handling, or disclosure? | All J4V agents | Read the agreement; if silent, ask J4V in writing |
| A4 | Is this repository (`forge-talent-connections`) public or private? | Whether any invention disclosure, client data, or draft may ever be committed here | Check GitHub settings. **Before the next commit** |
| A5 | ~~Does GPT-5.6 exist~~ **PARTIALLY CLOSED 2026-09-14:** `gpt-5.6-sol` is Repo-Verified in `adjudication/rates.json` with a vendor source URL and `verified_on: 2026-09-09`, and Andrew holds a $200/month ChatGPT Max subscription (Stated). **Still open:** Codex's sandbox, network policy, scheduling, and `AGENTS.md` behavior | BUILDER's second vendor track | OpenAI's own documentation. `developers.openai.com` remains `EGRESS_BLOCKED` from this session |
| **A7** | **What does FIU's doctoral program actually permit regarding AI use in dissertation research and writing?** Your Playbook flags it (p.23: *"follow your program's actual AI-use and research requirements"*); this system never checked | **The entire DBA lane — LIBRARIAN, TRACKER, the falsification loop** | **Your program handbook, your chair, and FIU's academic-integrity policy. Ask before the next DBA agent runs.** Unrecoverable-class risk |
| A6 | Do your DBA research plans involve organizational, client, or contract data? | LIBRARIAN's boundary; possibly IRB | FIU IRB + your chair, before any data touches an agent |

---

## B. Verification — needed before the relevant agent's first run

| # | Item | Needed by | Source |
|---|---|---|---|
| B1 | SAM.gov Get Opportunities: base URL, key requirement, date-range parameter format and span limit, rate limits | SCOUT | The provider's own published API documentation. **Blocked this session (`open.gsa.gov`)** |
| B2 | SAM.gov Entity Management: whether sensitive data requires a separate role or agreement | SCOUT eligibility gate | Same |
| B3 | FPDS and USASpending endpoints and response shapes | CAPTURE | Same |
| B4 | USPTO full-text / assignment API endpoints | PRIORART | USPTO's own documentation |
| B5 | Which agencies you actually target, and whether they publish forecasts | SCOUT source list | You |
| B6 | Your NAICS/PSC codes, size standard, and current socio-economic registrations | SCOUT gates 1–2. **Every gate decision is wrong without these** | SAM.gov registration; confirm with counsel |
| B7 | Your dissertation domain, research question, and current reference list | LIBRARIAN. It cannot surveil a domain it has not been given | You |
| B8 | Which mailboxes map to which lane, and their addresses | MAILROOM ×5 | You |
| B9 | Whether Gmail or Superhuman is the system of record per mailbox | MAILROOM tool scope | You |
| ~~B10~~ | ~~Whether routine **API credentials** are available on your plan~~ | — | **CLOSED 2026-09-14.** Andrew holds Claude Max. Docs-Verified: API credentials are available *"on Pro and Max plans"*. Metered keys for seats 2-4 go there, never in environment variables. See `17` §7 |

---

## C. Carried forward from your device fleet context pack

These were open in your pack v1.2 and remain open. Several now have an agent
consequence they did not have before.

| # | Item | New consequence |
|---|---|---|
| C1 | **MacBook Air vs MacBook Pro 15 M4 naming discrepancy** — Apple never shipped a 15-inch MacBook Pro with an M4 | Apple-platform build capacity is unconfirmed. Resolve from  → About This Mac |
| C2 | `powercfg /a` on the HP Envy 17, standby mode recorded | Determines whether any local unattended loop is viable at all (`03` §5) |
| C3 | Seagate drive confirmed paired to the ASUS ProArt 16 | Where GPU-side artifacts land |
| C4 | Surface Pro 8 external drive assignment | QA artifact storage |
| C5 | Surface Type Cover and Slim Pen 2 ownership | Whether pen QA is actually executable |
| C6 | Pixel 9 Pro replacement status (Asurion claim 2026-07-14) | Android test coverage |
| C7 | **MDM enrollment test device** — flagged since July 2026 as the largest product risk for the talent platform | **Still unassigned. No agent closes this; it needs a device** |
| C8 | Windows on ARM: acquire a target or formally accept the gap | Platform coverage |
| C9 | Apple Watch Ultra 2 loss coverage | Your escalation path runs through this watch (`03` §5) |

---

## D. Design decisions you may reasonably override

Stated as decisions so you can reverse them deliberately. **`01` §6 of your own
pack applies: recommendation, not fact, and may be overridden without argument.**

| # | Decision made here | The case against it |
|---|---|---|
| D1 | **No cross-lane agent**, not even a chief of staff | You lose "what's on my plate" in one question. If the compliance boundary is narrower than assumed (A1), a metadata-only cross-lane agent might be defensible |
| D2 | **MAILROOM never sends for at least 60 days** | Slower payoff on the largest time drain. The ladder can be shortened for the HOME lane specifically, where the downside is smallest |
| D3 | **Cloud-first placement** | Your 144GB sits idle. But it is idle *and available*, which is better than committed and asleep |
| D4 | **NIGHTWATCH stays manual** | Real hard problems queue overnight unattended. Your own `adjudicate.yml` header argues the other way, and I think it is right |
| D5 | **Ten agents** | Could be five. If Gate 1 is hard, cut to MAILROOM + BUILDER/REVIEWER + STEWARD and stop there |
| D6 | **No agent writes proposal or dissertation prose** | The largest single block of writing time stays with you. I consider this non-negotiable for integrity reasons; you may scope it differently for internal-only drafts |

---

## E. Known unknowns about this design itself

Stated plainly, because a design that claims no uncertainty is lying:

1. **The Trust Tier ladder thresholds (30/50 outputs) are Assumptions.** They are
   reasoned, not measured. If your approval rate is 95% at output 20, the
   threshold is too conservative. Adjust from your own data at day 90.
2. **The sixty-second review target is an Assumption.** It is a forcing function
   chosen because it makes artifacts decision-shaped. It has no empirical basis.
3. **I do not know your actual email volume.** MAILROOM's design assumes triage is
   a real drain. If you receive twenty messages a day, it is over-engineered and
   you should cut straight to Gate 2.
4. **The lane model may be wrong at the edges.** ABO and Just4Veterans may overlap
   more than a clean boundary allows in practice. If they do, say so before
   building around the boundary rather than after.
5. **Routines are in research preview.** Docs-Verified: *"Behavior, limits, and
   the API surface may change."* Anything load-bearing here could shift.
