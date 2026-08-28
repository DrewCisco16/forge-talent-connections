# Registry-first scholarly discovery + Crossref verification.
# Runs on a GitHub runner because the dev container's egress proxy blocks
# scholarly hosts. Discovery via OpenAlex; every candidate is then resolved
# against Crossref (api.crossref.org/works/{doi}) so nothing unverified is
# ever cited. Output goes to the job log only.
import json
import time
import urllib.parse
import urllib.request

MAILTO = "research@example.org"

QUERIES = [
    # (label, openalex fulltext search)
    ("gamif_genz", "gamification rewards motivation Generation Z"),
    ("tpb_apps", "theory of planned behavior mobile application intention"),
    ("referral", "referral program incentive customer acquisition"),
    ("loyalty_exp", "loyalty program experiential rewards young consumers"),
    ("leaderboard", "leaderboard competition motivation gamification"),
    ("points_engage", "points reward system engagement retention app"),
    ("lottery_incent", "lottery incentive uncertain reward motivation"),
    ("fairness_contest", "perceived fairness contest reward participation"),
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": f"mailto:{MAILTO}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def openalex(label, query):
    url = (
        "https://api.openalex.org/works?search="
        + urllib.parse.quote(query)
        + "&filter=from_publication_date:2024-01-01,type:article,is_retracted:false"
        + "&sort=cited_by_count:desc&per-page=12&mailto=" + MAILTO
    )
    try:
        data = get(url)
    except Exception as e:  # noqa: BLE001
        print(f"OPENALEX-FAIL {label}: {e}")
        return []
    out = []
    for w in data.get("results", []):
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        if not doi:
            continue
        out.append(
            {
                "q": label,
                "doi": doi,
                "title": w.get("title"),
                "year": w.get("publication_year"),
                "cited": w.get("cited_by_count"),
                "venue": (w.get("primary_location") or {})
                .get("source", {})
                .get("display_name")
                if (w.get("primary_location") or {}).get("source")
                else None,
            }
        )
    return out


def crossref(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    try:
        m = get(url)["message"]
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": str(e)}
    issued = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
    return {
        "ok": True,
        "type": m.get("type"),
        "title": (m.get("title") or [None])[0],
        "container": (m.get("container-title") or [None])[0],
        "year": issued,
        "volume": m.get("volume"),
        "issue": m.get("issue"),
        "pages": m.get("page"),
        "authors": [
            f"{a.get('family', '?')}, {(a.get('given') or '?')[:1]}."
            for a in m.get("author", [])
        ],
        "update_to": m.get("update-to"),
        "retracted": any(
            u.get("type") == "retraction" for u in m.get("update-to", []) or []
        ),
    }


seen = set()
for label, query in QUERIES:
    for cand in openalex(label, query):
        if cand["doi"] in seen:
            continue
        seen.add(cand["doi"])
        time.sleep(0.4)
        v = crossref(cand["doi"])
        print("RECORD " + json.dumps({"openalex": cand, "crossref": v}))
print(f"DONE candidates={len(seen)}")
