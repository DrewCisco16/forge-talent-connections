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

import fcntl
import hashlib
import json
import math
import os
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


class RunRecorder:
    """
    The three things a run writes, shared by every log that can append.

    These were defined on AuditLog alone, so DurableAuditLog -- the only log
    that survives the process -- could not be passed to run_sequential at all:
    the first call to record_artifact raised AttributeError. A real run could
    therefore write an in-memory chain that vanished, or a durable chain with
    nothing in it. Both are worse than no audit log, because both look like
    one. Every method here is a thin wrapper over append(), which both classes
    already implement identically.
    """

    def append(self, kind: str, payload: dict[str, Any]) -> AuditEntry:
        raise NotImplementedError

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
                # proposed does not equal accepted + rejected + escalated +
                # blocked once any claim has been made twice. Without these
                # two the arithmetic silently stops closing, and a later
                # round reads as "N proposed, 0 resolved" -- which looks
                # exactly like the gates having stopped working.
                "repeats": rec.repeats,
                # The one that matters: a speaker restating something the
                # gates already refuted is asserting a known falsehood, and
                # counting only fresh rulings made every repeat invisible.
                "repeated_failures": rec.repeated_failures,
                "eliminated_candidates": list(rec.eliminated_candidates),
                "claims": sorted(
                    {c.id for r in result.responses for c in r.claims}
                ),
                "seats_responding": list(div.seats_responding),
                "seats_errored": list(div.seats_errored),
                # WHY, not just WHICH. The console report gained this and the
                # durable record did not, so the audit -- the thing the
                # operator keeps -- could not say why a seat failed. A live
                # run lost a seat in four of five passes and the reason
                # existed only in a terminal window that later hung.
                "seat_errors": dict(div.seat_errors),
                # blocked serialised as None because the field postdated this
                # writer. A blocked count of "None" reads as "not applicable"
                # when it means zero checks were prevented.
                #
                # Both fields are read DIRECTLY, not via getattr with a
                # default. A defensive getattr here would turn a future rename
                # into a silently empty audit record -- the run would look
                # complete and would have destroyed the evidence -- instead of
                # an AttributeError at the moment the contract broke.
                "blocked": int(rec.blocked),
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



class AuditLog(RunRecorder):
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


# ===========================================================================
# DURABLE STORE
#
# An in-memory chain proves nothing after the process exits. SOP 8.5 requires
# the record to survive the run, which means the append itself has to be safe
# against two things that actually happen: the process dying mid-write, and a
# second writer appending at the same moment.
# ===========================================================================

HEAD_SUFFIX = ".head"
"""
Sidecar carrying the head hash and length.

This is the "independently recorded head" the chain needs to detect tail
truncation. Being honest about its strength: it defends against accidental
truncation, a crash, and a partial copy. It does NOT defend against an attacker
with write access to both files, who can simply rewrite the sidecar to match.
Real tamper-evidence needs the head recorded somewhere this process cannot
reach -- a separate host, an append-only bucket, a printed page.
"""


class AuditStoreError(AuditChainError):
    """Raised when the on-disk store cannot be used safely."""


class TornAppendError(AuditStoreError):
    """
    The final line of the log is incomplete: an append began and did not finish.

    This is the recoverable case. The torn entry was never committed, so the
    correct state is the log as it stood before that append -- the rollback.
    Recovery is explicit (recover=True) rather than automatic, because silently
    discarding a trailing line is indistinguishable from silently discarding
    evidence.
    """


def _read_head_sidecar(path: str) -> tuple[str, int] | None:
    side = path + HEAD_SUFFIX
    if not os.path.exists(side):
        return None
    with open(side, encoding="utf-8") as fh:
        raw = fh.read().strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        return str(obj["head"]), int(obj["length"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise AuditStoreError(f"head sidecar is unreadable: {exc}") from exc


def _split_committed(text: str) -> tuple[list[str], str | None]:
    """
    Separate fully-written lines from a torn trailing one.

    A committed line ends with a newline. Anything after the last newline is a
    write that did not finish.
    """
    if not text:
        return [], None
    idx = text.rfind("\n")
    if idx == -1:
        return [], text
    committed = [ln for ln in text[: idx + 1].splitlines() if ln.strip()]
    tail = text[idx + 1 :]
    return committed, (tail if tail.strip() else None)


class DurableAuditLog(RunRecorder):
    """
    Append-only audit chain persisted to a JSONL file.

    Every append is: take an exclusive lock, re-read the committed tail, chain
    onto whatever is actually on disk, write the line with a single write(),
    fsync, update the head sidecar, release. Only then does the entry become
    visible in memory.

    That ordering is the rollback guarantee. If the write or the fsync raises,
    the in-memory chain is untouched and the on-disk chain still ends at the
    last committed entry, so a failed append leaves no half-state behind.

    POSIX only: uses fcntl.flock.
    """

    def __init__(
        self,
        path: str,
        run_id: str | None = None,
        clock: Callable[[], str] | None = None,
        recover: bool = False,
    ):
        self.path = path
        self.clock = clock
        self._entries: list[AuditEntry] = []

        exists = os.path.exists(path) and os.path.getsize(path) > 0
        if exists:
            self._entries = self._load(recover=recover)
            if run_id is not None and self._entries[0].payload.get("run_id") != run_id:
                raise AuditStoreError(
                    f"log at {path} belongs to run "
                    f"{self._entries[0].payload.get('run_id')!r}, not {run_id!r}"
                )
        else:
            if not run_id:
                raise AuditStoreError("run_id is required to create a new log")
            self._commit("genesis", {"run_id": run_id})

    # -- loading ------------------------------------------------------------

    def _load(self, recover: bool) -> list[AuditEntry]:
        """
        Read under an exclusive lock.

        Without the lock a reader can land between the log write and the
        sidecar write and see a log of N+1 entries against a sidecar still
        claiming N -- reported as "extended", which looks exactly like
        tampering. Found by running parallel writers; a threaded test missed it
        because the window is only a few microseconds wide.
        """
        lock_fd = os.open(self.path, os.O_RDONLY)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            with open(self.path, encoding="utf-8") as fh:
                committed, torn = _split_committed(fh.read())
            side = _read_head_sidecar(self.path)

            if torn is not None and not recover:
                raise TornAppendError(
                    f"{self.path}: the final line is incomplete ({len(torn)} bytes, "
                    f"no newline). An append did not finish. The entry was never "
                    f"committed; reopen with recover=True to roll back to the last "
                    f"committed entry."
                )
            if torn is not None:
                self._truncate_to(len("\n".join(committed)) + 1 if committed else 0)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

        entries = [AuditEntry.from_dict(json.loads(ln)) for ln in committed]
        if not entries:
            raise AuditStoreError(f"{self.path}: no committed entries")

        verdict = verify_chain_integrity(
            entries,
            expected_head=side[0] if side else None,
            expected_length=side[1] if side else None,
        )
        if not verdict.valid:
            raise AuditStoreError(
                f"{self.path}: chain does not verify: " + "; ".join(verdict.failures)
            )
        return entries

    def _truncate_to(self, size: int) -> None:
        fd = os.open(self.path, os.O_WRONLY)
        try:
            os.ftruncate(fd, size)
            os.fsync(fd)
        finally:
            os.close(fd)

    # -- appending ----------------------------------------------------------

    def _make(self, kind: str, payload: dict[str, Any]) -> AuditEntry:
        body = scrub_nan(dict(payload))
        if self.clock is not None:
            body["at"] = self.clock()
        seq = len(self._entries)
        prev = GENESIS_PREV_HASH if seq == 0 else self._entries[-1].entry_hash
        return AuditEntry(seq, prev, kind, body, compute_entry_hash(seq, prev, kind, body))

    def _commit(self, kind: str, payload: dict[str, Any]) -> AuditEntry:
        """
        The only way an entry reaches disk.

        Under one exclusive lock: re-read the committed tail, chain onto it,
        write, fsync, update the sidecar. Holding the lock across BOTH writes
        is what stops a reader seeing the log and the sidecar disagree.

        The in-memory chain is extended only after the durable write returns,
        so a failed append is a no-op rather than a half-entry -- the rollback.
        """
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            with open(self.path, encoding="utf-8") as fh:
                committed, _ = _split_committed(fh.read())
            if committed:
                self._entries = [AuditEntry.from_dict(json.loads(ln)) for ln in committed]

            entry = self._make(kind, payload)
            line = (canonical_json(entry.to_dict()) + "\n").encode("utf-8")
            os.lseek(fd, 0, os.SEEK_END)
            written = os.write(fd, line)
            if written != len(line):
                raise AuditStoreError(
                    f"short write: {written} of {len(line)} bytes; not committed"
                )
            os.fsync(fd)

            self._entries.append(entry)
            self._write_head_sidecar()
            return entry
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _write_head_sidecar(self) -> None:
        side = self.path + HEAD_SUFFIX
        tmp = side + ".tmp"
        body = canonical_json({"head": self.head, "length": len(self._entries)})
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, side)            # atomic; the sidecar is never half-written

    def append(self, kind: str, payload: dict[str, Any]) -> AuditEntry:
        """Append one entry durably. See _commit for the locking contract."""
        if kind == "genesis":
            raise AuditStoreError("'genesis' is reserved for the first entry")
        return self._commit(kind, payload)

    # -- the same recording helpers as the in-memory log --------------------

    record_artifact = AuditLog.record_artifact
    record_pass = AuditLog.record_pass
    record_stop_decision = AuditLog.record_stop_decision

    # -- inspection ---------------------------------------------------------

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        return tuple(self._entries)

    @property
    def head(self) -> str:
        return self._entries[-1].entry_hash

    @property
    def run_id(self) -> str:
        return str(self._entries[0].payload["run_id"])

    def __len__(self) -> int:
        return len(self._entries)

    def verify(self, check_sidecar: bool = True) -> ChainVerdict:
        side = _read_head_sidecar(self.path) if check_sidecar else None
        return verify_chain_integrity(
            self._entries,
            expected_head=side[0] if side else None,
            expected_length=side[1] if side else None,
        )
