"""The Experiment Engine (spec 5; DISPATCH 4) and the EXPERIMENT operator inside HYBRID (DISPATCH 3.5).

BASELINE twice, then PROPOSE (P8, rotating generator) -> EXECUTE (EXECUTOR, fresh copy, fixed budget) ->
MEASURE (twice) -> DECIDE (the same keep_defects the guard and the checker use; KEEP only when G-9 ALLOWs)
-> LOG. The sandbox is copied under <root>/work/<run>/, never mutated in place.
"""
import json
import os
import re
import shutil
import subprocess
import sys

from . import PKG, guard, packets, parse

sys.path.insert(0, os.path.join(PKG, "TESTS"))
from na_gate import keep_defects  # noqa: E402

METRIC_LINE = re.compile(r"^\s*([A-Za-z_][\w]*)\s+(-?\d+(?:\.\d+)?)\s*$", re.M)


def parse_metrics(output: str) -> dict:
    return {k: float(v) for k, v in METRIC_LINE.findall(output or "")}


def workdir(night, name: str) -> str:
    d = os.path.join(night.root, "work", night.rf.run_id, name)
    return d


def fresh_copy(src: str, dst: str) -> str:
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", ".bench_runs"))
    return dst


def artifact_hash(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in (".git", "__pycache__"))
        for f in sorted(files):
            if f == ".bench_runs":
                continue
            p = os.path.join(root, f)
            h.update(os.path.relpath(p, path).encode())
            h.update(open(p, "rb").read())
    return h.hexdigest()


def objective(night) -> dict:
    objs = night.gate.get("objectives") or []
    return objs[0] if objs else {}


def baseline(night) -> dict:
    rf = night.rf
    if rf.exists("experiments/baseline.json"):
        return rf.read_json("experiments/baseline.json")
    night.begin_stage("BASELINE")
    guard.require(rf, "BASELINE")
    obj = objective(night)
    if not obj.get("procedure"):
        raise ValueError("the gate names no measurement procedure")
    budget_s = float(night.gate["budget"].get("experiment_budget_s") or 600)
    kept = fresh_copy(night.cfg.sandbox_dir, workdir(night, "kept"))
    ex = night.crew["EXECUTOR"]
    values, outputs = [], []
    for i in range(2):
        r = ex.measure(obj["procedure"], kept, budget_s)
        night.log("EXECUTOR", "measure", result=f"baseline run {i + 1}: exit {r.get('returncode')} {('error ' + r['error']) if r.get('error') else ''}", stage="BASELINE")
        m = parse_metrics(r.get("output", ""))
        if obj["name"] in m:
            values.append(m[obj["name"]])
        outputs.append(r.get("output", ""))
    if not values:
        raise ValueError(f"the procedure printed no line '{obj['name']} <value>'")
    noise = round(abs(values[0] - values[1]), 6) if len(values) == 2 else None
    base = {"metric": obj["name"], "direction": obj["direction"], "baseline_value": round(sum(values) / len(values), 6),
            "noise": noise if noise is not None else None, "noise_unknown": noise is None, "runs": len(values), "values": values,
            "environment": f"python {sys.version.split()[0]} {sys.platform}", "procedure": obj["procedure"],
            "guardrail": obj.get("guardrail", ""), "guardrail_baseline": parse_metrics(outputs[0]).get(obj.get("guardrail", ""), 0),
            "artifact_hash": artifact_hash(kept)}
    if noise is None:
        night.log("DISPATCH", "noise", result="NOISE_UNKNOWN: one run only; deltas under MIN_DELTA are INCONCLUSIVE", stage="BASELINE")
    rf.write_once("experiments/baseline.json", json.dumps(base, indent=1), stage="BASELINE")
    night.status("BASELINE", "baseline.json", "PROPOSE", last_complete="experiments/baseline.json")
    return base


def next_generator(night, n: int) -> str:
    gens = night.usable_generators("PROPOSE")
    if not gens:
        raise ValueError("no generator for PROPOSE")
    return gens[(n - 1) % len(gens)]


def one_experiment(night, n: int, base: dict) -> dict | None:
    rf = night.rf
    eid = f"exp-{n:03d}"
    if rf.exists(f"experiments/{eid}/record.json"):
        return rf.read_json(f"experiments/{eid}/record.json")
    obj = objective(night)
    budget_s = float(night.gate["budget"].get("experiment_budget_s") or 600)
    # PROPOSE
    log_so_far = "\n".join(json.dumps(x) for x in rf.read_jsonl("experiments/log.jsonl")) or "none yet"
    kept = workdir(night, "kept")
    p8 = packets.build_p8(night.ask, f"{obj['name']}, {obj['direction']} is better, procedure: {obj['procedure']}",
                          f"{obj.get('guardrail') or 'none'} tolerance {obj.get('tolerance', 0)}",
                          "\n".join(night.gate.get("hard_constraints") or []) or "none",
                          f"{base['metric']} {base['baseline_value']}, noise {base['noise']}, {base['environment']}", log_so_far,
                          f"the kept working copy (hash {base.get('artifact_hash', '')[:12]}); files: " + ", ".join(sorted(os.listdir(kept))))
    if not rf.exists(f"experiments/{eid}/proposal.md"):
        night.begin_stage("PROPOSE")
        g = next_generator(night, n)
        saved = night.ask_seat(g, p8, stage_dir=f"experiments/{eid}", stage_label="PROPOSE", save_as=f"experiments/{eid}/proposal.md",
                               required_headings=parse.PROPOSAL_HEADINGS, packet_file=f"experiments/{eid}/packet.md",
                               reprompt_line="Use exactly the headings ID, HYPOTHESIS, PRIMARY CHANGE, EXPECTED EFFECT, GUARDRAIL RISK, PROCEDURE, COST, DECISION RULE.")
        if saved is None:
            return None
    prop = parse.proposal_fields(rf.read(f"experiments/{eid}/proposal.md"))
    # EXECUTE
    night.begin_stage("EXECUTE")
    ex = night.crew["EXECUTOR"]
    wd = fresh_copy(kept, workdir(night, eid))
    applied = ex.apply_mutation(prop.get("PRIMARY CHANGE", ""), wd)
    night.log("EXECUTOR", "mutate", result=("applied: " + str(applied.get("log", ""))) if applied.get("ok") else f"FAILED: {applied.get('error')}", stage="EXECUTE")
    outputs, values, guard_vals, elapsed, within = [], [], [], 0.0, True
    if applied.get("ok"):
        for i in range(2):
            r = ex.measure(obj["procedure"], wd, budget_s)
            elapsed += float(r.get("elapsed_s") or 0)
            if r.get("error"):
                within = within and "timeout" not in (r.get("error") or "")
            m = parse_metrics(r.get("output", ""))
            outputs.append(r.get("output", ""))
            if obj["name"] in m:
                values.append(m[obj["name"]])
            if obj.get("guardrail") and obj["guardrail"] in m:
                guard_vals.append(m[obj["guardrail"]])
            night.log("EXECUTOR", "measure", result=f"{eid} run {i + 1}: exit {r.get('returncode')}", stage="MEASURE")
    within = within and elapsed <= budget_s
    rf.write_once(f"experiments/{eid}/output.txt", "\n".join(outputs) or (applied.get("error") or "no output"), seat="EXECUTOR", action="write", stage="EXECUTE")
    # MEASURE and DECIDE
    night.begin_stage("DECIDE")
    result_value = values[0] if values else None
    repeat_value = values[1] if len(values) > 1 else None
    delta = round(result_value - base["baseline_value"], 6) if result_value is not None else None
    tol = float(obj.get("tolerance") or 0)
    gbase = float(base.get("guardrail_baseline") or 0)
    guardrails = [{"name": obj["guardrail"], "baseline": gbase, "value": (max(guard_vals) if guard_vals else None), "tolerance": tol}] if obj.get("guardrail") else []
    constraint_broken = bool(guardrails and guardrails[0]["value"] is not None and abs(guardrails[0]["value"] - gbase) > tol)
    rec = {"id": eid, "hypothesis": prop.get("HYPOTHESIS", ""), "primary_change": prop.get("PRIMARY CHANGE", ""), "expected_effect": prop.get("EXPECTED EFFECT", ""),
           "metric": base["metric"], "direction": base["direction"], "baseline_value": base["baseline_value"], "procedure": obj["procedure"],
           "environment": base["environment"], "versions": {}, "inputs": "", "configuration": "", "seed": None,
           "constraints_checked": list(night.gate.get("hard_constraints") or []) if guardrails else [],
           "guardrails": guardrails, "result_value": result_value, "delta": delta, "noise": base.get("noise"), "repeat_value": repeat_value,
           "evidence": f"experiments/{eid}/output.txt", "artifact_hash": artifact_hash(wd) if applied.get("ok") else "", "decision": "INCONCLUSIVE",
           "interaction": "INTERACTION" in prop.get("PRIMARY CHANGE", "").upper(), "timestamp": rf.clock.iso(),
           "cost": {"runs": len(values), "elapsed_s": round(elapsed, 2)}, "budget_s": budget_s, "git_commit": "", "within_budget": within,
           "constraint_broken": constraint_broken, "guardrails_ok": not constraint_broken}
    if not applied.get("ok") or result_value is None:
        rec["decision"] = "INCONCLUSIVE"
        rec["settle"] = applied.get("error") or "the procedure printed no metric"
    elif constraint_broken:
        rec["decision"] = "REVERT"
    else:
        improves = (delta < 0) if base["direction"] == "lower" else (delta > 0)
        rec["decision"] = "KEEP" if improves else ("REVERT" if delta != 0 else "INCONCLUSIVE")
        if rec["decision"] == "KEEP" and keep_defects(rec, base, night.gate):
            rec["decision"] = "INCONCLUSIVE"
            rec["settle"] = "; ".join(keep_defects(rec, base, night.gate))
    if rec["decision"] == "KEEP":
        rec["git_commit"] = git_keep(wd, eid, rec["hypothesis"])
    rf.write_once(f"experiments/{eid}/record.json", json.dumps(rec, indent=1), stage="DECIDE")
    if rec["decision"] == "KEEP":
        guard.require(rf, "DECIDE", record=eid)  # G-9 must ALLOW before the KEEP is acted on
        fresh_copy(wd, kept)
        night.log("DISPATCH", "keep", result=f"{eid} kept; the working copy is now hash {rec['artifact_hash'][:12]}", stage="DECIDE")
    rf.append_jsonl("experiments/log.jsonl", {"id": eid, "decision": rec["decision"], "delta": delta, "repeat_value": repeat_value,
                                              "hypothesis": rec["hypothesis"], "guardrails_ok": rec["guardrails_ok"],
                                              "constraint_broken": constraint_broken, "within_budget": within})
    st = rf.read_json("status.json", {}) or {}
    rf.status(experiments_used=int(st.get("experiments_used", 0)) + 1, stage="DECIDE", step=eid, next="PROPOSE", last_complete=f"experiments/{eid}/record.json")
    night.experiment_results.append(rec)
    return rec


def git_keep(wd: str, eid: str, hypothesis: str) -> str:
    if not os.path.isdir(os.path.join(wd, ".git")):
        return ""
    try:
        subprocess.run(["git", "-C", wd, "add", "-A"], check=True, capture_output=True)
        subprocess.run(["git", "-C", wd, "commit", "-q", "-m", f"{eid}: {hypothesis}"], check=True, capture_output=True)
        return subprocess.run(["git", "-C", wd, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def loop(night, max_experiments: int) -> list:
    base = baseline(night)
    k = int(night.gate["budget"].get("plateau_k") or 3)
    results = list(night.experiment_results)
    n = len(night.rf.read_jsonl("experiments/log.jsonl"))
    non_keep = 0
    drift = 0
    while n < max_experiments:
        n += 1
        rec = one_experiment(night, n, base)
        if rec is None:
            break
        results.append(rec)
        non_keep = 0 if rec["decision"] == "KEEP" else non_keep + 1
        g = rec["guardrails"][0] if rec.get("guardrails") else None
        if rec["decision"] == "KEEP" and g and g["value"] is not None and abs(g["value"] - g["baseline"]) > 0:
            drift += 1
        if non_keep >= k:
            night.rf.status(stop_reason="PLATEAU")
            night.log("DISPATCH", "stop", result=f"PLATEAU after {k} non-KEEP decisions", stage="DECIDE")
            break
        if drift >= 2:
            night.rf.status(stop_reason="OVERFIT_RISK")
            night.log("DISPATCH", "stop", result="OVERFIT_RISK: guardrail drifted toward tolerance twice on kept mutations", stage="DECIDE")
            break
    return results


def run_operator(night) -> list:
    """The EXPERIMENT operator inside HYBRID: one experiment per differing measurable prediction, capped by
    max_experiments; the results feed the next stage's check as [X-<id>] claims."""
    n_pred = max(2, night.measurable_options())
    cap = min(n_pred, int(night.gate["budget"].get("max_experiments") or 8))
    results = loop(night, cap)
    if (night.rf.read_json("status.json", {}) or {}).get("stop_reason") in ("PLATEAU", "OVERFIT_RISK"):
        night.rf.status(stop_reason=None)  # an experiment-loop stop ends the operator, not the night
    return results


def run_class(night):
    """CLASS = EXPERIMENT: the loop is the night (DISPATCH 4)."""
    results = loop(night, int(night.gate["budget"].get("max_experiments") or 8))
    if not (night.rf.read_json("status.json", {}) or {}).get("stop_reason"):
        night.rf.status(stop_reason="BUDGET")
    night.experiment_results = results
