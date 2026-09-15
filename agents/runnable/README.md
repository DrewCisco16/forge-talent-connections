# RUNNABLE AGENT DEFINITIONS — built, reviewed, one command from live

**29 executable subagent definitions**, generated from the cards in
[`../cards/`](../cards/) by [`../../scripts/build_agents.py`](../../scripts/build_agents.py).

A card is a contract. **A file in Claude Code's agents directory is a thing that
runs.** This directory holds the second form of every agent that has one.

---

## Install — one command

```bash
cp agents/runnable/*.md .claude/agents/
```

Then they appear in the agent picker and can be invoked by name. **After
installing, run the gate:**

```bash
python3 scripts/agent_parity.py      # expect: 32 cards, 29 built, 33 live
```

### Why they are not already installed

Writing to Claude Code's own agents directory is blocked in the session that
generated them — every attempt returned `[Self-Modification]`, via both the shell
and the file tools. **That is a correct guard**: an agent that can silently
rewrite its own agent roster is exactly the thing worth blocking. It needs
Andrew, or a Bash permission rule.

So the work is done and staged rather than done and live, and the gate reports
the difference instead of glossing it.

---

## What is here, and what is deliberately not

| | Count | |
|---|---|---|
| Agent cards | 32 | |
| **Built here** | **29** | every card except the three below |
| Hand-written, already live | 3 | `reviewer` → `adversarial-reviewer`, `librarian` → `citation-verifier`, `matrix` → `compliance-matrix`. Their hand-written prose is better than a generated file; the generator refuses to clobber them |
| **Protocols — NOT built, on purpose** | 2 | `baseline` and `smoke`. **Nothing performs these for Andrew.** Emitting subagents for them would re-make the category error the roster already corrected, and would quietly defer the two things only he can do |

**Three are built but refuse on sight**, because their blocker is real:

```
capture    ⛔  the four contracts questions in agents/07-guardrails.md §2
matrix     ⛔  same
captable   ⛔  same
nightwatch ⛔  the seat 3 Mistral model id is unknown, so the panel cannot be priced
```

Each opens with a refusal and stops. They do not do "just the safe part" — the
blocker exists precisely because nobody has established what the safe part is.

---

## The contract lives in the card, not here

**Do not hand-edit these files.** Edit the card and regenerate:

```bash
python3 scripts/build_agents.py
```

`scripts/agent_parity.py` fails if a definition stops matching a fresh build of
its card — because the file Claude Code loads must be the contract Andrew
reviewed, and a silent divergence between the two is invisible in either file
alone.

The one thing the generator does **not** take from the cards is the tool grants.
Cards name domain actions ("never sends"); Claude Code needs tool names
(`mcp__Gmail__send_message`). That mapping is the `SPEC` table in
`build_agents.py` — a human judgement, made once, reviewed there. The parity gate
does not check that the grants are *right*; it checks that nobody changed them
afterwards without saying so.

`agent_parity.py` asserts the load-bearing one directly: **MAILROOM is granted no
send tool and explicitly disallows every one of them.** Four of its thirteen
self-tests exist for that single property.

---

## Honest status

```
specified        32 / 32     cards, goals, measures, acceptance tests
built            29 / 29     of the cards that should have a runnable form
INSTALLED         4 / 32     the three hand-written, plus evidence-auditor
EVER RUN          1          evidence-auditor, 2026-09-15
```

**`FM-47` is the gap between rows 2 and 4**, and it does not close by generating
more files. It closes the first time each of these runs against real work and
produces something Andrew uses. Everything above that line is preparation.
