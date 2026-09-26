"""Files Dispatch builds itself: kills-all.md, metrics-summary.json, the review package, the assembled
deliverable, ledger.json and the architecture history lines (DISPATCH 3.6, 3.7, 3.8, 3.9)."""
import json
import os

from . import packets, parse


def kills_all(rf) -> str:
    """Every KILLS section of every close, in stage order, entries verbatim (spec 4.7, I10)."""
    out = []
    for st in rf.stages():
        if rf.exists(f"{st}/close.md"):
            entries = parse.kills_entries(rf.read(f"{st}/close.md"))
            out.append(f"KILLS {st}\n" + ("\n".join(entries) if entries else "none") + "\n")
    return "".join(out) or "KILLS\nnone\n"


def metrics_summary(rf, extra: dict | None = None) -> dict:
    rows = rf.read_jsonl("metrics.jsonl")
    total = {"stages": [r.get("stage") for r in rows], "model_calls": sum(int(r.get("model_calls", 0) or 0) for r in rows),
             "earned_kills": sum(int(r.get("earned_kills", 0) or 0) for r in rows),
             "deprioritized": max([int(r.get("deprioritized", 0) or 0) for r in rows] or [0]),
             "passed": sum(int(r.get("passed", 0) or 0) for r in rows), "failed": sum(int(r.get("failed", 0) or 0) for r in rows),
             "options_standing": rows[-1].get("options_standing") if rows else None,
             "estimated_cost_usd": round(sum(float(r.get("estimated_cost_usd", 0) or 0) for r in rows), 4)}
    total.update(extra or {})
    return total


def claims_with_results(rf, upto=None) -> str:
    lines = []
    for st in rf.stages():
        if upto and st > upto:
            continue
        if rf.exists(f"{st}/check.md"):
            for c in parse.parse_claims(rf.read(f"{st}/check.md")):
                lines.append(f"{c['id']} {c['result']} {c['retrieved'] or c['settle']}".strip())
    return "\n".join(lines) or "none"


def review_package(rf, last_close: str, seat_ids: list) -> str:
    """MERGED, the claims with results, OPTIONS STANDING, OPEN, CONFLICT; nothing from earlier stages, no stamps,
    no KILLS, no model names or seat ids (spec 4.6, I2; na_check ISO-2b, ISO-4, NEUT)."""
    secs = parse.sections(last_close, parse.MERGE_CLOSE)
    body = ("MERGED\n" + secs.get("MERGED", "none").strip() + "\n"
            "CLAIMS\n" + claims_with_results(rf) + "\n"
            "OPTIONS STANDING\n" + secs.get("OPTIONS STANDING", "none").strip() + "\n"
            "OPEN\n" + secs.get("OPEN", "none").strip() + "\n"
            "CONFLICT\n" + (secs.get("CONFLICT", "none").strip() or "none") + "\n")
    return packets.strip_attribution(body, seat_ids)


def assembled(deliverable: str, verifier: str) -> str:
    return deliverable + "\n" + verifier


def ledger(rf, *, class_, profile, stages, stop_reason, options_created, options_standing, earned, deprioritized,
           review_hits_passed, review_hits_failed, holds_accepted, verifier_contradictions, verifier_confirmed,
           seats_failed, closer_swaps, model_calls, elapsed_s, flags, classification, next_question="") -> dict:
    return {"run": rf.run_id, "class": class_, "profile": profile, "stages": stages, "stop_reason": stop_reason,
            "options_created": options_created, "options_standing": options_standing, "earned_kills": earned,
            "review_hits_passed": review_hits_passed, "review_hits_failed": review_hits_failed, "holds_accepted": holds_accepted,
            "verifier_contradictions": verifier_contradictions, "verifier_confirmed": verifier_confirmed, "seats_failed": seats_failed,
            "closer_swaps": closer_swaps, "model_calls": model_calls, "elapsed_s": elapsed_s, "flags": flags,
            "morning_usefulness_1_to_5": None, "tonights_question": next_question, "classification": classification,
            "deprioritized": deprioritized, "rollback_hash_verified": None}


def architecture_lines(root: str, led: dict, date: str, generators: int, benchmark_task: str = ""):
    arch = os.path.join(root, "architecture")
    os.makedirs(arch, exist_ok=True)
    line = {"run": led["run"], "date": date, "profile": led["profile"], "generators": generators, "benchmark_task": benchmark_task,
            "correct": None, "unsupported_claims": 0, "doc_contradictions": led["verifier_contradictions"], "planted_faults_caught": 0,
            "planted_faults_total": 0, "earned_kills": led["earned_kills"], "deprioritized": led["deprioritized"],
            "review_hits_passed": led["review_hits_passed"], "verifier_contradictions": led["verifier_contradictions"],
            "model_calls": led["model_calls"], "elapsed_s": led["elapsed_s"], "usefulness": None}
    with open(os.path.join(arch, "runs.jsonl"), "ab") as f:
        f.write((json.dumps(line) + "\n").encode("utf-8"))


def capability_observation(root: str, obs: dict):
    arch = os.path.join(root, "architecture")
    os.makedirs(arch, exist_ok=True)
    with open(os.path.join(arch, "model-capability-ledger.jsonl"), "ab") as f:
        f.write((json.dumps(obs) + "\n").encode("utf-8"))
