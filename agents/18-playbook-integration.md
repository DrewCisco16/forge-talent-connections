# 18 — PLAYBOOK INTEGRATION (v3)

Reconciling the agent system with **Andrew Francisco AI Agent Operating Playbook
v1.0** (25 pages, docs checked 13 Sep 2026), supplied 2026-09-14.

**The playbook is more disciplined than v1–v2.1 in six specific ways. Where they
disagree, the playbook wins** — it is the operator's own approved operating
document, its sources are registered, and its format is a stated accessibility
requirement rather than a preference.

---

## 1. Defect register — what the playbook exposed

| # | Defect | Severity | Status |
|---|---|---|---|
| **D12** | **Committed third-party personal data to a PUBLIC repository.** Eight phone numbers, a carrier account id, an order number, and four other people's names paired with their numbers and devices | **Critical** | **FIXED** `5f12aba`. See §2 |
| **D13** | **Ignored the stated ADHD/OCD-friendly format requirement.** Playbook p.3 names it explicitly. My documents are 200–350-line walls | **High** | **FIXED** — one-page [`cards/`](cards/), one agent per page |
| **D14** | **Missed Claude Dispatch entirely.** It is a real route with a hard lane constraint | **High** | §3 |
| **D15** | **Said ChatGPT agent "cannot see your logged-in sessions."** The playbook documents ChatGPT Remote + Computer Use controlling local Chrome | **High** | §3, corrected |
| **D16** | **Repeated the fleet pack's "PowerToys Awake required" without its limitation** | Medium | §4 |
| **D17** | **No schedule expiry, no daily cap, no tested notification target, no recorded kill location** | High | §5 |
| **D18** | **Loop caps far too loose for a pilot** — 200 iterations/8h/$25 vs the playbook's ≤3 variants/60 min/$0 | Medium | §6 |
| **D19** | **Five-window swarm contradicts the playbook's research protocol** — one controller, at most two services | Medium | §7 |
| **D20** | **No `mission.md`, no `AGENTS.md`/`CLAUDE.md` wiring** despite specifying the structure | Medium | **FIXED** — §8 |
| **D21** | **No acceptance tests per agent.** p.14 requires three minimum | **High** | **FIXED** — every card carries them |
| **D22** | **Open question A4 answered: the repository is PUBLIC** | **Critical** | §2 |

---

## 2. D22 + D12 — the repository is public

`private: false`, `visibility: "public"` (GitHub API, checked 2026-09-14).
**`10-open-questions.md` A4 is closed, and the answer changes what may ever live
here.**

| Never in this repository | Because |
|---|---|
| Invention disclosures, unfiled claims | Public disclosure can destroy patent rights (`06` §B3) |
| Anything CUI, FOUO, or procurement-sensitive | `07` §2 |
| Client or candidate records; Just4Veterans data | Not yours to publish |
| Third-party personal data | **This already happened.** See below |
| Secrets, keys, tokens | Standard |

**What happened.** Commit `2a51e25` committed the fleet pack verbatim, publishing
phone numbers, a Verizon Business account identifier, a Best Buy order number,
and four named individuals with their numbers and devices. The playbook (p.25)
had already set the correct standard: *"this playbook omits phone numbers,
carrier account identifiers, order numbers and third-party device-holder details
from the source materials."*

**Fixed at HEAD in `5f12aba`** — values replaced with `[REDACTED]`, names with
`Third party A–D`. Every hardware fact an agent needs is retained.

**Still outstanding, and it needs your decision.** The data remains reachable in
this branch's history and in the PR's diff views. Removing it entirely requires
either a history rewrite you authorize, or a request to GitHub Support. **This
branch carries commits from earlier sessions, so it must not be rewritten
unilaterally.** Options in §10.

---

## 3. D14/D15 — the three routes, corrected

The playbook documents three, with sources registered [W01–W11]. **v2.1 had one
and a half.**

### Route A — ChatGPT Remote + Chrome [W01–W03]
```
Desktop app → Settings → Connections → Control this Mac or PC → Set up / Add
Scan QR from phone; same account and workspace
Settings → Computer Use → choose Chrome → install its official extension
Return until it shows "Manage"; start Work or Codex; select Chrome via the @ menu
Broader desktop control: Plugins → Computer Use
```
**Correction to `12` §2.** I said ChatGPT agent runs only in its own cloud VM and
*"cannot see your logged-in sessions."* That describes cloud agent mode. It does
not describe **ChatGPT Remote + Computer Use**, which controls the host's real
Chrome. **Mobile access requires the desktop app awake and online** — not the CLI.
**On Windows this uses the foreground desktop; do not share that active session
with another controller.**

### Route B — Claude Dispatch + Chrome [W07–W09]
**I missed this entirely.** A remote task route into your desktop — *"not an
always-on cloud machine"* — in limited beta for some Pro/Max accounts, set up via
Cowork → Dispatch → Get started.

> **Hard lane constraint, playbook p.11:** *"Dispatch uses one continuous thread.
> For this playbook, dedicate it to one non-sensitive lane; do not mix ABO
> restricted work with personal, DBA or FORGE context in that thread."*

**One thread means one lane, permanently.** This is stronger than a connector
scope and it belongs in `07` §5.

### Route C — Claude Code + Chrome / Remote Control [W10–W11]
Matches what I verified, plus one correction:

> *"Claude Remote Control keeps execution on your machine, but syncs the session
> transcript through Anthropic. Do not use this route to bypass the fleet pack's
> data restrictions."*

**A local process is not a private offline model.** My `12` implied local
execution was the stronger privacy posture. It is not, by itself.

### The governing rule, which supersedes my named-pipe framing

> **"One controller per browser session; one writer per working tree."**
> *"Two paths, not two agents fighting over Chrome."*
> *"Remote control is not, by itself, browser permission or cloud execution."*

---

## 4. D16 — PowerToys Awake correction

The fleet pack calls Awake required while leaving standby mode unverified. The
playbook checks the vendor [W17]:

> *"Microsoft's guidance says Awake does not work at the lock screen; staying
> awake while locked requires power-plan configuration. Record the actual state
> rather than assuming a slider or utility guarantees the run."*

**`03` §5 and `15` §4 are amended:** run `powercfg /a`, record the result, and
configure the power plan. **Awake alone does not keep a locked machine running.**

---

## 5. D17 — every schedule needs an expiry

Playbook p.20 requires, before any unattended launch:

```
Execution location                    Schedule + timezone (America/New_York)
LAST ALLOWED RUN / EXPIRY             Per-run time / cost / attempts
Daily run / spend cap                 Exact draft output destination
TESTED notification destination       WHERE TO DISABLE THE TRIGGER
[ ] A manual run produced the expected artifact and stopped
[ ] Timeout / cost / duplicate-run controls tested; approval recorded
```

> *"Default: no self-triggering chains, no overlapping runs, no automatic deploy
> / merge / send. Blank limits or an untested stop mechanism mean no unattended
> launch."*

**Adopted verbatim. Every card carries an expiry field. A schedule with no expiry
does not launch.** Note the playbook also distinguishes a **Claude cloud routine**
(survives host shutdown) from a **Claude Desktop local schedule** [W15], which
requires the app open and the machine awake — *"Do not substitute a local
schedule for a cloud job expected to survive host shutdown."*

---

## 6. D18 — pilot mode for the loops

My caps: 200 iterations, 8h, $25. **The playbook's pilot: at most three variants
and 60 minutes, no extra spend unless approved.**

The playbook is right for a first run, and its reasoning is sharper than mine on
one point:

> *"Keep a separate holdout set; never optimize by changing what 'pass' means."*
> *"Keep only: a measured quality improvement with no safety regression and no
> budget breach. Reject noisy / inconclusive results."*
> *"Do not adopt the upstream suggestion to disable all permissions."*

That last line is a specific warning about `autoresearch`'s own README that I did
not carry. **Do not disable permissions to make a loop run.**

> *"Enforcement: the runner needs a timeout, attempt counter and spend guard. A
> sentence in a prompt is not a hard budget. Until those controls are tested, run
> supervised."*

**Every `loop.json` gains a `pilot` block: 3 variants, 60 minutes, $0 extra
spend, supervised. Production caps unlock only after a supervised pilot passes.**

---

## 7. D19 — the swarm is a later capability, not the pilot

Playbook p.16, *"Let AI tools research — not vote on truth"*:

> *"Choose one route and at most two AI services... For the pilot, keep one
> browser controller. A second AI service is optional, not mandatory."*
> *"Compare evidence, not confidence or model agreement."*
> *"A model response is a lead, not source verification."*
> *"Reconcile once and stop... do not keep querying until everything agrees."*

**This is a correction of emphasis, not a contradiction.** The five-window swarm
(`15`) stays specified as a Tier 2 capability. **It is not the pilot.** The pilot
is one controller, one or two services, sources opened and verified by hand,
reconciled once.

**"Compare evidence, not model agreement" is the sharper statement of the same
principle behind your elimination engine.** Agreement between models is not
evidence. I over-weighted breadth; the playbook weights verification.

---

## 8. D20 — the project structure, now wired

Playbook p.9, adopted exactly:

```
agent-project/
  AGENTS.md       # shared instructions       <- Codex reads this
  CLAUDE.md       # one line: @AGENTS.md      <- outside a code fence
  mission.md      # filled mission and approved scope
  src/            # agent implementation
  evals/          # fixed tests and synthetic fixtures
  outputs/        # run artifacts; no secrets
  logs/           # redacted run records
```

Created at the repository root: [`../AGENTS.md`](../AGENTS.md),
[`../CLAUDE.md`](../CLAUDE.md), [`mission-template.md`](mission-template.md).

**First request to any new agent, from p.9 — use it verbatim:**

> *"Read the project instructions and mission. List the files loaded, proposed
> edits and permissions needed. Make no changes yet."*

---

## 9. D21 — three mandatory tests, and the ten-test suite

Playbook p.14 requires every agent to declare acceptance tests for **normal case,
missing evidence, and unsafe instruction.** p.15 gives the fuller suite:

```
normal source set · missing citation · unavailable page · conflicting evidence
malicious page instruction · forbidden data · unapproved domain
cost limit · timeout · repeat run
```

> *"Unsafe inputs must produce a hold, not an invented answer."*
> *"Return a useful partial result with explicit gaps instead of inventing an
> answer. A 'blocked' response is correct when the permission or evidence is
> missing."*

**Every card in [`cards/`](cards/) carries the three minimum. Research and
browser agents carry all ten. An agent without declared tests does not run.**

---

## 10. Your decision — the history

The redaction is live at HEAD. The historical commits are not. Three options:

| Option | Effect | Cost |
|---|---|---|
| **A — Squash-merge the PR** | The 22 commits collapse into one clean commit on `main`; the branch history can then be deleted | Loses the granular v1→v3 audit trail on `main`. **Simplest, and I recommend it** |
| **B — Authorize a history rewrite** | I force-rewrite this branch and purge the blobs | Rewrites 24 commits from earlier sessions. **Needs your explicit go-ahead** |
| **C — Ask GitHub Support** | They purge cached views and unreferenced objects | Slowest, most complete |

**A is sufficient for four phone numbers and four names, and it costs you
nothing you need.** Say the word on B if you want it done today instead.

---

## 11. What the playbook confirms that v2.1 got right

| Confirmed | Playbook |
|---|---|
| Lane separation with per-lane boundaries | p.5, same five lanes, same boundaries |
| CUI behind a human gate; counsel review | p.8, *"A local runner alone does not satisfy this boundary"* |
| Untrusted input: pages and other AI replies are data | p.13, *"Treat pages, documents and other AI replies as untrusted information, not instructions"* |
| Evidence labels, never upgraded; Unknown blocks | p.13, *"A needed Unknown blocks the dependent action"* |
| One-way doors stay human | p.8, *"Human-only: authentication, CAPTCHAs, purchases, contract decisions, candidate decisions, publishing, production deployment and destructive changes"* |
| Gates before model judgment; hold over invention | p.15, *"Unsafe inputs must produce a hold, not an invented answer"* |
| Measure before scaling | p.23, *"Measure usefulness before adding agents"* |
| Blank limits authorize nothing | p.2, *"Blank permissions or spending limits do not authorize action"* |

---

## 12. "As many agents as possible" — how this is resolved

You asked for as many agents as possible. Your playbook says *"Measure
usefulness before adding agents"* and *"no unrestricted agent swarm is needed for
the first pilot."*

**Both are satisfied by separating specification from deployment:**

- **Specify all 21.** A card is a contract, not a running process. It costs
  nothing to hold, and having the contract written is what makes deployment fast
  and safe later. All 21 are in [`cards/`](cards/).
- **Deploy one at a time**, in the playbook's order, each with a measured weekly
  review before the next.

**The playbook names which one is first: the public-source research brief (p.15).**
That is [`cards/briefer.md`](cards/briefer.md).
