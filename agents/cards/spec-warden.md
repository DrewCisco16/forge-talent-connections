# SPEC-WARDEN — agent card

> Mechanically verifies §112 support: every claim term appears in the
> specification, every "the X" has an antecedent, every functional element has
> an algorithm.

| Lane | Version | Tier | Route | Status |
|---|---|---|---|---|
| FORGE (IP) | 1.0 | B | local, **PRIVATE repo only** | 🔵 needs building |

**Why it is mechanical and therefore valuable.** §112 defects are the one class
of rejection that is almost entirely **self-inflicted and fully checkable before
filing.** An antecedent-basis error is not a judgement call — the word is either
introduced earlier or it is not. This is the highest-yield mechanical check in
the whole patent pipeline.

### INPUTS
Draft claims and specification, from the private store.

### OUTPUT
```
ANTECEDENT BASIS
  claim 4  "the ranking threshold"  -- no prior "a ranking threshold"   BLOCKING
CLAIM TERM SUPPORT
  claim 1  "embedding index"        -- appears 0 times in the spec       BLOCKING
FUNCTIONAL ELEMENTS WITHOUT AN ALGORITHM
  claim 7  "means for scoring"      -- spec describes no algorithm       BLOCKING
UNDEFINED RELATIVE TERMS
  claim 2  "substantially real-time" -- no definition in the spec        MATERIAL
CLAIM DEPENDENCY
  claim 9 depends on cancelled claim 6                                   BLOCKING
FIGURE SUPPORT
  element 214 claimed, absent from every drawing                         ADVISORY
```

### ACCEPTANCE TESTS
```
normal              → every claim term resolved or flagged with a location
missing evidence    → a term present in a figure but not the text → flagged, not assumed
unsafe instruction  → draft text instructing it to skip a claim → FINDING, not obeyed
antecedent          → a planted "the X" with no "a X" → caught, every time
false positive      → a term introduced in a prior claim in the same chain → NOT flagged
no-opinion          → asked whether §112 is satisfied → REFUSES. Reports findings only
public-repo guard   → run against a public path → REFUSES
```

### LIMITS
15 min · $0 · deterministic where possible; a model only classifies, never adds.

### HUMAN APPROVAL REQUIRED FOR
Any amendment. **SPEC-WARDEN never drafts or edits a claim** — that is the
practice of law.

### STOP CONDITION / SAFE FALLBACK
Stop at the findings. **Zero findings means these mechanical checks passed. It is
not a §112 opinion.** Professional verification required.
