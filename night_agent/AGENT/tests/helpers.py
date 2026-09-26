"""Shared paths and runners for the runtime tests. stdlib only."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.dirname(HERE)
PKG = os.path.dirname(AGENT)
FIX = os.path.join(HERE, "fixtures")
RUN_NIGHT = os.path.join(AGENT, "run_night.py")
NA_CHECK = os.path.join(PKG, "TESTS", "na_check.py")
sys.path.insert(0, PKG)
sys.path.insert(0, os.path.join(PKG, "TESTS"))


def tmp_root(prefix="na_test_"):
    return tempfile.mkdtemp(prefix=prefix)


def run_night(root, ask="ask_hybrid.md", sandbox=True, extra=()):
    cmd = [sys.executable, RUN_NIGHT, root, "--ask", os.path.join(FIX, ask), "--seats", "fake", "--documents", os.path.join(FIX, "documents"),
           "--net", "off", "--fixed-clock", "2026-09-26T22:00:00"]
    if sandbox:
        cmd += ["--sandbox", os.path.join(FIX, "sandbox")]
    cmd += list(extra)
    return subprocess.run(cmd, capture_output=True, text=True)


def resume_night(root, run="na-001", extra=()):
    cmd = [sys.executable, RUN_NIGHT, root, "--resume", f"runs/{run}", "--seats", "fake", "--documents", os.path.join(FIX, "documents"),
           "--sandbox", os.path.join(FIX, "sandbox"), "--net", "off", "--fixed-clock", "2026-09-26T22:00:00"] + list(extra)
    return subprocess.run(cmd, capture_output=True, text=True)


def na_check(run_dir):
    r = subprocess.run([sys.executable, NA_CHECK, run_dir], capture_output=True, text=True)
    fails = [l for l in r.stdout.splitlines() if l.startswith("FAIL")]
    return r.returncode, fails


def jsonl(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8").read().splitlines() if l.strip()]
