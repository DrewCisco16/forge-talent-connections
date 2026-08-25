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

import codecs
import html
import http.client
import ipaddress
import re
import socket
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

from adjudication_orchestrator import Claim, ClaimKind, GateResult, GateStatus

USER_AGENT = (
    "AdjudicationFive/1.0 (adjudication panel; quote verification)"
)

MAX_BYTES = 4_000_000
"""Cap on what a fetch will read.

The quote URL comes from a model. An unbounded read lets a hostile or merely
broken endpoint stream until memory runs out, which stops the whole run.
"""


def _resolve_public(host: str) -> str | None:
    """Resolve once and return the address, or None if any answer is private.

    Returning the ADDRESS matters: checking the hostname and then letting
    urllib resolve it again independently is a time-of-check/time-of-use gap.
    A name whose DNS answer changes between the two lookups -- classic DNS
    rebinding -- passes the check and then connects somewhere else. The caller
    connects to exactly the address that was approved.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:  # noqa: BLE001 - unresolvable is not public
        return None
    first: str | None = None
    for info in infos:
        addr = info[4][0]
        if not isinstance(addr, str):
            return None
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return None
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return None
        if first is None:
            first = addr
    return first


def _is_public(host: str) -> bool:
    """Resolve the host and refuse anything not on the public internet.

    The URL in a quote_verification warrant is model-controlled, so the gate
    is a server-side request forgery primitive unless this exists: a model
    could point it at 127.0.0.1, at 169.254.169.254, or at anything reachable
    from this machine but not from the internet, and the gate would fetch it
    and report on the contents.

    Resolution happens here rather than trusting the hostname, because
    a name under an attacker's control can point anywhere.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:  # noqa: BLE001 - unresolvable is not public
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return False
    return True


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects. A public https URL that redirects to loopback or to
    plaintext is the standard way past an origin check done only on hop one."""

    def redirect_request(self, req: object, fp: object, code: int, msg: str,
                         headers: object, newurl: str) -> None:
        raise urllib.error.HTTPError(
            getattr(req, "full_url", ""), code,
            f"refusing a {code} redirect to {newurl!r}", headers, fp,  # type: ignore[arg-type]
        )


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    """Dial one approved IP while validating the certificate for the hostname.

    Resolving, checking the address, and then letting urllib resolve the name
    again is a time-of-check/time-of-use gap -- a name whose DNS answer changes
    between the two lookups passes the check and connects elsewhere. Rewriting
    the URL to the IP closes that and breaks TLS, because the certificate is
    then validated against the address. This does both correctly: the socket
    goes to the checked address, and server_hostname carries the real name so
    SNI and hostname verification see it.
    """

    def __init__(self, addr: str) -> None:
        super().__init__()
        self._addr = addr

    def https_open(self, req: Any) -> Any:
        addr = self._addr

        class _Conn(http.client.HTTPSConnection):
            def connect(self) -> None:
                self.sock = socket.create_connection(
                    (addr, self.port or 443), self.timeout)
                # _context is HTTPSConnection's own ssl context. Typed as
                # private, but it is the only handle on the verification
                # settings urllib built, and rebuilding one here would silently
                # drop the caller's CA configuration.
                ctx = self._context  # type: ignore[attr-defined]
                self.sock = ctx.wrap_socket(self.sock, server_hostname=self.host)

        return self.do_open(_Conn, req)


_INTERSTITIAL = (
    "subscribe to continue", "subscription required", "create a free account",
    "sign in to read", "log in to continue", "you have reached your",
    "enable javascript", "verify you are human", "checking your browser",
    "access denied", "please accept cookies", "cookie consent",
)


def _looks_like_an_interstitial(text: str) -> bool:
    """A wall served with HTTP 200 instead of 401 or 403.

    A soft paywall, consent gate, or bot check returns a normal status and a
    page that is not the article. Matching the quote against THAT and calling
    the non-match a FAIL turns a subscription into a fabrication finding, and
    through the cascade eliminates a candidate that cited a real source
    correctly.
    """
    low = (text or "").casefold()[:4000]
    return any(marker in low for marker in _INTERSTITIAL)


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


_CHARSET = re.compile(r"charset\s*=\s*[\"']?([\w.-]+)", re.IGNORECASE)


def extract_text(raw: bytes, content_type: str) -> str:
    """Page bytes to matchable text. HTML is stripped; anything else is decoded.

    THE DECLARED CHARSET IS HONOURED. Decoding everything as UTF-8 with
    errors="replace" turned every non-ASCII character on an ISO-8859-1 page
    into U+FFFD, so a quote containing "Cafe" with an accent could not match
    a page that genuinely contained it -- and the gate reported FAIL, which
    through the cascade eliminates a candidate whose quote was real and
    correctly transcribed.
    """
    encoding = "utf-8"
    m = _CHARSET.search(content_type or "")
    if m:
        candidate = m.group(1).strip().lower()
        try:
            # codecs.lookup, not a trial decode of b"": decoding empty bytes
            # succeeds for names Python cannot actually resolve, so the probe
            # accepted "x-not-a-charset" and the real decode then raised
            # LookupError out of the gate.
            codecs.lookup(candidate)
            encoding = candidate
        except LookupError:
            encoding = "utf-8"
    body = raw.decode(encoding, errors="replace")
    if "html" in content_type.lower() or body.lstrip()[:1] == "<":
        body = _TAG.sub(" ", body)
        body = _ANYTAG.sub(" ", body)
        body = html.unescape(body)
    return normalize(body)


class QuoteVerificationGate:
    """Confirms an asserted quote is present at the URL it cites."""

    name = "quote_verification"

    def __init__(self, timeout_s: float = 20.0,
                 fetcher: Callable[..., Any] | None = None,
                 min_text_chars: int = MIN_TEXT_CHARS):
        # fetcher is injectable so the whole gate is testable without a socket,
        # the same way HttpSeat takes its transport.
        self.timeout_s = timeout_s
        self.fetcher = fetcher or self._fetch
        self.min_text_chars = min_text_chars
        self.cache: dict[str, tuple[int, str, bool]] = {}

    # -- warrant shape ------------------------------------------------------
    MIN_QUOTE_CHARS = 12
    """Shortest asserted quote this gate will rule on.

    A quote of two or three characters matches by accident on any page of
    ordinary length, so a PASS on one is not evidence. Below this the gate has
    nothing to say and the claim escalates to a person, which is the honest
    outcome -- not a PASS, and not a FAIL either.
    """

    @classmethod
    def parse_warrant(cls, warrant: str | None) -> tuple[str, str] | None:
        """warrant is "<url> :: <quote>". Returns (url, quote) or None.

        THE QUOTE IS VALIDATED AFTER NORMALISATION, NOT BEFORE.
        Emptiness was checked on the RAW string, and Python treats the empty
        string as a substring of everything. A warrant whose quote was a
        single zero-width character therefore passed the non-empty check,
        normalised to "", and matched every page on the internet -- a PASS
        against 500 characters of entirely unrelated text, verified.
        """
        if not warrant or "::" not in warrant:
            return None
        url, _, quote = warrant.partition("::")
        url, quote = url.strip(), normalize(quote)
        if not url.startswith("https://"):
            return None
        if len(quote) < cls.MIN_QUOTE_CHARS:
            return None
        return url, quote

    def applies_to(self, claim: Claim) -> bool:
        return (claim.kind is ClaimKind.QUOTE_VERIFICATION
                and self.parse_warrant(claim.warrant) is not None)

    # -- the fetch ----------------------------------------------------------
    def _fetch(self, url: str) -> tuple[int, str, bool]:
        parts = urllib.parse.urlparse(url)
        host = parts.hostname or ""
        addr = _resolve_public(host)
        if addr is None:
            raise ValueError(
                f"refusing {host!r}: not a public address. This URL came from "
                f"a model, and fetching a private or loopback host on its "
                f"say-so is server-side request forgery."
            )
        # CONNECT TO THE APPROVED ADDRESS, VALIDATE THE ORIGINAL HOSTNAME.
        #
        # The previous version rewrote the URL to contain the IP and set a
        # Host header. That closed the DNS-rebinding gap and opened a worse
        # one: TLS then validated the certificate against the IP ADDRESS, so
        # every ordinary https site failed with a hostname mismatch and every
        # honest quote check came back BLOCKED. A safety control that breaks
        # the normal path gets switched off.
        #
        # _PinnedHTTPSHandler dials the checked address and passes the real
        # hostname as server_hostname, so SNI and certificate validation both
        # see the name the operator's claim actually cited.
        req = urllib.request.Request(
            url, method="GET",
            headers={"User-Agent": USER_AGENT,
                     "Accept": "text/html,application/xhtml+xml,text/plain,*/*"},
        )
        opener = urllib.request.build_opener(
            _NoRedirect, _PinnedHTTPSHandler(addr))
        with opener.open(req, timeout=self.timeout_s) as r:  # nosec B310
            ctype = r.headers.get("Content-Type", "")
            # READ ONE BYTE PAST THE CAP, so truncation is detectable. Reading
            # exactly MAX_BYTES made a page that is one byte too long
            # indistinguishable from one that fits, and a quote sitting past
            # the cap produced a confident FAIL about a source we had not
            # finished reading.
            raw = r.read(MAX_BYTES + 1)
            truncated = len(raw) > MAX_BYTES
            return r.status, extract_text(raw[:MAX_BYTES], ctype), truncated

    def _get(self, url: str) -> tuple[int, str, bool]:
        """(status, text, truncated). Injected fetchers may return a pair."""
        if url in self.cache:
            return self.cache[url]
        try:
            got = self.fetcher(url)
            if len(got) == 2:          # a test fetcher; nothing was truncated
                got = (got[0], got[1], False)
        except urllib.error.HTTPError as exc:
            got = (exc.code, "", False)
        except Exception as exc:  # noqa: BLE001 - DNS, TLS, timeout: not a finding
            got = (-1, f"transport: {type(exc).__name__}", False)
        self.cache[url] = got
        return got

    # -- the check ----------------------------------------------------------
    def check(self, claim: Claim) -> GateResult:
        parsed = self.parse_warrant(claim.warrant)
        if parsed is None:  # unreachable via _route; guard, not cast
            return GateResult(self.name, GateStatus.INAPPLICABLE,
                              "warrant is not '<https url> :: <quote>'")
        url, quote = parsed
        status, text, truncated = self._get(url)

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
        if _looks_like_an_interstitial(text):
            # A subscription wall, a consent gate, or a bot check served with
            # HTTP 200. The page we were given is not the page cited, so a
            # non-match says nothing about the quote.
            return GateResult(
                self.name, GateStatus.BLOCKED,
                f"{url} served an access interstitial rather than the article; "
                f"the check did not happen",
            )
        if truncated:
            # We stopped reading at the byte cap. The quote may sit just past
            # it, so a non-match here is a fact about our read limit, not about
            # the source.
            return GateResult(
                self.name, GateStatus.BLOCKED,
                f"{url} is larger than the {MAX_BYTES:,}-byte read cap; the "
                f"quote may lie beyond what was fetched",
            ) if normalize(quote) not in text else GateResult(
                self.name, GateStatus.PASS, f"quote present at {url}")
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
