// Lint for the agent layer: definitions, least privilege, the shared Council
// contract, the walls, and the scan tool itself.
// Run: node --test ".claude/tests/*.test.mjs"

import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import { loadRecruitingWords, loadWalledTerms, REPO_ROOT, RuleSourceError, scanFiles, scanText } from "../tools/scan-copy.mjs";

const AGENT_DIR = join(REPO_ROOT, ".claude/agents");
const WORKFLOW_DIR = join(REPO_ROOT, ".claude/workflows");

// Tools an agent may list. An allowlist, so a new capability (an MCP send
// tool, a spawn tool) is a deliberate edit here, reviewed, not a silent drift.
const KNOWN_TOOLS = new Set(["Read", "Grep", "Glob", "Bash", "Edit", "Write", "WebFetch", "WebSearch"]);
const WRITE_TOOLS = ["Edit", "Write", "NotebookEdit"];
const MODELS = new Set(["inherit", "sonnet", "opus", "haiku", "fable"]);
const COLORS = new Set(["red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"]);

// Separation of duties: the agents that check work never change it.
const READ_ONLY = new Set([
  "council-evidence-scout", "council-contrarian", "council-first-principles", "council-expansionist",
  "council-executor", "council-steward", "council-chairman", "gate-runner", "claim-auditor",
  "fmea-engineer", "reliability-statistician", "guardrail-auditor",
]);
const COUNCIL_SEATS = ["council-contrarian", "council-first-principles", "council-expansionist", "council-executor", "council-steward", "council-chairman"];
const COUNCIL = ["council-evidence-scout", ...COUNCIL_SEATS];

function parseAgent(file) {
  const text = readFileSync(join(AGENT_DIR, file), "utf8");
  const m = /^---\n([\s\S]*?)\n---\n/.exec(text);
  if (!m) return { file, text, front: null, body: text };
  const front = {};
  for (const line of m[1].split("\n")) {
    const kv = /^([A-Za-z]+):\s*(.*)$/.exec(line);
    assert.ok(kv, `${file}: frontmatter line is not "key: value": ${line}`);
    front[kv[1]] = kv[2];
  }
  return { file, text, front, body: text.slice(m[0].length) };
}

const agents = readdirSync(AGENT_DIR).filter((f) => f.endsWith(".md")).map(parseAgent);
const byName = Object.fromEntries(agents.map((a) => [a.front?.name, a]));
const toolsOf = (a) => a.front.tools.split(",").map((t) => t.trim()).filter(Boolean);

test("every agent file has valid frontmatter and a name matching its file", () => {
  assert.ok(agents.length >= 16, `expected the full roster, found ${agents.length}`);
  for (const a of agents) {
    assert.ok(a.front, `${a.file}: no frontmatter (it would be ignored as documentation)`);
    assert.equal(`${a.front.name}.md`, a.file);
    assert.match(a.front.name, /^[a-z][a-z-]*$/);
    assert.ok(a.front.description?.length >= 80, `${a.file}: description too thin to route on`);
    assert.ok(a.front.description.length <= 1024, `${a.file}: description too long`);
    assert.ok(MODELS.has(a.front.model), `${a.file}: model ${a.front.model}`);
    assert.ok(COLORS.has(a.front.color), `${a.file}: color ${a.front.color}`);
    assert.ok(a.body.trim().length > 400, `${a.file}: body too thin to be a real instruction set`);
  }
});

test("every agent declares its tools explicitly, from the allowlist", () => {
  for (const a of agents) {
    assert.ok(a.front.tools, `${a.file}: tools omitted, so it would inherit every tool including MCP send tools`);
    for (const t of toolsOf(a)) assert.ok(KNOWN_TOOLS.has(t), `${a.file}: tool ${t} is not on the allowlist`);
  }
});

test("checkers never hold write tools (separation of duties)", () => {
  for (const name of READ_ONLY) {
    const a = byName[name];
    assert.ok(a, `missing agent ${name}`);
    for (const t of WRITE_TOOLS) assert.ok(!toolsOf(a).includes(t), `${name} must not hold ${t}`);
  }
});

test("Council seats reason over the packet: no shell and no independent retrieval", () => {
  for (const name of COUNCIL_SEATS) {
    assert.deepEqual(toolsOf(byName[name]).sort(), ["Glob", "Grep", "Read"], `${name} tools`);
  }
});

function contractBlock(a) {
  const body = a.body.trimStart();
  const end = body.indexOf("\n# ");
  assert.ok(body.startsWith("## Operating contract"), `${a.file}: the operating contract must open the body (v13: at the top of every seat)`);
  assert.ok(end > 0, `${a.file}: seat heading after the contract not found`);
  return body.slice(0, end);
}

test("all seven Council agents carry the identical operating contract", () => {
  const blocks = COUNCIL.map((n) => contractBlock(byName[n]));
  for (const [i, b] of blocks.entries()) assert.equal(b, blocks[0], `${COUNCIL[i]} contract drifted from ${COUNCIL[0]}`);
  for (const phrase of ["Use no numeric probability of success", "Zero-Defects self-check", "professional verification required", "shared-model cap", "No em-dashes or en-dashes"]) {
    assert.ok(blocks[0].includes(phrase), `contract lost: ${phrase}`);
  }
});

test("only the reliability statistician may be told to state percentages", () => {
  const stat = byName["reliability-statistician"].text;
  assert.match(stat, /only agent permitted to state a percentage/);
  assert.match(stat, /Wilson/);
});

test("every agentType a saved workflow names exists as an agent", () => {
  for (const f of readdirSync(WORKFLOW_DIR).filter((x) => x.endsWith(".js"))) {
    const src = readFileSync(join(WORKFLOW_DIR, f), "utf8");
    const named = [...src.matchAll(/agentType:\s*'([a-z-]+)'/g)].map((m) => m[1]);
    assert.ok(named.length > 0 || !src.includes("agentType"), `${f}: agentType used but none parsed`);
    for (const t of named) assert.ok(byName[t], `${f} names agentType ${t}, which has no .claude/agents/${t}.md`);
  }
});

test("the roster doc names every agent", () => {
  const doc = readFileSync(join(REPO_ROOT, "docs/AI_AGENTS.md"), "utf8");
  for (const a of agents) assert.ok(doc.includes(`\`${a.front.name}\``), `docs/AI_AGENTS.md does not list ${a.front.name}`);
});

test("CLAUDE.md routes to the roster, and every name it routes to exists", () => {
  const md = readFileSync(join(REPO_ROOT, "CLAUDE.md"), "utf8");
  assert.ok(md.includes("docs/AI_AGENTS.md"));
  // Every backticked hyphenated name must be an agent or a saved workflow, so a
  // typo cannot hide behind a prefix filter.
  const workflows = new Set(readdirSync(WORKFLOW_DIR).filter((f) => f.endsWith(".js")).map((f) => f.slice(0, -3)));
  const named = [...md.matchAll(/`([a-z]+(?:-[a-z]+)+)`/g)].map((m) => m[1]);
  assert.ok(named.length >= 10);
  for (const n of named) assert.ok(byName[n] || workflows.has(n), `CLAUDE.md names ${n}, which is neither an agent nor a saved workflow`);
  for (const a of agents) assert.ok(named.includes(a.front.name), `CLAUDE.md never routes to ${a.front.name}`);
});

// ------------------------------------------------------------ the walls

const LAYER_FILES = [
  ...readdirSync(AGENT_DIR).map((f) => `.claude/agents/${f}`),
  ...readdirSync(WORKFLOW_DIR).map((f) => `.claude/workflows/${f}`),
  ".claude/tools/scan-copy.mjs",
  ".claude/tests/agents.test.mjs",
  ".claude/tests/full-council.test.mjs",
  ".claude/tests/lib/workflow-harness.mjs",
  "CLAUDE.md",
  "docs/AI_AGENTS.md",
  "adjudication/decision_log.py",
  "adjudication/test_decision_log.py",
  "adjudication/eval/numeric-audit-v1.json",
  ".github/workflows/agents.yml",
];

test("the agent layer carries no dashes and no walled internal names", () => {
  const findings = scanFiles(LAYER_FILES);
  assert.deepEqual(findings, [], findings.map((f) => `${f.path}:${f.line} ${f.rule} ${f.detail}`).join("\n"));
});

// ------------------------------------------------------------ the scan tool

test("the walled list and the recruiting list load from the Dart tests", () => {
  assert.ok(loadWalledTerms().length > 0);
  const words = loadRecruitingWords();
  assert.ok(words.includes("candidate"));
});

test("scanText finds dashes, and recruiting words only in copy mode", () => {
  const em = String.fromCharCode(0x2014);
  const en = String.fromCharCode(0x2013);
  const text = `fine line\nwe are hiring ${em} now\nrange 1${en}2`;
  const plain = scanText(text, { walled: [], recruiting: null });
  assert.deepEqual(plain.map((f) => [f.line, f.rule, f.detail]), [[2, "dash", "em dash"], [3, "dash", "en dash"]]);
  const copy = scanText(text, { walled: [], recruiting: ["hiring"] });
  assert.ok(copy.some((f) => f.rule === "recruiting-vocabulary" && f.line === 2));
});

test("recruiting words inside embedded data URIs are not copy", () => {
  const findings = scanText('<img src="data:image/png;base64,QUJDaGlyaW5nWFla">', { walled: [], recruiting: ["hiring"] });
  assert.deepEqual(findings, []);
});

test("walled terms are matched case-insensitively in content and path, and never printed", () => {
  const findings = scanText("a Probe-Term here", { path: "dir/probe-term.txt", walled: ["PROBE-TERM"] });
  assert.deepEqual(findings.map((f) => f.detail), ["walled term #1 in file path", "walled term #1"]);
  assert.ok(findings.every((f) => !/probe/i.test(f.detail)));
});

test("a missing or empty rule source fails closed", () => {
  const root = mkdtempSync(join(tmpdir(), "scan-"));
  assert.throws(() => loadWalledTerms(root), RuleSourceError);
  mkdirSync(join(root, "test/copy"), { recursive: true });
  writeFileSync(join(root, "test/copy/walled_repo_test.dart"), "final List<String> _banned = <String>[\n];\n");
  assert.throws(() => loadWalledTerms(root), /empty/);
  writeFileSync(join(root, "test/copy/walled_repo_test.dart"), "no list here");
  assert.throws(() => loadWalledTerms(root), /not found/);
  assert.throws(() => loadRecruitingWords(root), RuleSourceError);
});

test("scanFiles reports an unreadable file instead of calling it clean", () => {
  const findings = scanFiles(["no/such/file.txt"]);
  assert.equal(findings.length, 1);
  assert.equal(findings[0].rule, "unreadable");
});
