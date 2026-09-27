# AGENT/: the Night Agent SDK runtime (v11.4)

`run_night.py` is a second implementation of Dispatch. It executes DISPATCH.md with deterministic Python and
drives the seats through the Claude Agent SDK, one fresh session per send. It is not a thinker: the only model
calls it makes are the sends DISPATCH.md names, the CHECK stage is its own code (arithmetic, doi.org and
crossref.org lookups, document reads; commands only through the EXECUTOR), and `TESTS/na_gate.py` runs before
every stage and every send. DISPATCH.md Section 9 is the mapping from browser concepts to SDK concepts.

## Run a night (live, the default)

```
export ANTHROPIC_API_KEY=...            # the SDK reads the process environment, not .env
pip install -r AGENT/requirements.txt   # claude-agent-sdk; the SDK bundles the Claude Code binary
python3 AGENT/run_night.py <root> --ask ask.md --documents <project docs dir> [--sandbox <artifact dir>] \
    [--budget-usd 40] [--hard-stop 06:00]
```

`<root>` receives `runs/na-NNN/` (the run folder the checker audits), `architecture/` (runs.jsonl,
model-capability-ledger.jsonl) and `work/<run>/` (working copies for the EXECUTOR). Every seat is
`claude-opus-5` unless `--model` or `--model-seat G2=claude-sonnet-5` says otherwise.

Credentials: `--auth key` (the default) requires `ANTHROPIC_API_KEY` and exits 2 without it. `--auth cli` uses
whatever the SDK's Claude Code binary is signed in with (a `claude` login on the machine, or a host that manages
the provider) and needs no key; the registry records the route in each seat's `auth` field. Either way the
runtime never falls back to fake seats on its own; a seat that cannot authenticate fails its handshake and the
night stops with STOP_REASON CREW before any GENERATE spend.

Spend: every text send is capped at 2 USD and every EXECUTOR session at 5 USD by the SDK's own budget option.
`--budget-usd N` adds a total cap on the night: Dispatch charges the SDK's cost estimate of every call it
observes (`AGENT/budget.py`) and stops with STOP_REASON BUDGET before the call that would pass the cap, taking
the most expensive call of that kind so far as the expectation, so the overshoot is at most one per-call cap.
SELECT also refuses another operator when one operator plus the tail would pass it. The running total is in
`status.json` and `ledger.json` as `cost_usd_estimate`; it is the SDK's estimate, not an invoice.

The first live night to run was DIRECT on BT-1 (`TESTS/BENCHMARK_TASKS.md`); its records are under
`EVIDENCE/`. The HYBRID rehearsal on BT-8 has not been run and is the operator's to start, with a cap they choose:

```
python3 AGENT/run_night.py <root> --ask AGENT/tests/fixtures/ask_hybrid.md \
    --documents AGENT/tests/fixtures/documents --sandbox AGENT/tests/fixtures/sandbox \
    --auth cli --budget-usd <cap> --hard-stop <HH:MM> --max-wait-min 10
```

Afterwards: `python3 TESTS/na_check.py <root>/runs/na-NNN` must exit 0. The deliverable is
`final/DELIVERABLE_ASSEMBLED.md`; the flags and the classification are in `ledger.json`.

## Rehearsal and CI (no credentials, no spend)

```
python3 AGENT/run_night.py /tmp/na --ask AGENT/tests/fixtures/ask_hybrid.md --seats fake \
    --documents AGENT/tests/fixtures/documents --sandbox AGENT/tests/fixtures/sandbox --net off
python3 TESTS/na_check.py /tmp/na/runs/na-001
python3 -m unittest discover -s AGENT/tests -t . -v
python3 AGENT/tests/run_faults.py /tmp/na_faults      # the Layer B knobs the fake seats can inject
```

Fake seats (`seats/fake_seat.py`) answer every prompt deterministically with text derived from the packet they
receive; their provider is `fake`, their url `fake://fake/<seat>`, and their deliverable is never a result.
`--fault B1:G2:GENERATE` and the other knobs in `TESTS/ADVERSARIAL_TESTS.md` inject the Layer B faults.

## What the runtime writes

Exactly the SCHEMA `files` layout, write-once, with every write logged with its sha256. In addition to what a
browser Dispatch writes: every filled packet as `packet.md` (generators), `packet-close.md`, `packet-final.md`,
`packet-verify.md`, `review/packet.md`, `gate/packet.md`; rejected replies as `rejected-<seat>-<n>.md`;
`executions.jsonl` for every command the EXECUTOR ran on Dispatch's behalf; capture records with `aborted: true`
for slots the runtime closed at MAX_WAIT or found dead on resume.

## Seats

| Seat | Runtime | Tools | System prompt |
|---|---|---|---|
| G1..Gn, CLOSER, REVIEWER, VERIFIER | fresh `ClaudeSDKClient` per send, `disallowed_tools=["*"]`, `permission_mode="dontAsk"`, `max_turns=1`, `setting_sources=[]`, `max_budget_usd` per send | none | `PROMPTS/S0_system.md` |
| EXECUTOR (with `--sandbox`) | fresh session per task, `cwd` = the working copy, `permission_mode="acceptEdits"` | Read, Write, Edit, Glob, Grep, Bash | Claude Code preset plus the executor rules |

The EXECUTOR's PreToolUse hook denies any path outside the working copy and any Bash command that is not the
exact command Dispatch asked for (the gate's procedures, or a command the gate's ground truth names); every denial
and every tool result is recorded, and RETRIEVED values are taken from tool output, never from the seat's prose.

## What the runtime never does

Decide truth; ask a model whether a claim is true; send anything to a seat that is not a registered seat; edit a
written file (status.json excepted); follow a redirect off the allowed check domains; run a command the gate did
not name; hand a fake-seat deliverable to the operator as a result.

## Costs

`ResultMessage.total_cost_usd` is the SDK's client-side estimate. It is recorded per send in
`architecture/model-capability-ledger.jsonl` and summed into `final/metrics-summary.json` as
`estimated_cost_usd`. It is not a bill; the Console usage page is.
