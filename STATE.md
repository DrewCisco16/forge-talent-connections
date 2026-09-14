# STATE

**Single source of truth for where this system actually stands.**
Update it at the end of every session. If this file and a document disagree, fix
the document.

**Last updated:** 2026-09-14 · **System version:** v4 (inversion pass)

---

## Agents actually running

**None.** Twenty-five are specified; zero have run.

> This is the system's current single greatest risk — `19` A1. The next action
> below is the whole job.

## Next action — one, not a list

**Run [BRIEFER](agents/cards/briefer.md) once.** 25 minutes, $0, one sanitized
question, up to three approved public sources. Fill
[`agents/mission-template.md`](agents/mission-template.md) first.

## Decisions waiting on Andrew

| # | Decision | Blocks | Raised |
|---|---|---|---|
| 1 | **Git history PII**: squash-merge the PR / authorize a force-rewrite / GitHub Support | Closing the privacy incident | 2026-09-14 |
| 2 | **Does Cloudflare Pages serve the repo's markdown?** Open a per-deployment URL + `/agents/context/device-fleet.md` | Whether the PII was live on the web | 2026-09-14 |
| 3 | **Contracts counsel** — the four questions in `agents/07-guardrails.md` §2 | The entire ABO lane on non-public data | 2026-09-14 |
| 4 | **FIU AI-use policy** for doctoral work | The DBA lane. **Unrecoverable-class risk, never checked** | 2026-09-14 |
| 5 | **Seat 3 Mistral model id** — 2 minutes in the console | Tier 3 panel + the panel-economics loop | 2026-09-14 |

## Gates live right now

| Gate | Status | Evidence |
|---|---|---|
| `scripts/redaction_guard.py` | **ACTIVE** — pre-commit hook installed | 35 self-tests; denial live-tested; 171 files scan clean |
| `agents/loops/harness/loop_guard.py` | ACTIVE | 24 self-tests; clears 3 loops, blocks 2 |
| `adjudication/` cost ceiling | ACTIVE | checked before the call, not after |
| Counsel block on ABO | ACTIVE | `loop_guard` refuses `counsel_cleared: false` |

## Loops

| Loop | Guard verdict | Blocker |
|---|---|---|
| forge-software | CLEARED (pilot: 3 × 60 min × $0) | none |
| dba-research | CLEARED | none |
| home-decisions | CLEARED | none |
| abo-govcon | **REFUSED** | counsel |
| panel-economics | **REFUSED** | seat 3 model id |

## Measurement

**Baseline: NOT STARTED.** Day 90 cannot be answered until it is. No claim about
time saved is permitted before then — see [BASELINE](agents/cards/baseline.md).

## Open pull request

`#12` — draft, `mergeable_state: clean`, CI green. Contains the whole system.

## The kill date

**2026-10-14.** No used artifact by then → cut to BRIEFER only (`19` §3).
