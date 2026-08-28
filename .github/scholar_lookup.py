#!/usr/bin/env python3
"""Discovery pass for the category-realignment review: journal articles from
2024 onward on collaboration-network themes, from the OpenAlex registry.
Read-only; prints registered metadata to stdout."""
import json
import time
import urllib.parse
import urllib.request

THEMES = [
    ("pbl", "project-based learning employability skills higher education"),
    ("pbl2", "project-based learning teamwork outcomes empirical university"),
    ("community", "online community membership participation belonging"),
    ("exclusivity", "exclusive community gated membership online platform"),
    ("social-capital", "social capital online networks career development young"),
    ("avatar-identity", "avatar self-presentation digital identity virtual community"),
    ("team-formation", "team formation skill complementarity collaboration online"),
    ("peer-assessment", "peer assessment reputation systems online platform trust"),
    ("wil", "work-integrated learning graduate outcomes empirical"),
    ("inst-trust", "institutional trust technology adoption young adults platform"),
    ("eportfolio2", "e-portfolio evidence learning employability assessment"),
    ("mentoring", "peer mentoring community college students belonging outcomes"),
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "forge-analysis-lookup"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def abstract_from_inverted(inv):
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    words = [pos[i] for i in sorted(pos)]
    return " ".join(words[:110])


for theme, query in THEMES:
    print(f"===== THEME {theme} =====")
    q = urllib.parse.quote(query)
    url = ("https://api.openalex.org/works?search=" + q +
           "&filter=from_publication_date:2024-01-01,type:article"
           "&sort=relevance_score:desc&per-page=4")
    try:
        data = fetch(url)
        for w in data.get("results", []):
            authors = [a["author"]["display_name"] for a in w.get("authorships", [])][:8]
            src = (w.get("primary_location") or {}).get("source") or {}
            print(json.dumps({
                "theme": theme,
                "title": w.get("title"),
                "authors": authors,
                "year": w.get("publication_year"),
                "venue": src.get("display_name"),
                "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                "type": w.get("type"),
                "cited_by": w.get("cited_by_count"),
                "abstract": abstract_from_inverted(w.get("abstract_inverted_index")),
            }, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"theme": theme, "error": str(e)}))
    time.sleep(1)

print("===== DONE =====")
