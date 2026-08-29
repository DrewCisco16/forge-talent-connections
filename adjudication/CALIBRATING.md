# Calibrating the panel — and running it from your phone

## What calibration is, in one paragraph

You pay for five AI seats because five sets of eyes catch more than one. That
only holds if the five make **different** mistakes. If they all fail on the
same things, you are paying five times for one opinion. Calibration measures
which situation you are actually in.

The way it measures is a quiz. All five seats get the **same** list of
arithmetic statements — some correct, some not — and each one says which it
believes are correct. The answer key is computed by the arithmetic gate, so no
human and no model decides what is true. Then the scoring asks a single
question: **do they get things wrong together, or separately?**

The score is called `rho`.

| `rho` | What it means | What to do |
|---|---|---|
| **0.2 or below** | They err independently | **Keep five seats** |
| **0.2 to 0.5** | They share a fair part of their errors | **Marginal** — three well-chosen seats likely buy most of it |
| **above 0.5** | They mostly fail together | **Cut seats.** Replace them with more different ones, don't add more |

## Why a normal run can't tell you this

In a normal adjudication each seat writes its own free-form answer. If seat 3
never mentions something, you don't know whether it missed it or simply wrote
about something else. Silence is **missing data**, and the tool refuses to
compute `rho` from it rather than invent a number. You'll see it say so:

> *NOT MEASURABLE: independence is not measurable from open-ended generation…*

The quiz is the other regime. Everyone must decide every item, so silence
means "I don't think that one is correct" — a real answer. That is the only
setup in which the number is honest.

## Try it first without spending anything

```
python calibrate.py --demo             # five seats that slip on different items
python calibrate.py --demo-collapsed   # five seats that slip on the same items
```

No network, no credentials, no cost. The first prints roughly `rho = -0.13`
and "KEEP FIVE SEATS"; the second prints `rho = 1.000`, `1.00 effective
seats`, and "CUT SEATS". Those are the two extremes the real number will sit
between. Run both so you know what each verdict looks like before money is
involved.

## Running it for real, from your Mac

```
python calibrate.py --profiles profiles.json --max-cost 1.00
```

Costs **five API calls total** — one per seat. Every item is in a single
prompt, so twenty-four questions cost the same as one. Keep `--max-cost`; it
is a hard ceiling and the run stops rather than exceed it.

---

# Running it from your phone

This is the part that needs a one-time setup, and **you do all of it — no
assistant ever handles a key.**

## Why GitHub secrets and not a file

A GitHub **secret** is write-only. You paste a value in once; after that
nobody can read it back — not you, not a collaborator, not an admin, not an
assistant. It is decrypted only inside a running job, and GitHub masks it in
the logs. That is a real secrets manager, and it is the mechanism your own
rule points at.

What it is **not** is a file in the repository. Never commit a key. `.env` is
ignored in three places precisely so it cannot happen by accident.

## Step 1 — add eleven secrets (once)

On the web or in the GitHub mobile app:

**Settings → Secrets and variables → Actions → New repository secret**

| Secret name | What goes in it |
|---|---|
| `ADJ_SEAT_1_API_KEY` … `ADJ_SEAT_5_API_KEY` | The five vendor API keys |
| `ADJ_SEAT_1_MODEL` … `ADJ_SEAT_5_MODEL` | The exact model id for each seat, copied from the vendor's own page |
| `ADJ_PROFILES_JSON` | The entire contents of your filled-in `profiles.json`, pasted as one value |

`ADJ_PROFILES_JSON` holds **no key** — it is endpoints and request shapes. It
travels as a secret only because `profiles.json` is gitignored and therefore
isn't in the repository at all, and a secret is the only channel that gets it
onto a runner without publishing your vendor setup.

On your Mac, get its contents with:

```
cd adjudication && cat profiles.json
```

Copy the whole thing, including the braces.

## Step 2 — press the button

In the GitHub mobile app or at github.com on your phone:

**Actions → calibrate → Run workflow**

Four boxes:

| Box | Meaning |
|---|---|
| `n_items` | How many questions. Must be even. `24` is a sensible default |
| `seed` | Which questions. The same seed gives the same quiz, so two runs are comparable |
| `max_cost_usd` | Hard ceiling. The run stops rather than exceed it |
| `confirm` | Type **`SPEND`**. Anything else and the run refuses |

The confirmation box exists because this is the only workflow in the repo that
spends money, and a phone is easy to mis-tap. It is checked **before** the
code is even checked out, so a mistap costs nothing whatsoever.

There is deliberately **no** automatic trigger — no push, no schedule. It runs
when you decide it runs.

## Step 3 — read the result

The job prints the full report in its log. It also attaches
**calibration-report** at the bottom of the run page, containing
`calibration.txt` (the readable report) and `calibration.json` (the raw
numbers). Both are kept 30 days and are uploaded **even if the run fails** —
a run that spent money and then broke is exactly the one whose output you want.

## What to watch for in the report

**`SEAT ERRORS`** — a seat that failed contributes no answers. `rho` is then a
measurement of the seats that *did* answer, not of the five you intended. Fix
the seat and re-run before trusting the number.

**`CONFIRMATIONS THAT MATCHED NO ITEM ID`** — a seat reworded the statements
instead of copying them, so its agreement couldn't be matched to the others.
That biases `rho` **downward**, making the panel look *more* independent than
it is. That is the flattering direction, which makes it the dangerous one.
Re-run before believing a good score that carries this warning.

**`NOT MEASURABLE`** — no number was produced, and the report says why. Exit
code is non-zero so an automated caller can't mistake it for success.

## Honest limits

- **It measures arithmetic only.** Five seats that are independent on
  arithmetic may still share a blind spot on domain reasoning. This is the
  cheapest honest probe available, not a general one.
- **Twenty-four items is a small sample.** It reliably separates "clearly
  independent" from "clearly collapsed". It does not support trusting `rho` to
  two decimal places.
- **It expires.** Vendors ship new models. Re-run when any seat's model id
  changes, and every few months regardless.
- **Nothing confidential goes to the vendors on this path.** The quiz is
  generated arithmetic — no claim text, no artifact, no RED material. That is
  a property of calibration specifically, and it does not extend to a normal
  adjudication run, where the artifact *is* sent to all five vendors.

## If something goes wrong

| Message | Cause | Fix |
|---|---|---|
| `Not confirmed` | `confirm` box wasn't `SPEND` | Re-run and type it exactly |
| `Secret ADJ_PROFILES_JSON is not set` | Step 1 incomplete | Add the secret |
| `Missing repository secrets: …` | A key or model secret is absent | Add the ones named |
| `still contains 'FILL-IN'` | `profiles.json` was never filled in | Fill it from the vendors' API references, then re-paste the secret |
| `seat credentials absent` | Keys didn't reach the runner | Check the secret **names** match the table above exactly |

Every one of these stops before any vendor is called. The message always ends
with what did not happen: *nothing was sent and nothing was spent.*
