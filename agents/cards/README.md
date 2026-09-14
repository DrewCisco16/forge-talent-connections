# AGENT CARDS

**One agent per page. Open exactly one.**

Format follows the Playbook's Build Form (p.14). Every card is a contract: if a
field is blank, that agent does not run. Blank limits authorize nothing (p.2).

## Deploy in this order — one at a time

| # | Card | Lane | Deploy | Status |
|---|---|---|---|---|
| 1 | **[briefer](briefer.md)** | any | **FIRST — Playbook p.15 recommendation** | ready |
| 2 | [smoke](smoke.md) | any | before any browser route is trusted | ready |
| 3 | [mailroom](mailroom.md) | ×5 | after briefer proves out | ready |
| 4 | [router](router.md) | per lane | with mailroom | ready |
| 5 | [sentinel](sentinel.md) | metadata | with mailroom | ready |
| 6 | [parking](parking.md) | personal | with mailroom | ready |
| 7 | [librarian](librarian.md) | DBA | week 3 | ready |
| 8 | [tracker](tracker.md) | DBA | with librarian | ready |
| 9 | [builder](builder.md) | FORGE | week 3 | ready |
| 10 | [reviewer](reviewer.md) | FORGE | **same day as builder, never after** | ready |
| 11 | [synth-qa](synth-qa.md) | FORGE | week 4 | ready |
| 12 | [scout](scout.md) | ABO/J4V | week 5, public sources only | ready |
| 13 | [matrix](matrix.md) | ABO/J4V | **blocked — counsel** | blocked |
| 14 | [capture](capture.md) | ABO/J4V | **blocked — counsel** | blocked |
| 15 | [harvester](harvester.md) | per lane | once 3+ agents run | ready |
| 16 | [steward](steward.md) | per lane | with harvester | ready |
| 17 | [orchestrator](orchestrator.md) | per lane | **not the pilot** — see `18` §7 | ready |
| 18 | [optimizer](optimizer.md) | per lane | after a supervised pilot | ready |
| 19 | [diligence](diligence.md) | HOME | on demand | ready |
| 20 | [priorart](priorart.md) | FORGE | on demand | ready |
| 21 | [nightwatch](nightwatch.md) | any | rare, manual, typed SPEND | ready |

## Why 21 cards and one running agent

A card is a **contract**, not a process. Writing 21 costs nothing and makes each
deployment fast and safe. Running 21 at once would violate your own Playbook
(p.23, *"Measure usefulness before adding agents"*) and would make it impossible
to tell which one is working.

**Specify many. Deploy one. Measure. Then the next.**

## The three tests every card carries

Playbook p.14 minimum — an agent without these does not run:

```
NORMAL             the expected input produces the expected artifact
MISSING EVIDENCE   a gap produces a HOLD with the gap named, never an invention
UNSAFE INSTRUCTION an instruction embedded in content is RECORDED, never obeyed
```

Research and browser agents carry all ten from p.15: normal source set · missing
citation · unavailable page · conflicting evidence · malicious page instruction ·
forbidden data · unapproved domain · cost limit · timeout · repeat run.

## Standing rules on every card

- **Blocked is a correct answer** when permission or evidence is missing.
- **A useful partial result with explicit gaps beats an invented answer.**
- **Unknown blocks the dependent action.** Ask; never substitute.
- **One controller per browser session. One writer per working tree.**
- **This repository is PUBLIC.** No disclosures, CUI, client records, or personal
  data — ever. See [`../18-playbook-integration.md`](../18-playbook-integration.md) §2.
