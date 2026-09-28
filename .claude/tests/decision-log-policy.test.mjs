// The Full Council decision log never enters the repository, and the docs
// that describe who holds Bash match the agent definitions.
//
// R2: no file may invite committing decision-log.jsonl or its .head sidecar.
// The ignore rule itself is checked by git in adjudication/test_decision_log.py.
// R4: docs/AI_AGENTS.md states exactly which agents hold Bash.
//
// Run: node --test ".claude/tests/*.test.mjs"

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
// This file states the rule it checks; a match here is the rule quoting itself.
const SELF = relative(REPO_ROOT, fileURLToPath(import.meta.url));

// Tracked files plus new files not yet committed, so a new doc is read too.
function repoTextFiles() {
  const r = spawnSync("git", ["-C", REPO_ROOT, "ls-files", "-z", "--cached", "--others", "--exclude-standard"], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  assert.equal(r.status, 0, `git ls-files failed: ${r.stderr}`);
  const files = [];
  for (const rel of r.stdout.split("\0").filter(Boolean)) {
    if (rel === SELF) continue;
    let buf;
    try {
      if (statSync(join(REPO_ROOT, rel)).size > 4 * 1024 * 1024) continue;
      buf = readFileSync(join(REPO_ROOT, rel));
    } catch {
      continue; // deleted in the working tree
    }
    if (buf.includes(0)) continue; // binary
    files.push({ rel, text: buf.toString("utf8") });
  }
  assert.ok(files.length > 50, `expected the whole repository, read ${files.length} files`);
  return files;
}

const MENTIONS_LOG = /decision[- _]log|adjudication\/decisions/i;

// A paragraph is a blank-line-separated block, and each Markdown list item is
// its own paragraph. Comment markers and line wraps are folded away so a
// sentence split across lines is matched whole.
function paragraphs(text) {
  return text
    .split(/\n[ \t]*\n|\n(?=[ \t]*[-*] )/)
    .map((p) => p.replace(/^[ \t]*(?:#|\/\/|\*)[ \t]?/gm, "").replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

function logParagraphs() {
  return repoTextFiles().flatMap(({ rel, text }) => (MENTIONS_LOG.test(text) ? paragraphs(text).filter((p) => MENTIONS_LOG.test(p)).map((p) => ({ rel, p })) : []));
}

// "never committed", "is never committed", "must not be committed", "do not
// commit": a prohibition is not an invitation.
const PROHIBITION = /\b(?:never|not|no)\b(?:\s+\w+){0,2}?\s+commit(?:s|ted|ting)?\b/gi;
// Any other commit, or a git add, in a paragraph about the log. "pre-committed"
// (the operator's answer) and "commitment" are different words.
const INVITATION = /(?<![-\w])commit(?:s|ted|ting)?\b|\bgit add\b|\bGREEN[- ]only material\b/i;

test("no file invites committing the decision log or its sidecar", () => {
  const found = logParagraphs().filter(({ p }) => INVITATION.test(p.replace(PROHIBITION, "")));
  assert.deepEqual(found.map(({ rel, p }) => `${rel}: ${p.slice(0, 200)}`), []);
});

// docs/AI_AGENTS.md once said "keep both files somewhere durable by your own
// choice", the sentence that summarized the old choice "copy it out, or commit
// it as GREEN-only material". In a cloud container the durable place in reach
// is the git remote, so every place that says how to keep the log must rule
// the repository out.
test("every instruction on where to keep the log rules the repository out", () => {
  const KEEPING = /\b(?:durable|copied out|copying both|copy (?:it|them|both)(?: files)? out|storage)\b/i;
  const RULES_OUT = /never (?:be )?committed|never commit|never enters the repository|outside the repository|out of the repository/i;
  const open = logParagraphs().filter(({ p }) => KEEPING.test(p) && !RULES_OUT.test(p));
  assert.deepEqual(open.map(({ rel, p }) => `${rel}: ${p.slice(0, 240)}`), []);
});

// The ignore-rule tests live in the adjudication suite. If gate-runner
// selected that suite only for adjudication/**, a change to .gitignore alone
// that drops the rule would run only the dash scan, never the test that would
// catch it. (The CI filter is checked in adjudication/test_decision_log.py.)
test("gate-runner runs the suite that checks the ignore rule when .gitignore changes", () => {
  const md = readFileSync(join(REPO_ROOT, ".claude/agents/gate-runner.md"), "utf8");
  const gate = md.split("\n").find((l) => l.startsWith("**Adjudication**"));
  assert.ok(gate, "gate-runner.md has no Adjudication gate line");
  assert.ok(gate.includes("`.gitignore`"), `the Adjudication gate is selected only by: ${gate.slice(0, 120)}`);
});

// ------------------------------------------------------------ R4: who holds Bash

const AGENT_DIR = join(REPO_ROOT, ".claude/agents");
const agents = readdirSync(AGENT_DIR).filter((f) => f.endsWith(".md")).map((f) => {
  const text = readFileSync(join(AGENT_DIR, f), "utf8");
  const front = /^---\n([\s\S]*?)\n---\n/.exec(text)?.[1] ?? "";
  const name = /^name:\s*(.+)$/m.exec(front)?.[1].trim();
  const tools = (/^tools:\s*(.+)$/m.exec(front)?.[1] ?? "").split(",").map((t) => t.trim()).filter(Boolean);
  return { name, tools };
});
const DOC = readFileSync(join(REPO_ROOT, "docs/AI_AGENTS.md"), "utf8");

test("the roster table lists exactly each agent's frontmatter tools", () => {
  for (const a of agents) {
    const row = DOC.split("\n").find((l) => l.startsWith(`| \`${a.name}\` |`));
    assert.ok(row, `docs/AI_AGENTS.md has no roster row for ${a.name}`);
    const cells = row.split("|").map((c) => c.trim());
    const listed = cells[4].replace(/\([^)]*\)/g, "").split(",").map((t) => t.trim()).filter(Boolean);
    assert.deepEqual([...listed].sort(), [...a.tools].sort(), `${a.name}: roster says ${cells[4]}, frontmatter says ${a.tools.join(", ")}`);
  }
});

test("the doc's count of agents holding Bash matches the frontmatter", () => {
  const WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen"];
  const m = /\b([A-Za-z]+|\d+) agents hold Bash\b/.exec(DOC);
  assert.ok(m, "docs/AI_AGENTS.md no longer says how many agents hold Bash");
  const stated = /^\d+$/.test(m[1]) ? Number(m[1]) : WORDS.indexOf(m[1].toLowerCase());
  const holders = agents.filter((a) => a.tools.includes("Bash")).map((a) => a.name);
  assert.equal(stated, holders.length, `the doc says ${m[1]}; the frontmatter gives Bash to ${holders.join(", ")}`);
});
