"""
citation_gate.py
================
Does the DOI resolve to the paper that was actually cited?

RESOLUTION IS NOT VERIFICATION. CitationResolutionGate answers "is this
identifier registered". That rules out a wholly invented DOI and nothing
else. The characteristic language-model citation error is not an invented
identifier -- it is a REAL DOI attached to the wrong paper, produced when a
model recalls a plausible reference and pairs it with a plausible identifier.
Resolution passes that every time.

This gate retrieves what the DOI is registered TO and compares it with what
the claim said. It is the single most valuable check available for doctoral
work, where a citation that resolves to a different paper survives every
other check in the system and reaches a committee.

WARRANT FORMAT, extending the citation warrant rather than adding a kind:

    10.1038/s41586-020-2649-2 :: Harris ;; 2020 ;; Array programming with NumPy

The inner separator is ";;" and NOT "|", because the outer claim line is
already pipe-delimited: "CLAIM | kind | warrant | text". A warrant containing
pipes was truncated by line_claim_extractor at the first inner one, so this
gate never applied to anything a model actually emitted -- it passed its unit
tests, where claims were constructed directly, and was dead in production.

A bare DOI with no metadata still resolves, and still passes the resolution
gate. It is weaker evidence and the report says so, because "this identifier
exists" and "this identifier is the paper you named" are different findings.

THRESHOLDS ARE ENGINEERING JUDGEMENT AND ARE LABELLED AS SUCH. No published
standard sets them. They are chosen to be tolerant of transcription and
intolerant of substitution, and every one of them is named here so a
disagreement is about a number in the open rather than about hidden behaviour.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from typing import Any

from adjudication_orchestrator import Claim, ClaimKind, GateResult, GateStatus

TITLE_OVERLAP_MIN = 0.70
"""Share of the shorter title's significant words that must also appear in the
other title.

Engineering judgement, not a standard. Chosen because subtitle handling,
trailing punctuation, and "a"/"the" differences routinely cost 10-20% of a
title's tokens between a citation and a Crossref record, while a genuinely
different paper rarely shares even half. Raising it starts failing honest
citations; lowering it starts passing substitutions.
"""

YEAR_TOLERANCE = 1
"""Years may differ by one without failing, and the difference is reported.

A preprint and its published version routinely differ by a year, and Crossref
carries published-print and published-online dates that can straddle a new
year. A two-year gap is a different work.
"""

_STOP = {"a", "an", "the", "of", "for", "and", "in", "on", "with", "to",
         "from", "by", "at", "as", "is", "are", "using", "via"}
_WORD = re.compile(r"\w+", re.UNICODE)
"""UNICODE, not [a-z0-9]. The ASCII class tokenised a CJK title to nothing, so
two IDENTICAL Chinese titles scored 0% overlap and the gate reported
WRONG_PAPER -- refuting an honest citation because of the alphabet it is
written in. Any non-Latin script had the same problem."""

MIN_INFORMATIVE_TOKENS = 3
"""Fewest content words a claimed title must have to be matchable.

Overlap is measured against the SHORTER title, so a claimed title of one word
that appears anywhere in the real one scored 100%. "Learning" matched
"Learning to rank with deep networks for search" perfectly, which means a model
could cite any paper by naming one of its words. Below this the gate cannot
rule and the claim goes to a person."""

_POLARITY = {
    "increases": "decreases", "decreases": "increases",
    "improves": "reduces", "reduces": "improves",
    "raises": "lowers", "lowers": "raises",
    "higher": "lower", "lower": "higher",
    "positive": "negative", "negative": "positive",
    "supports": "refutes", "refutes": "supports",
    "effective": "ineffective", "ineffective": "effective",
    "safe": "unsafe", "unsafe": "safe",
    "with": "without", "without": "with",
    "no": "yes", "not": "",
}
"""Words whose swap reverses a title's meaning while barely moving the overlap.

"reduces survival" against "improves survival" differs by one token out of
three and can clear a 70% threshold -- so the gate would confirm a citation
that says the OPPOSITE of the work it names. Bag-of-words similarity cannot
see this; it has to be checked for separately."""


def polarity_conflict(claimed: str, actual: str) -> str | None:
    """A directional term present in one title whose opposite is in the other."""
    a, b = _tokens_raw(claimed), _tokens_raw(actual)
    for word, opposite in _POLARITY.items():
        if not opposite:
            continue
        if word in a and opposite in b and word not in b:
            return f"{word!r} vs {opposite!r}"
    return None


def _tokens_raw(title: str) -> set[str]:
    """All words, stopwords included. Polarity often lives in a stopword."""
    return set(_WORD.findall(_fold(title)))


def _fold(s: str) -> str:
    """Case, diacritics, and punctuation removed. Muller and Müller are one name."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.casefold()


def _tokens(title: str) -> set[str]:
    return {w for w in _WORD.findall(_fold(title)) if w not in _STOP and len(w) > 1}


def title_overlap(claimed: str, actual: str) -> float:
    """Share of the SHORTER title's words present in the other.

    Shorter-side rather than Jaccard because a Crossref record often carries a
    full subtitle the citation omitted. Penalising the citation for the
    record's extra words would fail honest references.
    """
    a, b = _tokens(claimed), _tokens(actual)
    if not a or not b:
        return 0.0
    shorter = a if len(a) <= len(b) else b
    return len(a & b) / len(shorter)


def title_is_matchable(claimed: str) -> bool:
    """False when the claimed title is too thin for overlap to mean anything."""
    return len(_tokens(claimed)) >= MIN_INFORMATIVE_TOKENS


def _record_year(rec: dict[str, Any]) -> int | None:
    for key in ("published-print", "published-online", "issued", "created"):
        parts = (rec.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and isinstance(parts[0][0], int):
            return parts[0][0]
    return None


def _surnames(rec: dict[str, Any]) -> set[str]:
    return {_fold(a.get("family", "")) for a in (rec.get("author") or [])
            if a.get("family")}


class CitationFieldMatchGate:
    """Resolves the DOI, then checks it is the work that was cited."""

    name = "citation_field_match"

    def __init__(
        self,
        record_fn: Callable[[str], dict[str, Any] | None] | None = None,
        timeout_s: float = 12.0,
    ) -> None:
        # Injectable so the gate is testable without a socket.
        if record_fn is None:
            from doi_resolver import crossref_record
            record_fn = lambda d: crossref_record(d, timeout_s)  # noqa: E731
        self.record_fn = record_fn
        self.cache: dict[str, dict[str, Any] | None] = {}

    @staticmethod
    def parse_warrant(
        warrant: str | None,
    ) -> tuple[str, str, int, str] | None:
        """"<doi> :: <surname> | <year> | <title>" -> parts, or None."""
        if not warrant or "::" not in warrant:
            return None
        doi, _, meta = warrant.partition("::")
        bits = [b.strip() for b in meta.split(";;")]
        if len(bits) < 3:
            return None
        surname, year_raw, title = bits[0], bits[1], ";;".join(bits[2:]).strip()
        if not (doi.strip() and surname and title):
            return None
        try:
            year = int(re.sub(r"\D", "", year_raw)[:4])
        except ValueError:
            return None
        return doi.strip(), surname, year, title

    def applies_to(self, claim: Claim) -> bool:
        return (claim.kind is ClaimKind.CITATION
                and self.parse_warrant(claim.warrant) is not None)

    def _record(self, doi: str) -> dict[str, Any] | None:
        if doi not in self.cache:
            try:
                self.cache[doi] = self.record_fn(doi)
            except Exception:  # noqa: BLE001 - unreachable is not a finding
                self.cache[doi] = None
        return self.cache[doi]

    def check(self, claim: Claim) -> GateResult:
        parsed = self.parse_warrant(claim.warrant)
        if parsed is None:  # unreachable via _route; guard, not cast
            return GateResult(self.name, GateStatus.INAPPLICABLE,
                              "warrant is not '<doi> :: <surname> ;; <year> ;; <title>'")
        doi, surname, year, title = parsed
        rec = self._record(doi)
        if rec is None:
            # Could not retrieve. That is not evidence the citation is wrong.
            return GateResult(
                self.name, GateStatus.BLOCKED,
                f"no Crossref record retrieved for {doi} -- the check did not "
                f"happen, which is not a finding against the citation",
            )

        got_title = (rec.get("title") or [""])[0]
        got_year = _record_year(rec)
        got_surnames = _surnames(rec)

        if not got_title or not got_surnames:
            # A record too sparse to compare against. Absence of metadata is
            # not evidence of fabrication.
            return GateResult(
                self.name, GateStatus.BLOCKED,
                f"{doi} resolves but its record carries no "
                f"{'title' if not got_title else 'authors'} to compare",
            )

        if not title_is_matchable(title):
            # Overlap is measured against the shorter title, so a one-word
            # claimed title that appears anywhere in the real one scores 100%.
            # The gate cannot rule; a person must.
            return GateResult(
                self.name, GateStatus.BLOCKED,
                f"the cited title {title[:60]!r} carries fewer than "
                f"{MIN_INFORMATIVE_TOKENS} informative words, which is too "
                f"thin for a title comparison to mean anything",
            )

        conflict = polarity_conflict(title, got_title)
        if conflict is not None:
            # Bag-of-words similarity cannot see a reversed meaning: "reduces
            # survival" against "improves survival" differs by one token and
            # clears the threshold, so the gate would confirm a citation
            # asserting the OPPOSITE of the work it names.
            return GateResult(
                self.name, GateStatus.FAIL,
                f"OPPOSITE_FINDING: {doi} is registered to "
                f"\"{got_title[:70]}\", which reverses the cited title "
                f"({conflict}). The words mostly match and the meaning does not",
            )

        overlap = title_overlap(title, got_title)
        if overlap < TITLE_OVERLAP_MIN:
            return GateResult(
                self.name, GateStatus.FAIL,
                f"WRONG_PAPER: {doi} is registered to \"{got_title[:80]}\", not "
                f"\"{title[:80]}\" (title overlap {overlap:.0%}, "
                f"need {TITLE_OVERLAP_MIN:.0%})",
            )
        if _fold(surname) not in got_surnames:
            return GateResult(
                self.name, GateStatus.FAIL,
                f"AUTHOR_MISMATCH: {doi} lists "
                f"{', '.join(sorted(got_surnames)[:4])} -- no author named "
                f"{surname}",
            )
        if got_year is None:
            # A record with no date cannot confirm or refute the cited year.
            # Passing anyway let a citation clear the gate on two fields out of
            # three while silently skipping the third.
            return GateResult(
                self.name, GateStatus.BLOCKED,
                f"{doi} resolves and the title and author match, but its "
                f"record carries no date, so the cited year {year} was not "
                f"checked",
            )
        if abs(got_year - year) > YEAR_TOLERANCE:
            return GateResult(
                self.name, GateStatus.FAIL,
                f"YEAR_MISMATCH: {doi} is dated {got_year}, cited as {year}",
            )

        note = ""
        if got_year != year:
            note = (f" (record year {got_year} vs cited {year}, within the "
                    f"{YEAR_TOLERANCE}-year tolerance)")
        venue = (rec.get("container-title") or [""])[0]
        return GateResult(
            self.name, GateStatus.PASS,
            f"{doi} is \"{got_title[:70]}\", {surname} {got_year}"
            + (f", {venue[:40]}" if venue else "") + note,
        )
