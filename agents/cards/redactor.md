# REDACTOR — agent card

> Before anything leaves this machine — a commit, an email, an artifact, a
> screenshot — scan it for what must never leave. **Blocks, does not warn.**

| Lane | Version | Tier | Route | Status |
|---|---|---|---|---|
| any | 1.0 | **A — autonomous** | local; pre-commit hook installed | **GATED — rung 1** |

**Closes `19` C1–C3.** The rule existed in three documents and was violated
anyway. It is now code: `scripts/redaction_guard.py`, **35 self-tests, installed
as `.git/hooks/pre-commit`, denial live-tested 2026-09-14.**

### GOAL
**Nothing that must never be published reaches this public repository.**

- **Measured by:** Escaped defects = 0. Currently 0 since E-01.
- **Rolls up to:** outcome B — nothing irreversible goes wrong
- **Which serves:** the goal Andrew writes in [`../analysis/goal-ledger.md`](../analysis/goal-ledger.md). No agent authors that one.

### INPUTS
Staged changes (automatic, every commit) · any outbound draft, artifact,
screenshot or attachment (on request, before sending).

### WHAT IT BLOCKS
```
phone numbers (consistent-separator forms, and parenthesized)
SSNs · payment cards · long account / order / reference identifiers
private keys · Anthropic, OpenAI, GitHub, AWS, Google, Slack key shapes
inline-assigned credentials
CUI / FOUO / official-use / source-selection markings  <!-- redaction-guard: allow - policy text naming the markings, not marked material -->
```

### HOW IT AVOIDS CRYING WOLF
Hardened against this repository as its own corpus. It does **not** fire on:
DFARS/FAR clause numbers (`252.204-7012` — mixed separators, so not a phone) ·
float-precision literals (`0.3333333333333333`) · DOI URLs · version strings ·
commit SHAs · token counts.

**Suppressions are rule-scoped**, not file-wide: a test file full of numeric
specimens stays armed against credentials. Blanket-allowlisting to silence one
float literal would blind the key rules on a 5,000-line file.

### ACCEPTANCE TESTS — 35, all passing
```
normal              → clean tree scans clean (171 files)
must-block          → 18 specimen classes, each blocked
must-pass           → 15 false-positive classes, none blocked
unsafe instruction  → a file containing "redaction-guard: allow" without a reason
                      is still a human decision, never the agent's
suppression scope   → a rule-scoped suppression still catches credentials
DENIAL LIVE-TESTED  → a staged file with a phone number and account number:
                      commit BLOCKED, HEAD unchanged, nothing committed
```

### LIMITS
Seconds · $0 · runs on every commit, unavoidably.

### HUMAN APPROVAL REQUIRED FOR
**Every allowlist entry, with a written reason.** Bypassing with `--no-verify`
is a human act and should be rare enough to be memorable.

### STOP CONDITION / SAFE FALLBACK
**Blocks. It never warns-and-continues.** A match stops the commit. The report
never reprints the matched value — a finding that echoes the secret has
republished it.
