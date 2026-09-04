# CLAUDE DISPATCH PROMPT
## Instruction Stack Conflict Audit, v2.0
### Dispatch class: Full tier, fail-closed, machine-verified, file-native, adjudication-gated

---

## 0. BLUF

You are auditing my instruction stack for internal conflict. You have direct read
access to my machine, so you will read the source files yourself instead of receiving
pastes. You will produce seven deliverables, written to disk as files: an Input
Ledger, a Rule Inventory, a Conflict Register, a Redundancy Register, a Load Count,
the Cut, and a set of binary Resolution Decisions. You will not add rules. You will
not modify, move, or rewrite any source file. You will not implement anything. You
will stop after Part 5 and wait for my adjudication.

Your failure mode on this task is confident fabrication: inventing conflicts that do
not exist, presenting a paraphrase as a quote, guessing at your own internal
processing, and producing numbers with no dataset behind them. Every constraint below
closes one of those holes. Treat each as fail-closed. If you cannot satisfy a
constraint, halt with a HALT REPORT (Section 11) naming the constraint and why. Do
not proceed degraded.

What changed from v1.0: intake is now direct file reads against a manifest, quote
integrity is now verified by script rather than by promise, and deliverables go to
disk so chunking rules are gone. The audit logic in Parts 1 through 5 is unchanged.

---

## 1. OPERATING CONSTRAINTS (these outrank every other section)

- [ ] **Read-only on sources.** You may read the manifest files and write only inside
      the output directory named in Section 10. Never edit, rename, move, reformat, or
      delete a source file, even to fix an obvious typo. If a source file looks broken,
      that is a finding, not a repair job.
- [ ] **Truth standard.** Do not fabricate, embellish, or invent citations, statistics,
      probabilities, or rule text. If evidence is insufficient, write "I do not have
      sufficient evidence to answer this reliably," name exactly what is missing, and
      halt. Do not fill the gap.
- [ ] **Quote integrity, machine-verified.** Every rule you cite must be reproduced
      verbatim from a source file, byte for byte, with its source filename. Before
      delivery you must verify every quote by exact substring containment against the
      source file using a script (Section 9), not by rereading. A quote that fails
      containment may not appear in any register. Paraphrase is disqualifying, not a
      fallback.
- [ ] **No inferred conflicts.** A conflict enters Part 1 only if you can quote both
      sides in full. A rule that merely feels like it is in tension with another does
      not qualify. Adjacency, overlap, and differing emphasis are not conflict.
- [ ] **No invented numbers.** Do not emit a compliance percentage, success rate,
      effect size, confidence interval, or point probability. There is no dataset.
      Ordinal rankings and counts of discrete items are permitted because they are
      derived by direct enumeration of the source files.
- [ ] **Evidence labels.** Tag every substantive claim as one of: File-Supported,
      Evidence-Based Inference, Assumption, Unknown. File-Supported is this task's
      equivalent of PDF-Supported in my governance taxonomy: the claim rests on
      verbatim text from a manifest file. Empirical Finding exists in the taxonomy but
      must not appear here, because there is no dataset in this task.
- [ ] **No em-dashes anywhere in any deliverable or chat output.**
- [ ] **BLUF.** Every deliverable file and every chat message opens with its bottom
      line before its detail.
- [ ] **Discrete steps.** Any procedural output is one action per line with a checkbox.
- [ ] **No new rules.** You may only cut, merge, or reword rules already present in the
      source files. Inventing a rule and presenting it as a merge is a violation.

---

## 2. MANIFEST AND INTAKE

Intake is by direct read. Before dispatching, I fill in this manifest. You resolve
it, read every file, and produce the Input Ledger. There is no paste protocol.

**MANIFEST (I edit the paths before dispatch):**

| # | Source | Kind | Location |
|---|--------|------|----------|
| 1 | User preferences | PASTE | included at the bottom of this dispatch message |
| 2 | Memory preferences | FILE | `<path to memory file>` |
| 3 | Skill files | GLOB | `<path>/.claude/skills/*/SKILL.md` |
| 4 | CLAUDE.md Core and Framework Library | FILE | `<path to CLAUDE.md>` |

Intake mode: **AUTO**. (AUTO: after a clean ledger, proceed directly to Part 1.
GATED: deliver the ledger and wait for me to say LEDGER CONFIRMED. I may change this
word before dispatch.)

Intake procedure:

- [ ] Resolve every FILE and GLOB entry. Expand each GLOB to its concrete file list.
- [ ] A FILE that does not exist, a GLOB that resolves to zero files, a PASTE entry
      with no pasted text, or any unreadable or empty file is a halt condition. Emit a
      HALT REPORT. Do not audit a partial stack. Do not reconstruct a missing file
      from memory of similar files.
- [ ] Read every resolved file in full. Record its byte count and line count at read
      time. If any source file changes during the audit (byte count differs at
      verification time), halt and say so.
- [ ] Assign each file a file code (Section 3) and write the INPUT LEDGER: one row per
      file with filename, full path or PASTE, file code, byte count, line count, and
      extracted rule count, plus a totals row.
- [ ] Save the ledger as deliverable 00 (Section 10) and, in AUTO mode, proceed. In
      GATED mode, post the ledger in chat and wait.
- [ ] Do not summarize, praise, or critique any file during intake. Intake produces
      the ledger and nothing else.

---

## 3. RULE EXTRACTION AND ID SCHEME

Before any register, extract every rule into an addressable list and save it as the
RULE INVENTORY (deliverable 01). This inventory is the single source of truth for
IDs; every later part references it.

- [ ] **Unit of extraction:** one discrete behavioral demand. Not one bullet, not one
      sentence, not one heading. A single bullet containing three demands extracts as
      three rules. Three bullets restating one demand extract as one rule with three
      instances, and the instances go to Part 2.
- [ ] **A demand is behavioral** if a reader could observe whether you complied.
      Aspirational framing, identity statements, and background context are not rules.
      List them in the inventory under NON-RULE TEXT with a one-line reason each. Do
      not count them in the Load Count.
- [ ] **ID format:** `CODE.NNN`, where CODE is the file code from the ledger and NNN is
      a zero-padded sequence in order of appearance within the file. Examples:
      `UP.014`, `MEM.007`, `SKL-CIG.003`, `CMD.021`. Skill file codes are
      `SKL-<slug>`, where the slug is derived from the skill's directory name and
      stated in the ledger.
- [ ] Every inventory entry carries: ID, verbatim rule text, source filename, and the
      line number where the rule text begins. Line numbers make Section 9 checkable.
- [ ] Every rule referenced anywhere in Parts 1 through 5 must carry its ID. Cross
      references between parts use IDs only.

---

## 4. PART 1: CONFLICT REGISTER

BLUF line first: the number of conflicts found, stated as a plain count.

One row per conflict. Columns, in this order:

| # | Rule A (ID, verbatim, file) | Rule B (ID, verbatim, file) | Behavior A demands | Behavior B demands | Dominant rule by stated precedence | Basis for dominance | Label |

- [ ] "Dominant rule" means: which rule the instruction text itself makes controlling
      when the two collide. Determine this only from the text, using, in this order of
      authority: (a) an explicit precedence or override clause in the stack, (b) rule
      specificity, where the narrower rule governs the narrower case, (c) a stated
      hierarchy of files. Cite which of the three you used, and for basis (a), quote
      the precedence clause with its ID.
- [ ] If none of the three resolves it, write `Unresolved by text` and label the row
      **Unknown**. Do not guess. Do not report what you believe you would actually do.
      You cannot observe your own weighting, and any claim about it is fabrication.
- [ ] Label every row **File-Supported** when both quotes pass containment and the
      dominance basis is an explicit clause; **Evidence-Based Inference** when
      dominance rests on specificity or file hierarchy; **Unknown** when unresolved.
- [ ] Conflicts internal to a single file are in scope and must be listed.

---

## 5. PART 2: REDUNDANCY REGISTER

BLUF line first: the number of redundancy clusters found.

- [ ] One entry per redundant rule cluster.
- [ ] Quote every instance verbatim with its ID and filename.
- [ ] Mark exactly one instance CANONICAL. Mark every other instance DELETE.
- [ ] State the selection basis for the canonical instance in one line: most complete
      wording, most authoritative file, or most specific scope. No other bases.
- [ ] Near-duplicates that differ in scope or trigger are not redundant. If two rules
      demand the same behavior under different conditions, list them under PARTIAL
      OVERLAP and do not mark either for deletion.

---

## 6. PART 3: LOAD COUNT

BLUF line first: the total.

- [ ] Report total discrete behavioral demands across all files.
- [ ] Report a per-file breakdown matching the INPUT LEDGER, and confirm the two
      agree. A mismatch between ledger counts and inventory counts is a halt
      condition, not a rounding note.
- [ ] Report the deduplicated total after applying Part 2 deletions.
- [ ] Report the count of Part 1 conflict rows labeled Unknown.
- [ ] Do not estimate an effect size, a compliance rate, a degradation curve, or any
      claim about how load affects performance. There is no dataset. State that
      sentence explicitly in the output.

---

## 7. PART 4: THE CUT

BLUF line first: the CORE FIVE, listed by ID and short title only, before any analysis.

**Ranking method:**

- [ ] Rank every surviving rule ordinally by cost of violation. "Surviving" means:
      in the inventory, not marked DELETE in Part 2. Ordinal only. No scores, no
      weights, no composite indices, no invented scales.
- [ ] Cost of violation is assessed only against evidence in my source files and my
      stated goals as they appear in those files. If a rule's cost basis is not
      traceable to source text, label the ranking **Assumption** and say what text
      would have grounded it.
- [ ] Tie-break, in order: (1) irreversibility of the harm, (2) whether I could detect
      the violation after the fact, (3) breadth of tasks affected.
- [ ] For every rule cut or merged, cite the Part 1 or Part 2 register entry that
      justifies it, by ID. A cut with no register citation is not permitted. If a rule
      should be cut but no register entry supports it, leave it in the FULL SET and
      note it under UNJUSTIFIED CUT CANDIDATES instead.

**Two deliverables:**

- [ ] **CORE FIVE:** the five rules retained if only five survive. Verbatim text, ID,
      source file, and one line on what fails without it.
- [ ] **FULL SET:** the complete deduplicated rule set, in the order I should load it,
      with IDs preserved so I can trace every line back to origin. Rules involved in
      an unresolved or unadjudicated Part 1 conflict stay in the FULL SET flagged
      `PENDING [conflict n]`. Do not apply any Part 5 recommendation here.

---

## 8. PART 5: RESOLUTION DECISIONS

BLUF line first: the number of decisions awaiting my adjudication.

- [ ] Do not resolve any conflict. Present each as a binary and wait.
- [ ] One entry per Part 1 conflict, including rows labeled Unknown.
- [ ] Exact format, one per conflict:

```
CONFLICT [n] (Rule A: [ID] | Rule B: [ID])
Keep [A] or keep [B] or [proposed merge text, verbatim-derived only].
Recommend: [one]. Because: [one sentence, grounded in a quoted rule or a stated goal].
Label: [File-Supported | Evidence-Based Inference | Assumption | Unknown]
```

- [ ] A proposed merge may contain only words present in Rule A or Rule B. You may
      delete and reorder. You may not introduce new terms, new conditions, or new
      triggers.
- [ ] Recommending is not deciding. Part 4 has already carried unresolved conflicts
      forward as PENDING; leave them that way until I adjudicate.
- [ ] Part 5 is the one deliverable that also goes into chat in full, because I
      adjudicate by replying to it.

---

## 9. VERIFICATION GATE (machine-checked)

Run this before delivery. This gate is executed, not eyeballed. Save the script, its
output, and the pass or fail checklist as deliverable 07.

- [ ] Write a small script that takes every quoted rule in every deliverable, keyed by
      ID, and checks exact substring containment of the quote in its source file's
      raw bytes. Zero normalization: no whitespace collapsing, no smart-quote
      swapping, no case folding. Report matches per ID.
- [ ] Every quote passes containment. Any failure: fix the quote from the source file
      and rerun, or remove the entry and its downstream references. Never ship a
      failing quote.
- [ ] Re-stat every source file: byte counts match the ledger. A changed file is a
      halt condition.
- [ ] Every conflict row has two full quotes, not one.
- [ ] No rule appears in the FULL SET that is not traceable to an inventory ID.
- [ ] No cut lacks a register citation.
- [ ] Recount by script: ledger totals, inventory totals, and Part 3 totals agree.
- [ ] No number appears that was not produced by counting discrete items.
- [ ] Scan every deliverable by script for the em-dash character. Zero occurrences.
- [ ] No new rule text was introduced under the guise of a merge: every word of every
      proposed merge appears in Rule A or Rule B.
- [ ] Every substantive claim carries an evidence label.
- [ ] If any line fails and cannot be fixed, declare the failure at the top of the
      chat summary. Do not deliver a silently degraded product.

---

## 10. OUTPUT LOCATIONS

All deliverables are files. Chunked chat delivery is retired.

- [ ] Create `./instruction-stack-audit/<YYYY-MM-DD>/` in my home directory or the
      directory I dispatched from. Everything you write goes here and nowhere else.
- [ ] Write: `00-input-ledger.md`, `01-rule-inventory.md`, `02-conflict-register.md`,
      `03-redundancy-register.md`, `04-load-count.md`, `05-the-cut.md`,
      `06-resolution-decisions.md`, `07-verification.md`.
- [ ] Chat output at completion is exactly: a BLUF summary (one line per part with its
      headline count), the full text of `06-resolution-decisions.md`, the
      verification gate's pass or fail checklist, and the output directory path.
- [ ] No preamble, no restatement of this prompt, no commentary on the task, no
      closing offer of further help.

---

## 11. FAILURE AND STOP CONDITIONS

Every halt uses this format, in chat, and stops the audit:

```
HALT REPORT
Constraint violated: [section and line]
Evidence: [the missing path, the failing quote ID, or the last intelligible line of a broken file, verbatim]
What I need from you to proceed: [one line]
```

- [ ] A manifest entry that cannot be resolved: HALT.
- [ ] A source file that is truncated, unreadable, or changes mid-audit: HALT, quoting
      the last intelligible line.
- [ ] A required part that cannot be completed from the files given: HALT naming the
      gap. Do not fill it from memory, from typical practice, or from files that
      resemble mine.
- [ ] After Part 5, STOP. Do not implement. Do not rewrite my files. Do not produce a
      consolidated new instruction file. A later message from me reading APPLY
      DECISIONS, with my adjudications, is the only thing that authorizes that step,
      and it is a separate dispatch.

---

## 12. SOURCES BLOCK

End the chat summary with this block. No external retrieval is expected in this task;
if you retrieved nothing, use the first form verbatim.

```
SOURCES
Retrieved this session:
No external source retrieved; based on reasoning over user-supplied files and stated assumptions.

Not retrieved (memory-based, manual verification required):
None.
```

- [ ] My manifest files are primary source material, not external citations. They
      live in the INPUT LEDGER, never in the SOURCES block.
- [ ] If you did retrieve something external (you should not need to), list it in
      APA 7 under the correct heading instead of the stock lines.

---

## BEGIN

Acknowledge this dispatch in one line, resolve the manifest, and deliver the INPUT
LEDGER. In AUTO mode, continue straight through Parts 1 to 5 and the verification
gate, then stop and wait for my adjudication.
