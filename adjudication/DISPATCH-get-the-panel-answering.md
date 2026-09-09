# Get the five-seat panel answering — dispatch to the container that holds the keys

**Paste this whole file and say: "Do everything in this brief."**

You have the API keys. The container that wrote most of this does not, so every
step below has been built, tested offline, and left at the exact point where a
real credential is required. Nothing here is exploratory.

---

## 0. Rules that do not bend

1. **Never ask the operator to paste an API key to you.** Not in chat, not in a
   file you read back, not "just to check". If offered one, refuse and point at
   `.env`.
2. **Never print, `cat`, echo, log or repeat the contents of `.env` or
   `profiles.json`.** You may check *whether* a line is blank. You may not show
   what is on it.
3. **Never `git add`, commit or push `.env` or `profiles.json`.** Confirm both
   are still in `.gitignore` before you finish.
4. **Only push to `claude/adjudication-test-suite-w27c3h`.** Never to `main`.
5. **Do not invent an endpoint, model id, request body, or response path.**
   Every one comes from that vendor's own current API reference, which you
   fetch. If you cannot reach a vendor's docs, leave the value alone and say so.
   A guessed endpoint one version stale returns a successful `200` with nothing
   usable, and the tool records that as *a seat that had nothing to say* rather
   than *a seat that was never reached*. Those are opposite facts, and the
   second silently corrupts the statistics this whole tool exists to produce.
6. **Every step below has a hard spend ceiling in code.** Do not raise one to
   make something pass. If a ceiling refuses a run, report that.

---

## 1. Start from the current branch

```bash
cd ~/forge-talent-connections
git fetch origin claude/adjudication-test-suite-w27c3h
git checkout claude/adjudication-test-suite-w27c3h
git pull origin claude/adjudication-test-suite-w27c3h
cd adjudication
.venv/bin/python -m pytest -q          # expect 1724 passing
```

Head at time of writing: `ac7ca8f`. If your local copy is behind, everything
below behaves differently — several of these scripts were parsing model replies
incorrectly until this branch.

**What changed that matters to you:** every marker line the protocol defines
(`OPTION`, `PREDICATE`, `FORMULA`, `INPUT`, `CHALLENGE`, `MERGE`, and the
seeded-truth `ANSWER`) was matched only when a model wrote it bare. Eleven of
twelve shapes a model actually uses lost the `PREDICATE` entirely, in silence.
All of them now read through one undecorator. If you ran any of these scripts
before this branch, the results are not comparable.

---

## 2. Settle seats 1 and 2 — the cheapest step, do it first

> **SETTLED, 2026-09-09.** `diagnose-seats.py` was run with real credentials
> and **every seat probed returned HTTP 200 with `text_path` resolving**.
> `profiles.json` was not changed. The five-of-five failure below is run-001
> in **August**, and it no longer describes this panel. This section is kept
> because the diagnostic is still the right first move after any settings
> change, and because the failure table is still how to read its output.

Run-001 failed seats 1 and 2 five of five identically, which is a deterministic
config or credential fault rather than a blip. The error message was discarded
by the old code, so nobody could tell which. That is fixed.

```bash
.venv/bin/python diagnose-seats.py
```

One call per seat, ~6-token prompt, 64-token cap, hard ceiling **$0.05** for the
whole script. It prints the HTTP status, the vendor's own error body, and
whether `text_path` resolved. Credentials are redacted from every line.

That single output decides between all the competing hypotheses. Read it, then:

### seat_1 (OpenAI, `gpt-5.6-sol`)

| What you see | What it means | What to do |
|---|---|---|
| HTTP 400 | wrong parameter — `max_completion_tokens` was chosen for reasoning models but never confirmed on this model's page | check the vendor page, fix `profiles.json` |
| HTTP 200, `text_path` did not resolve | reasoning tokens spent the whole cap before any reply | raise that seat's `max_tokens` **and** `--max-cost` in proportion — see §5 |
| HTTP 401 / 403 | credential or account | operator fixes `.env`; do not touch it yourself |

### seat_2 (Google, `gemini-3.1-pro-preview`)

> **THE HYPOTHESIS BELOW WAS WRONG, and the diagnostic settled it.** This seat
> answers through the compatibility endpoint. Nothing here needs changing. The
> `{{model}}`-in-a-URL capability described next is real and still useful if
> this seat ever has to move to the native endpoint, but it is not a fix for
> anything currently broken.

The hypothesis was: `profiles.run001.json` points this seat at Google's
OpenAI-**compatibility** endpoint, and Google's newer auth keys are reported to
be rejected by that layer while working against the native endpoint. The stored
key is 53 characters where an older-style `AIza` key is 39.

**That endpoint was chosen because of a constraint of ours, not Google's.**
`seat_profiles` used to reject any placeholder in a URL, and Google's native
call names the model in the path. **That constraint is gone.** An endpoint may
now carry `{{model}}` — and only `{{model}}` — filled in per call and
URL-quoted:

```json
"endpoint": "https://<from Google's API reference>/models/{{model}}:generateContent"
```

So if the diagnostic shows an auth-type rejection, switch this seat to the
native endpoint. **Copy the URL, the request body shape and the reply path from
Google's own API reference.** Do not copy them from this file and do not write
them from memory. Then:

```bash
.venv/bin/python run_adjudication.py --check-profiles
```

That is offline and free. It confirms the shape parses; it does **not** confirm
the endpoint is real. Only a call does that, which is what §2's diagnostic is.

---

## 3. Re-measure rho — the number that says whether five seats are five

The first seeded-truth measurement returned **rho = +0.9024, 1.08 effective
seats of five**, for $0.18. It rested on the 9 items every seat decided.

It was reading verdicts with the same anchored pattern described in §1: seven of
eight shapes a model writes returned nothing. A lost verdict was correctly
dropped rather than scored wrong, so **rho was not inflated** — but the sample
shrank toward the items where all five seats happened to write plainly. That is
now fixed, so re-run it:

```bash
.venv/bin/python seeded_rho.py
```

10 items x 5 seats = 50 calls, 2048-token cap, ceiling **$6.00**
(`SEEDED_RHO_CEILING`). Last measured cost: $0.18, five minutes.

**Report the full output**, including `items EVERY seat decided`. If that count
went up from 9 and rho moved, say by how much. If rho stayed near 0.90 on a
larger sample, that is a firmer finding, not a worse one.

---

## 4. Ask whether live seats write the contract at all

Nobody knows whether a real seat emits `PREDICATE`, `FORMULA` or `INPUT`. The
contract asks for them in the same block seats demonstrably obey for `CLAIM`,
but that is an inference from one observation.

```bash
.venv/bin/python compliance_probe.py
```

Five thinker calls, ceiling **$2.50** (`PROBE_CEILING`), 4096-token cap.
`PROBE_SEATS=seat_1,seat_2` limits it to seats you are debugging.

**Read its verdict carefully and do not act on it blindly.** Until this branch,
this probe counted contract lines with the anchored pattern too, so a seat that
complied perfectly and used bullets counted zero on every column — and the
probe's own verdict text then recommends abandoning the text contract for each
vendor's structured-output mode. That would have been a rewrite bought with a
false measurement. It counts correctly now. If it *still* reports silence after
this fix, the finding is real and worth acting on.

---

## 5. Only then, a full five-round run

```bash
.venv/bin/python full_run.py
```

Ceiling **$17.00** (`FULL_RUN_CEILING`). It plans before it spends and refuses
before the first call if the plan does not fit.

**The output cap and the spend ceiling are coupled.** Raising a seat's
`max_tokens` raises the worst-case estimate the ceiling checks against, because
the estimator allows 5x the cap in billed output (reasoning tokens are billed
and are not bounded by `max_tokens`). Measured on a 24-item calibration, worst
case across all five seats:

```
cap  4096  ->  $0.72   fits --max-cost 1.00
cap  6144  ->  $1.08   REFUSED at 1.00
cap  8192  ->  $1.43   REFUSED at 1.00
cap 16000  ->  $2.80   REFUSED at 1.00
```

So raising a cap without raising the ceiling in proportion turns *one seat
returns empty text* into *the run never starts*. Raise both together.

Read the output in the order it prints. It prints gate results before any model
prose deliberately — SOP 9.1 step 4, on the finding that wrong answers from AI
users are graded *more* coherent, so reading the prose first is how a polished
error gets committed.

---

## 6. What to report back

1. `diagnose-seats.py` output in full — the status and vendor body per seat.
2. What you changed in `profiles.json` and **which vendor page you took each
   value from**. Name the URL.
3. The full `seeded_rho.py` output: rho, effective seats, items every seat
   decided, per-seat scores, spend.
4. The compliance table from `compliance_probe.py`.
5. Anything you could not verify against a vendor's own documentation, left
   unchanged and flagged.

Push to `claude/adjudication-test-suite-w27c3h`. Do not push `.env` or
`profiles.json`.

---

## Two things already flagged, that need a vendor page you may be able to reach

- **`rates.json` seat_3**: Mistral retired the Magistral reasoning line, so this
  seat is a general-purpose model rather than the stepwise reasoner the panel
  design asked for. The id `mistral-medium-latest` is unconfirmed — Mistral
  documents `mistral-medium-3504` and does not list `-latest` aliases — and the
  $1.50/$7.50 prices could not be re-verified. Both are flagged in a key the
  code now reads and warns about before any call. Confirm both on Mistral's own
  pages and stamp `verified_on`.
- **`max_input_tokens` is `null` on all five seats.** That means a request larger
  than the price was checked at is still authorised. Fill each in from the
  vendor's own documentation; a guessed limit is a guessed ceiling.
