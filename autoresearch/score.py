#!/usr/bin/env python3
"""
score.py -- the frozen harness for the overnight loop (see ../program.md).

This is the file the agent cannot edit. It answers one question -- did this
attempt make the package measurably better without cheating -- with one
number, and it performs the keep-or-revert itself so the decision never
depends on the agent's judgment.

    python autoresearch/score.py                    # score the working tree, no git changes
    python autoresearch/score.py --report           # where the uncovered lines are
    python autoresearch/score.py --record "desc"    # commit, score, keep or revert, log
    python autoresearch/score.py --record "desc" --push

Score: branch coverage percentage of adjudication/, higher is better, and
only after every gate passes. Any gate failure scores 0.0.

Exit codes: 0 scored (KEEP or REVERT), 2 cannot run, 3 STOP (stopping rule fired).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# constants: the harness. Changing these changes the meaning of every row in
# results.tsv, so they are not flags.
# --------------------------------------------------------------------------
PACKAGE = "adjudication"
RESULTS_COLUMNS = ["commit", "score", "status", "tests", "elapsed_s", "decision", "description"]
RESULTS_COMMIT_PREFIX = "autoresearch results:"
DEFAULT_MAX_ITER = 60
DEFAULT_PATIENCE = 10
SCOPE_ALLOWED = (
    re.compile(r"^adjudication/[^/]+\.py$"),
    re.compile(r"^autoresearch/results\.tsv$"),
    re.compile(r"^autoresearch/NIGHT-SUMMARY\.md$"),
)
# Tokens that excuse a line from a gate instead of satisfying it. Their count
# may never rise above the base commit's count.
SUPPRESSION_PATTERNS = {
    "pragma_no_cover": r"pragma:\s*no\s*cover",
    "noqa": r"#\s*noqa",
    "type_ignore": r"type:\s*ignore",
    "pytest_skip": r"pytest\.(mark\.(skip|skipif|xfail)|skip|xfail)\b",
}
GATE_ORDER = ["scope", "suppression", "lint", "types", "security", "frozen_tests", "test_count", "tests"]


@dataclass
class Outcome:
    score: float = 0.0
    status: str = "crash"
    tests: int = 0
    elapsed_s: float = 0.0
    detail: str = ""
    coverage_json: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# plumbing
# --------------------------------------------------------------------------
def sh(cmd: list[str], cwd: Path, check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=check, env=env)


def git(root: Path, *args: str, check: bool = True) -> str:
    return sh(["git", *args], root, check=check).stdout.strip()


def repo_root() -> Path:
    here = Path(__file__).resolve().parent
    return Path(sh(["git", "rev-parse", "--show-toplevel"], here).stdout.strip())


def read_base(ar: Path) -> dict:
    p = ar / ".base"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def write_base(ar: Path, data: dict) -> None:
    (ar / ".base").write_text(json.dumps(data, indent=2) + "\n")


def base_commit(root: Path, ar: Path) -> str:
    data = read_base(ar)
    if data.get("commit"):
        return data["commit"]
    # Fallback for scoring outside a launched run: the branch point from main.
    for ref in ("origin/main", "main"):
        r = sh(["git", "merge-base", "HEAD", ref], root, check=False)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return git(root, "rev-parse", "HEAD")


def py() -> str:
    return sys.executable


# --------------------------------------------------------------------------
# gates
# --------------------------------------------------------------------------
def gate_scope(root: Path, base: str) -> str | None:
    changed = set(git(root, "diff", "--name-only", base).splitlines())
    changed |= set(git(root, "ls-files", "--others", "--exclude-standard").splitlines())
    bad = sorted(p for p in changed if p and not any(rx.match(p) for rx in SCOPE_ALLOWED))
    if bad:
        return "out of scope: " + ", ".join(bad[:10]) + (" ..." if len(bad) > 10 else "")
    return None


def _count_pattern(root: Path, pattern: str, ref: str | None) -> int:
    cmd = ["git", "grep", "-o", "-E"]
    if ref:
        cmd += ["-e", pattern, ref, "--", f"{PACKAGE}/*.py"]
    else:
        cmd += ["--untracked", "-e", pattern, "--", f"{PACKAGE}/*.py"]
    r = sh(cmd, root, check=False)
    if r.returncode not in (0, 1):
        raise RuntimeError(f"git grep failed: {r.stderr.strip()}")
    return len([ln for ln in r.stdout.splitlines() if ln.strip()])


def gate_suppression(root: Path, base: str) -> str | None:
    grew = []
    for name, pattern in SUPPRESSION_PATTERNS.items():
        before = _count_pattern(root, pattern, base)
        now = _count_pattern(root, pattern, None)
        if now > before:
            grew.append(f"{name} {before}->{now}")
    if grew:
        return "suppression tokens increased: " + "; ".join(grew)
    return None


def gate_lint(adj: Path) -> str | None:
    r = sh([py(), "-m", "ruff", "check", "."], adj, check=False)
    return None if r.returncode == 0 else (r.stdout.strip() or r.stderr.strip())[-2000:]


def gate_types(adj: Path) -> str | None:
    r = sh([py(), "-m", "mypy"], adj, check=False)
    return None if r.returncode == 0 else (r.stdout.strip() or r.stderr.strip())[-2000:]


def gate_security(adj: Path) -> str | None:
    r = sh([py(), "-m", "bandit", "-q", "-c", "pyproject.toml", "-r", "."], adj, check=False)
    return None if r.returncode == 0 else (r.stdout.strip() or r.stderr.strip())[-2000:]


_COLLECT_RX = re.compile(r"(\d+)\s+tests?\s+collected")
_ERRORS_RX = re.compile(r"(\d+)\s+errors?")


def count_tests(adj: Path) -> tuple[int | None, str]:
    r = sh([py(), "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"], adj, check=False)
    tail = "\n".join(r.stdout.splitlines()[-3:])
    m = _COLLECT_RX.search(r.stdout)
    if r.returncode != 0 or _ERRORS_RX.search(tail) or not m:
        return None, (r.stdout.strip() or r.stderr.strip())[-2000:]
    return int(m.group(1)), tail


def _test_files_at(root: Path, ref: str) -> list[str]:
    out = git(root, "ls-tree", "--name-only", ref, f"{PACKAGE}/")
    return [p for p in out.splitlines() if re.match(rf"^{PACKAGE}/test_[^/]+\.py$", p)]


def test_files_differ(root: Path, base: str) -> bool:
    diff = git(root, "diff", "--name-only", base, "--", f"{PACKAGE}/test_*.py")
    untracked = [p for p in git(root, "ls-files", "--others", "--exclude-standard").splitlines()
                 if re.match(rf"^{PACKAGE}/test_[^/]+\.py$", p)]
    return bool(diff.strip() or untracked)


def make_frozen_dir(root: Path, adj: Path, base: str) -> Path:
    """Working-tree code with the test files exactly as they were at base."""
    tmp = Path(tempfile.mkdtemp(prefix="autoresearch-frozen-"))
    dst = tmp / PACKAGE
    ignore = shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache", "htmlcov", ".coverage",
                                    "runs", "*.pyc", ".env", "profiles.json")
    shutil.copytree(adj, dst, ignore=ignore)
    for p in dst.glob("test_*.py"):
        p.unlink()
    for rel in _test_files_at(root, base):
        (dst / Path(rel).name).write_text(git(root, "show", f"{base}:{rel}"))
    return dst


def run_pytest(cwd: Path, extra: list[str]) -> subprocess.CompletedProcess:
    return sh([py(), "-m", "pytest", "-q", "-p", "no:cacheprovider", *extra], cwd, check=False)


def _pytest_tail(r: subprocess.CompletedProcess) -> str:
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    return "\n".join(lines[-15:]) if lines else r.stderr.strip()[-2000:]


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------
def score_tree(root: Path, base: str, base_tests: int | None, log) -> tuple[Outcome, int | None]:  # noqa: PLR0911
    """Run every gate in order; return the outcome and the base test count
    (computed here if it was not known)."""
    adj = root / PACKAGE
    ar = root / "autoresearch"
    t0 = time.time()
    out = Outcome()

    def fail(status: str, detail: str) -> tuple[Outcome, int | None]:
        out.status, out.detail, out.elapsed_s = status, detail, round(time.time() - t0, 1)
        log(f"  gate {status}: FAIL")
        return out, base_tests

    log(f"  base {base[:10]}")
    for gate in ("scope", "suppression"):
        detail = gate_scope(root, base) if gate == "scope" else gate_suppression(root, base)
        if detail:
            return fail(gate, detail)
        log(f"  gate {gate}: ok")

    for gate, fn in (("lint", gate_lint), ("types", gate_types), ("security", gate_security)):
        detail = fn(adj)
        if detail:
            return fail(gate, detail)
        log(f"  gate {gate}: ok")

    # Frozen tests: only needed when the attempt touched a test file; otherwise
    # the working-tree suite IS the frozen suite and the final run covers it.
    frozen_needed = test_files_differ(root, base) or base_tests is None
    if frozen_needed:
        fdir = make_frozen_dir(root, adj, base)
        try:
            if base_tests is None:
                base_tests, msg = count_tests(fdir)
                if base_tests is None:
                    return fail("frozen_tests", "could not collect base tests: " + msg)
            if test_files_differ(root, base):
                r = run_pytest(fdir, [])
                if r.returncode != 0:
                    return fail("frozen_tests", _pytest_tail(r))
                log("  gate frozen_tests: ok")
            else:
                log("  gate frozen_tests: ok (no test file changed)")
        finally:
            shutil.rmtree(fdir.parent, ignore_errors=True)
    else:
        log("  gate frozen_tests: ok (no test file changed)")

    n, msg = count_tests(adj)
    if n is None:
        return fail("test_count", "collection failed: " + msg)
    if base_tests is not None and n < base_tests:
        return fail("test_count", f"collected {n} < base {base_tests}")
    out.tests = n
    log(f"  gate test_count: ok ({n} >= {base_tests})")

    cov_json = ar / ".coverage.json"
    r = run_pytest(adj, ["--cov", "--cov-branch", f"--cov-report=json:{cov_json}"])
    if r.returncode != 0:
        return fail("tests", _pytest_tail(r))
    try:
        data = json.loads(cov_json.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return fail("crash", f"coverage report unreadable: {exc}")
    out.coverage_json = data
    out.score = round(float(data["totals"]["percent_covered"]), 2)
    out.status = "ok"
    out.elapsed_s = round(time.time() - t0, 1)
    log("  gate tests: ok")
    return out, base_tests


def report(out: Outcome, log) -> None:
    files = out.coverage_json.get("files", {})
    rows = []
    for name, info in files.items():
        s = info["summary"]
        rows.append((s.get("missing_lines", 0) + s.get("missing_branches", 0), name,
                     s.get("missing_lines", 0), s.get("missing_branches", 0), s.get("percent_covered", 0.0)))
    rows.sort(reverse=True)
    log("\nUncovered, largest first (missing lines, missing branches, percent):")
    for _total, name, ml, mb, pct in rows[:20]:
        log(f"  {name:40s} {ml:5d} {mb:5d} {pct:6.1f}%")


# --------------------------------------------------------------------------
# results.tsv
# --------------------------------------------------------------------------
def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0].split("\t")
    return [dict(zip(header, ln.split("\t"), strict=False)) for ln in lines[1:]]


def append_row(path: Path, row: dict) -> None:
    new = not path.exists() or not path.read_text().strip()
    with path.open("a") as fh:
        if new:
            fh.write("\t".join(RESULTS_COLUMNS) + "\n")
        fh.write("\t".join(str(row[c]).replace("\t", " ").replace("\n", " ") for c in RESULTS_COLUMNS) + "\n")


def best_score(rows: list[dict]) -> float | None:
    scores = [float(r["score"]) for r in rows if r.get("status") == "ok" and r.get("decision") == "KEEP"]
    return max(scores) if scores else None


def stopping_rule(rows: list[dict], max_iter: int, patience: int) -> str | None:
    attempts = [r for r in rows if r.get("description") != "baseline"]
    if len(attempts) >= max_iter:
        return f"STOP: {len(attempts)} attempts reached the cap of {max_iter}"
    streak = 0
    for r in reversed(attempts):
        if r.get("decision") == "KEEP":
            break
        streak += 1
    if streak >= patience:
        return f"STOP: {streak} consecutive attempts without improvement (patience {patience})"
    return None


# --------------------------------------------------------------------------
# record: the keep-or-revert
# --------------------------------------------------------------------------
def last_results_commit(root: Path, base: str) -> str:
    out = git(root, "log", "--format=%H %s", f"{base}..HEAD")
    for line in out.splitlines():
        sha, _, subject = line.partition(" ")
        if subject.startswith(RESULTS_COMMIT_PREFIX):
            return sha
    return base


def push_with_retry(root: Path, log) -> None:
    delay = 2
    for attempt in range(5):
        r = sh(["git", "push", "-u", "origin", "HEAD"], root, check=False)
        if r.returncode == 0:
            log("  pushed")
            return
        log(f"  push failed (attempt {attempt + 1}): {r.stderr.strip()[-300:]}")
        if attempt < 4:
            time.sleep(delay)
            delay *= 2
    log("  push gave up; results are committed locally")


def record(root: Path, description: str, push: bool, log) -> int:
    ar = root / "autoresearch"
    results = ar / "results.tsv"
    base_data = read_base(ar)
    base = base_commit(root, ar)
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if not branch.startswith("autoresearch/"):
        log(f"refusing to record on branch {branch!r}: the loop runs only on autoresearch/<tag> branches")
        return 2
    if not base_data.get("commit"):
        base_data["commit"] = base
    max_iter = int(base_data.get("max_iter", DEFAULT_MAX_ITER))
    patience = int(base_data.get("patience", DEFAULT_PATIENCE))
    base_tests = base_data.get("tests")

    # Commit whatever the agent left in the tree, inside the package only.
    # Anything outside it stays untracked and trips the scope gate.
    git(root, "add", "-A", "--", PACKAGE)
    if git(root, "status", "--porcelain", "--", PACKAGE):
        git(root, "commit", "-q", "-m", f"autoresearch: {description}")
    experiment = git(root, "rev-parse", "--short", "HEAD")
    log(f"scoring {experiment}: {description}")

    out, base_tests = score_tree(root, base, base_tests, log)
    if base_tests is not None and base_data.get("tests") != base_tests:
        base_data["tests"] = base_tests
        write_base(ar, base_data)

    rows = read_rows(results)
    best = best_score(rows)
    if description == "baseline":
        decision = "KEEP" if out.status == "ok" else "REVERT"
    else:
        decision = "KEEP" if out.status == "ok" and (best is None or out.score > best) else "REVERT"

    if decision == "REVERT":
        target = last_results_commit(root, base)
        git(root, "reset", "-q", "--hard", target)
        git(root, "clean", "-fdq", "--", PACKAGE, "autoresearch")
        log(f"  REVERT -> {target[:10]}")

    row = {"commit": experiment, "score": f"{out.score:.2f}", "status": out.status, "tests": out.tests,
           "elapsed_s": f"{out.elapsed_s:.0f}", "decision": decision, "description": description}
    append_row(results, row)
    git(root, "add", "--", "autoresearch/results.tsv")
    git(root, "commit", "-q", "-m", f"{RESULTS_COMMIT_PREFIX} {decision} {out.score:.2f} {description}")
    if push:
        push_with_retry(root, log)

    log("\nRESULT\t" + "\t".join(f"{c}={row[c]}" for c in RESULTS_COLUMNS))
    if out.detail:
        log("DETAIL\n" + out.detail)
    log(f"BEST\t{max(best or 0.0, out.score if decision == 'KEEP' else 0.0):.2f}")

    if description == "baseline" and out.status != "ok":
        log("the baseline does not pass its own gates; fix the tree before launching a run")
        return 2
    stop = stopping_rule(read_rows(results), max_iter, patience)
    if stop:
        log(stop)
        return 3
    return 0


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", metavar="DESCRIPTION", help="commit, score, keep or revert, append to results.tsv")
    ap.add_argument("--push", action="store_true", help="push the branch after recording")
    ap.add_argument("--report", action="store_true", help="print the uncovered-lines table after scoring")
    args = ap.parse_args()

    root = repo_root()
    if not (root / PACKAGE).is_dir():
        print(f"no {PACKAGE}/ under {root}", file=sys.stderr)
        return 2
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    log = lambda s: print(s, flush=True)  # noqa: E731

    if args.record:
        return record(root, args.record, args.push, log)

    ar = root / "autoresearch"
    base = base_commit(root, ar)
    out, _ = score_tree(root, base, read_base(ar).get("tests"), log)
    log(f"\nRESULT\tscore={out.score:.2f}\tstatus={out.status}\ttests={out.tests}\telapsed_s={out.elapsed_s:.0f}")
    if out.detail:
        log("DETAIL\n" + out.detail)
    if args.report and out.status == "ok":
        report(out, log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
