# SAFE Strategy Container — Forgelink LLC

A reproducible research + document-generation container that produces
**`output/Forgelink-SAFE-Playbook.pdf`** — a 39-page fillable strategy workbook on
Simple Agreements for Future Equity, written in plain language and built only on
U.S. government primary sources and peer-reviewed legal scholarship.

## Layout

| Path | What it is |
|---|---|
| `research/RESEARCH-NOTES.md` | The full autoresearch log: every finding, its evidence label, the sources excluded and why, and the open unknowns. **Read this to audit the PDF.** |
| `build/engine.py` | Layout engine — ADHD/OCD-oriented grid, colour system, AcroForm fields, real Noto Color Emoji rasterisation. |
| `build/build_pdf.py` | Document content + two-pass build (pass 1 collects TOC page numbers, pass 2 renders). |
| `output/` | The generated PDF. |

## Rebuild

```bash
pip install reportlab pillow
cd safe-strategy
python3 build/build_pdf.py output/Forgelink-SAFE-Playbook.pdf
```

Requires `/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf` for emoji.
Output: 39 pages, 174 fillable AcroForm fields (77 checkboxes, 97 text fields),
51 clickable source links.

## Research method

"Karpathy autoresearch" is the requester's term; no formalised published protocol
under that name could be verified, so it was interpreted as an autonomous iterative
retrieval loop: broad sweep → targeted verification → adversarial re-read → explicit
gap statement. That interpretation is labelled as an assumption in the notes.

## Evidence discipline applied

- Every claim carries a label: government source / empirical finding / inference /
  assumption / unknown / professional-verification-required.
- **Stale data rejected:** an early retrieval returned micro-purchase `$3,500` and
  SAT `$150,000`. Both are outdated and were discarded, not carried forward.
- **Conflict left unresolved:** three government sources disagreed on the current
  simplified acquisition threshold. No figure was asserted; the PDF tells the reader
  to verify it and gives them a field to record it.
- **Source gate enforced:** vendor cap-table benchmark data (proprietary,
  non-peer-reviewed) was excluded rather than quietly lowering the stated standard.
- **Retrieval limitation disclosed:** this environment's egress policy blocked
  full-document access to sec.gov, sba.gov, sbir.gov, ecfr.gov and investor.gov.
  Substantive extracts of those real documents were retrieved via search, but the
  underlying regulations were not read end to end — so every regulatory citation is
  marked "verify at source."

## Scope note

The PDF is a planning aid. It is not legal, tax, or investment advice. Its two
central findings — that SBIR/STTR ownership is tested on a fully diluted basis, and
that SBA affiliation turns on the *power* to control — both require confirmation
with qualified counsel before any structuring decision is made.
