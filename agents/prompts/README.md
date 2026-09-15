# PORTABLE AGENT PROMPTS

> **The card is authoritative.** These are paste-able renderings of
> [`../cards/`](../cards/). If a prompt and its card disagree, the card is right
> and the prompt is stale.


Vendor-neutral. Paste into a Claude Code routine, an OpenAI Codex configuration,
a Custom GPT, or anywhere else that takes a system prompt.

**Every agent prompt is assembled the same way:**

```
_SHARED-PREAMBLE.md          ← always first, never edited per-agent
  + ../context/principal-profile.md
  + ../context/device-fleet.md      (only if the agent touches hardware placement)
  + <agent>.md                      ← the charter
```

The preamble carries the truth standard, the evidence labels, the untrusted-input
rule and the lane boundary. **Putting it first is deliberate** — an agent that
reads its task before it reads its constraints has already started reasoning
about the task.

| File | Agent |
|---|---|
| `_SHARED-PREAMBLE.md` | all |
| `mailroom.md` | MAILROOM ×5 |
| `scout.md` | SCOUT |
| `reviewer.md` | REVIEWER |
| `SOURCES-GOVCON.md` | **`FILL-IN` stub.** Complete before SCOUT's first run |
| `SUBSTRATE-CODEX.md` | **`FILL-IN` stub.** Complete before any Codex agent |
| `AGENTS.template.md` | Template for a repository-root `AGENTS.md` |

Prompts for CAPTURE, MATRIX, LIBRARIAN, PRIORART, NIGHTWATCH and STEWARD are
specified in full in `../02-agent-roster.md` and `../05`/`../06`. Write them from
those specifications when you reach the gate that deploys them — writing all ten
now would mean writing eight prompts against requirements that Gate 1 is going to
change.
