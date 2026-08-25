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

import json
import re
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
            return self._crossref(doi) or self._doi_org(doi)
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

    def _crossref(self, doi: str) -> bool:
        """Authoritative for registered DOIs. A 200 whose payload carries the
        DOI back is a confirmed record; anything else is not."""
        url = CROSSREF_API + urllib.parse.quote(doi, safe="")
        try:
            status, raw = self._get(url)
        except urllib.error.HTTPError:
            return False          # 404 means not registered
        except Exception:         # noqa: BLE001 - timeout, DNS, TLS: fail closed
            return False
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
        except urllib.error.HTTPError:
            return False
        except Exception:         # noqa: BLE001 - fail closed
            return False
        return 200 <= status < 400

    def _url_head(self, url: str) -> bool:
        """A plain URL is weaker evidence than a DOI and is treated as such:
        it confirms only that something is served there today. Pass
        allow_url_fallback=False to refuse URLs outright."""
        if not url.startswith("https://"):
            return False          # never confirm a plaintext source
        try:
            status, _ = self._get(url, method="HEAD")
        except urllib.error.HTTPError:
            return False
        except Exception:         # noqa: BLE001 - fail closed
            return False
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
