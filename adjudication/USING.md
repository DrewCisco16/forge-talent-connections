# Using it — from your phone

This is the whole procedure. Nothing here needs a laptop, a terminal, or a
local copy of anything.

## Once: three secrets, already set if calibration runs

The button uses exactly the secrets the calibration button uses. If you have
run a calibration from your phone, skip this. If not, `CALIBRATING.md` step 1
walks through them: five `ADJ_SEAT_n_API_KEY`, five `ADJ_SEAT_n_MODEL`, and
`ADJ_PROFILES_JSON` (your settings file pasted as one value — it holds no key).

## Every time: the button

1. Open the repository in the GitHub app or a browser.
2. **Actions** → **adjudicate** → **Run workflow**.
3. Fill in three boxes:

   | Box | What to put |
   |---|---|
   | `ask` | Your question, decision, or the artifact to check. Paste the whole thing. All five seats see exactly this and nothing else. |
   | `max_cost_usd` | The most this run may spend. It plans first and refuses before the first call if the plan does not fit. Default `17.00`; a full run has measured about $5 and bounded under $17. |
   | `confirm` | Type `SPEND`. Anything else stops before a single vendor is called. |

4. Tap **Run workflow**. A full five-round run takes on the order of an hour.

## What comes back

Open the run. The **Summary** tab carries the whole report, in the order the
manual says to read it:

1. **What the gates found** — read this before the answer. Which claims were
   mechanically refuted, which options were removed and why, which seats
   failed or were cut off at their cap.
2. **The answer** — what survived, and every reason the rest went.
3. **Convergence, divergence and the holes** — whether the rounds were still
   finding new errors, how much the five seats disagreed, and every open hole
   with what would close it.
4. **May this be committed?** — YES only when one candidate survives *and* no
   hole remains. Both halves. Most runs say NO here, and that is a result: it
   tells you what is still open.
5. **What to do next** — the judgment queue, which is where a person decides
   the claims no gate could.

The run's colour means:

| Colour | Meaning |
|---|---|
| green, no warning | resolved — one survivor, nothing open |
| green with a warning | not resolved — read sections 2 and 5. This is the ordinary outcome, not a fault |
| red | refused before spending, or a real failure. Nothing was billed if it says REFUSED |

The **adjudication-run** artifact on the same page is the full record: your
ask, every seat's raw reply for every round, the verifier packet you can hand
to a fresh model, and the judgment queue. Kept 90 days.

## Two things it will not do

**It will not choose between survivors.** If two answers survive, it reports
two. SOP 9.3: supply claims that distinguish them, or accept the set as the
honest result.

**It will not tell you an answer is right.** It removes answers that are
demonstrably wrong. A survivor with every commitment checked has been shown
internally consistent, which is real and smaller than correctness.
