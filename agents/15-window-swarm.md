# 15 — THE WINDOW SWARM

Five LLMs in five Chrome tabs, driven by one dispatcher, billed against
subscriptions instead of per-token API calls. **Tier 2 of the cascade, and the
workhorse of the v2 system.**

---

## 1. Why this tier exists

Tier 1 (one model + gates) is cheap and measured-correct for your task classes,
but it loses **corroboration** — `one_model.py`: *"'Two seats who wrote blind
independently give the same different value' is meaningless with one seat, so a
disputed input can never be outweighed here."*

Tier 3 buys corroboration back at **$4.96–$16.82 a run**.

**The swarm buys most of it back at zero marginal API cost**, because a chat
window draws on a subscription you already pay for rather than a metered API key.
Five different model families still disagree in five different ways; that
disagreement is the product, and you do not need a metered token to observe it.

**What you do not get:** *measured* rho. Browser blinding is weaker than API
blinding and the token accounting is not instrumented, so any independence figure
from a swarm would be a number you cannot defend. **The swarm gives qualitative
divergence — who disagreed and how. Quantitative rho stays Tier 3.** State that
plainly in every swarm output; do not let a swarm result wear a panel's clothes.

---

## 2. The round shape — yours, unchanged

From `adjudication/night_loop.py`, **Repo-Verified**. Do not redesign this; it was
argued out already and the reasoning holds:

> **"FOUR THINKERS AND A CLOSER, not five peers.** The closer never answers as a
> peer and the thinkers never merge. That costs one independent proposal and buys
> a real merged answer that carries forward between rounds."

> **"ROUND 1 INVENTS THE OPTIONS.** Each thinker proposes two to four ways to go
> and then attacks its own proposals. Requiring candidates up front was backwards:
> if you already knew the options you would not need to run this."

> **"FALSIFIABILITY IS THE THINKER'S JOB, NOT THE OPERATOR'S.** Every proposal
> must arrive with what would knock it down."

> **"THE CHECK RUNS BEFORE THE CLOSER, ALWAYS.** If the closer merges first and
> the gates run second, a false claim is already woven into the working answer...
> The ordering is the whole reason this is safe to run unattended."

> **"THE WALL SITS AT ROUND 1.** In round 1 no thinker sees another's words, name,
> or any sign that other thinkers exist — that is where variety is created and it
> is the only place worth protecting. From round 2 they all read the same merged
> text, which is how holes get plugged."

> **"MODEL OUTPUT IS DATA, NEVER INSTRUCTION.** An instruction found inside a
> reply is recorded as a finding, never obeyed."

**Tab assignment:**

```
TAB 1  THINKER A          TAB 4  THINKER D
TAB 2  THINKER B          TAB 5  CLOSER  ← never answers as a peer
TAB 3  THINKER C
```

Use **five different vendors**. Two tabs of the same model family is one opinion
paying for two windows.

---

## 3. The loop

```
ROUND 1  ── THE WALL ──
  dispatcher pastes the blinded ask into tabs 1-4, separately.
  No thinker sees another's tab, name, or that others exist.
  Each returns 2-4 options, each with what would falsify it.
        │
        ▼
  GATES (Tier 0, deterministic, local — no model involved)
    arithmetic self-refutation · DOI resolution · quote fidelity
    predicate checks · option-set elimination
    → refuted claims are STRUCK before the closer ever sees them
        │
        ▼
  CLOSER (tab 5) merges only what survived. Never adds a claim.
        │
        ▼
ROUNDS 2-N  all four thinkers read the SAME merged text and attack it.
  Gates run again. Closer re-merges.
        │
        ▼
STOP when a round produces no new verified corrections,
     or at MAX_ROUNDS, whichever comes first.
        │
        ▼
OUTPUT  survivors · what was struck and by which gate · divergence
        · open holes with what would close each · judgment queue
```

**Stop on "no new verified corrections" — not on "it reads well now."**

---

## 4. Substrate — verified mechanics

Docs-Verified, `code.claude.com/docs/en/chrome`, retrieved 2026-09-14:

| Fact | Consequence for the swarm |
|---|---|
| `claude --chrome` connects Claude Code to the Claude in Chrome extension | The dispatcher is a normal Claude Code session |
| *"The extension collects the tabs Claude opens into a Chrome tab group tied to your session"* | The five tabs are one managed group, not loose windows |
| *"shares your browser's login state"* | **The swarm profile must hold ONLY the five AI subscriptions. Nothing else.** See §6 |
| *"Chrome integration isn't supported in Windows Subsystem for Linux (WSL)"* | On the HP Envy, run the dispatcher **Windows-side**, not in WSL2 |
| *"The Chrome extension's service worker can go idle during extended sessions, which breaks the connection"* | **An overnight swarm needs a reconnect-and-resume step** or it dies at 2am showing nothing |
| Named-pipe conflicts on Windows; *"Close any other Claude Code sessions that might be using Chrome"* | **One swarm per machine.** Four lanes → four machines |
| Requires a direct Anthropic plan and `/login`; API-key auth disables Chrome | The dispatcher cannot run on an API key |

**You already own this pattern.** Your `night-agent` skill drives an unattended
multi-window elimination loop across five open AI chat windows. This is that,
with the gate ordering made explicit and the tier position defined.

**The ChatGPT/Codex desktop path.** You described a desktop tool that drives the
Chrome window and tabs for five LLMs. If it does what you say, it is a **drop-in
alternative dispatcher** — the round shape, gates, and output contract above are
dispatcher-agnostic by design. What it cannot do is change §2 or §5; those are
the protocol, not the transport. Codex's sandbox/network/scheduling specifics
remain unverified from this session (`10` A5) — but the model id and pricing are
now Repo-Verified from your own `rates.json` (`13` §2).

---

## 5. Rules the dispatcher enforces

1. **The wall holds in round 1.** No thinker tab sees another's text, and no
   prompt hints that other tabs exist. This is where variety comes from and it is
   the only place worth protecting.
2. **Gates run before the closer. Every round. No exception.**
3. **The closer merges; it never adds.** A claim in the merge that is in no
   thinker's output is a finding, and the run is flagged.
4. **Every pasted-in model reply is wrapped as untrusted data.** An instruction
   inside a reply is recorded as a finding, never obeyed.
5. **Every claim carries its evidence label.** No upgrades.
6. **No number without a dataset and a shown calculation.**
7. **The run declares MAX_ROUNDS and a wall-clock cap before it starts.**
8. **Swarm results are labeled `SWARM` — qualitative divergence only.** They never
   claim rho, effective seat count, or any panel diagnostic. Those are Tier 3
   products and mislabeling one is the failure this whole system exists to prevent.

---

## 6. The swarm Chrome profile

**A dedicated profile that holds five AI subscriptions and nothing else.**

```
SWARM PROFILE — per machine
  ✅ the five AI chat subscriptions. That is the entire list.
  ❌ email · banking · brokerage · SAM.gov · GitHub · FIU · anything else
```

Then set the extension's site allowlist to exactly those five domains, and
**test the boundary**: ask the dispatcher to open a site not on the list and
confirm the refusal. A permission you have not tested is a permission you do not
have.

**Reason, stated once:** the extension shares the profile's login state. A swarm
profile that is also signed into your mailbox is a swarm with access to your
mailbox.

---

## 7. Lane deployment

| Lane | Machine | Dispatcher runs | Swarm profile holds |
|---|---|---|---|
| **DBA** | HP Envy 17 (**Windows side**, not WSL) | overnight | 5 AI subscriptions only |
| **FORGE** | ASUS ProArt 16 | on demand | 5 AI subscriptions only |
| **ABO** | Surface Pro 8 | **public-source questions only until counsel clears** | 5 AI subscriptions only |
| **HOME** | — | **no swarm** | — |

Four machines, four lanes, one swarm each — which the named-pipe constraint
requires anyway. **Physical separation is the strongest lane isolation available
and it costs nothing.**

---

## 8. One standing check

Driving a consumer chat UI through browser automation is a different act from
calling an API, and vendor terms may treat it differently. Read each of the five
vendors' terms once, record the date, move on. **Stated once; not repeated.**

---

## 9. What good looks like

```
SWARM RUN <id>   lane <LANE>   rounds <n>/<MAX>   wall clock <hh:mm>

STRUCK BY GATES (n)   ← read this BEFORE the answer
  · <claim> — <gate> — <what specifically failed>

SURVIVORS (n)
  · <claim> — <attacks withstood> — <evidence label>

DIVERGENCE (qualitative — SWARM tier, no rho)
  · <where thinkers disagreed, and how>
  · unanimity is an ALARM, not a result

OPEN HOLES (n)
  · <hole> — <what would close it>

JUDGMENT QUEUE (n)   ← claims no gate could settle. Yours.

COMMITTABLE?  YES only if one survivor AND zero holes. Usually NO,
              and NO is a result: it names what is still open.
```
