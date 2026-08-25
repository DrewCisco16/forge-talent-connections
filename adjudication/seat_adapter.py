"""
seat_adapter.py
===============
Turns a configured seat into the plain callable BlindedSeatRunner expects.

WHAT THIS IS FOR
----------------
SOP Manual v1.1 section 8.3: "Write a seat function for each provider: it takes
a prompt string, returns a text response." Everything upstream of this module
has been exercised against synthetic seats, which validates the machinery and
says nothing about how a real model behaves. This is the boundary where that
changes.

WHAT THIS MODULE DELIBERATELY DOES NOT CONTAIN
----------------------------------------------
No vendor endpoints. No request bodies. No response paths. Not one.

Every provider's URL, auth scheme, body shape, and reply structure arrives as a
ProviderProfile that the OPERATOR fills in from that vendor's own API
documentation. Writing them from memory is how a build acquires an endpoint
that looks right and is a version stale, or a response path that silently
returns None and reads as an empty answer. Vendor API docs are technical
manuals -- admissible evidence under the section 8.3 rule. Recollection is not.

FAIL CLOSED
-----------
A seat that cannot produce a verified reply produces NO reply. Every failure
path raises SeatError rather than returning a partial or empty string, because
BlindedSeatRunner records a raised seat as errored and excludes it from the
divergence statistics, whereas an empty string reads as a seat that examined
the artifact and found nothing. Those are opposite facts and must not be
confused: one is a missing measurement, the other is a measurement of zero.

CREDENTIALS
-----------
The key is read through ResolvedSeat.credential() at call time and is never
stored on this object, never placed in an exception message, and never included
in a repr. SeatError messages are built from status codes and shapes, never
from request headers.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from adjudication_orchestrator import ResolvedSeat

# (method, url, headers, body_bytes, timeout_s) -> (status_code, body_bytes)
#
# Injected rather than imported so this module makes no network call of its own
# and the whole surface is testable without one. A real transport is a thin
# wrapper over requests, httpx, or urllib -- the operator's choice, and the
# only place a socket is opened.
Transport = Callable[[str, str, Mapping[str, str], bytes, float], tuple[int, bytes]]

RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
"""
Transient by definition: rate limiting, timeouts, and upstream faults.

401, 403, and 404 are NOT here and must never be. An auth failure is a
configuration error, and retrying it burns quota, multiplies the audit trail,
and delays the operator seeing the one thing that needs fixing.
"""


class SeatError(RuntimeError):
    """A seat could not produce a verified reply. Carries no credential."""


@dataclass(frozen=True)
class ProviderProfile:
    """
    Everything vendor-specific, supplied by the operator from vendor docs.

    name          : label for logs and the audit record.
    endpoint      : full URL to POST to.
    auth_header   : header name carrying the credential.
    auth_template : format string with one {key} placeholder, e.g. "Bearer {key}".
    build_body    : (model, prompt, max_tokens, temperature) -> JSON-serialisable dict.
    extract_text  : parsed response dict -> the reply text, or None if absent.
    extra_headers : any additional constant headers the vendor requires.
    max_tokens    : per-seat output cap, overriding HttpSeat's default when set.

    WHY max_tokens IS PER-SEAT. On a reasoning model the thinking tokens are
    drawn from the SAME cap as the reply, so one budget that suits a
    non-reasoning seat can leave a reasoning seat no room to answer -- it
    returns a well-formed 200 whose reply text is empty, and the seat reads as
    having examined the artifact and found nothing. A shared default cannot fit
    both kinds of seat, and the alternative was editing the adapter per panel.
    """

    name: str
    endpoint: str
    auth_header: str
    auth_template: str
    build_body: Callable[[str, str, int, float], dict[str, Any]]
    extract_text: Callable[[dict[str, Any]], str | None]
    extra_headers: Mapping[str, str] = field(default_factory=dict)
    max_tokens: int | None = None
    usage_input_path: Sequence[Any] | None = None
    usage_output_path: Sequence[Any] | None = None
    """Where this vendor reports token counts, declared per profile.

    Declarative for the same reason the reply path is: five vendors put usage
    in five places and hard-coding them is how the adapter learns about
    vendors again. A path that misses yields None, the call is counted as
    unmeasured, and the run total prints as a lower bound -- never a
    fabricated estimate dressed as a measurement.
    """

    def __post_init__(self) -> None:
        if "{key}" not in self.auth_template:
            raise ValueError(
                f"{self.name}: auth_template must contain a {{key}} placeholder"
            )
        if not self.endpoint.startswith("https://"):
            raise ValueError(
                f"{self.name}: endpoint must be https, got {self.endpoint!r}. "
                f"A credential must never cross a plaintext connection."
            )

    def __repr__(self) -> str:
        return f"ProviderProfile(name={self.name!r}, endpoint={self.endpoint!r})"


@dataclass(frozen=True)
class RetryPolicy:
    """
    Bounded retries on transient status only.

    max_attempts counts the FIRST try, so 1 means no retry. Backoff is
    expressed as a sequence the caller supplies to its own sleeper; this module
    never sleeps and never reads a clock, so it stays deterministic and global
    rule 4 holds.
    """

    max_attempts: int = 3
    backoff_seconds: tuple[float, ...] = (0.5, 2.0)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")


class HttpSeat:
    """
    One seat. Call it with a prompt, get text back, or get SeatError.

    Deliberately has no memory between calls: each pass is an independent
    request carrying only the blinded prompt it was handed. A seat that
    accumulated conversation state would reintroduce exactly the cross-pass
    leakage BLINDING_CONTRACT forbids.
    """

    def __init__(
        self,
        seat: ResolvedSeat,
        profile: ProviderProfile,
        transport: Transport,
        *,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        timeout_s: float = 120.0,
        retry: RetryPolicy | None = None,
        sleeper: Callable[[float], None] | None = None,
        ledger: Any = None,
        est_input_tokens: int = 3000,
    ):
        resolved_model = model or seat.model
        if not resolved_model:
            raise SeatError(
                f"seat {seat.seat_id}: no model configured. Set its model "
                f"environment variable or pass model= explicitly."
            )
        if seat.in_process:
            raise SeatError(
                f"seat {seat.seat_id} is marked in-process and has no outbound "
                f"credential; HttpSeat cannot drive it. See the note on "
                f"PANEL_OF_FIVE about the orchestrator not being its own seat."
            )
        if not seat.credential():
            raise SeatError(f"seat {seat.seat_id}: no credential resolved")

        self.seat = seat
        self.profile = profile
        self.transport = transport
        self.model = resolved_model
        # The PROFILE's cap wins when it has one. The ceiling estimate reads
        # this value, so a seat constructed without the profile cap propagated
        # would estimate 4096 while actually generating up to its real cap --
        # a silent under-estimate, which is the one direction a spend limit
        # must never err in. Making the seat self-consistent removes the
        # dependence on every construction path remembering to pass it.
        self.max_tokens: int = (profile.max_tokens
                                if profile.max_tokens is not None
                                else max_tokens)
        self.temperature = temperature
        self.timeout_s = timeout_s
        self.retry = retry or RetryPolicy()
        self.sleeper = sleeper
        self.attempts_made = 0
        self.ledger = ledger
        self.est_input_tokens = est_input_tokens
        self.last_usage: tuple[int | None, int | None] = (None, None)

    @property
    def seat_id(self) -> str:
        return self.seat.seat_id

    def __repr__(self) -> str:
        return (
            f"HttpSeat(seat_id={self.seat_id!r}, provider={self.profile.name!r}, "
            f"model={self.model!r})"
        )

    __str__ = __repr__

    def _headers(self) -> dict[str, str]:
        """Built fresh per request; the credential is never held on self."""
        key = self.seat.credential() or ""
        return {
            "content-type": "application/json",
            self.profile.auth_header: self.profile.auth_template.format(key=key),
            **dict(self.profile.extra_headers),
        }

    def __call__(self, prompt: str) -> str:
        if self.ledger is not None:
            # BEFORE the call, never after. A limit you can only detect having
            # crossed is a report, not a limit. The estimate assumes this
            # seat's full output cap because that is the worst case this call
            # can produce; estimating smaller lets the last call of a run
            # cross the ceiling it was checked against.
            self.ledger.check_before_call(
                self.seat_id, self.est_input_tokens, self.max_tokens
            )
        body = json.dumps(
            self.profile.build_body(
                self.model, prompt, self.max_tokens, self.temperature
            )
        ).encode("utf-8")

        last: str = "no attempt was made"
        for attempt in range(self.retry.max_attempts):
            self.attempts_made = attempt + 1
            try:
                status, raw = self.transport(
                    "POST", self.profile.endpoint, self._headers(), body, self.timeout_s
                )
            except Exception as exc:  # fail closed on any transport fault
                # The message is the exception TYPE and text, never the request,
                # because the request carries the credential.
                last = f"transport raised {type(exc).__name__}: {exc}"
                if attempt + 1 < self.retry.max_attempts:
                    self._backoff(attempt)
                    continue
                raise SeatError(f"seat {self.seat_id}: {last}") from exc

            if status in RETRYABLE_STATUS and attempt + 1 < self.retry.max_attempts:
                self._backoff(attempt)
                last = f"transient HTTP {status}"
                continue
            if status < 200 or status >= 300:
                raise SeatError(
                    f"seat {self.seat_id}: HTTP {status} from {self.profile.name}"
                    + ("" if status not in RETRYABLE_STATUS else " (retries exhausted)")
                )
            text = self._parse(raw)
            self._book(raw)
            return text

        raise SeatError(f"seat {self.seat_id}: {last} (retries exhausted)")

    def _book(self, raw: bytes) -> None:
        """Record what the call actually cost, from the vendor's own count."""
        if self.ledger is None:
            return
        tin = tout = None
        try:
            from cost_ledger import usage_from_payload
            payload = json.loads(raw)
            if isinstance(payload, dict):
                tin, tout = usage_from_payload(
                    payload, self.profile.usage_input_path,
                    self.profile.usage_output_path,
                )
        except Exception:  # noqa: BLE001 - unmeasured is honest, guessing is not
            tin = tout = None
        self.last_usage = (tin, tout)
        self.ledger.record(self.seat_id, tin, tout)

    def _backoff(self, attempt: int) -> None:
        if self.sleeper is None or not self.retry.backoff_seconds:
            return
        idx = min(attempt, len(self.retry.backoff_seconds) - 1)
        self.sleeper(self.retry.backoff_seconds[idx])

    def _parse(self, raw: bytes) -> str:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SeatError(
                f"seat {self.seat_id}: {self.profile.name} returned "
                f"{len(raw)} bytes that are not JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise SeatError(
                f"seat {self.seat_id}: expected a JSON object, got "
                f"{type(payload).__name__}"
            )
        try:
            text = self.profile.extract_text(payload)
        except Exception as exc:  # a raising extractor fails closed
            raise SeatError(
                f"seat {self.seat_id}: extract_text raised "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        if text is None:
            raise SeatError(
                f"seat {self.seat_id}: {self.profile.name} reply contained no "
                f"text at the configured path. Top-level keys: "
                f"{sorted(payload)[:8]}"
            )
        if not isinstance(text, str):
            raise SeatError(
                f"seat {self.seat_id}: extract_text returned "
                f"{type(text).__name__}, expected str"
            )
        return text


def build_seat_callables(
    seats: Sequence[ResolvedSeat],
    profiles: Mapping[str, ProviderProfile],
    transport: Transport,
    **kwargs: Any,
) -> dict[str, Callable[[str], str]]:
    """
    Assemble the {seat_id: callable} mapping BlindedSeatRunner takes.

    FAIL CLOSED on a seat with no profile: a panel that quietly runs short
    misstates rho, effective seats, and the residual, which is the same reason
    load_panel refuses a missing credential.

    In-process seats are skipped rather than errored -- they are driven by the
    host session, not by this adapter -- but the caller is responsible for
    supplying them, and for the separation PANEL_OF_FIVE documents.
    """
    out: dict[str, Callable[[str], str]] = {}
    missing = [s.seat_id for s in seats if not s.in_process and s.seat_id not in profiles]
    if missing:
        raise SeatError(
            f"no ProviderProfile for seat(s): {', '.join(sorted(missing))}. "
            f"A panel that runs short misstates every downstream statistic."
        )
    for s in seats:
        if s.in_process:
            continue
        prof = profiles[s.seat_id]
        seat_kwargs = dict(kwargs)
        if prof.max_tokens is not None:
            seat_kwargs["max_tokens"] = prof.max_tokens
        out[s.seat_id] = HttpSeat(s, prof, transport, **seat_kwargs)
    return out


# ===========================================================================
# WORKED SHAPE
#
# The values below are PLACEHOLDERS, not any vendor's real API. Copy the shape
# and fill every field from that provider's own API reference, then confirm it
# against a live call before trusting a run. Two fields are worth checking
# twice:
#
#   auth_template   some vendors want "Bearer {key}", others send the raw key
#                   in a vendor-specific header. Getting this wrong yields 401,
#                   which this module does NOT retry -- deliberately, so the
#                   misconfiguration surfaces immediately.
#
#   extract_text    the single most dangerous field. A wrong path returns None
#                   on a perfectly successful 200, and without the guard in
#                   _parse that would read as a seat which examined the artifact
#                   and found nothing to say. Verify it against a real response
#                   body, not against what the shape looks like it should be.
#
# EXAMPLE_PROFILE = ProviderProfile(
#     name="<vendor label>",
#     endpoint="https://<from the vendor's API reference>",
#     auth_header="<from the vendor's API reference>",
#     auth_template="Bearer {key}",
#     build_body=lambda model, prompt, max_tokens, temperature: {
#         # exact keys come from the vendor's request schema
#         "model": model,
#         "max_tokens": max_tokens,
#         "temperature": temperature,
#         "messages": [{"role": "user", "content": prompt}],
#     },
#     extract_text=lambda payload: (
#         # exact path comes from the vendor's response schema; return None
#         # rather than raising when the path is absent
#         payload.get("content", [{}])[0].get("text")
#     ),
# )
#
# TEMPERATURE AND REPLAY. temperature=0.0 is the default because global rule 4
# blocks nondeterminism in replay mode. A nonzero temperature makes a run
# unreproducible, which does not invalidate it but does mean the audit chain
# records what happened rather than something that can be re-derived. Set it
# deliberately, not by accident.
# ===========================================================================
