"""
domains.py
==========
Problem profiles for the panel console.

A domain profile is data, not code paths. Adding a domain is adding an entry
here; nothing branches on domain name anywhere else. The moment a profile
becomes an `if domain == ...` somewhere in intake, the sixth domain costs as
much as the first did.

Each profile answers four questions the operator otherwise has to answer from
memory every time: what counts as an artifact here, what a candidate looks
like, which claim kinds carry weight, and which gates must therefore be on.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Domain:
    key: str
    title: str
    blurb: str
    artifact_is: str
    artifact_examples: tuple[str, ...]
    candidate_is: str
    candidate_examples: tuple[str, ...]
    primary_claim_kinds: tuple[str, ...]
    gates: tuple[str, ...]
    resolve_dois: bool = False
    red_gate: bool = False
    red_prompt: str = ""
    extra_questions: tuple[str, ...] = field(default_factory=tuple)
    zero_kill_note: str = (
        "Zero earned kills means nothing was mechanically refuted. That is a "
        "consensus run, not a clean one."
    )


BUSINESS = Domain(
    key="business",
    title="Business decision",
    blurb="Pricing, hiring, vendor choice, capacity, market entry.",
    artifact_is="The memo, model, or proposal -- including every number and how it was derived.",
    artifact_examples=(
        "A Q4 placement review with the revenue and margin figures spelled out",
        "A pricing proposal with the unit economics stated",
    ),
    candidate_is="The competing decisions, each stated as a complete position.",
    candidate_examples=(
        "Raise placement fees 8%",
        "Hold fees and add a service tier",
        "Raise 15% and accept volume loss",
    ),
    primary_claim_kinds=("arithmetic", "unit"),
    gates=("arithmetic", "schema", "unit"),
    extra_questions=("What would make this decision wrong twelve months from now?",),
    zero_kill_note=(
        "A business run with zero earned kills means the memo had no checkable "
        "derivations. Put the arithmetic in the memo and run it again."
    ),
)

DOCTORATE = Domain(
    key="doctorate",
    title="FIU DBA doctorate",
    blurb="Dissertation chapters, literature review, methodology, defense prep.",
    artifact_is="The chapter, lit-review section, methodology, or defense argument.",
    artifact_examples=(
        "A literature review section with its citations",
        "A methodology section defending a sampling choice",
    ),
    candidate_is="Competing theoretical positions, methodological choices, or interpretations.",
    candidate_examples=(
        "The construct is best measured by instrument A",
        "Instrument B, because A was validated on a different population",
    ),
    primary_claim_kinds=("citation", "arithmetic", "judgment"),
    gates=("arithmetic", "schema", "unit"),
    resolve_dois=True,
    extra_questions=(
        "Which claims are load-bearing for the committee, and which are context?",
    ),
    zero_kill_note=(
        "For doctoral work the citation gate is the point. Zero earned kills "
        "with citations present usually means the DOIs were not supplied."
    ),
)

PATENT = Domain(
    key="patent",
    title="Patent strategy -- PUBLISHED material only",
    blurb="Prior art, published-application interpretation, filing strategy.",
    artifact_is="Published patent text, published application text, or a strategy question built only on published material.",
    artifact_examples=(
        "A prior-art comparison between two published applications",
        "A claim-construction question about someone else's granted claims",
    ),
    candidate_is="Competing readings, competing strategies, or competing prior-art positions.",
    candidate_examples=(
        "Reference X anticipates element 3",
        "Reference X teaches away from element 3",
    ),
    primary_claim_kinds=("citation", "judgment"),
    gates=("arithmetic", "schema", "unit"),
    resolve_dois=True,
    red_gate=True,
    red_prompt=(
        "This tool transmits every word of your artifact to FIVE OUTSIDE COMPANIES.\n"
        "  PERMITTED: text already published by the USPTO or another patent office.\n"
        "  REFUSED:   unpublished amendments, office-action responses, draft\n"
        "             continuation claims, or provisional text not carried into a\n"
        "             published document -- in any form, including paraphrase.\n"
        "\n"
        "  There is no redaction option. Partial redaction of claim language is how\n"
        "  claim language leaks."
    ),
    extra_questions=(
        "Publication number and date for every document quoted in the artifact?",
    ),
)

SOFTWARE = Domain(
    key="software",
    title="Software build under adjudication",
    blurb="One bounded build decision, adjudicated before you write the code.",
    artifact_is="ONE build decision document -- not the whole design, and not the patent.",
    artifact_examples=(
        "Three ways to make shadow-region activation atomic under concurrent writers, "
        "with throughput and memory for each",
        "The DecisionToken validation path and the failure behaviour for each missing field",
    ),
    candidate_is="Competing implementations, each with the numbers it rests on.",
    candidate_examples=(
        "Copy-on-write shadow page; activation is a pointer swap, O(1), one page per epoch",
        "Append-only journal replayed on activation; O(n) activation, no page duplication",
        "In-place under a lock with rollback; O(1), no extra memory, not crash-atomic",
    ),
    primary_claim_kinds=("arithmetic", "code_behavior", "unit"),
    gates=("arithmetic", "schema", "unit"),
    extra_questions=(
        "Which behaviours already have tests that run, and which tests do you still owe?",
    ),
    zero_kill_note=(
        "A build run with zero earned kills is a FAILED run: five models agreed "
        "about something nobody measured. Add derivations and run again."
    ),
)

CODING = Domain(
    key="coding",
    title="Coding / debugging",
    blurb="Competing diagnoses of a bug, or competing designs for a change.",
    artifact_is="The code, the diff, the failing test output, or the design note.",
    artifact_examples=(
        "A stack trace plus the two functions involved",
        "A diff and the test that started failing after it",
    ),
    candidate_is="Competing diagnoses or competing fixes.",
    candidate_examples=(
        "The race is in the cache invalidation",
        "The race is in the connection pool checkout",
    ),
    primary_claim_kinds=("code_behavior", "arithmetic"),
    gates=("arithmetic", "schema", "unit"),
    extra_questions=("What command reproduces it, and what is its exit code today?",),
)

GENERAL = Domain(
    key="general",
    title="General",
    blurb="Anything else. Works hardest to find a mechanical warrant.",
    artifact_is="Whatever document the question is about.",
    artifact_examples=("A plan, a report, an analysis",),
    candidate_is="Two or more competing answers.",
    candidate_examples=("Option A", "Option B"),
    primary_claim_kinds=("arithmetic", "judgment"),
    gates=("arithmetic", "schema", "unit"),
)

ALL: tuple[Domain, ...] = (BUSINESS, DOCTORATE, PATENT, SOFTWARE, CODING, GENERAL)
BY_KEY = {d.key: d for d in ALL}
