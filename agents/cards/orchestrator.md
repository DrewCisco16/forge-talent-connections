# ORCHESTRATOR — agent card

> Drive a multi-window elimination run: four thinkers, one closer, gates before
> the merge, stop on no-new-corrections.

| Lane | Version | Tier | Route | Status |
|---|---|---|---|---|
| per lane, one machine each | 1.0 | B | Route A, B or C — **one controller** | **not the pilot** |

> **Not the first agent.** Playbook p.16: *"For the pilot, keep one browser
> controller… A second AI service is optional, not mandatory."* Start with
> [briefer](briefer.md). ORCHESTRATOR is a later capability.

### INPUTS
One sanitized question. **Its lane only.** A swarm Chrome profile holding the AI
subscriptions **and nothing else**.

### OUTPUT
`STRUCK BY GATES` (read first) · `SURVIVORS` · `DIVERGENCE (qualitative)` ·
`OPEN HOLES with what would close each` · `JUDGMENT QUEUE` · `COMMITTABLE? YES
only if one survivor AND zero holes`.

### THE ROUND SHAPE — from `night_loop.py`, unchanged
```
R1  THE WALL: no thinker sees another's text, name, or that others exist
    each proposes 2-4 options WITH what would falsify each
    ↓ GATES (deterministic, local, no model) — refuted claims STRUCK
    ↓ CLOSER merges only survivors. Never adds a claim
R2+ all thinkers read the SAME merged text and attack it. Gates again.
STOP on a round with no new verified corrections, or MAX_ROUNDS
```

### ACCEPTANCE TESTS
```
normal              → survivors, strikes and holes returned within MAX_ROUNDS
missing evidence    → a hole nothing closes → reported as an OPEN HOLE, not resolved
unsafe instruction  → a model reply containing an instruction → FINDING, not obeyed
wall integrity      → no round-1 prompt reveals another thinker
closer discipline   → a claim in the merge from no thinker → run FLAGGED
label               → output says SWARM. NEVER reports rho or any panel diagnostic
reconnect           → extension service worker idles → reconnects and resumes, does not die silently
concurrency         → a second controller on the same browser → REFUSES
```

### LIMITS
MAX_ROUNDS and a wall-clock cap declared **before** starting. One swarm per
machine. One controller per browser session.

### HUMAN APPROVAL REQUIRED FOR
Any paid seat · any new domain in the profile · committing any survivor.

### STOP CONDITION / SAFE FALLBACK
Stop on no-new-corrections — **not on "it reads well now."** Compare evidence,
not model agreement (Playbook p.16).
