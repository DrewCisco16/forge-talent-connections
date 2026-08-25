"""
doi_resolver.py
===============
A real DOI resolver for CitationResolutionGate.

WHY THIS FILE EXISTS. The citation gate takes a `resolver_fn` and the codebase
shipped none, so every citation claim escalated. CONNECTING.md is explicit that
the admissibility gate answers "is this the right KIND of source" and never
"does this source EXIST" -- alone it accepted the invented DOI
10.1038/s41586-000-0000-0. This supplies the half that was missing.

WHAT IT COSTS. Nothing. Crossref and doi.org are free public services and take
no credential. No model is called and no vendor is billed.

FAIL CLOSED, ALWAYS. Every path that is not a confirmed record returns False:
a 404, a timeout, a DNS failure, a malformed identifier, a redirect to a
landing page that does not confirm registration. SOP 8.3 names a permissive
resolver -- one that returns True by default -- as the single most common way
this build fails, because it silently converts a verified system back into an
unverified ensemble while every dashboard still reads green. probe_resolver()
in the orchestrator exists to catch exactly that, and this module is written to
pass it for the right reason rather than by accident.

A NOTE ON WHAT "RESOLVED" MEANS. Confirmed here means the identifier is
REGISTERED and its record is retrievable. It does not mean the work says what
the claim says it says, and no network call can establish that. A resolved DOI
rules out fabrication, not misrepresentation.
"""
from __future__ import annotations

import ipaddress
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

CROSSREF_API = "https://api.crossref.org/works/"
DOI_ORG = "https://doi.org/"

_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")

USER_AGENT = (
    "AdjudicationFive/1.0 (adjudication panel; mailto:noreply@example.com)"
)
"""Crossref asks API users to identify themselves and gives politely-identified
callers a faster pool. Replace the mailto with a real address you monitor if
you run this at volume -- Crossref may throttle anonymous traffic."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every 3xx on a model-supplied URL.

    A public https endpoint that redirects to loopback, or downgrades to
    plaintext http, is the standard way past an origin check performed only on
    the first hop.
    """

    def redirect_request(  # noqa: PLR0913, PLR0917 - urllib's signature
            self, req: object, fp: object, code: int, msg: str,
            headers: object, newurl: str) -> None:
        raise urllib.error.HTTPError(
            getattr(req, "full_url", ""), code,
            f"refusing a {code} redirect to {newurl!r}: a citation URL came "
            f"from a model and every hop after the first is unchecked",
            headers, fp,  # type: ignore[arg-type]
        )


def _is_public_host(host: str) -> bool:
    """False for anything not on the public internet, and for the unresolvable."""
    if not host:
        return False
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


class ResolverBlocked(RuntimeError):
    """The lookup could not be performed. NOT evidence the DOI is absent.

    Returning bare False for a DNS failure, a TLS error, or a timeout made an
    offline machine turn every honest DOI into a FAIL, a conduct finding
    against the seat that cited it, and an EARNED elimination. Absence of a
    network is not absence of a paper.
    """


class DoiResolver:
    """Resolves DOIs against Crossref, falling back to doi.org.

    Results are cached for the life of the object because a panel of five
    seats across five passes will propose the same DOI many times, and
    re-fetching it would be slow, rude to a free service, and would make the
    run's duration depend on how often seats happened to repeat themselves.
    A cached False is as durable as a cached True: an identifier that did not
    resolve at the start of a run has not started existing by the end of it.
    """

    def __init__(self, timeout_s: float = 12.0, allow_url_fallback: bool = True):
        self.timeout_s = timeout_s
        self.allow_url_fallback = allow_url_fallback
        self.cache: dict[str, bool] = {}
        self.calls = 0

    # -- the callable the gate takes ---------------------------------------
    def __call__(self, identifier: str) -> bool:
        ident = (identifier or "").strip()
        if not ident:
            return False
        if ident in self.cache:
            return self.cache[ident]
        result = self._resolve(ident)
        self.cache[ident] = result
        return result

    # -- internals ---------------------------------------------------------
    def _resolve(self, ident: str) -> bool:
        doi = self._as_doi(ident)
        if doi is not None:
            try:
                if self._crossref(doi):
                    return True
            except ResolverBlocked:
                # Crossref unreachable. Try doi.org before giving up, but if
                # that is also unreachable the caller learns BLOCKED, not
                # "absent".
                return self._doi_org(doi)
            return self._doi_org(doi)
        if ident.startswith(("http://", "https://")) and self.allow_url_fallback:
            return self._url_head(ident)
        return False

    @staticmethod
    def _as_doi(ident: str) -> str | None:
        """Pull a bare DOI out of a DOI, a doi.org URL, or a doi: prefix."""
        s = ident.strip()
        for prefix in ("doi:", "DOI:"):
            if s.startswith(prefix):
                s = s[len(prefix):].strip()
        for host in ("https://doi.org/", "http://doi.org/",
                     "https://dx.doi.org/", "http://dx.doi.org/"):
            if s.lower().startswith(host):
                s = s[len(host):]
                break
        return s if _DOI_RE.match(s) else None

    def _get(self, url: str, method: str = "GET") -> tuple[int, bytes]:
        self.calls += 1
        req = urllib.request.Request(
            url, method=method,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        # https is enforced by the constants above; nosec on the next line
        # because bandit reads everything after it as test ids.
        with urllib.request.urlopen(req, timeout=self.timeout_s) as r:  # nosec B310
            return r.status, r.read()

    def _get_untrusted(self, url: str, method: str = "HEAD") -> tuple[int, bytes]:
        """Fetch a URL that came from a MODEL, with redirects refused.

        Crossref and doi.org are fixed constants in this file and are fetched
        by _get. A citation URL is model-controlled, and _get was being used
        for it too -- which followed redirects. A public https endpoint that
        302s to http://127.0.0.1 therefore reached loopback: the origin check
        applied to the first hop only, and every later hop was unchecked. That
        would let a model's warrant direct a fetch at a host that is not on the
        public internet.

        Redirects are refused rather than revalidated per hop. A citation URL
        that redirects is weak evidence anyway, and refusing is the version
        with no gap in it.
        """
        parts = urllib.parse.urlparse(url)
        if parts.scheme != "https":
            raise ResolverBlocked(f"refusing a non-https citation URL: {url!r}")
        if not _is_public_host(parts.hostname or ""):
            raise ResolverBlocked(
                f"refusing {parts.hostname!r}: not a public address. This URL "
                f"came from a model, and fetching a private or loopback host "
                f"on its say-so would let it read whatever this machine can reach."
            )
        self.calls += 1
        req = urllib.request.Request(
            url, method=method,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(req, timeout=self.timeout_s) as r:  # nosec B310
            return r.status, r.read(0)

    def _crossref(self, doi: str) -> bool:
        """Authoritative for registered DOIs. A 200 whose payload carries the
        DOI back is a confirmed record; anything else is not."""
        url = CROSSREF_API + urllib.parse.quote(doi, safe="")
        try:
            status, raw = self._get(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False      # authoritative: not registered
            raise ResolverBlocked(f"Crossref returned HTTP {exc.code}") from exc
        except Exception as exc:
            raise ResolverBlocked(
                f"could not reach Crossref: {type(exc).__name__}") from exc
        if status != 200:
            return False
        try:
            payload = json.loads(raw)
        except Exception:         # noqa: BLE001 - unparseable is not confirmed
            return False
        msg = payload.get("message")
        if not isinstance(msg, dict):
            return False
        got = str(msg.get("DOI", "")).lower()
        return got == doi.lower()

    def _doi_org(self, doi: str) -> bool:
        """Second opinion for DOIs registered outside Crossref (DataCite and
        friends). doi.org redirects a registered DOI and 404s an unregistered
        one, so the status alone is the answer."""
        try:
            status, _ = self._get(DOI_ORG + urllib.parse.quote(doi, safe=""),
                                  method="HEAD")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False
            raise ResolverBlocked(f"doi.org returned HTTP {exc.code}") from exc
        except Exception as exc:
            raise ResolverBlocked(
                f"could not reach doi.org: {type(exc).__name__}") from exc
        return 200 <= status < 400

    def _url_head(self, url: str) -> bool:
        """A plain URL is weaker evidence than a DOI and is treated as such:
        it confirms only that something is served there today. Pass
        allow_url_fallback=False to refuse URLs outright.

        A TRANSPORT FAILURE RAISES ResolverBlocked; it does not return False.
        Returning False here made a connection error indistinguishable from
        "this source does not exist", and CitationResolutionGate turns False
        into FAIL -- so an outage produced a refuted citation, a conduct
        finding against the seat that cited it, and an EARNED elimination of
        whatever candidate rested on it. The bare DOI paths already made this
        distinction; the URL path did not.
        """
        if not url.startswith("https://"):
            return False          # never confirm a plaintext source
        try:
            status, _ = self._get_untrusted(url, method="HEAD")
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 410):
                return False      # authoritative: nothing is served there
            raise ResolverBlocked(
                f"{url} returned HTTP {exc.code}; the check did not happen"
            ) from None
        except Exception as exc:  # noqa: BLE001
            raise ResolverBlocked(
                f"could not reach {url}: {type(exc).__name__}"
            ) from None
        if 500 <= status < 600 or status in (401, 403, 429):
            raise ResolverBlocked(f"{url} returned HTTP {status}")
        return 200 <= status < 400


def crossref_record(doi: str, timeout_s: float = 12.0) -> dict[str, Any] | None:
    """The Crossref record for a DOI, or None if it could not be retrieved.

    Separate from resolution because they answer different questions.
    Resolution asks whether the identifier is registered; this asks what it is
    registered TO, which is the only way to catch a real DOI attached to a
    paper that is not the one cited.
    """
    r = DoiResolver(timeout_s=timeout_s)
    bare = r._as_doi(doi)
    if bare is None:
        return None
    try:
        status, raw = r._get(CROSSREF_API + urllib.parse.quote(bare, safe=""))
    except Exception:  # noqa: BLE001 - unreachable is not a finding
        return None
    if status != 200:
        return None
    try:
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001
        return None
    msg = payload.get("message")
    return msg if isinstance(msg, dict) else None


def build_resolver(timeout_s: float = 12.0,
                   allow_url_fallback: bool = True) -> Callable[[str], bool]:
    """The resolver as a plain callable, for CitationResolutionGate."""
    return DoiResolver(timeout_s=timeout_s, allow_url_fallback=allow_url_fallback)


if __name__ == "__main__":  # pragma: no cover - operator smoke test
    import sys

    from adjudication_orchestrator import probe_resolver

    r = DoiResolver()
    probe = probe_resolver(r)
    print(f"probe: {probe.status.value.upper()} -- {probe.detail}")
    for ident in sys.argv[1:]:
        print(f"  {ident} -> {'RESOLVED' if r(ident) else 'DID NOT RESOLVE'}")
    print(f"network calls made: {r.calls}")
    sys.exit(0 if probe.status.value == "pass" else 1)
