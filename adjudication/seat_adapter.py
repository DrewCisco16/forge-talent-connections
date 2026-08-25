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
import urllib.parse
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



def _is_timeout(exc: BaseException) -> bool:
    """True if this exception is, or wraps, a read timeout.

    urllib usually lets socket.timeout (an alias of TimeoutError since 3.10)
    propagate, which is what a live grok-4.6 call produced. But a transport is
    injectable here, and some wrap the timeout in URLError or OSError. Matching
    only the bare type would send those down the retry path, which is the exact
    behaviour this distinction exists to stop.
    """
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, TimeoutError):
            return True
        reason = getattr(cur, "reason", None)
        if isinstance(reason, BaseException):
            cur = reason
            continue
        cur = cur.__cause__ or cur.__context__
    return False

TIMEOUT_IS_NOT_RETRYABLE = True
"""A read timeout means the model is still thinking, not that the call failed.

Measured live: grok-4.6 answered a 632-token prompt after 275 seconds. Under
the old 120-second timeout every attempt expired, all three retries expired
with it, and the seat was marked FAILED after burning six minutes -- in four
of five passes of a real run. Retrying a timeout re-sends the same prompt to
the same model and waits for the same duration, so it converts one slow call
into three, and the vendor may bill the abandoned generations.
"""
"""
Transient by definition: rate limiting, timeouts, and upstream faults.

401, 403, and 404 are NOT here and must never be. An auth failure is a
configuration error, and retrying it burns quota, multiplies the audit trail,
and delays the operator seeing the one thing that needs fixing.
"""


def scrub(text: str, secret: str | None) -> str:
    """Remove a known credential from a diagnostic string.

    THE FAILURE THIS EXISTS TO STOP. The handler below carried a comment
    saying the message is "the exception TYPE and text, never the request,
    because the request carries the credential". That was wrong in the one way
    that matters: we do not include the request, but the EXCEPTION'S OWN TEXT
    can. urllib raises ValueError containing the offending header value for a
    malformed Authorization; several transports include the request in their
    message. Verified: the credential appeared in SeatError, which is written
    to seat_errors, into the audit record, and into status.md on disk.

    Exact-value removal, not pattern matching, because the credential is known
    here. Also scrubs any chained cause, since traceback printing walks it.
    """
    if not text:
        return text
    if secret:
        for form in (secret, secret.strip()):
            if form and len(form) >= 8:
                text = text.replace(form, "[redacted credential]")
    return text


def redact_url(url: str) -> str:
    """scheme://host/path, with userinfo and any query dropped.

    Enough to identify which endpoint was called; not enough to carry a
    credential someone put in the URL.
    """
    try:
        p = urllib.parse.urlsplit(url or "")
    except ValueError:
        return "[unparseable endpoint]"
    if not p.scheme:
        return "[endpoint]"
    host = p.hostname or ""
    port = f":{p.port}" if p.port else ""
    query = "?[redacted]" if p.query else ""
    userinfo = "[redacted]@" if (p.username or p.password) else ""
    return f"{p.scheme}://{userinfo}{host}{port}{p.path}{query}"


def _stop_reason(payload: Mapping[str, Any]) -> str:
    """Whatever this vendor calls the reason it stopped generating."""
    for key in ("stop_reason", "finish_reason"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        value = choices[0].get("finish_reason")
        if isinstance(value, str) and value:
            return value
    return ""


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
        # THE ENDPOINT IS REDACTED, NOT PRINTED. repr() lands in tracebacks,
        # logs, debugger output and pytest failure messages, and an endpoint
        # carrying userinfo or a credential query parameter would be copied
        # into all of them. validate_config refuses such endpoints, but repr
        # is reached by profiles built directly in code and by anything that
        # bypasses validation.
        return f"ProviderProfile(name={self.name!r}, endpoint={redact_url(self.endpoint)!r})"


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
        timeout_s: float = 600.0,
        retry: RetryPolicy | None = None,
        sleeper: Callable[[float], None] | None = None,
        ledger: Any = None,
        est_input_tokens: int = 3000,
        pass_id: str | None = None,
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
        # WITHOUT THIS A PER-STAGE CEILING IS INERT. The ledger keys stage
        # spend by pass_id; HttpSeat passed none, so every live call recorded
        # pass_id=None, stage spend stayed at zero, and a configured
        # per-stage limit could never be reached however much was spent.
        self.pass_id = pass_id
        # Worst case of the dispatch currently in flight, so a failure can be
        # charged for what it might have cost rather than for nothing.
        self._last_worst_case = 0.0
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
        body = json.dumps(
            self.profile.build_body(
                self.model, prompt, self.max_tokens, self.temperature
            )
        ).encode("utf-8")

        last: str = "no attempt was made"
        for attempt in range(self.retry.max_attempts):
            self.attempts_made = attempt + 1
            # BEFORE EVERY DISPATCH, not once before the loop.
            #
            # The check ran a single time and the retry loop then sent the
            # request up to max_attempts times. Three requests produced one
            # ceiling check, and a vendor bills each of them. A timed-out
            # request produced no ledger entry at all, so a run that dispatched
            # work and paid for it reported "no billable call was made".
            self._precheck(prompt, body)
            try:
                status, raw = self.transport(
                    "POST", self.profile.endpoint, self._headers(), body, self.timeout_s
                )
            except Exception as exc:  # noqa: BLE001 - fail closed on any transport fault
                # A READ TIMEOUT IS THE MODEL STILL THINKING, NOT A FAULT,
                # and it is the one transport failure that must not be retried.
                #
                # Retrying resends the identical prompt to the identical model
                # and waits the identical duration, so it turns one slow call
                # into max_attempts slow calls, and the vendor may bill every
                # abandoned generation. Measured live: grok-4.6 answered a
                # 632-token prompt after 275 seconds. Under the old 120-second
                # timeout every attempt expired, all three retries expired with
                # it, and the seat was recorded FAILED after burning six
                # minutes -- in four of five passes of a real run.
                #
                # Fail once, immediately, and name the duration, because the
                # duration is the entire diagnosis.
                self._record_unmeasured("timeout or transport failure")
                if _is_timeout(exc):
                    raise SeatError(
                        f"seat {self.seat_id}: {self.profile.name} did not "
                        f"reply within {self.timeout_s:.0f}s. Reasoning models "
                        f"routinely exceed this on a full-size prompt. Raise "
                        f"timeout_s -- do not lower max_tokens, which "
                        f"truncates the reply instead of speeding it up."
                    # from None: the chained cause is walked by traceback
                    # printing and by the watcher's format_exc(), and a
                    # transport exception can carry the request headers.
                    ) from None
                # The exception's OWN text can contain the request, and the
                # request carries the credential. Naming only the type would
                # discard the vendor's explanation, which is what made the
                # first live run unreadable -- so the text is kept and the
                # known credential is removed from it by exact value.
                last = scrub(f"transport raised {type(exc).__name__}: {exc}",
                             self.seat.credential())
                if attempt + 1 < self.retry.max_attempts:
                    self._backoff(attempt)
                    continue
                # from None, not from exc: __cause__ is walked by traceback
                # printing and by the watcher's format_exc(), so a chained
                # cause carrying the credential lands in ERROR.md on disk.
                raise SeatError(f"seat {self.seat_id}: {last}") from None

            if status in RETRYABLE_STATUS and attempt + 1 < self.retry.max_attempts:
                # A 429 or 503 was still a dispatch. Some vendors bill it.
                self._record_unmeasured(f"HTTP {status}, retrying")
                self._backoff(attempt)
                last = f"transient HTTP {status}"
                continue
            if status < 200 or status >= 300:
                # A TERMINAL NON-2XX STILL REACHED THE VENDOR. It was raised
                # without any ledger entry, so a final 401 cost nothing on
                # paper and could be repeated without limit.
                self._record_unmeasured(f"HTTP {status}")
                raise SeatError(
                    f"seat {self.seat_id}: HTTP {status} from {self.profile.name}"
                    + ("" if status not in RETRYABLE_STATUS else " (retries exhausted)")
                )
            # BOOK BEFORE PARSING. _parse raises on invalid JSON, on a
            # payload that is not an object, and on a reply the configured
            # text path cannot reach -- and every one of those raises happened
            # BEFORE the ledger saw the call. A 200 we could not read cost
            # nothing on paper and could be repeated without limit. The vendor
            # billed it either way.
            self._book(raw)
            return self._parse(raw)

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
        # A SUCCESSFUL CALL WITH NO USABLE USAGE KEEPS ITS RESERVATION.
        #
        # This passed no estimate, and record() defaults it to zero, so an
        # HTTP 200 whose usage block was missing, malformed, or
        # self-contradictory consumed NOTHING. Twenty such calls ran under a
        # $0.01 ceiling with committed spend at $0.00 and no overrun recorded
        # -- an unlimited, repeatable spend route straight through the control
        # that exists to stop it. Only a call we could actually price may
        # settle its reservation.
        self.ledger.record(self.seat_id, tin, tout, pass_id=self.pass_id,
                           estimated_dollars=self._last_worst_case,
                           authorised=self._last_worst_case)

    def set_pass(self, pass_id: str | None) -> None:
        """Tell this seat which pass its next calls belong to.

        WITHOUT A CALLER, pass_id WAS DEAD. It was added as a constructor
        argument, tested through a seat built by hand, and set by nothing on
        the production path -- so every live call still recorded pass_id=None,
        stage spend stayed at zero, and a configured per-stage ceiling could
        never be reached however much was spent. The parameter existed, the
        test passed, and the control was inert.

        Seats are built once and reused across every pass, so the pass has to
        be told to them as the run moves, not fixed at construction.
        """
        self.pass_id = pass_id


    def _precheck(self, prompt: str, body: bytes = b"") -> None:
        """Refuse this dispatch if its worst case would cross a ceiling.

        The bound is derived from the ACTUAL prompt rather than a flat 3,000
        tokens, and the output side allows for reasoning tokens, which are
        billed and are not bounded by max_tokens. Both were measured failures:
        a 400,000-character prompt passed a check computed as 3,000 tokens,
        and a call whose cap was 4,096 billed roughly 15,400 output tokens.
        """
        if self.ledger is None:
            return
        from cost_ledger import (
            HIDDEN_OUTPUT_MULTIPLIER,
            estimate_input_tokens,
            estimate_request_tokens,
        )
        # THE SERIALISED BODY, not just the prompt. A short question carrying
        # a large constant system field was checked as if it were the question
        # alone: a $0.004 ceiling authorised a request that billed $0.333.
        est_in = max(self.est_input_tokens,
                     estimate_input_tokens(prompt),
                     estimate_request_tokens(body))
        self._last_worst_case = self._worst_case_dollars(prompt, body)
        self.ledger.check_before_call(
            self.seat_id, est_in,
            int(self.max_tokens * HIDDEN_OUTPUT_MULTIPLIER),
            pass_id=self.pass_id,
        )

    def _worst_case_dollars(self, prompt: str, body: bytes = b"") -> float:
        """What this dispatch could have cost, for enforcement purposes."""
        if self.ledger is None:
            return 0.0
        from cost_ledger import HIDDEN_OUTPUT_MULTIPLIER, estimate_input_tokens
        rate = getattr(self.ledger, "rates", {}).get(self.seat_id)
        if rate is None:
            return 0.0
        from cost_ledger import estimate_request_tokens
        return float(rate.cost(
            max(self.est_input_tokens, estimate_input_tokens(prompt),
                estimate_request_tokens(body)),
            int(self.max_tokens * HIDDEN_OUTPUT_MULTIPLIER)))

    def _record_unmeasured(self, why: str) -> None:
        """Book a dispatch whose cost we never learned.

        A failed or timed-out attempt still reached the vendor and may still be
        billed. Recording nothing made the run total silently exclude it, and
        unmeasured_calls -- which is what turns the report into an explicit
        LOWER BOUND rather than a total -- never saw it either. A run that
        dispatched three requests and timed out reported "no billable call was
        made".
        """
        self.last_unmeasured_reason = why
        if self.ledger is not None:
            # CHARGED AT ITS WORST CASE, not at zero. Recording it as merely
            # "unmeasured" made the report say LOWER BOUND and left the
            # ceiling untouched, so three real dispatches consumed $0.0000 of
            # a $1.00 limit. The figure is separated from measured spend so
            # `spent` still reconciles against an invoice.
            self.ledger.record(self.seat_id, None, None, pass_id=self.pass_id,
                               estimated_dollars=self._last_worst_case)

    def _backoff(self, attempt: int) -> None:
        if self.sleeper is None or not self.retry.backoff_seconds:
            return
        idx = min(attempt, len(self.retry.backoff_seconds) - 1)
        self.sleeper(self.retry.backoff_seconds[idx])

    def _parse(self, raw: bytes) -> str:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise SeatError(
                f"seat {self.seat_id}: {self.profile.name} returned "
                f"{len(raw)} bytes that are not JSON"
            # from None: chaining prints the decode error, which quotes the
            # response body. A vendor error body can echo the request.
            ) from None
        if not isinstance(payload, dict):
            raise SeatError(
                f"seat {self.seat_id}: expected a JSON object, got "
                f"{type(payload).__name__}"
            )
        try:
            text = self.profile.extract_text(payload)
        except Exception as exc:  # noqa: BLE001 - a raising extractor fails closed
            raise SeatError(
                scrub(f"seat {self.seat_id}: extract_text raised "
                      f"{type(exc).__name__}: {exc}", self.seat.credential())
            ) from None

        if text is None:
            # SAY WHY THE TEXT IS MISSING, not just that it is.
            #
            # "reply contained no text at the configured path" reads as a
            # broken text_path, so the operator goes looking at their profile.
            # The commonest cause is nothing of the sort: a reasoning model
            # given a long prompt and a small cap spends the whole budget
            # thinking and is cut off before it writes anything. Both look
            # identical from here, and only one is fixed by editing a config
            # file. A live canary lost its closer to exactly this and the
            # message pointed at the wrong thing.
            stop = _stop_reason(payload)
            if stop in ("max_tokens", "length", "MAX_TOKENS"):
                raise SeatError(
                    f"seat {self.seat_id}: {self.profile.name} was cut off at "
                    f"the {self.max_tokens}-token cap before writing any "
                    f"reply (stop reason {stop!r}). On a reasoning model the "
                    f"thinking counts against that cap, so a long prompt can "
                    f"consume all of it. Raise max_tokens for this seat; the "
                    f"text path is not the problem."
                )
            raise SeatError(
                f"seat {self.seat_id}: {self.profile.name} reply contained no "
                f"text at the configured path"
                + (f" (stop reason {stop!r})" if stop else "")
                + f". Top-level keys: {sorted(payload)[:8]}"
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
