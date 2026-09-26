"""METHOD document: claims about the operator's project documents, read by Dispatch from an allowlisted folder."""
import os
import re

from .sources import source_line


def list_documents(documents_dir: str | None) -> list:
    if not documents_dir or not os.path.isdir(documents_dir):
        return []
    return sorted(f for f in os.listdir(documents_dir) if os.path.isfile(os.path.join(documents_dir, f)) and not f.startswith(".")
                  and f != "dois.json")  # dois.json is the offline resolver's fixture, not a project document


def read_document(documents_dir: str, name: str) -> str | None:
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    p = os.path.join(documents_dir, name)
    if not os.path.isfile(p):
        return None
    with open(p, "rb") as f:
        return f.read().decode("utf-8", "replace")


def check_document(claim, documents_dir: str | None, now: str) -> dict:
    docs = list_documents(documents_dir)
    name = claim.document
    if not name:
        for d in docs:  # a claim naming the document by its stem
            if d.rsplit(".", 1)[0].lower() in claim.text.lower():
                name = d
                break
    if not docs or not name:
        return {"result": "NOT TESTABLE", "retrieved": "", "settle": "name the project document (file name) and quote the passage",
                "source": source_line("project document", "C", bool(claim.quote), "UNVERIFIED", "no document named", now), "action": "no document named"}
    text = read_document(documents_dir, name)
    action = f"read {name}"
    if text is None:
        return {"result": "BLOCKED", "retrieved": "", "settle": f"{name} is not in the project documents; supply it",
                "source": source_line("project document", "C", bool(claim.quote), "UNVERIFIED", f"{name} missing", now), "action": action}
    if not claim.quote:
        return {"result": "NOT TESTABLE", "retrieved": "", "settle": f"quote the passage of {name} the claim rests on",
                "source": source_line("project document", "B", False, "PARTIAL", f"{name} present, no quote", now), "action": action}
    flat = re.sub(r"\s+", " ", text.lower())
    if re.sub(r"\s+", " ", claim.quote.lower()) in flat:
        idx = flat.find(re.sub(r"\s+", " ", claim.quote.lower()))
        line_no = text.lower()[: text.lower().find(claim.quote.lower().split()[0])].count("\n") + 1 if claim.quote.split() else 0
        return {"result": "PASSED", "retrieved": f'"{claim.quote}" ({name}, offset {idx}, about line {line_no})', "settle": "",
                "source": source_line("project document", "A", True, "SUPPORTED", f"{name}", now), "action": action}
    return {"result": "INCONCLUSIVE", "retrieved": f"{name} read; the quoted words are not in it", "settle": f"point to the exact passage of {name}, or correct the quote",
            "source": source_line("project document", "B", True, "UNSUPPORTED", f"{name}, quote absent", now), "action": action}
