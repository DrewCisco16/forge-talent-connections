# Decision record request: finishing the Adjudication Panel

Paste this whole document into the Claude Project MVP Code Generator.

**Answer with decisions, not code.** Code from another model has to be reviewed line by
line before it can enter a repo that produces evidence for a patent file and a federal
proposal, so a decision I can implement and test is worth more to me than a patch I have
to audit. Where you do supply code, keep it to a short reference snippet showing the shape
you mean.

**Answer every numbered question. Where you cannot answer, say "unknown" and say why.**
Do not invent a threshold, a rate, a timeout, or a taxonomy value and present it as a
recommendation without saying what it is grounded in. An invented default that looks
reasonable is the single most expensive thing you can hand me here, because it will end up
in a hash-chained audit log.

---

## 0. What exists, so you do not redesign it

macOS 26.5.1, Python 3.13 in `.venv`, at `~/forge-talent-connections/adjudication`.
**11,393 lines across 18 files. 503 tests pass.** Branch
`claude/adjudication-test-suite-w27c3h`.

Working and tested:
- Five blinded seats, one per vendor, five sequential passes. No seat ever sees another's
  output.
- Mechanical gates: arithmetic, schema, unit, DOI resolution (Crossref then doi.org),
  source admissibility. Gates never ask a model whether something is true.
- Content-addressed claims; two seats asserting the same proposition collide into one
  claim checked once.
- Elimination only. Nothing is ranked, scored, or weighted.
- Tamper-evident append-only audit chain per run.
- Intake layer with two non-skippable refusals (no disproof test; fewer than two
  candidates) and six domain profiles.
- Per-seat conduct ledger, kill provenance (EARNED vs STRUCTURAL), `CONSENSUS ONLY` header.
- Spend ceiling module, built and unit-tested — **but not wired to the run path.**

Verified seat rates, per million tokens, read from vendor pricing pages on 2026-08-25:

| Seat | Model | In | Out |
|---|---|---|---|
| seat_1 | gpt-5.6-sol | $4.00 | $20.00 |
| seat_2 | gemini-3.1-pro-preview | $2.00 | $12.00 |
| seat_3 | mistral-medium-latest | $1.50 | $7.50 |
| seat_4 | grok-4.6 | $2.00 | $6.00 |
| seat_5 | claude-opus-5 | $5.00 | $25.00 |

Derived cost per 25-call run: **$0.64 light, $1.28 typical, $4.67 worst case.**

Two vendor facts that cost real runs to learn. Do not contradict them:
- Anthropic returns HTTP 400 on **every** call if a non-default `temperature`, `top_p`, or
  `top_k` is sent to `claude-opus-5`.
- On thinking models the reply is not at a fixed index. Claude returns
  `content: [{type: thinking}, {type: text}]` when it thinks and `[{type: text}]` when it
  does not.

---

## 1. Wire the cost ceiling to the run path  — HIGHEST PRIORITY

`cost_ledger.py` enforces per-run, per-stage, and per-day ceilings and refuses a call that
would cross one. Nothing calls it. `profiles.json` carries no usage-extraction paths, so no
token counts are captured.

**1.1** For each of the five vendors, what is the exact JSON path to input and output token
counts in a successful chat-completion response? I need path lists, e.g.
`["usage","prompt_tokens"]`. Anthropic differs from the OpenAI-shaped four. State the path
per vendor and cite the doc page.

**1.2** Google's OpenAI-compatibility layer documents that it silently ignores unlisted
parameters, so `max_tokens` does not bind on seat_2. Is there any parameter that *does* cap
output through that endpoint — `extra_body`, `generationConfig.maxOutputTokens`, anything?
If there is none, say so plainly; that makes the ceiling the only bound and changes how
hard I make it.

**1.3** When a ceiling trips mid-run, what should happen to the partial result? My default:
write everything completed, mark the deliverable PARTIAL with the ceiling that fired and
the amount, exit non-zero, and never continue. Confirm or improve.

**1.4** Should the pre-call estimate use the seat's configured `max_tokens` as the assumed
output, or a rolling average of that seat's actual output this run? My default is the
configured cap, because estimating with anything smaller lets the last call of a run cross
the limit it was checked against. Argue me out of it if you disagree.

---

## 2. Crossref field-matching

Today a DOI that resolves is PASSED. A DOI that resolves to a **real paper that is not the
cited one** also passes. That is the characteristic language-model citation error and the
check my doctorate work most needs.

**2.1** Title comparison: what normalization and what similarity threshold? Name the
algorithm (token set ratio, Jaccard on normalized tokens, something else) and the cut-off,
and say what that cut-off is based on rather than asserting a number.

**2.2** Author matching: first-author surname only, or all listed authors? How do I handle
transliteration, hyphenated surnames, "et al." in the seat's claim, and initials-only
records?

**2.3** Year: exact match, or tolerance? A preprint and its published version routinely
differ by a year, and Crossref sometimes carries both `published-print` and
`published-online`. Which field is authoritative and what tolerance is defensible?

**2.4** Venue: is a mismatch a FAIL, or advisory? Journals rename and Crossref
`container-title` is inconsistent.

**2.5** What is the correct verdict when Crossref resolves the DOI but returns a record too
sparse to field-match at all — no title, no authors? My instinct is BLOCKED rather than
FAILED, because absence of metadata is not evidence of fabrication. Confirm or correct.

---

## 3. BLOCKED versus FAILED

A firewall must never masquerade as a fabrication. The tool currently conflates them.

**3.1** Give me the complete mapping. For each of: HTTP 429, 500, 502, 503, 504, 403, 404,
401, 400; DNS failure; TLS failure; connect timeout; read timeout; malformed JSON; empty
body — is it BLOCKED or FAILED, and why?

**3.2** A 404 from Crossref is genuinely ambiguous: the DOI does not exist, or Crossref does
not have it. Which way should it fall, and what would justify the other?

**3.3** How should BLOCKED claims be reported so they never read as findings? My default:
counted separately in the holes list, never contributing to earned kills, never entering
the seat conduct ledger. Confirm.

---

## 4. The code_behavior test runner  — I CANNOT DECIDE THIS FOR YOU

`TestExecutionGate` exists and is unreachable from the CLI because it needs a test-runner
callable, and there is no honest default: a runner nobody chose is either inert or
dangerous. Constraint: model output is never executed, never determines a path, never
becomes a command.

**4.1** What command shapes should be permitted? An allowlist of executables
(`pytest`, `python -m pytest`, `make test`), a regex, or a config list of exact approved
commands?

**4.2** What sandbox? Subprocess with a working directory and no shell, a container, or
something else? Should network be available to a test?

**4.3** Timeout per test, and what a timeout means — BLOCKED or FAILED?

**4.4** A seat proposes a `code_behavior` warrant. My design records it as *a test the
operator should write*, never a command to run. Confirm that is right, and say what should
happen if the operator later approves it — does it become runnable, and how is that
approval recorded in the audit chain?

---

## 5. Stage-6 adversarial auditors

Not built. Two auditors receive the final answer and its surviving claims only, never the
round files and never each other's output. Findings go in the deliverable and are never fed
back into another stage.

**5.1** Which two seats should audit? They must not have participated in stages 1–5, which
with five seats means the panel drops to three thinkers. Is that the right trade, or should
auditors be a second call to two of the same five with no run context? Say what you lose
either way.

**5.2** Give me the two auditor prompts. One hunts what is NOT TRUE (false claims,
unresolvable citations, arithmetic, unsupported figures). One hunts what is MISFRAMED
(scope drift, swapped question, buried assumptions).

**5.3** If an auditor lands a hit, the answer is labelled PROVISIONAL rather than FINAL.
What counts as a hit, mechanically? An auditor asserting a problem is not the same as there
being one, and I will not let a model's say-so change a verdict.

---

## 6. Watched folder on macOS

Not built. The spec I was given assumed Windows/WSL2 and prescribed polling for reasons
that do not apply here.

**6.1** FSEvents via `watchdog`, or polling? macOS has no `/mnt/c` boundary problem. If
polling, what interval and what debounce so a partially synced file is not read mid-write?

**6.2** What happens when a run fails at 3am — retry, quarantine the input, or stop the
watcher? Say which failure classes justify which.

**6.3** Should the watcher be allowed to run at all before ceilings are wired? My position
is no. Argue if you disagree.

---

## 7. Answer format

For each numbered question:

```
Q<number>
DECISION:  the choice, stated flatly
GROUNDED IN: doc URL, standard, measured figure, or "engineering judgement"
IF WRONG:  what breaks, and how I would notice
```

Do not answer questions you have to guess at. A list of eighteen confident answers where
four are invented is worse than fourteen answers and four honest unknowns, because I cannot
tell which four to distrust.
