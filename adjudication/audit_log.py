"""
audit_log.py
============
Append-only, hash-chained audit record for adjudication runs.

WHY THIS EXISTS
---------------
SOP Manual v1.1 section 8.5: "Every run writes an audit record: inputs, claims,
gate results, decisions." Without it a run leaves no evidence that the gates
ran, that the queue was worked, or that the stop decision was earned. A system
whose central claim is "the verification bottleneck is the entire difference"
has to be able to prove the bottleneck was there.

WHAT THE CHAIN DOES AND DOES NOT PROVE
--------------------------------------
Each entry commits to the one before it, so the chain detects a modified
payload, a reordered entry, a spliced-in entry, and a deleted middle entry.

It does NOT, on its own, detect truncation of the TAIL. Entries 0..3 of a
six-entry log verify perfectly as a four-entry log, because nothing inside the
chain knows how long it was supposed to be. Detecting that requires comparing
against a head recorded somewhere the attacker does not control, which is why
verify_chain_integrity takes expected_head and expected_length and why an
EMPTY log is treated as a failure rather than as a vacuous pass.

DETERMINISM
-----------
Global rule 4: replay mode blocks all nondeterminism. This module never calls
time(), never generates a uuid, and never reads a random source. Timestamps are
supplied by the caller through an injected clock, or omitted entirely. Two runs
over identical inputs with no clock produce byte-identical chains, which is
what makes deterministic replay a testable property rather than an aspiration.

RED / GREEN
-----------
The artifact under review is recorded as a SHA-256 digest, not as text. That
proves which artifact was adjudicated without copying its contents into the
log, so a log of a RED run does not itself become RED. Pass full text only by
explicit opt-in, and only when you know the artifact is GREEN.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

GENESIS_PREV_HASH = "0" * 64
"""prev_hash of the first entry. A real hash never collides with this."""

_REQUIRED_KEYS = ("seq", "prev_hash", "kind", "payload", "entry_hash")


class AuditChainError(RuntimeError):
    """Raised when a chain operation cannot be completed safely."""


def canonical_json(obj: Any) -> str:
    """
    Byte-stable JSON. Keys sorted, no incidental whitespace, no NaN.

    allow_nan is False deliberately: NaN is not valid JSON, it does not compare
    equal to itself, and a hash computed over it would be reproducible only by
    accident. A statistic that came back NaN must be converted to null by the
    caller before it is committed to the chain.
    """
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def digest(text: str) -> str:
    """SHA-256 of a string, hex encoded."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def scrub_nan(obj: Any) -> Any:
    """
    Replace every float NaN or infinity with None, recursively.

    The diagnostics legitimately produce NaN -- an uncalibrated singleton
    fraction, a capture fraction with no headroom. Those must reach the log as
    null so the entry is canonicalisable and its hash is reproducible.
    """
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: scrub_nan(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [scrub_nan(v) for v in obj]
    if isinstance(obj, set):
        return sorted(scrub_nan(v) for v in obj)
    return obj


@dataclass(frozen=True)
class AuditEntry:
    """One immutable link in the chain."""

    seq: int
    prev_hash: str
    kind: str
    payload: dict[str, Any]
    entry_hash: str

    def recompute_hash(self) -> str:
        """Recompute this entry's hash from its own contents."""
        return compute_entry_hash(self.seq, self.prev_hash, self.kind, self.payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "prev_hash": self.prev_hash,
            "kind": self.kind,
            "payload": self.payload,
            "entry_hash": self.entry_hash,
        }

    @staticmethod
    def from_dict(d: Any) -> AuditEntry:
        """
        Fail closed on anything that is not a well-formed entry. A malformed
        record is refused at the boundary rather than admitted and hoped about.
        """
        if not isinstance(d, dict):
            raise AuditChainError(f"entry is not an object: {type(d).__name__}")
        missing = [k for k in _REQUIRED_KEYS if k not in d]
        if missing:
            raise AuditChainError(f"entry missing required keys: {missing}")
        if not isinstance(d["seq"], int) or isinstance(d["seq"], bool):
            raise AuditChainError("seq must be an integer")
        if not isinstance(d["payload"], dict):
            raise AuditChainError("payload must be an object")
        for k in ("prev_hash", "kind", "entry_hash"):
            if not isinstance(d[k], str):
                raise AuditChainError(f"{k} must be a string")
        return AuditEntry(d["seq"], d["prev_hash"], d["kind"], d["payload"], d["entry_hash"])


def compute_entry_hash(seq: int, prev_hash: str, kind: str, payload: dict[str, Any]) -> str:
    """
    The commitment. Covers the sequence number, the predecessor, the kind, and
    the payload -- so renumbering, re-parenting, relabelling, and editing are
    all detected.
    """
    return digest(canonical_json([seq, prev_hash, kind, payload]))


@dataclass
class ChainVerdict:
    valid: bool
    entries_checked: int
    head: str | None
    failures: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


def verify_chain_integrity(
    entries: Sequence[AuditEntry],
    expected_head: str | None = None,
    expected_length: int | None = None,
) -> ChainVerdict:
    """
    Verify a chain, fail-closed.

    An EMPTY log FAILS. This is the truncation check: a log truncated to
    nothing is indistinguishable from a run that never happened, and treating
    "no entries" as "nothing wrong" is exactly the vacuous pass that makes an
    audit trail worthless. If you have genuinely not started a run, you have no
    chain to verify, not a valid empty one.

    expected_head and expected_length are how you detect tail truncation. The
    chain cannot do it alone -- see the module docstring.
    """
    failures: list[str] = []

    if not entries:
        return ChainVerdict(
            valid=False,
            entries_checked=0,
            head=None,
            failures=[
                "empty log: refusing to verify. A truncated-to-empty log is "
                "indistinguishable from a run that never happened."
            ],
        )

    for i, e in enumerate(entries):
        if e.seq != i:
            failures.append(f"entry {i}: seq is {e.seq}, expected {i} (gap or reordering)")
        expected_prev = GENESIS_PREV_HASH if i == 0 else entries[i - 1].entry_hash
        if e.prev_hash != expected_prev:
            failures.append(
                f"entry {i}: prev_hash {e.prev_hash[:12]}... does not match "
                f"{'genesis' if i == 0 else f'entry {i - 1}'} ({expected_prev[:12]}...)"
            )
        try:
            recomputed = e.recompute_hash()
        except (ValueError, TypeError) as exc:
            failures.append(f"entry {i}: payload is not canonicalisable: {exc}")
            continue
        if recomputed != e.entry_hash:
            failures.append(
                f"entry {i}: hash mismatch -- stored {e.entry_hash[:12]}..., "
                f"recomputed {recomputed[:12]}... (payload was modified)"
            )

    if expected_length is not None and len(entries) != expected_length:
        failures.append(
            f"length is {len(entries)}, expected {expected_length} "
            f"({'truncated' if len(entries) < expected_length else 'extended'})"
        )
    if expected_head is not None and entries[-1].entry_hash != expected_head:
        failures.append(
            f"head is {entries[-1].entry_hash[:12]}..., expected "
            f"{expected_head[:12]}... (tail truncated or rewritten)"
        )

    return ChainVerdict(
        valid=not failures,
        entries_checked=len(entries),
        head=entries[-1].entry_hash,
        failures=failures,
    )


class AuditLog:
    """
    Append-only hash chain for one adjudication run.

    There is no update and no delete. The only mutation is append, which is the
    property that makes the chain meaningful.
    """

    def __init__(self, run_id: str, clock: Callable[[], str] | None = None):
        """
        clock : optional callable returning a timestamp string. Left as None,
                the log records no time at all and two runs over identical
                inputs produce byte-identical chains -- required for
                deterministic replay under global rule 4. Supply a real clock
                in production, and swap it out to replay.
        """
        if not run_id:
            raise AuditChainError("run_id is required")
        self.run_id = run_id
        self.clock = clock
        self._entries: list[AuditEntry] = []
        self._append("genesis", {"run_id": run_id})

    # -- construction -------------------------------------------------------

    def _append(self, kind: str, payload: dict[str, Any]) -> AuditEntry:
        body = scrub_nan(dict(payload))
        if self.clock is not None:
            body["at"] = self.clock()
        seq = len(self._entries)
        prev = GENESIS_PREV_HASH if seq == 0 else self._entries[-1].entry_hash
        entry = AuditEntry(seq, prev, kind, body, compute_entry_hash(seq, prev, kind, body))
        self._entries.append(entry)
        return entry

    def append(self, kind: str, payload: dict[str, Any]) -> AuditEntry:
        """Append an arbitrary record. 'genesis' is reserved for entry 0."""
        if kind == "genesis":
            raise AuditChainError("'genesis' is reserved for the first entry")
        return self._append(kind, payload)

    def record_artifact(self, artifact: str, *, include_text: bool = False) -> AuditEntry:
        """
        Record WHICH artifact was adjudicated.

        The digest is always written; the text only on explicit opt-in. Default
        off so a log of a RED run does not itself become RED.
        """
        payload: dict[str, Any] = {
            "artifact_sha256": digest(artifact),
            "artifact_length": len(artifact),
        }
        if include_text:
            payload["artifact_text"] = artifact
        return self.append("artifact", payload)

    def record_pass(self, result: Any) -> AuditEntry:
        """Record one pass: what was proposed, how the gates ruled, what
        diverged. Accepts a SequentialPassResult without importing it, so this
        module stays free of a circular dependency on the orchestrator."""
        rec, div = result.record, result.divergence
        return self.append(
            "pass",
            {
                "pass_id": result.pass_id,
                "pass_name": result.pass_name,
                "proposed": rec.proposed,
                "auto_accepted": rec.auto_accepted,
                "auto_rejected": rec.auto_rejected,
                "escalated": rec.escalated,
                "eliminated_candidates": list(rec.eliminated_candidates),
                "claims": sorted(
                    {c.id for r in result.responses for c in r.claims}
                ),
                "seats_responding": list(div.seats_responding),
                "seats_errored": list(div.seats_errored),
                "mean_pairwise_jaccard": div.mean_pairwise_jaccard,
                "unanimous": div.unanimous,
                "all_seats_silent": div.all_seats_silent,
                "collapse_warning": div.collapse_warning,
            },
        )

    def record_stop_decision(self, decision: dict[str, Any]) -> AuditEntry:
        """Record the stop verdict and, critically, its blockers. SOP 9.1
        step 8 makes an empty queue a precondition for commit; the reason a
        run did NOT stop is the part an auditor needs."""
        return self.append(
            "stop_decision",
            {
                "stop": decision.get("stop"),
                "blockers": list(decision.get("blockers", [])),
                "surviving_candidates": decision.get("surviving_candidates"),
                "extrapolated_residual": decision.get("extrapolated_residual"),
                "escalations_pending": decision.get("escalations_pending"),
                "singleton_fraction": decision.get("singleton_fraction"),
                "singleton_alarm_calibrated": decision.get("singleton_alarm_calibrated"),
            },
        )

    # -- inspection ---------------------------------------------------------

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        """Immutable view. Callers cannot append by mutating this."""
        return tuple(self._entries)

    @property
    def head(self) -> str:
        """The current head commitment. Record this outside the log to make
        tail truncation detectable."""
        return self._entries[-1].entry_hash

    def __len__(self) -> int:
        return len(self._entries)

    def verify(
        self, expected_head: str | None = None, expected_length: int | None = None
    ) -> ChainVerdict:
        return verify_chain_integrity(self._entries, expected_head, expected_length)

    # -- serialisation ------------------------------------------------------

    def to_jsonl(self) -> str:
        """One canonical JSON object per line. Append-friendly on disk."""
        return "\n".join(canonical_json(e.to_dict()) for e in self._entries)

    @staticmethod
    def parse_jsonl(text: str) -> list[AuditEntry]:
        """
        Parse a serialised chain. Fails closed on any malformed line rather
        than skipping it -- a line that will not parse is exactly what a
        tampered log looks like.
        """
        out: list[AuditEntry] = []
        for n, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AuditChainError(f"line {n}: not valid JSON: {exc}") from exc
            out.append(AuditEntry.from_dict(obj))
        return out


def replay(entries: Iterable[AuditEntry]) -> str:
    """
    Recompute the chain from entry payloads alone and return the resulting head.

    This is the deterministic-replay check. It ignores every stored hash and
    rebuilds the commitments from the payloads, so a chain whose hashes were
    recomputed to cover a tampered payload still fails when its head is
    compared against an independently recorded one.
    """
    prev = GENESIS_PREV_HASH
    seq = 0
    for e in entries:
        prev = compute_entry_hash(seq, prev, e.kind, e.payload)
        seq += 1
    if seq == 0:
        raise AuditChainError("cannot replay an empty chain")
    return prev
