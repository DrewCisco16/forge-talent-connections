"""Adversarial review of the decision-log guards (R2): what the tests in
test_decision_log.py do not reach.

1. The ignore rule can be undone by ANY .gitignore, not only the root one:
   git gives a nested .gitignore precedence over its parents, so a single
   `!decision-log.jsonl*` line in android/.gitignore re-includes the log under
   android/. CI must therefore run the suite that checks the rule whenever any
   .gitignore changes. A GitHub `paths` entry without a slash or `**` matches
   one path at the repository root only.
2. The ignore-rule test probes seven hand-picked directories. A nested
   .gitignore anywhere else (web/, test/, tool/) re-includes the log unseen.
3. The no-invitation rule for the log is checked by
   .claude/tests/decision-log-policy.test.mjs, which only the agents workflow
   runs. The .gitignore comment carried exactly such an invitation before this
   change, and an edit to .gitignore alone runs the adjudication workflow, not
   that one.

The two CI-filter tests failed against the first version of this change and
pass once every .gitignore is inside the filters. The any-directory test
closes a hole a planted mutation walked through.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import decision_log as dl
from audit_log import HEAD_SUFFIX

ROOT = Path(dl.HERE).parent
WORKFLOWS = ROOT / ".github" / "workflows"
LOG_NAME = os.path.basename(dl.DEFAULT_LOG)
LOG_FILES = [LOG_NAME, LOG_NAME + HEAD_SUFFIX, LOG_NAME + ".lock", LOG_NAME + HEAD_SUFFIX + ".tmp"]


def _git(*args: str) -> str:
    git = shutil.which("git")
    assert git, "git is required"
    out = subprocess.run([git, "-C", str(ROOT), *args], capture_output=True, text=True, timeout=120, check=False)
    assert out.returncode == 0, out.stderr
    return out.stdout


def _repo_files() -> list[str]:
    """Tracked files plus new files git would offer to add."""
    return [p for p in _git("ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0") if p]


def _gitignores() -> list[str]:
    found = sorted(p for p in _repo_files() if p.rsplit("/", 1)[-1] == ".gitignore")
    assert ".gitignore" in found, f"expected the root .gitignore among {found}"
    return found


def _github_glob(pattern: str) -> re.Pattern[str]:
    """GitHub's documented filter semantics for the characters used here:
    `*` never crosses `/`, `**` does, and `**/` may match nothing. Anything
    else special fails closed, so a new pattern is read correctly or not at
    all."""
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] in "?+[]!":
            raise AssertionError(f"pattern {pattern!r} uses {pattern[i]!r}, which this reader does not model")
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def _triggers(text: str) -> dict[str, list[str] | None]:
    """{event: paths filter or None when unfiltered} for push and pull_request,
    read from the `on:` block by indentation."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if re.match(r"^on:\s*(#.*)?$", ln)), None)
    if start is None:
        inline = next((ln for ln in lines if ln.startswith("on:")), "")
        return {e: None for e in ("push", "pull_request") if re.search(rf"\b{e}\b", inline)}
    events: dict[str, list[str] | None] = {}
    current: str | None = None
    i = start + 1
    while i < len(lines):
        ln = lines[i]
        if ln and not ln[0].isspace() and not ln.startswith("#"):
            break
        ev = re.match(r"^  ([a-z_]+):", ln)
        if ev:
            current = ev.group(1)
            events.setdefault(current, None)
        pm = re.match(r"^(\s+)paths:\s*(.*)$", ln)
        if pm and current:
            rest = pm.group(2).split("#", 1)[0].strip()
            if rest.startswith("["):
                events[current] = [e.strip().strip("\"'") for e in rest.strip("[]").split(",") if e.strip()]
            else:
                entries: list[str] = []
                while i + 1 < len(lines) and re.match(r"^\s+-\s", lines[i + 1]):
                    i += 1
                    entries.append(lines[i].split("- ", 1)[1].split(" #", 1)[0].strip().strip("\"'"))
                events[current] = entries
        i += 1
    return {e: f for e, f in events.items() if e in ("push", "pull_request")}


def _runs_on_pull_request(workflow: str, path: str) -> bool:
    trig = _triggers((WORKFLOWS / workflow).read_text(encoding="utf-8"))
    if "pull_request" not in trig:
        return False
    flt = trig["pull_request"]
    return flt is None or any(_github_glob(p).match(path) for p in flt)


def test_the_filter_reader_reads_this_repositorys_workflows() -> None:
    """A reader that finds no filter would make the tests below pass vacuously."""
    trig = _triggers((WORKFLOWS / "adjudication.yml").read_text(encoding="utf-8"))
    assert trig.get("pull_request") and trig.get("push"), trig
    assert _triggers((WORKFLOWS / "agents.yml").read_text(encoding="utf-8")).get("pull_request"), "agents.yml"
    assert _github_glob(".gitignore").match(".gitignore")
    assert not _github_glob(".gitignore").match("android/.gitignore")
    assert _github_glob("**/.gitignore").match(".gitignore")
    assert _github_glob("**/.gitignore").match("android/.gitignore")
    assert _github_glob("adjudication/**").match("adjudication/.gitignore")


def test_every_gitignore_in_the_repository_is_inside_the_ci_path_filters() -> None:
    """android/.gitignore and ios/.gitignore can re-include the log
    (test_decision_log.py itself probes android/app/ and ios/Runner/ for that
    reason), so an edit to either alone must start a run of the suite that
    would catch it."""
    trig = _triggers((WORKFLOWS / "adjudication.yml").read_text(encoding="utf-8"))
    gaps = []
    for event, flt in trig.items():
        if flt is None:
            continue
        missed = [g for g in _gitignores() if not any(_github_glob(p).match(g) for p in flt)]
        if missed:
            gaps.append(f"{event}: {flt} does not match {missed}")
    assert not gaps, "an edit to one of these .gitignore files alone runs no test of the decision-log rule: " + "; ".join(gaps)


def test_a_gitignore_only_change_runs_the_no_invitation_scan_in_ci() -> None:
    """At f99e13e the .gitignore comment itself carried the invitation that
    decision-log-policy.test.mjs forbids. That test runs only in a workflow
    that runs `node --test`, so an edit to any .gitignore must start one."""
    node_runners = [w.name for w in sorted(WORKFLOWS.glob("*.yml"))
                    if re.search(r"node --test\b[^\n]*\.claude/tests", w.read_text(encoding="utf-8"))]
    assert node_runners, "no workflow runs the agent-layer suite at all"
    for g in _gitignores():
        runs = [w for w in node_runners if _runs_on_pull_request(w, g)]
        assert runs, (f"a pull request that changes only {g} runs none of {node_runners}, so the "
                      f"no-invitation scan never reads it")


def test_no_directory_in_the_repository_can_reinclude_the_log(tmp_path: Path) -> None:
    """Passes now. test_decision_log.py probes seven fixed directories, so a
    `!decision-log.jsonl*` line in a NEW web/.gitignore (or test/, tool/, docs/)
    passes it. This probes every directory that holds a repository file, the
    root included, and every directory that holds a .gitignore."""
    dirs = {""}
    for f in _repo_files():
        parts = f.split("/")[:-1]
        for k in range(1, len(parts) + 1):
            dirs.add("/".join(parts[:k]) + "/")
    paths = sorted(d + n for d in dirs for n in LOG_FILES)
    no_global = tmp_path / "no-global-excludes"
    no_global.write_text("", encoding="utf-8")
    git = shutil.which("git")
    assert git
    out = subprocess.run([git, "-c", f"core.excludesFile={no_global}", "-C", str(ROOT), "check-ignore",
                          "--no-index", "--verbose", "--non-matching", "--stdin"],
                         input="\n".join(paths) + "\n", capture_output=True, text=True, timeout=120, check=False)
    assert out.returncode in (0, 1), out.stderr
    open_paths = []
    for line in out.stdout.splitlines():
        rule, _, path = line.partition("\t")
        source, _, rest = rule.partition(":")
        pattern = rest.partition(":")[2]
        if not source or pattern.startswith("!") or not source.endswith(".gitignore") or source.startswith(".git/"):
            open_paths.append(f"{path} ({rule or 'no rule'})")
    assert len(out.stdout.splitlines()) == len(paths), "git did not report on every probed path"
    assert not open_paths, f"{len(open_paths)} log paths git does not ignore: {open_paths[:8]}"
