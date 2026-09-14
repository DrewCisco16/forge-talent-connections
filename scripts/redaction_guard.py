#!/usr/bin/env python3
"""
redaction_guard.py
==================
Mechanical pre-commit scan for data that must never enter this PUBLIC repository.

WHY THIS EXISTS, AND WHY IT IS CODE RATHER THAN A RULE. The rule already existed.
AGENTS.md carries it, the Playbook carries it on p.25, and the fleet pack's own
header carries it. It was written down, agreed, and then violated anyway: commit
2a51e25 published eight phone numbers, a carrier account identifier, a retail
order number, and four named individuals paired with their devices, to a
repository whose visibility is public.

A rule in prose has a failure rate nobody has measured. A gate that blocks the
commit has one you can test. This is the gate.

WHAT IT REFUSES TO DO. It does not judge intent, it does not ask a model, and it
does not weigh a match against the value of the commit. A match blocks. Anything
softer reintroduces the judgement call that already failed once.

FALSE POSITIVES ARE EXPECTED AND CHEAP. The cost of a false positive is one
allowlist line with a reason attached. The cost of a false negative is a third
party's phone number on the public internet. The thresholds are set accordingly,
and deliberately err toward blocking.

ALLOWLISTING. A line carrying the marker `redaction-guard: allow` is skipped, and
the marker is meant to be used with a reason on the same line. Paths listed in
scripts/redaction_allowlist.txt are skipped whole -- use that only for fixtures
whose entire purpose is to contain specimen patterns.

Usage:
    python3 scripts/redaction_guard.py                 # scan tracked files at HEAD
    python3 scripts/redaction_guard.py --staged        # scan staged changes (pre-commit)
    python3 scripts/redaction_guard.py PATH [PATH...]  # scan specific paths
    python3 scripts/redaction_guard.py --install-hook  # install .git/hooks/pre-commit
    python3 scripts/redaction_guard.py --self-test

Exit codes: 0 clean, 1 findings, 2 usage error.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ALLOW_MARKER = "redaction-guard: allow"
ALLOWLIST_FILE = "scripts/redaction_allowlist.txt"

# Binary and vendored paths are skipped: a scan that takes minutes gets disabled.
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist",
             "build", ".pdfenv", "pdfenv"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf",
                 ".zip", ".gz", ".tar", ".woff", ".woff2", ".ttf", ".otf",
                 ".mp4", ".mov", ".docx", ".xlsx", ".pptx", ".DS_Store"}


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern
    why: str


def _c(p: str) -> re.Pattern:
    return re.compile(p)


RULES: list[Rule] = [
    # Two forms, and both demand a CONSISTENT separator via the backreference.
    # Without that, a FAR/DFARS clause number such as 252.204-7012 reads as a
    # phone: three digits, separator, three digits, separator, four digits. It
    # mixes "." and "-", and a real phone number does not.
    Rule("us-phone-parens",
         _c(r"\(\d{3}\)\s?\d{3}[.\s-]\d{4}\b"),
         "a phone number. Third-party numbers are not yours to publish"),
    Rule("us-phone",
         _c(r"(?<![\d.\-/])(?:\+?1[\s.-])?[2-9]\d{2}([.\s-])\d{3}\1\d{4}(?![\d\-/])"),
         "a phone number. Third-party numbers are not yours to publish"),
    Rule("ssn",
         _c(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
         "looks like a Social Security number"),
    Rule("carrier-or-account-number",
         # long digit runs, optionally hyphen-segmented, e.g. 342710906-00001
         # Not preceded by "." or "/": 0.3333333333333333 is float precision and
         # doi.org/10.1177/00221856241234567 is a citation. Neither is an account.
         _c(r"(?<![\d./])\b\d{9,}(?:-\d{4,})?\b(?!\.\d)"),
         "a long numeric identifier: carrier account, order, or customer number"),
    Rule("embedded-reference-number",
         # No word boundary: an order or reference number often carries a letter
         # prefix, e.g. BBY01807143128604, which \b\d{9,} never sees. Ten digits
         # in a row inside a token is not a version, a date, or a token count.
         _c(r"(?<![\d./])\d{10,}(?!\.\d)"),
         "a long digit run inside an identifier: order, reference or account number"),
    Rule("private-key",
         _c(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
         "a private key"),
    Rule("anthropic-key", _c(r"\bsk-ant-[A-Za-z0-9_\-]{16,}"), "an Anthropic API key"),
    Rule("openai-key", _c(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}\b"), "an OpenAI API key"),
    Rule("github-token", _c(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b"), "a GitHub token"),
    Rule("aws-key", _c(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "an AWS access key id"),
    # No trailing \b and an open-ended quantifier: a key one character longer
    # than the expected 35 must still match. An anchored length is a gap.
    Rule("google-key", _c(r"\bAIza[0-9A-Za-z_\-]{30,}"), "a Google API key"),
    Rule("slack-token", _c(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "a Slack token"),
    Rule("generic-bearer",
         _c(r"(?i)\b(?:authorization|bearer|api[_-]?key|secret|passwd|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{20,}"),
         "a credential assigned inline"),
    Rule("cui-marking",
         _c(r"(?:CONTROLLED UNCLASSIFIED INFORMATION|CUI//|\bFOUO\b|FOR OFFICIAL USE ONLY|SOURCE SELECTION (?:INFORMATION|SENSITIVE))"),
         "a CUI or source-selection marking. This must not be in a public repo"),
    Rule("payment-card",
         _c(r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6011)[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
         "looks like a payment card number"),
]


def _load_allowlist(root: Path) -> dict[str, set[str] | None]:
    """path -> set of suppressed rule names, or None meaning the whole file.

    Rule-scoped entries exist so a file full of numeric test specimens does not
    have to go dark to the credential rules as well. Blanket-allowlisting a
    5,000-line test file to silence a float literal would hide a real key in it.

        path/to/file.py                      # whole file, needs a strong reason
        path/to/file.py :: rule-a,rule-b     # only those rules, everything else armed
    """
    f = root / ALLOWLIST_FILE
    if not f.exists():
        return {}
    out: dict[str, set[str] | None] = {}
    for line in f.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if "::" in line:
            path, rules = line.split("::", 1)
            out[path.strip()] = {r.strip() for r in rules.split(",") if r.strip()}
        else:
            out[line] = None
    return out


def scan_text(text: str, path: str = "<text>",
              suppress: set[str] | None = None) -> list[tuple[int, str, str, str]]:
    """Return (lineno, rule, why, redacted_excerpt). The excerpt never contains
    the match itself -- a report that reprints the secret has republished it."""
    findings = []
    for i, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARKER in line:
            continue
        for rule in RULES:
            if suppress and rule.name in suppress:
                continue
            m = rule.pattern.search(line)
            if m:
                col = m.start()
                excerpt = line[max(0, col - 24):col].rstrip()
                findings.append((i, rule.name, rule.why,
                                 f"...{excerpt}[{len(m.group(0))} chars REDACTED]..."))
                break  # one finding per line is enough to block it
    return findings


def _iter_paths(root: Path, explicit: list[str] | None) -> list[Path]:
    if explicit:
        return [Path(p) for p in explicit]
    # Tracked AND untracked-but-not-ignored. `git ls-files` alone misses a new
    # file entirely, so a secret in one would scan clean right up to the moment
    # it was staged -- found by this guard blocking its own author's commit.
    try:
        tracked = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True,
                                 text=True, check=True).stdout.split("\n")
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"], cwd=root,
            capture_output=True, text=True, check=True).stdout.split("\n")
        out = tracked + untracked
    except (subprocess.CalledProcessError, FileNotFoundError):
        out = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]
    return [root / p for p in dict.fromkeys(out) if p]


def _staged_paths(root: Path) -> list[Path]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                         cwd=root, capture_output=True, text=True, check=True)
    return [root / p for p in out.stdout.split("\n") if p]


def _rel(p: Path, root: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return p.as_posix()


def _skip(p: Path, root: Path, allow: dict[str, set[str] | None]) -> bool:
    rel = _rel(p, root)
    if rel in allow and allow[rel] is None:
        return True
    if any(part in SKIP_DIRS for part in p.parts):
        return True
    return p.suffix in SKIP_SUFFIXES


def run(root: Path, paths: list[Path]) -> int:
    allow = _load_allowlist(root)
    total = 0
    scanned = 0
    for p in paths:
        if _skip(p, root, allow) or not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable: not a text disclosure risk
        scanned += 1
        suppress = allow.get(_rel(p, root)) or None
        for lineno, rule, why, excerpt in scan_text(text, str(p), suppress):
            if total == 0:
                print("BLOCKED by redaction_guard. This repository is PUBLIC.\n")
            rel = p.relative_to(root).as_posix() if p.is_absolute() else p
            print(f"  {rel}:{lineno}  [{rule}]  {why}")
            print(f"      {excerpt}")
            total += 1

    if total:
        print(f"\n{total} finding(s) across {scanned} file(s). Nothing was committed.\n")
        print("  To fix: remove the value, or replace it with [REDACTED].")
        print(f"  If it is genuinely safe, append '{ALLOW_MARKER} <reason>' to that line,")
        print(f"  or add the path to {ALLOWLIST_FILE} with a reason.")
        print("  Do not allowlist to get past a commit you are unsure about.")
        return 1
    print(f"redaction_guard: clean ({scanned} files scanned)")
    return 0


HOOK = """#!/bin/sh
# Installed by scripts/redaction_guard.py. This repository is PUBLIC.
exec python3 "$(git rev-parse --show-toplevel)/scripts/redaction_guard.py" --staged
"""


def install_hook(root: Path) -> int:
    hooks = root / ".git" / "hooks"
    if not hooks.is_dir():
        print("No .git/hooks directory found.")
        return 2
    target = hooks / "pre-commit"
    if target.exists():
        print(f"{target} already exists. Not overwriting. Merge by hand:")
        print(HOOK)
        return 2
    target.write_text(HOOK)
    target.chmod(0o755)
    print(f"Installed {target}")
    print("Every commit is now scanned. Bypass with --no-verify only when you")
    print("have read the finding and know why it is safe.")
    return 0


def self_test() -> int:
    """Prove it catches what it must and does not cry wolf on ordinary prose."""
    must_block = [
        ("phone hyphen", "| 305-849-4187 | iPhone 14 | Third party A |"),
        ("phone dotted", "call 808.388.1289 for details"),
        ("phone parens", "reach me at (904) 931-5657 any time"),
        ("carrier account", "Verizon Business account 342710906-00001."),
        ("order number", "Order number BBY01807143128604 shipped"),
        ("ssn", "SSN 123-45-6789 on file"),
        ("anthropic key", "ANTHROPIC_API_KEY=sk-ant-api03-AbCdEfGh12345678ijkl"),
        ("openai key", "key sk-proj-abcdefghijklmnopqrstuvwxyz0123456789"),
        ("github token", "token ghp_abcdefghijklmnopqrstuvwxyz0123"),
        ("aws key", "AKIAIOSFODNN7EXAMPLE is the id"),
        ("google key", "AIzaSyA1234567890abcdefghijklmnopqrstuvw"),
        ("slack token", "xoxb-1234567890-abcdefghijkl"),
        ("private key", "-----BEGIN RSA PRIVATE KEY-----"),
        ("inline secret", 'api_key: "abcdefghijklmnopqrstuvwxyz123456"'),
        ("cui marking", "This document is CUI//SP-PROCURE and restricted"),
        ("fouo", "Marked FOR OFFICIAL USE ONLY by the program office"),
        ("source selection", "SOURCE SELECTION SENSITIVE material enclosed"),
        ("payment card", "card 4111 1111 1111 1111 on file"),
    ]
    must_pass = [
        ("ordinary prose", "The agent returns a brief with three findings."),
        ("a date", "Verified on 2026-09-09 against the vendor page."),
        ("a price", "measured $4.96 and bounded $16.82 per run"),
        ("a version", "Claude Code v2.1.211 or later is required"),
        ("a commit sha", "Fixed at HEAD in 5f12aba; history still carries it."),
        ("rates", "input_per_mtok 4.0, output_per_mtok 20.0"),
        ("short digits", "Run 3 variants in 60 minutes with 0 extra spend."),
        ("allowlisted", f"phone 305-849-4187 {ALLOW_MARKER} specimen in guard docs"),
        ("token count", "max_input_tokens 1050000 from the vendor model page"),
        ("percent", "roughly 88.2% reduction at the measured end"),
        # Regressions found by running the guard over this repository:
        ("dfars clause", "Anything under a DFARS 252.204-7012 obligation"),
        ("far clause", "see FAR 52.219-14 and DFARS 252.225-7001"),
        ("float precision", 'assert self._check("1/3 = 0.3333333333333333")'),
        ("doi url", "https://doi.org/10.1177/00221856241234567 resolved"),
        ("semver-ish", "version 2.1.211 or later is required"),
    ]
    fails = 0
    for label, text in must_block:
        if not scan_text(text):
            print(f"  FAIL  should BLOCK but did not: {label}")
            fails += 1
        else:
            print(f"  ok    blocks {label}")
    for label, text in must_pass:
        found = scan_text(text)
        if found:
            print(f"  FAIL  false positive on {label}: rule={found[0][1]}")
            fails += 1
        else:
            print(f"  ok    allows {label}")
    # the rule-scoped suppression must narrow, never disarm
    specimen = 'SECRET = "sk-ant-api03-AbCdEfGh12345678ijkl"  and 9007199254740993'
    if not scan_text(specimen, suppress={"carrier-or-account-number",
                                         "embedded-reference-number"}):
        print("  FAIL  rule-scoped suppression disarmed the credential rules")
        fails += 1
    else:
        print("  ok    rule-scoped suppression still catches credentials")
    if scan_text("2 ** 9007199254740993", suppress={"carrier-or-account-number",
                                                    "embedded-reference-number"}):
        print("  FAIL  rule-scoped suppression did not suppress its own rules")
        fails += 1
    else:
        print("  ok    rule-scoped suppression silences only the named rules")

    n = len(must_block) + len(must_pass) + 2
    print(f"\n{n - fails}/{n} passed")
    return 1 if fails else 0


def main(argv: list[str]) -> int:
    root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"],
                               capture_output=True, text=True).stdout.strip()
                or os.getcwd())
    args = argv[1:]
    if args and args[0] == "--self-test":
        return self_test()
    if args and args[0] == "--install-hook":
        return install_hook(root)
    if args and args[0] == "--staged":
        return run(root, _staged_paths(root))
    return run(root, _iter_paths(root, args or None))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
