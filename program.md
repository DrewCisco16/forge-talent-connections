# program.md — the overnight loop for this repository

You are an autonomous engineer running an unattended experiment loop on the
`adjudication/` package. The design is Karpathy's autoresearch, adapted for
software: one editable scope, one score, keep or revert, log every attempt,
run until the stopping rule fires.

You never decide whether an attempt was good. `autoresearch/score.py` decides.

## The score

**Branch coverage of `adjudication/` as a percentage, higher is better**, as
computed by `autoresearch/score.py`. Coverage is the number only after every
gate passes. Any gate failure scores `0.0` and the attempt is reverted.

The gates, all deterministic, all outside your control:

| Gate | What it checks | Why it exists |
|---|---|---|
| scope | Only `adjudication/*.py` (top level) changed since the run's base commit | An unreviewable morning diff is a failed night |
| suppression | No new `pragma: no cover`, `noqa`, or `type: ignore` versus base | Coverage and lint must be earned, not excused |
| lint | `ruff check .` clean | Existing CI gate |
| types | `mypy` clean under the repository's strict config | Existing CI gate |
| security | `bandit -q -c pyproject.toml -r .` clean | Existing CI gate |
| frozen tests | The test files **as they were at the base commit** still pass against your code | You cannot make a test pass by editing it |
| test count | Collected tests never fall below the base count | You cannot delete your way to green |
| tests | Your full working-tree suite passes | The score is only meaningful on green |

Read-only for you, enforced by the scope gate: `autoresearch/`, `program.md`,
`adjudication/pyproject.toml`, `adjudication/requirements*.txt`,
`adjudication/eval/`, every `.md`, `.github/`, and everything outside
`adjudication/`.

## Setup, once per run

1. Confirm you are on a branch named `autoresearch/<tag>` and that
   `autoresearch/.base` names the commit the run started from. If either is
   missing, stop and say so; the operator's launcher creates both.
2. Confirm `autoresearch/results.tsv` has a `baseline` row. If it does not,
   run `python autoresearch/score.py --record baseline`.
3. Read `autoresearch/results.tsv`. The best `ok` row is the number to beat.
4. Skim `adjudication/pyproject.toml` `[tool.coverage.run]` and run
   `python autoresearch/score.py --report` once to see which modules carry the
   uncovered lines and branches. That report is your idea list.

## The loop

Repeat until `score.py` prints `STOP`:

1. **Pick one idea.** One module, one uncovered region, one mechanism. Good
   ideas, in order of value:
   - A test that exercises an uncovered branch **and asserts on behavior**,
     not merely on the absence of an exception.
   - A bug that such a test exposes, fixed in the production module. The
     frozen-test gate protects existing behavior while you do it.
   - A property test in the style of `test_properties.py` for an invariant a
     module claims in its docstring.
   Bad ideas, which the morning reviewer will throw out and which the score
   penalizes only indirectly: tests without assertions, tests that mock the
   thing under test, tests that restate the implementation.
2. **Make the change** inside the editable scope. Follow the conventions you
   see: the module's existing test file, `pytest` style, type hints, no new
   dependencies. Read `adjudication/AGENTS.md` for the standard the verifier
   will hold you to.
3. **Run the scorer and let it decide:**

   ```bash
   python autoresearch/score.py --record "one line describing the change" --push
   ```

   It commits your working tree, runs every gate, computes the score, appends
   a row to `results.tsv`, and then either keeps the commit or resets the
   branch to the last kept state. It commits and pushes `results.tsv` either
   way. Do not run `git reset` or `git commit` yourself around this step.
4. **Read the row it printed.** `KEEP` means the number rose. `REVERT` means
   it did not, and the `status` column names the gate that failed if one did.
   Learn from it: a `frozen_tests` failure means you changed behavior an
   existing test depends on; a `suppression` failure means you tried to excuse
   a line instead of covering it.
5. **If the scorer prints `STOP`, stop.** It fires after the configured
   number of consecutive non-improvements or the iteration cap. Write a short
   summary to `autoresearch/NIGHT-SUMMARY.md`: best score, the kept changes
   in one line each, the ideas that failed and why, and what a human should
   look at first. Commit and push it with `git add autoresearch/NIGHT-SUMMARY.md && git commit -m "autoresearch: night summary" && git push`.
   That file is the one exception to the scope rule and the scorer is not
   run on it.

## Rules that do not bend

- Only `score.py` keeps or reverts. Never bypass it, never `--no-verify`,
  never edit `results.tsv` by hand.
- Never touch anything outside the editable scope. The scope gate will
  revert it, but the attempt is wasted.
- Never add a dependency, a network call, a subprocess to an external
  service, or anything that reads `.env`, `profiles.json`, or a credential.
- Never modify `pyproject.toml` to widen coverage omissions or relax a gate.
- Never write a test that passes for a reason unrelated to the behavior it
  names. The verifier reads for that specifically.
- One idea per attempt. A revert of a five-file change teaches nothing.
- Do not stop early because progress is slow. Do not continue after `STOP`.

## Output the operator reads in the morning

- `autoresearch/results.tsv`: every attempt, in order, with its score and
  status.
- The branch's kept commits: each one is a single scored improvement.
- `autoresearch/NIGHT-SUMMARY.md`: your own account of the night.
- The pull request the operator opens from the branch, which the CI gate and
  the Codex verifier then review.
