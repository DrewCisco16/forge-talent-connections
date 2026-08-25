# Re-verification request

You reviewed this codebase at commit `2699b94` and found 5 critical, 19 high
and 8 medium defects. I reproduced every finding I could before changing
anything. Every one I could reproduce was real, and none of your reasoning was
wrong where I could check it.

This is the second pass. **Do not trust that anything below is fixed because I
say it is.** Re-derive your own checks, re-run your own reproductions, and
assume nothing. Where my description and the code disagree, the code is the
fact and my description is the defect.

I am also asking you to look for what the *fixes themselves* broke. Several of
my earlier repairs created the next round's findings — a DNS-rebinding fix that
disabled certificate validation, a claim-identity fix that addressed aliasing
and left the underlying attack open, a coverage change that broke the security
gate. Treat every change below as new code with new failure modes.

---

## What the tool is for

An operator has a hard question with several possible answers. Five language
models from five different vendors answer independently, none seeing another's
response. Code — not a model — mechanically checks every claim it can:
recomputes arithmetic, resolves DOIs, verifies quoted strings appear at the
URLs they are attributed to, checks cited papers are the papers named, runs
operator-approved commands.

Answers whose claims are mechanically refuted are eliminated. What survives is
consolidated by one seat and becomes the next round's starting point. Five
rounds, five analytical frameworks. The result goes to the operator to verify
independently.

The tool's entire claim on a reader's trust is that something was ruled out by
machinery rather than agreed on by models.

## The rules it is built on

1. **Blindness.** No seat sees another's response within a round.
2. **Fail closed on the conclusion, never on the candidate.** Demonstrably
   wrong is eliminated. Unverifiable survives and is listed open — it could be
   true. Only verified is accepted. Three outcomes, not two.
3. **BLOCKED is not FAILED.** A check that could not run is not evidence.
4. **Consensus is not adjudication.**
5. **Never invent.** Confidence is bounded by measured independence, and
   unmeasured independence is not high independence.
6. **Money and credentials fail closed absolutely.**
7. **The record must say WHY, not just WHAT.**

---

## What I changed

Grouped as you ordered them. Each is my claim, not an established fact.

**Approved-command isolation (C1, C2, H18).** The child now gets a minimal
environment built from an allowlist of variable names rather than inheriting
the panel's credentials; output is redacted as a second layer; the policy file
is validated strictly and raises rather than silently approving nothing;
commands run in their own process group and the whole tree is killed on
timeout.

**The closer (C4).** Sentences in the merge whose content words appear in no
seat's answer are flagged, contaminate the round, and block an ADJUDICATED
verdict. This does **not** make the closer a formatter over a code-owned
survivor set, which is what you actually asked for. I closed the path by which
unchecked content reached the operator wearing the panel's authority; I did not
re-represent options as candidates with structured claim ownership. If you
think that leaves the finding open, say so.

**Warrant versus proposition (C5).** After any gate PASS, the warrant must be
shown to bear on the claim's text or the claim escalates. Arithmetic and unit
claims must name the computed value; quote and code_behavior claims must share
substantive terms; citations never establish a proposition at all. The checks
are deliberately weak and one-directional — they catch a warrant that is not
*about* the proposition, and everything else goes to a person.

**Cost (H2–H6, M4).** Bounds derived from the actual prompt rather than a flat
3,000 tokens; output bounded at 5× the cap to allow for reasoning tokens; every
dispatch checked and every attempt booked, failed ones as unmeasured; unreadable
daily state blocks instead of granting a fresh budget; unique temp files;
non-finite ceilings and unusable prices refused; pass_id threaded so per-stage
ceilings bind; only exact non-negative integers count as measured.

**Tri-state (H7, H9, M1).** `verified_true` is True/False/None. Blocked claims
appear in holes. URL-fallback transport failures raise ResolverBlocked. Soft
paywalls, truncated reads and non-UTF-8 pages are BLOCKED rather than FAILED.

**Evidence transport (H10, H11, H12, H13, M2).** Model-supplied URLs refuse
redirects and private addresses. Quotes are validated after normalisation and
must clear a minimum length. TLS pins the address while validating the
hostname. Quote-support ownership is structured data, not a substring search.
Citation matching handles polarity, Unicode, thin titles and missing dates.

**Independence (H16, H17, H19).** `measure_rho` now returns None with a
structural reason: a gate verdict is per-claim and error correlation needs
per-seat correctness, which open-ended generation cannot supply. Non-finite rho
can no longer become effective seats or High confidence. The escalation
fraction uses one deduplicated population. Five distinct vendor/model pairs are
enforced at start-up and recorded.

I also **separated adjudication from confidence**: unmeasured independence now
yields INCONCLUSIVE rather than NOT ADJUDICATED, because once rho became honest
the old rule would have stamped NOT ADJUDICATED on every run this tool can
produce, including runs that eliminated real answers. **Please attack this
decision specifically** — it is the one place I chose a weaker verdict, and I
may have chosen wrong.

**Watcher (H14, H15, M5).** Inputs are claimed by atomic rename before the
marker and content are revalidated on that snapshot; asks below 20 characters
are refused as mid-write fragments; symlinked stage folders and inbox entries
are refused; the scan and debounce are inside the backstop; a cost record is
written on every path.

**Remaining (H1, H8, M3, M6, M7, M8).** Endpoint userinfo and credential query
parameters refused; repr redacts; auth_template not echoed. Escalation queue
round-trips and only real booleans resolve a claim. CI profile probe asserts
status *and* message. Console test action uses discovery. Diagnostics scrub
credentials. A missing closer policy refuses to start.

## What I did NOT do

- **H8 (citation warrant formats).** Bare-DOI gates require the whole warrant
  to be a DOI while the field gate requires DOI plus metadata, so no single
  format satisfies all three. I did not unify them into one parsed structure.
- **C4's full remedy**, as above.
- **console.py and intake.py remain untested** — 480 statements of interactive
  terminal prompting.

## Verify it yourself

Python 3.11+ (numpy 2.x will not build below it).

```
cd adjudication
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/bandit -q -c pyproject.toml -r .
.venv/bin/python -m pytest --cov --cov-fail-under=80
```

`python3 run_adjudication.py --demo` costs nothing. `profiles.json` and `.env`
hold live credentials — do not read, print or transmit them, and make no live
call.

## What I want back

Findings, most severe first, with the concrete input or state that makes each
break. Distinguish what you **executed and observed** from what you reasoned
about but did not run.

Say plainly which of your original findings are still open, which are closed,
and which I made worse. If a claim above is false, the code is the fact. If the
architecture is wrong, that is a more useful finding than a list of small ones.
