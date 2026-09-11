# autoresearch — the overnight loop for this repository

Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) pattern,
applied to software instead of LLM training: **one editable scope, one score,
keep or revert, log every attempt, stop by rule.** The agent proposes; the
scorer decides.

| autoresearch | here |
|---|---|
| `train.py`, the one editable file | `adjudication/*.py` |
| `prepare.py`, the frozen harness | `autoresearch/score.py` plus the tests as they were at the run's base commit |
| `val_bpb`, lower is better | branch coverage of `adjudication/`, higher is better, after every CI gate passes |
| `results.tsv`, untracked | `autoresearch/results.tsv`, tracked and pushed after every attempt |
| "NEVER STOP" | a stopping rule: attempt cap and a patience count |
| the agent runs `git reset` | the scorer runs it, so the agent never judges its own work |

## Files

| File | Who edits it | What it is |
|---|---|---|
| `program.md` (repo root) | you | the agent's brief: setup, loop, rules |
| `autoresearch/score.py` | you | the frozen harness: gates, score, keep-or-revert, results row, stopping rule |
| `autoresearch/settings.json` | you | the agent's permission allowlist: scoped, no blanket bypass |
| `autoresearch/run_night.sh` | you | local launcher: branch, baseline, tmux, timeout |
| `.github/workflows/autoresearch.yml` | you | the same loop as a button on a GitHub-hosted runner |
| `autoresearch/results.tsv` | the scorer only | every attempt: commit, score, status, tests, seconds, KEEP or REVERT, description |
| `autoresearch/NIGHT-SUMMARY.md` | the agent, once, at STOP | its own account of the night |

## The gates, in order

Every gate is deterministic and runs outside the agent's control. The first
failure sets the row's `status`, the score is `0.00`, and the attempt is
reverted.

| status | meaning |
|---|---|
| `scope` | something outside `adjudication/*.py` changed since the base commit |
| `suppression` | more `pragma: no cover`, `noqa`, `type: ignore`, or `pytest.mark.skip/xfail` than the base commit had |
| `lint` | `ruff check .` failed |
| `types` | `mypy` failed under the repository's strict config |
| `security` | `bandit` found something |
| `frozen_tests` | the base commit's test files fail against the new code (only run when a test file changed) |
| `test_count` | fewer tests collected than the base commit had |
| `tests` | the working-tree suite failed |
| `ok` | all gates passed; `score` is the coverage percentage |

## Verified in the session that built this (2026-09-11)

A live self-test on a throwaway branch, base commit with 1,735 tests and
79.74% branch coverage:

| attempt | expected | observed | seconds |
|---|---|---|---|
| baseline | KEEP | KEEP 79.74 | 133 |
| add `# pragma: no cover` to a function | REVERT, `suppression` | REVERT, `suppression`, tree restored | 0 |
| add three asserting tests for `intake.slugify` | KEEP, score up | KEEP 79.95, 1,738 tests | 216 |
| delete `test_truncation.py` | REVERT, `test_count` | REVERT, `test_count`, file restored | 87 |
| append to `program.md` | REVERT, `scope`, then STOP at patience 2 | REVERT, `scope`, `STOP` printed, exit 3 | 0 |

So a scoring pass costs about two to four minutes, which is roughly fifteen
attempts an hour when the agent is quick and ten when it thinks.

**Not yet verified:** a full unattended night on a real machine, and the
first run of the GitHub workflow (the `claude-code-action` inputs come from
its documentation, not from a run). Make the first cloud run a short one:
`max_iter` 3, `patience` 2, and read the job log.

## Running it at home

Any machine with Python 3.11, git, tmux, and the Claude Code CLI signed in.
Windows machines run it inside WSL2 Ubuntu. Keep the machine awake at the OS
level; the launcher adds `caffeinate` on a Mac but cannot stop Windows from
sleeping.

```bash
git clone https://github.com/DrewCisco16/forge-talent-connections.git
cd forge-talent-connections
autoresearch/run_night.sh night-01 --hours 8
```

That creates `autoresearch/night-01`, records the baseline, and starts the
agent in a detached tmux session. Watch it from another terminal or from a
phone through [Remote Control](https://code.claude.com/docs/en/remote-control):

```bash
tmux attach -t autoresearch-night-01        # detach with Ctrl-b d
tail -f autoresearch/night-night-01.log
cat autoresearch/results.tsv
tmux kill-session -t autoresearch-night-01  # stop early
```

Options: `--hours`, `--model` (default `claude-opus-5`), `--max-iter`,
`--patience`, `--no-push`, `--print-only`.

Permissions: the agent runs with `autoresearch/settings.json`, an allowlist
that covers the scorer, the test tools, read-only git, and edits inside
`adjudication/`. Reading `.env` or `profiles.json`, installing packages,
network calls, `git reset`, and `rm` are denied. In non-interactive mode a
denied tool call fails instead of prompting, and the scorer's scope gate is
the backstop.

## Running it as a button

1. On any machine where `claude` is signed in, run `claude setup-token` and
   store the result as the repository secret `CLAUDE_CODE_OAUTH_TOKEN`.
2. Actions → **autoresearch** → **Run workflow**. Fill in a `tag`, type
   `RUN` in `confirm`, tap Run.
3. The job's **Summary** tab shows `results.tsv` and the night summary when
   it finishes; the branch `autoresearch/<tag>` holds the kept commits.

GitHub-hosted jobs stop at six hours, so a cloud night is about forty
attempts. The `concurrency` group means a second press waits for the first.

## The morning

1. `cat autoresearch/results.tsv` on the run branch. Every KEEP row is one
   scored improvement; every REVERT row names the gate that caught it.
2. Read `autoresearch/NIGHT-SUMMARY.md`.
3. Open a pull request from the run branch. The existing `adjudication`
   workflow runs the same gates in CI, and Codex reviews under
   `adjudication/AGENTS.md`. Nothing merges on the scorer's word alone.
4. Judge the tests the way `program.md` tells the agent they will be judged:
   an assertion-free test raises the number and is still worthless.

## Changing the harness

The score's meaning is fixed by `score.py`'s constants. Changing the
scope, the suppression patterns, the gate order, or the metric makes every
earlier row in `results.tsv` incomparable, so start a new run tag when you
do. To point the same loop at another package, copy `program.md` and
`autoresearch/` and change `PACKAGE` in `score.py`.
