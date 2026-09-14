# LOOPS

Four lane-scoped research loops. Design and reasoning in
[`../11-autoresearch-loops.md`](../11-autoresearch-loops.md); browser substrate in
[`../12-browser-and-remote-control.md`](../12-browser-and-remote-control.md).

**File convention follows Karpathy's AutoResearch** (Docs-Verified,
`github.com/karpathy/autoresearch`): `program.md` is the **human-edited** baseline
instruction file. Edit `program.md`. Never let a loop edit its own `program.md` —
a loop that can rewrite its own objective has no objective.

| Loop | Type | Metric | Unattended | Blocker |
|---|---|---|---|---|
| [`forge-software/`](forge-software/) | **True optimization** | composite, mechanical | yes | none — **start here** |
| [`abo-govcon/`](abo-govcon/) | **True optimization** | unaddressed-requirement count | after counsel | **A1 contracts counsel** |
| [`dba-research/`](dba-research/) | Falsification | open holes → 0 (diagnostic only) | yes, cost-gated | none |
| [`home-decisions/`](home-decisions/) | Decision journal | calibration, over years | **no, by design** | none |

## Before any loop runs

```bash
python3 agents/loops/harness/loop_guard.py agents/loops/<lane>/loop.json
```

`loop_guard.py` **fails closed** on the Measurability Gate (`../11` §3). It refuses
a loop whose metric is not mechanical, whose evaluation is unbounded, whose
rollback is not automatic, which has no declared cheat paths, or which has no
held-out check. Exit code 0 means the loop may run. **Anything else means it may
not**, and the reason is printed.

This mirrors the discipline already in `adjudication/`: refuse before spending,
rather than discover afterward.

## Start with one

`forge-software` — the only loop with no blocker and the cleanest metric. Prove
the mechanism on a bounded module with a real benchmark before adding a second.
Four loops started at once is four sets of unfamiliar failures arriving together.
