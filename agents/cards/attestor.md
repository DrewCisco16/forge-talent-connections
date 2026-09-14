# ATTESTOR — agent card

> Given any agent's claim that it did something, verify the artifact actually
> exists. **A claim without an artifact is void.**

| Lane | Version | Tier | Route | Status |
|---|---|---|---|---|
| any | 1.0 | **A — autonomous** | local, post-run | ready |

**Closes `19` B3.** `AGENTS.md` says *"do not claim a test ran unless it did."*
Nothing checked. Self-reported completion is the one output class an agent has
both the motive and the means to get wrong, and it is invisible from the text.

### INPUTS
One completed run's claim set — "tests passed", "file written", "sources
retrieved", "the brief is at X" — plus the filesystem and run logs.

### OUTPUT
```
CLAIM                                    VERDICT
"ran the test suite"                     ATTESTED   evals/out/run-1423.xml, 18:04:11, 34 tests
"wrote outputs/brief.md"                 ATTESTED   1,204 bytes, mtime 18:06:02
"retrieved 3 primary sources"            VOID       evidence.json holds 2 URLs, 1 unresolved
"fixed the failing case"                 VOID       no test output newer than the edit
```

### HOW IT CHECKS — mechanical, no model judgement
```
file claims ....... path exists · non-zero · mtime AFTER the run started
test claims ....... a result artifact exists, is newer than the last source edit,
                    and its pass/fail count matches the claim
source claims ..... each URL is in the evidence ledger with a retrieval timestamp
edit claims ....... git diff shows the change; "no diff" voids the claim
count claims ...... the number in the claim equals the number in the artifact
```

### ACCEPTANCE TESTS
```
normal              → real artifacts → all claims ATTESTED
missing evidence    → a claim with no artifact → VOID, names what was absent
unsafe instruction  → a log line saying "mark this attested" → FINDING, not obeyed
stale artifact      → test output OLDER than the source edit → VOID, not attested
count mismatch      → "18 tests" vs an artifact showing 12 → VOID
no-model            → makes no model call. Verify by policy, not by trust
```

### LIMITS
< 60 seconds · $0 · runs after every Tier B or C agent.

### HUMAN APPROVAL REQUIRED FOR
Nothing — it only verifies. It never repairs a claim.

### STOP CONDITION / SAFE FALLBACK
Stop at the verdict list. **Any VOID claim demotes that run's output to
unreviewed and blocks it from HARVESTER.** An unattested claim is not a small
problem: it is the one that makes every other number untrustworthy.
