#!/usr/bin/env python3
"""Crossref verification pass: full registered metadata + retraction flags
for the selected DOIs (all taken verbatim from OpenAlex registry records).
Read-only; prints to stdout."""
import json
import time
import urllib.parse
import urllib.request

DOIS = [
    "10.1080/03075079.2025.2516709",
    "10.3390/educsci15050525",
    "10.1007/s11528-025-01148-z",
    "10.3390/educsci14121307",
    "10.1007/s11846-024-00789-3",
    "10.1111/ijsa.12472",
    "10.1145/3696457",
    "10.1016/j.techfore.2025.124042",
    "10.1007/s10639-024-12493-6",
    "10.3390/s25113450",
    "10.1111/ejed.12862",
    "10.3390/admsci15010029",
    "10.3390/admsci15040133",
    "10.1002/job.2775",
    "10.1177/14697874241275346",
    "10.1007/s11159-024-10111-8",
    "10.1016/j.heliyon.2024.e25948",
    "10.1080/13639080.2024.2383561",
    "10.3389/fcomm.2024.1460321",
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "forge-analysis-lookup"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


for doi in DOIS:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    try:
        m = fetch(url)["message"]
    except Exception as e:  # noqa: BLE001 - report and continue
        print(json.dumps({"crossref_doi": doi, "error": str(e)}))
        time.sleep(1)
        continue
    print(json.dumps({
        "crossref_doi": doi,
        "title": (m.get("title") or [""])[0],
        "authors": [f"{a.get('family','')}, {a.get('given','')}" for a in m.get("author", [])][:12],
        "container": (m.get("container-title") or [""])[0],
        "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
        "volume": m.get("volume"),
        "issue": m.get("issue"),
        "pages": m.get("page"),
        "article_number": m.get("article-number"),
        "type": m.get("type"),
        "update_to": m.get("update-to", []),
        "publisher": m.get("publisher"),
    }, ensure_ascii=False))
    time.sleep(1)

print("===== DONE =====")
