# Verification request

You are verifying a codebase. I am not going to tell you what to check.

I am going to tell you what this tool is supposed to be, what was changed and
why, and what I claim is now true. Your job is to decide, from the code itself,
whether those claims hold — and to find whatever is wrong that I have not
mentioned, including things I would not think to mention.

Derive your own checks. Assume nothing I say is true because I said it. Where
my description and the code disagree, the code is the fact and my description
is the defect. Where the code is correct but a comment explains it wrongly,
that is also a defect: every claim in this repository is load-bearing, because
the next person to change it will believe the comment.

Read the code. Run it. Run the tests. Write your own tests where mine look like
they would pass whether or not the behaviour is right.

---

## What the tool is for

An operator has a hard question with several possible answers. Five language
models from five different vendors are given the question independently. None
of them sees any other's response. Each produces claims. Code — not a model —
mechanically checks every claim it can: recomputes arithmetic, resolves DOIs
against registries, verifies quoted strings appear at the URLs they are
attributed to, checks cited papers are the papers named, runs operator-approved
commands, validates against schemas.

Answers whose claims are mechanically refuted are eliminated. What remains is
consolidated by one seat and becomes the starting point for the next round.
Five rounds, each applying a different analytical framework. What survives goes
to the operator to verify independently.

The tool's entire claim on a reader's trust is that something was ruled out by
machinery rather than agreed on by models. Any path by which an unchecked
assertion reaches the operator looking checked is the failure that matters most.

## The design rules it is built on

These are the rules. Verify the code obeys them; where it does not, that is a
finding regardless of whether a test covers it.

1. **Blindness.** No seat may see another seat's response within a round. The
   statistical claims about panel independence are void if this leaks.

2. **Fail closed on the conclusion, never on the candidate.** Something shown
   WRONG is eliminated. Something that could not be CHECKED survives and is
   listed as open — it could be true, and killing it would let an outage,
   paywall or rate limit destroy a correct answer. Only something verified is
   accepted. Three outcomes, not two.

3. **BLOCKED is not FAILED.** A check that could not run is not evidence
   against the claim. Every consumer of a verdict must honour this.

4. **Consensus is not adjudication.** A merged answer from a panel that
   eliminated nothing must not be presented as an answer that survived
   scrutiny. They look identical on the page and are different facts.

5. **Never invent.** No number, citation, probability, cost or timeline that
   did not come from the material or from a mechanical check. Confidence is
   bounded by measured seat independence, and unmeasured independence is not
   high independence.

6. **Money and credentials fail closed absolutely.** Ceilings are checked
   before a call, never after. A credential never crosses a plaintext
   connection or a redirect.

7. **The record must say WHY, not just WHAT.** A durable artifact that says a
   seat failed without saying how is evidence destroyed.

## What I changed, and what I claim

I ran the tool live against all five real vendors. It completed, cost real
money, and produced a result. The result was worthless in a way the tool did
not report: 352 claims proposed, 210 escalated to a human, **zero eliminations
across all five passes**, a seat error in four of five passes, and pairwise
claim overlap between 0.0000 and 0.0238 — the seats were not disagreeing, they
were not addressing the same points at all. The tool emitted something shaped
like an answer anyway.

Everything below came out of diagnosing that run.

**Seat timeouts.** I reproduced one vendor answering a real full-size prompt
after 275 seconds against a 120-second timeout. I raised the default and made a
read timeout fail once instead of retrying. I claim retrying a timeout is
always wrong here and that other transport faults still retry.

**Billing.** The same call reported 1320 prompt tokens, 2433 completion tokens,
and 16748 total. I claim roughly 13,000 tokens were generated, billed, and
invisible to the cost ledger, that every ceiling was therefore enforced against
a fraction of real spend, and that this is now reconciled without hard-coding
any vendor's payload shape.

**Claim volume.** I claim 59% of claims escalating means the panel produced a
queue rather than an answer, and that seat prompts now carry ceilings that make
this structurally hard.

**Personas.** Five fixed stances, one per seat, stable for the run. I claim
they lower measured error correlation by making seats fail differently, that
they are search strategies rather than licences to conclude, and that the
closer sees which lens produced what without ever learning which vendor did.

**The verdict gate.** I claim a run that refuted nothing, or whose independence
was never measured, now declares itself NOT ADJUDICATED above the answer rather
than below it, and that nothing is withheld from the operator when it does.

**Claim identity.** I found that a claim constructed without an id kept an empty
one, and that empty ids alias — so the first such claim was adjudicated and
every later one was silently dropped, uncounted. I claim this is now impossible
by construction.

**The watcher.** I found that hitting a spend ceiling raised an unhandled error
from inside the ceiling handler, stranded the input file, and killed the
unattended loop. I claim a ceiling is now a clean stop and the loop survives
anything.

**Verification infrastructure.** I found three CI lists that had silently
stopped covering new code: named test files, named coverage modules, named
security-scan targets. The engine implementing the round design was in none of
them. I claim all three are now discovery-based and that the coverage number is
honest for the first time.

## What I know is still incomplete

Stated so you do not have to find it, and so you can tell me if it is worse
than I think: `console.py` and `intake.py` are untested — roughly 480
statements of interactive terminal prompting. Everything else stands at 92%.

## How to run it

Python 3.11 or newer is required — numpy 2.x will not build below it.

```
cd adjudication
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/bandit -q -c pyproject.toml -r .
```

`python3 run_adjudication.py --demo` runs the engine on fake seats and costs
nothing. `profiles.json` and `.env` hold live credentials — do not read, print
or transmit their contents, and do not make a live call.

## What I want back

Findings, most severe first. For each: where it is, what breaks, and the
concrete input or state that makes it break. Distinguish what you executed and
observed from what you reasoned about but did not run — I have had reviews
where every finding was plausible and none had been tested, and they cost more
than they were worth.

If a claim above is false, say so plainly. If the code is right and my reasoning
for it is wrong, say that too. If you think the architecture is wrong, say that
— it is a more useful finding than a list of small ones.
