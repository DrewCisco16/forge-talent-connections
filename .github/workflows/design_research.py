# Registry-first scholarly discovery + Crossref verification, design pass.
# Title/abstract-scoped queries on motion design, typography, aesthetics,
# onboarding, and Gen Z UX. Runs on a GitHub runner because the dev
# container's egress proxy blocks scholarly hosts.
import json
import time
import urllib.parse
import urllib.request

MAILTO = "research@example.org"

QUERIES = [
    ("aest_usab", "interface aesthetics perceived usability"),
    ("first_impr", "first impressions visual appeal website users"),
    ("load_anim", "loading animation perceived waiting time"),
    ("anim_feedback", "animated feedback interface user perception"),
    ("font_read", "font size reading performance smartphone screen"),
    ("legibility", "typeface legibility digital reading"),
    ("darkmode2", "dark mode light mode reading performance"),
    ("visual_complex", "visual complexity webpage user preference"),
    ("eye_ui", "eye tracking user interface attention design"),
    ("aesth_trust", "aesthetics trust perception e-commerce interface"),
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": f"mailto:{MAILTO}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def openalex(label, query):
    url = (
        "https://api.openalex.org/works?"
        + "filter=title_and_abstract.search:"
        + urllib.parse.quote(query)
        + ",from_publication_date:2024-01-01,type:article,is_retracted:false"
        + "&sort=cited_by_count:desc&per-page=8&mailto=" + MAILTO
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
        out.append({
            "q": label,
            "doi": doi,
            "title": w.get("title"),
            "year": w.get("publication_year"),
            "cited": w.get("cited_by_count"),
        })
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
