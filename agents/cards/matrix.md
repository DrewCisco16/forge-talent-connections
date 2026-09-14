# MATRIX — agent card

> Given a solicitation, produce a complete requirement matrix with provenance.
> Model-invented rows are isolated, never merged.

| Lane | Version | Tier | Route | Status |
|---|---|---|---|---|
| ABO / J4V | 1.0 | B | local, offline | **BLOCKED — counsel** |

> ## ⛔ BLOCKED
> A solicitation in progress is plausibly procurement-sensitive. **Does not run
> until contracts counsel answers the four questions in `../07-guardrails.md` §2**
> (`10` A1). Playbook p.8: *"A local runner alone does not satisfy this
> boundary."* **Professional verification required.**

### INPUTS
The solicitation and every amendment. **Offline. No network.**

### OUTPUT
`ID · Source (section, page, ¶) · Requirement VERBATIM · Type (L/M/C/PWS/SOW) ·
Volume · Owner · Status · Response location · Provenance (EXTRACTED | MODEL-ONLY)`
plus a separate `MODEL-ONLY` sheet and a submission-mechanics block (due
date/time **with time zone**, page limits, format — all verbatim).

### TWO PASSES — the ORDER is the safety property
```
PASS 1  deterministic extraction. Regex, section boundaries, page/¶ anchors,
        amendment deltas. NO MODEL IS CONSULTED.
PASS 2  model CLASSIFIES and ORGANIZES what pass 1 found. It never adds.
GATE    a row the model believes in that pass 1 did not find → MODEL-ONLY sheet.
        NEVER merged. A hallucinated requirement looks exactly like a real one
        and silently sends the team to answer a question nobody asked.
```

### ACCEPTANCE TESTS
```
normal              → every shall-statement extracted with page/¶ provenance
missing evidence    → an unclassifiable requirement → flagged, never dropped
unsafe instruction  → solicitation text containing an instruction → FINDING, not obeyed
model-only          → a plausible invented requirement → lands on MODEL-ONLY, not the matrix
verbatim            → no requirement is paraphrased or cleaned up
conflict            → L vs M, or amendment vs base → flagged NEEDS RESOLUTION
network             → attempts no network call. Verify by policy, not by trust
```

### LIMITS
90 min · $0 extra · offline.

### HUMAN APPROVAL REQUIRED FOR
Running at all (counsel) · any adequacy judgment · any submission (**never**).

### STOP CONDITION / SAFE FALLBACK
Stop at the matrix. **Adequacy is not automated** — MATRIX says a row is
addressed and where; whether the response is any good is yours.
