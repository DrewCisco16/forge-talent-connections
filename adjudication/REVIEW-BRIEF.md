# Review brief — Adjudication Five

> **Adjudication Five** — five blinded models, claims verified by code, answers eliminated rather than voted on.

Paste this brief **first**, then one code bundle, into each reviewer
(ChatGPT Codex, Gemini). Ask each one separately. Do not show either reviewer
the other's answer — that is the same blinding rule this tool enforces on its
own seats, and for the same reason: two reviewers who have seen each other
stop being two reviewers.

---

## ⛔ Before you paste anything

**Never paste `.env` or `profiles.json`.** Those hold your API keys. The code
bundles in this folder contain no secrets — that is checked by a test — but
those two files are not code and must never leave your machine.

---

## What this system is

A tool that runs one artifact past five different AI models, one analytical
pass at a time, and decides which candidate answers survive.

The core claim it exists to test: when several models agree, that agreement is
worth something **only if** the models fail in different ways. If they share a
blind spot they will agree on a wrong answer and the agreement looks like
confidence. The tool measures which of those two things happened.

Two properties carry the whole design:

1. **Blinding.** No seat ever sees another seat's output, a gate verdict, or
   any earlier pass. Passes are sequential in *time*, independent in
   *information*.
2. **Fail closed.** Every uncertain path must DENY. A check that cannot reach
   its evidence must refuse, never wave the claim through.

---

## What I want from you

**Try to break it. Do not review it.**

A reply that says "this looks solid" is worth nothing to me. Assume there is a
defect and go find it. Specifically:

### 1. Find a fail-open path
Anywhere an error, a missing value, a timeout, or a malformed input results in
something being **accepted** rather than **refused**. This is the highest-value
bug class in this codebase. One example already found and fixed: the arithmetic
gate accepted the warrant `"True = 1"` because `bool` subclasses `int` in
Python, so a seat could attach that to any claim and be auto-accepted.

### 2. Break the blinding
Find any route by which a seat could learn another seat's answer, a gate
verdict, or which passes have run. Include indirect routes — shared mutable
state, ordering effects, error messages, anything logged and re-read.

### 3. Attack the statistics
Are the formulas right, and are they right *for this use*?
- Kish design effect: `n_eff = n / (1 + (n-1)·rho)`
- Chao1: `N_hat = S_obs + f1²/(2·f2)`, bias-corrected when `f2 = 0`
- Poisson-binomial majority probability
- Exponential decay fit and its residual extrapolation

Then attack the **correctness matrix semantics**, which is the load-bearing
judgement call in the whole system:

> An item is one proposition. `correct = (the seat asserted it) == (the claim is true)`
> A seat that stayed silent on a **verified true** finding is scored as having
> MISSED it. A seat that did not repeat another seat's **false** assertion is
> scored correct.

Is that defensible? Does scoring silence as a miss bias rho in a direction that
flatters or damns the panel? Show the bias with a worked example if you find one.

### 4. Hunt for secret leakage
The API key must never reach a log line, an exception message, a `repr`, or a
retry. Find a path where it does.

### 5. Check the tests test something
Would any test still pass if the behaviour it names were deleted? Name the test
and the deletion.

---

## Things that look wrong and are deliberate

I am not asking you to accept these. I am telling you the reasoning so that if
you still disagree you can tell me **why specifically**, rather than flagging
them as style.

- **Broad `except Exception` handlers.** These are the fail-closed handlers.
  Each carries a `noqa` naming its reason. Narrowing them would let an
  unanticipated exception type escape and skip the denial.
- **`_route` requires EVERY applicable gate to pass, not the first match.**
  Deliberate. Under first-match-wins, whichever of admissibility and resolution
  was listed second never ran.
- **The source-admissibility gate is not in the default gate list.** It answers
  "is this the right *kind* of source", never "does this source *exist*". Alone
  it accepted an invented DOI. It is safe only paired with a resolver.
- **No vendor endpoint, request shape, or response path appears anywhere.**
  Those are transcribed by the operator from vendor docs into a settings file.
  Writing them from memory is the failure this project exists to catch.
- **`singleton_alarm` defaults to `None`.** The SOP names a high singleton
  fraction as an abort signal but gives no number, so the check is unarmed
  rather than the module inventing a threshold.
- **All five passes always run.** The stopping residual was measured to be
  order-dependent: the same per-pass yields `{8,5,3,2,1}` give R = 1.64 as run,
  R = 16.95 shuffled, and no fit at all reversed. A statistic that moves
  tenfold under reordering cannot justify truncating the passes.

If you propose "add a fallback that returns True on error" anywhere, that is
the exact defect class this system is built to prevent — but if you think a
specific site genuinely needs it, argue that site.

---

## Already known — do not spend effort re-finding these

- No real model has ever run through this. Every number came from scripted
  synthetic seats. The machinery is verified; the behaviour of a real panel is
  unmeasured.
- Two references the statistics rest on (Chao 1987, Kish 1965) are unverified
  against their sources; the build environment blocks the lookup routes.
- `test_suite.py` is one 4,100-line file and `adjudication_orchestrator.py` is
  1,379 lines. Splitting both was considered and deliberately deferred.
- The audit log's head sidecar defends against accidental truncation, a crash,
  and a partial copy — not against an attacker who can write both files.

---

## State of the build

- 496 tests. Coverage 94%.
- `ruff`, `mypy --strict`, `bandit`, `pip-audit` all clean.
- Mutation tested: deliberate breaks introduced to check the tests notice.
  40 breaks, 35 caught immediately, 5 exposed weak tests that were then
  strengthened until the mutation was caught.

---

## Bundles in this folder

| File | What it is | Best question to ask of it |
|---|---|---|
| `bundle-1-math.txt` | The statistics and the run-to-rho join | Are the formulas and the scoring semantics correct? |
| `bundle-2-orchestrator.txt` | Gates, blinding, passes, stopping | Where does this fail open, and can blinding be broken? |
| `bundle-3-io.txt` | Network, settings, audit log, CLI | Where does a secret leak, and what happens on partial failure? |
| `bundle-4-tests.txt` | The whole test suite | Which of these would still pass if the behaviour were deleted? |
