#!/usr/bin/env python3
"""Crossref verification pass for the category-realignment sources (DOIs
taken verbatim from OpenAlex registry records). Read-only; prints to stdout."""
import json
import time
import urllib.parse
import urllib.request

DOIS = [
    "10.1038/s41598-025-10385-4",
    "10.3390/educsci14060617",
    "10.1016/j.heliyon.2024.e39988",
    "10.1038/s44271-024-00112-6",
    "10.1108/jpbm-02-2023-4373",
    "10.1016/j.chb.2024.108544",
    "10.1145/3637347",
    "10.1002/cb.2482",
    "10.1108/cdi-02-2024-0073",
    "10.1002/berj.4050",
    "10.1002/mar.22129",
    "10.3389/frvir.2024.1305758",
    "10.1186/s41239-024-00501-1",
    "10.1080/03075079.2024.2334837",
    "10.1080/03075079.2024.2326956",
    "10.1186/s40594-024-00472-9",
    "10.1187/cbe.23-04-0059",
    "10.1002/job.2898",
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "forge-analysis-lookup"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


for doi in DOIS:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    try:
        m = fetch(url)["message"]
    except Exception as e:  # noqa: BLE001
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
