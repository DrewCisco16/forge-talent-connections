// Lint for the agent layer: definitions, least privilege, the shared Council
// contract, the walls, and the scan tool itself.
// Run: node --test ".claude/tests/*.test.mjs"

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative } from "node:path";
import { test } from "node:test";

import { decodeText, loadRecruitingWords, loadWalledTerms, REPO_ROOT, RuleSourceError, scanFiles, scanText } from "../tools/scan-copy.mjs";

const AGENT_DIR = join(REPO_ROOT, ".claude/agents");
const WORKFLOW_DIR = join(REPO_ROOT, ".claude/workflows");

// Tools an agent may list. An allowlist, so a new capability (an MCP send
// tool, a spawn tool) is a deliberate edit here, reviewed, not a silent drift.
const KNOWN_TOOLS = new Set(["Read", "Grep", "Glob", "Bash", "Edit", "Write", "WebFetch", "WebSearch"]);
const WRITE_TOOLS = ["Edit", "Write", "NotebookEdit"];
const MODELS = new Set(["inherit", "sonnet", "opus", "haiku", "fable"]);
// Frontmatter keys an agent may carry. Everything else (permissionMode, hooks,
// mcpServers, skills, memory, isolation, ...) changes what an agent can do and
// must be a deliberate edit to this list, not something the tool check misses.
const FRONTMATTER_KEYS = new Set(["name", "description", "tools", "model", "color"]);
const COLORS = new Set(["red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"]);

// Separation of duties: the agents that check work never change it.
const READ_ONLY = new Set([
  "council-evidence-scout", "council-contrarian", "council-first-principles", "council-expansionist",
  "council-executor", "council-steward", "council-chairman", "gate-runner", "claim-auditor",
  "fmea-engineer", "reliability-statistician", "guardrail-auditor",
]);
// Bash can write files, so it is a capability, not a reading tool. Only the
// checkers whose job is to run commands hold it, and they are restricted to
// read-only use by instruction (the statistician also writes the decision log
// through its command line). That restriction is prompt-level, not enforced.
const BASH_CHECKERS = new Set(["council-evidence-scout", "gate-runner", "claim-auditor", "guardrail-auditor", "reliability-statistician"]);
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
    for (const key of Object.keys(a.front)) {
      assert.ok(FRONTMATTER_KEYS.has(key), `${a.file}: frontmatter key ${key} is not on the allowlist`);
    }
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

test("checkers hold no editing tools, and only the five that must run commands hold Bash", () => {
  for (const name of READ_ONLY) {
    const a = byName[name];
    assert.ok(a, `missing agent ${name}`);
    for (const t of WRITE_TOOLS) assert.ok(!toolsOf(a).includes(t), `${name} must not hold ${t}`);
    assert.equal(toolsOf(a).includes("Bash"), BASH_CHECKERS.has(name), `${name}: Bash ${BASH_CHECKERS.has(name) ? "required" : "not allowed"}`);
  }
});

test("no agent but the statistician is told to state a probability or a percentage", () => {
  const asks = [/\bstate (?:the |a )?(?:probability|percentage|likelihood)\b/i, /\bas a percentage\b/i, /\bpercent(?:age)? chance\b/i,
    /\b(?:give|report|estimate) (?:the |a )?(?:probability|likelihood|chance) of success\b/i];
  for (const a of agents.filter((x) => x.front.name !== "reliability-statistician")) {
    for (const re of asks) assert.ok(!re.test(a.body), `${a.file} asks for a probability: ${re}`);
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

// DISCOVERY, NOT A LIST, for .claude/: a file added there tomorrow is scanned
// without anyone remembering to add it.
function walk(dir) {
  return readdirSync(dir).flatMap((f) => {
    const full = join(dir, f);
    return statSync(full).isDirectory() ? walk(full) : [relative(REPO_ROOT, full)];
  });
}

const LAYER_FILES = [
  ...walk(join(REPO_ROOT, ".claude")),
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

test("the wall scan discovers new files under .claude/", () => {
  for (const f of [".claude/agents/gate-runner.md", ".claude/tests/lib/workflow-harness.mjs", ".claude/tools/scan-copy.mjs"]) {
    assert.ok(LAYER_FILES.includes(f), `${f} not discovered`);
  }
});

test("HTML entity dashes count as dashes", () => {
  // Built at runtime so this file holds no entity the wall scan would flag.
  const [mdash, n8211, x2014, ndash] = ["mdash;", "#8211;", "#x2014;", "NDASH;"].map((e) => `&${e}`);
  const found = scanText(`a ${mdash} b ${n8211} c ${x2014} d ${ndash}`, { walled: [] });
  assert.deepEqual(found.map((f) => f.detail), ["em dash (HTML entity)", "en dash (HTML entity)", "em dash (HTML entity)", "en dash (HTML entity)"]);
});

test("UTF-16 text is decoded before scanning, and NUL bytes without a BOM are unreadable", () => {
  const em = String.fromCharCode(0x2014);
  const le = Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from(`x ${em} y`, "utf16le")]);
  const be = Buffer.from(le);
  be.swap16();
  be[0] = 0xfe;
  be[1] = 0xff;
  assert.equal(decodeText(le), `x ${em} y`);
  assert.equal(decodeText(Buffer.concat([Buffer.from([0xfe, 0xff]), Buffer.from(`x ${em} y`, "utf16le").swap16()])), `x ${em} y`);
  assert.equal(decodeText(Buffer.from([0xef, 0xbb, 0xbf, 0x61])), "a");
  assert.equal(decodeText(Buffer.from([0x61, 0x00, 0x62])), null);
  const dir = mkdtempSync(join(tmpdir(), "scan-"));
  writeFileSync(join(dir, "u16.txt"), le);
  writeFileSync(join(dir, "bin.txt"), Buffer.from([0x61, 0x00, 0x62]));
  const found = scanFiles([join(dir, "u16.txt"), join(dir, "bin.txt")]);
  assert.ok(found.some((f) => f.rule === "dash"));
  assert.ok(found.some((f) => f.rule === "unreadable" && /encoding/.test(f.detail)));
});

function syntheticRoot(entries) {
  const root = mkdtempSync(join(tmpdir(), "scan-root-"));
  mkdirSync(join(root, "test/copy"), { recursive: true });
  writeFileSync(join(root, "test/copy/walled_repo_test.dart"),
    `final List<String> _banned = <String>[\n${entries.map((e) => `  "${e}",`).join("\n")}\n].map((String e) => e).toList();\n`);
  writeFileSync(join(root, "test/copy/product_language_test.dart"), 'const List<String> _bannedWords = <String>[\n  "hire",\n];\n');
  return root;
}

test("base64url rule entries are decoded, and an undecodable entry stops the scan", () => {
  const term = "Probe~Term?";
  const urlSafe = Buffer.from(term).toString("base64url");
  assert.ok(/[-_]/.test(urlSafe), "fixture must exercise the url-safe alphabet");
  assert.deepEqual(loadWalledTerms(syntheticRoot([urlSafe])), [term.toUpperCase()]);
  assert.throws(() => loadWalledTerms(syntheticRoot(["not base64!"])), /entry #1 is not base64/);
});

test("a file whose path holds a walled term is reported without printing the path", () => {
  const root = syntheticRoot([Buffer.from("probewall").toString("base64")]);
  mkdirSync(join(root, "docs"));
  writeFileSync(join(root, "docs/probewall-notes.md"), "clean text\n");
  const found = scanFiles(["docs/probewall-notes.md"], { root });
  assert.equal(found.length, 1);
  assert.ok(!/probewall/i.test(found[0].path), found[0].path);
});

const TOOL = join(REPO_ROOT, ".claude/tools/scan-copy.mjs");
const cli = (args) => spawnSync(process.execPath, [TOOL, ...args], { cwd: REPO_ROOT, encoding: "utf8" });

test("the scan tool's exit codes: 0 clean, 1 findings, 2 not run, and every file argument is scanned", () => {
  const dir = mkdtempSync(join(tmpdir(), "scan-cli-"));
  writeFileSync(join(dir, "a.txt"), "clean\n");
  writeFileSync(join(dir, "b.txt"), "clean\n");
  writeFileSync(join(dir, "c.txt"), `dash ${String.fromCharCode(0x2013)} here\n`);
  const clean = cli([join(dir, "a.txt"), join(dir, "b.txt")]);
  assert.equal(clean.status, 0);
  assert.match(clean.stdout, /CLEAN: 2 file\(s\)/);
  const first = cli([join(dir, "c.txt"), join(dir, "a.txt")]);
  assert.equal(first.status, 1, "the first file argument must be scanned too");
  assert.equal(cli([join(dir, "missing.txt")]).status, 2);
  const noRules = cli(["--root", mkdtempSync(join(tmpdir(), "empty-")), join(dir, "a.txt")]);
  assert.equal(noRules.status, 2);
  assert.match(noRules.stderr, /SCAN NOT RUN/);
  assert.doesNotMatch(noRules.stdout, /CLEAN/);
  assert.equal(cli([]).status, 2);
  assert.equal(cli(["--root"]).status, 2);
  assert.equal(cli(["--copy", "--root", REPO_ROOT, join(dir, "a.txt")]).status, 0);
});

test("scanFiles reports an unreadable file instead of calling it clean", () => {
  const findings = scanFiles(["no/such/file.txt"]);
  assert.equal(findings.length, 1);
  assert.equal(findings[0].rule, "unreadable");
});
