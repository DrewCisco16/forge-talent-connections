"""
quote_gate.py
=============
Does the quoted string actually appear at the URL it is attributed to?

WHY THIS GATE EXISTS. Every other check here reads a claim against its own
warrant: recompute the arithmetic, resolve the DOI, parse the JSON. None of
them can see the failure where a quote supports its answer perfectly and is
simply not in the source. That failure produced, in a three-run verification
exercise on this project, a confident and well-organised run that asserted a
parameter table exists on a page where it does not -- and would have reversed
a correct conclusion, because it looked better-sourced than the truth. It was
caught only because the operator had independently read the page. This gate
removes the dependence on that luck.

The check needs no model judgment at any point. "String Q appears at URL U"
is a substring match, which is why it belongs on the mechanical side of the
architecture rather than in a reviewer's reading.

BLOCKED IS NOT FAILED, AND THE DISTINCTION IS THE WHOLE POINT. A paywall, a
rate limit, a timeout, or a robots exclusion means the check did not happen.
Recording that as FAILED would let a firewall masquerade as a fabrication --
and, through the cascade below, let an outage eliminate a true candidate.
"""
from __future__ import annotations

import html
import re
import unicodedata
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping

from adjudication_orchestrator import Claim, ClaimKind, GateResult, GateStatus

USER_AGENT = (
    "AdjudicationFive/1.0 (adjudication panel; quote verification)"
)

MIN_TEXT_CHARS = 400
"""Below this, treat the fetch as BLOCKED rather than as a failed match.

A page that renders its text with JavaScript, or serves a stub to a
non-browser client, yields a nearly empty document. Matching against that
produces a false FAILED, which through the cascade would eliminate a
candidate on the strength of a client-side rendering quirk. Too little text
means the check did not happen.
"""

_TAG = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_ANYTAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

# ruff RUF001 flags every entry below as an "ambiguous unicode character".
# They are the entire point: this table exists to fold exactly those glyphs to
# their ASCII equivalents, so a quote typed with a smart apostrophe still
# matches a page that uses a straight one. Silencing per-line would bury the
# reason in ten identical noqa comments.
_PUNCT_MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",  # noqa: RUF001
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "–": "-", "—": "-", "―": "-", "−": "-",  # noqa: RUF001
    " ": " ", " ": " ", " ": " ", " ": " ",  # noqa: RUF001
    "​": "", "…": "...",
}


def normalize(text: str) -> str:
    """Identical treatment for the page and the asserted quote.

    Collapses whitespace, folds smart quotation marks and dashes to ASCII,
    and removes zero-width characters. Case is preserved here; the caller
    retries case-folded and records that it had to.
    """
    text = unicodedata.normalize("NFKC", text)
    for src, dst in _PUNCT_MAP.items():
        text = text.replace(src, dst)
    return _WS.sub(" ", text).strip()


def extract_text(raw: bytes, content_type: str) -> str:
    """Page bytes to matchable text. HTML is stripped; anything else is decoded."""
    body = raw.decode("utf-8", errors="replace")
    if "html" in content_type.lower() or body.lstrip()[:1] == "<":
        body = _TAG.sub(" ", body)
        body = _ANYTAG.sub(" ", body)
        body = html.unescape(body)
    return normalize(body)


class QuoteVerificationGate:
    """Confirms an asserted quote is present at the URL it cites."""

    name = "quote_verification"

    def __init__(self, timeout_s: float = 20.0,
                 fetcher: Callable[[str], tuple[int, str]] | None = None,
                 min_text_chars: int = MIN_TEXT_CHARS):
        # fetcher is injectable so the whole gate is testable without a socket,
        # the same way HttpSeat takes its transport.
        self.timeout_s = timeout_s
        self.fetcher = fetcher or self._fetch
        self.min_text_chars = min_text_chars
        self.cache: dict[str, tuple[int, str]] = {}

    # -- warrant shape ------------------------------------------------------
    @staticmethod
    def parse_warrant(warrant: str | None) -> tuple[str, str] | None:
        """warrant is "<url> :: <quote>". Returns (url, quote) or None."""
        if not warrant or "::" not in warrant:
            return None
        url, _, quote = warrant.partition("::")
        url, quote = url.strip(), quote.strip()
        if not url.startswith("https://") or not quote:
            return None
        return url, quote

    def applies_to(self, claim: Claim) -> bool:
        return (claim.kind is ClaimKind.QUOTE_VERIFICATION
                and self.parse_warrant(claim.warrant) is not None)

    # -- the fetch ----------------------------------------------------------
    def _fetch(self, url: str) -> tuple[int, str]:
        req = urllib.request.Request(
            url, method="GET",
            headers={"User-Agent": USER_AGENT,
                     "Accept": "text/html,application/xhtml+xml,text/plain,*/*"},
        )
        # https is enforced in parse_warrant; nosec on the next line because
        # bandit reads everything after it as test ids.
        with urllib.request.urlopen(req, timeout=self.timeout_s) as r:  # nosec B310
            ctype = r.headers.get("Content-Type", "")
            return r.status, extract_text(r.read(), ctype)

    def _get(self, url: str) -> tuple[int, str]:
        if url in self.cache:
            return self.cache[url]
        try:
            got = self.fetcher(url)
        except urllib.error.HTTPError as exc:
            got = (exc.code, "")
        except Exception as exc:  # noqa: BLE001 - DNS, TLS, timeout: not a finding
            got = (-1, f"transport: {type(exc).__name__}")
        self.cache[url] = got
        return got

    # -- the check ----------------------------------------------------------
    def check(self, claim: Claim) -> GateResult:
        parsed = self.parse_warrant(claim.warrant)
        if parsed is None:  # unreachable via _route; guard, not cast
            return GateResult(self.name, GateStatus.INAPPLICABLE,
                              "warrant is not '<https url> :: <quote>'")
        url, quote = parsed
        status, text = self._get(url)

        if status == -1:
            return GateResult(self.name, GateStatus.BLOCKED,
                              f"could not reach {url} ({text})")
        if status == 404:
            # The cited source is not there at all. That is a statement about
            # the citation, not about the network, so it is a finding.
            return GateResult(self.name, GateStatus.FAIL,
                              f"SOURCE_NOT_RETRIEVABLE: 404 at {url}")
        if status in (401, 403, 429) or 500 <= status < 600:
            return GateResult(self.name, GateStatus.BLOCKED,
                              f"HTTP {status} at {url} -- check not performed")
        if status < 200 or status >= 300:
            return GateResult(self.name, GateStatus.BLOCKED,
                              f"HTTP {status} at {url}")
        if len(text) < self.min_text_chars:
            return GateResult(
                self.name, GateStatus.BLOCKED,
                f"only {len(text)} chars of text at {url}; the page probably "
                f"renders client-side, so a non-match would prove nothing",
            )

        needle = normalize(quote)
        if needle in text:
            return GateResult(self.name, GateStatus.PASS,
                              f"quote present at {url}")
        if needle.casefold() in text.casefold():
            return GateResult(self.name, GateStatus.PASS,
                              f"quote present at {url} (case-folded match)")
        return GateResult(
            self.name, GateStatus.FAIL,
            f"QUOTE_NOT_IN_SOURCE: {len(text):,} chars fetched from {url} and "
            f"the asserted string is not among them",
        )


def cascade_unsupported(
    verdicts: Mapping[str, object], claims_by_id: Mapping[str, Claim]
) -> dict[str, str]:
    """Claims whose supporting quote was shown not to exist.

    Returns {claim_id: why}. A quote_verification claim that FAILED does not
    merely drop itself: every claim it was offered in support of has lost its
    stated evidentiary basis and must leave the working answer too.

    A BLOCKED quote cascades nothing. The check did not happen, so the
    supported claim is exactly as well or badly evidenced as it was before.
    """
    out: dict[str, str] = {}
    for cid, v in verdicts.items():
        claim = claims_by_id.get(cid)
        if claim is None or claim.kind is not ClaimKind.QUOTE_VERIFICATION:
            continue
        if getattr(getattr(v, "status", None), "value", None) != "fail":
            continue
        for supported in claim.supports:
            out[supported] = (
                f"UNSUPPORTED: its supporting quote ({cid}) was checked against "
                f"the source and is not there -- {getattr(v, 'detail', '')}"
            )
    return out
