#!/usr/bin/env python3
"""Query OpenAlex (discovery) and Crossref (verification) for journal
articles from 2024 onward on themes relevant to the product analysis, and
print the registered metadata to stdout. Read-only; no commits."""
import json
import time
import urllib.parse
import urllib.request

THEMES = [
    ("micro-credentials", "micro-credentials employability graduates higher education"),
    ("ai-career", "generative artificial intelligence career development university students"),
    ("ai-hiring-perception", "artificial intelligence hiring applicant reactions fairness perceptions"),
    ("verifiable-credentials", "verifiable credentials blockchain diploma employer verification"),
    ("genz-linkedin", "Generation Z LinkedIn professional identity social media career"),
    ("referrals", "employee referrals social capital job search networks"),
    ("endorsement-trust", "peer endorsement online reputation system trust platform"),
    ("gig-reputation", "gig economy platform reputation trust freelancer"),
    ("genz-work", "Generation Z workplace expectations mentoring early career"),
    ("eportfolio", "e-portfolio skills employability signaling employers graduates"),
    ("gamification", "gamification engagement mobile application Generation Z"),
    ("psych-safety", "psychological safety virtual team collaboration students"),
    ("privacy", "privacy concerns young adults personal data platforms"),
    ("skills-hiring", "skills-based hiring degree requirements employers"),
]

EXPLICIT_DOIS = [
    # Seen in publisher URLs during web search; verify against the registry.
    "10.1080/03075079.2025.2516709",
    "10.1007/s11528-025-01148-z",
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
    return " ".join(words[:120])


def show_openalex(theme, query):
    q = urllib.parse.quote(query)
    url = ("https://api.openalex.org/works?search=" + q +
           "&filter=from_publication_date:2024-01-01,type:article"
           "&sort=relevance_score:desc&per-page=4")
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


def show_crossref_doi(doi):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    try:
        m = fetch(url)["message"]
    except Exception as e:  # noqa: BLE001 - report and continue
        print(json.dumps({"crossref_doi": doi, "error": str(e)}))
        return
    print(json.dumps({
        "crossref_doi": doi,
        "title": (m.get("title") or [""])[0],
        "authors": [f"{a.get('family','')}, {a.get('given','')}" for a in m.get("author", [])][:10],
        "container": (m.get("container-title") or [""])[0],
        "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
        "volume": m.get("volume"),
        "issue": m.get("issue"),
        "pages": m.get("page"),
        "type": m.get("type"),
        "update_to": m.get("update-to", []),
        "publisher": m.get("publisher"),
    }, ensure_ascii=False))


for theme, query in THEMES:
    print(f"===== THEME {theme} =====")
    try:
        show_openalex(theme, query)
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"theme": theme, "error": str(e)}))
    time.sleep(1)

print("===== EXPLICIT DOI CHECKS (Crossref) =====")
for doi in EXPLICIT_DOIS:
    show_crossref_doi(doi)
    time.sleep(1)

print("===== DONE =====")
