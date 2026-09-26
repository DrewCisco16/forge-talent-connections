"""METHOD source: DOI and URL claims, resolved by Dispatch's own code on the allowed check domains
(spec 3). Support statuses map to results through SCHEMA support_to_status; a quote alone never passes."""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

ALLOWED_HOSTS = ("doi.org", "crossref.org", "openalex.org", "pubmed.ncbi.nlm.nih.gov")
SUPPORT_TO_RESULT = {"SUPPORTED": "PASSED", "CONTRADICTED": "FAILED", "NOT_FOUND": "FAILED", "PARTIAL": "INCONCLUSIVE",
                     "UNSUPPORTED": "INCONCLUSIVE", "UNVERIFIED": "BLOCKED"}
WORD = re.compile(r"[a-z]{4,}")


def host_allowed(url: str, extra_hosts=()) -> bool:
    host = urllib.parse.urlparse(url).hostname or ""
    if host.endswith(".gov"):
        return True
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS + tuple(extra_hosts))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_host = urllib.parse.urlparse(newurl).hostname or ""
        old_host = urllib.parse.urlparse(req.full_url).hostname or ""
        if new_host != old_host and not host_allowed(newurl):
            return None  # a redirect off the allowed domains is a failed fetch, never followed (never 6)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class CrossrefResolver:
    """Live resolver. resolve_doi -> ("FOUND", record) | ("NOT_FOUND", None) | ("BLOCKED", reason)."""

    def __init__(self, timeout_s=20.0, user_agent="night_agent/11.4 (mailto:operator@example.invalid)"):
        self.timeout = timeout_s
        self.opener = urllib.request.build_opener(NoRedirect())
        self.ua = user_agent

    def _get(self, url: str) -> tuple:
        req = urllib.request.Request(url, headers={"User-Agent": self.ua, "Accept": "application/json, text/html;q=0.8"})
        with self.opener.open(req, timeout=self.timeout) as r:
            return r.status, r.read(2_000_000).decode("utf-8", "replace")

    def resolve_doi(self, doi: str) -> tuple:
        url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
        try:
            status, body = self._get(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ("NOT_FOUND", None)
            return ("BLOCKED", f"crossref HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return ("BLOCKED", f"crossref unreachable: {e}")
        try:
            msg = json.loads(body)["message"]
        except (ValueError, KeyError):
            return ("BLOCKED", "crossref reply not parseable")
        rec = {"doi": doi, "title": " ".join(msg.get("title") or []), "year": _year(msg),
               "authors": [a.get("family", "") for a in msg.get("author", [])],
               "venue": " ".join(msg.get("container-title") or []), "url": msg.get("URL", ""), "text": ""}
        return ("FOUND", rec)

    def fetch_text(self, url: str) -> tuple:
        if not host_allowed(url):
            return ("BLOCKED", f"host not on the allowed check domains: {urllib.parse.urlparse(url).hostname}")
        try:
            status, body = self._get(url)
        except urllib.error.HTTPError as e:
            return ("NOT_FOUND" if e.code == 404 else "BLOCKED", f"HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return ("BLOCKED", f"unreachable: {e}")
        return ("FOUND", re.sub(r"<[^>]+>", " ", body))


def _year(msg: dict):
    for k in ("published-print", "published-online", "issued", "created"):
        parts = (msg.get(k) or {}).get("date-parts") or []
        if parts and parts[0]:
            return parts[0][0]
    return None


class FixtureResolver:
    """Offline resolver for rehearsal and CI: dois.json maps DOI -> record; unknown DOIs are NOT_FOUND."""

    def __init__(self, path: str):
        with open(path, encoding="utf-8") as f:
            self.records = json.load(f)

    def resolve_doi(self, doi: str) -> tuple:
        rec = self.records.get(doi)
        return ("FOUND", dict(rec, doi=doi)) if rec else ("NOT_FOUND", None)

    def fetch_text(self, url: str) -> tuple:
        for rec in self.records.values():
            if rec.get("url") == url:
                return ("FOUND", rec.get("text", ""))
        return ("NOT_FOUND", "no fixture for this url")


class OfflineResolver:
    """--net off: every live lookup is BLOCKED with a SETTLE line (spec 3: UNVERIFIED is BLOCKED)."""

    def resolve_doi(self, doi: str) -> tuple:
        return ("BLOCKED", "network disabled by the operator (--net off)")

    def fetch_text(self, url: str) -> tuple:
        return ("BLOCKED", "network disabled by the operator (--net off)")


def _overlap(a: str, b: str) -> float:
    wa, wb = set(WORD.findall(a.lower())), set(WORD.findall(b.lower()))
    return len(wa & wb) / len(wa) if wa else 0.0


def source_line(provenance, grade, quote_present, support, scope, now, age="ok"):
    return (f"provenance={provenance} grade={grade} quote_present={'yes' if quote_present else 'no'} support={support} "
            f'scope="{scope}" retrieved={now} retraction=unchecked age={age}')


def check_source(claim, resolver, now: str) -> dict:
    """Return dict(result, retrieved, settle, source, action) for a source claim.

    Rules (spec 3): NOT_FOUND is FAILED; a resolvable DOI whose bibliographic facts match is PASSED with grade A
    only when the claim is about the work's existence or its quoted words are on the retrieved text; a content
    claim without a matching quote is PARTIAL (INCONCLUSIVE); a field mismatch is CONTRADICTED (FAILED);
    an unreachable resolver is UNVERIFIED (BLOCKED)."""
    if not claim.doi and not claim.url:
        return {"result": "NOT TESTABLE", "retrieved": "", "settle": "supply a DOI or a URL on an allowed check domain",
                "source": source_line("unknown", "C", False, "UNVERIFIED", "no locator", now), "action": "no DOI or URL in the claim"}
    if claim.doi:
        status, rec = resolver.resolve_doi(claim.doi)
        action = f"resolved DOI {claim.doi} at crossref.org"
        if status == "NOT_FOUND":
            return {"result": "FAILED", "retrieved": f"DOI {claim.doi} not found at doi.org/crossref.org", "settle": "",
                    "source": source_line("citation", "C", bool(claim.quote), "NOT_FOUND", "the DOI does not resolve", now), "action": action}
        if status == "BLOCKED":
            return {"result": "BLOCKED", "retrieved": "", "settle": f"resolve the DOI when the resolver is reachable ({rec})",
                    "source": source_line("citation", "C", bool(claim.quote), "UNVERIFIED", "resolver unreachable", now), "action": action}
        title = rec.get("title", "")
        year = rec.get("year")
        cited_year = re.search(r"\b(19|20)\d{2}\b", claim.text)
        age = "flag" if isinstance(year, int) and year < 2024 else "ok"
        quoted_title = claim.quote and _overlap(claim.quote, title) >= 0.6
        if cited_year and year and int(cited_year.group(0)) != int(year):
            return {"result": "FAILED", "retrieved": f"record year {year} differs from the cited {cited_year.group(0)}; title: {title}", "settle": "",
                    "source": source_line("peer-reviewed or indexed record", "A", bool(claim.quote), "CONTRADICTED", "bibliographic fields", now, age), "action": action}
        if claim.quote and not quoted_title and rec.get("text") and claim.quote.lower() not in rec["text"].lower():
            return {"result": "INCONCLUSIVE", "retrieved": f"record found: {title} ({year}); the quoted words were not on the retrieved text",
                    "settle": "supply the passage and its location so the quote can be matched",
                    "source": source_line("peer-reviewed or indexed record", "B", True, "PARTIAL", "record found, quote unmatched", now, age), "action": action}
        if claim.quote and not quoted_title and not rec.get("text"):
            return {"result": "INCONCLUSIVE", "retrieved": f"record found: {title} ({year}); full text not retrievable on the allowed domains",
                    "settle": "supply the passage location, or a text on an allowed domain, so the quote can be matched",
                    "source": source_line("peer-reviewed or indexed record", "B", True, "PARTIAL", "record found, content unverified", now, age), "action": action}
        if quoted_title or not claim.quote and _overlap(claim.text, title) >= 0.25:
            return {"result": "PASSED", "retrieved": f"crossref record: {title} ({year}), {rec.get('venue', '')}".strip(), "settle": "",
                    "source": source_line("peer-reviewed or indexed record", "A", bool(claim.quote), "SUPPORTED", "the work exists as cited", now, age), "action": action}
        if claim.quote and rec.get("text") and claim.quote.lower() in rec["text"].lower():
            return {"result": "PASSED", "retrieved": f"quote present in the retrieved text of {title} ({year})", "settle": "",
                    "source": source_line("peer-reviewed or indexed record", "A", True, "SUPPORTED", "quoted passage present", now, age), "action": action}
        return {"result": "INCONCLUSIVE", "retrieved": f"record found: {title} ({year}); the claim's wording does not match the record",
                "settle": "state which words of the record support the claim",
                "source": source_line("peer-reviewed or indexed record", "B", bool(claim.quote), "PARTIAL", "record found, claim unmatched", now, age), "action": action}
    # URL only
    status, body = resolver.fetch_text(claim.url)
    action = f"fetched {claim.url}"
    if status == "BLOCKED":
        return {"result": "BLOCKED", "retrieved": "", "settle": f"fetch the page when reachable ({body})",
                "source": source_line("web page", "C", bool(claim.quote), "UNVERIFIED", "page not fetched", now), "action": action}
    if status == "NOT_FOUND":
        return {"result": "FAILED", "retrieved": f"{claim.url}: not found ({body})", "settle": "",
                "source": source_line("web page", "C", bool(claim.quote), "NOT_FOUND", "page missing", now), "action": action}
    if not claim.quote:
        return {"result": "INCONCLUSIVE", "retrieved": "page fetched; the claim quotes nothing from it", "settle": "quote the passage the claim rests on",
                "source": source_line("web page", "B", False, "PARTIAL", "page exists, no quote", now), "action": action}
    if claim.quote.lower() in re.sub(r"\s+", " ", body.lower()):
        return {"result": "PASSED", "retrieved": f'quote present on the page: "{claim.quote}"', "settle": "",
                "source": source_line("web page on an allowed domain", "A", True, "SUPPORTED", "quoted passage present", now), "action": action}
    return {"result": "INCONCLUSIVE", "retrieved": "page fetched; the quoted words were not on it", "settle": "point to the exact passage",
            "source": source_line("web page", "B", True, "UNSUPPORTED", "quote absent", now), "action": action}
