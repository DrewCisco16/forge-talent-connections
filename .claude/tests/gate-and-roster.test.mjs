// Adversarial review of R2, R3, and R4: what decision-log-policy.test.mjs and
// agents.test.mjs do not reach.
//
// The gate-runner tests and the read-only test each failed against the first
// version of this change and pass once the gap they name is closed. The
// invitation, Bash-holder, and roster tests each close a hole a planted
// mutation walked through.
//
// Run: node --test ".claude/tests/*.test.mjs"

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const SELF = relative(REPO_ROOT, fileURLToPath(import.meta.url));
const SCAN = join(REPO_ROOT, ".claude/tools/scan-copy.mjs");
const AGENT_DIR = join(REPO_ROOT, ".claude/agents");
const GATE = readFileSync(join(AGENT_DIR, "gate-runner.md"), "utf8");
const DOC = readFileSync(join(REPO_ROOT, "docs/AI_AGENTS.md"), "utf8");

const agents = readdirSync(AGENT_DIR).filter((f) => f.endsWith(".md")).map((f) => {
  const text = readFileSync(join(AGENT_DIR, f), "utf8");
  const m = /^---\n([\s\S]*?)\n---\n/.exec(text);
  const tools = (/^tools:\s*(.+)$/m.exec(m?.[1] ?? "")?.[1] ?? "").split(",").map((t) => t.trim()).filter(Boolean);
  return { name: f.replace(/\.md$/, ""), body: m ? text.slice(m[0].length) : text, tools };
});
const sentences = (text) => text.replace(/\s+/g, " ").split(/(?<=[.!?])\s+(?=[A-Z0-9*`(])/);
const gateLine = (label) => {
  const line = GATE.split("\n").find((l) => l.startsWith(label));
  assert.ok(line, `gate-runner.md has no line starting ${label}`);
  return line;
};

// ------------------------------------------------------------ R2 in the gate

test("gate-runner runs the no-invitation scan when only .gitignore changes", () => {
  // The .gitignore comment held the invitation this change removed. The test
  // that forbids it lives in .claude/tests, which the Agent layer gate runs,
  // and that gate is not selected by .gitignore.
  const line = gateLine("**Agent layer**");
  assert.ok(line.includes(".gitignore"), `the Agent layer gate is selected only by: ${line.slice(0, 140)}`);
});

test("gate-runner selects the ignore-rule suite for a .gitignore at any depth", () => {
  // A nested .gitignore outranks the root one: `!decision-log.jsonl*` in
  // android/.gitignore re-includes the log under android/. The Adjudication
  // gate names `.gitignore`, which reads as the root file.
  const line = gateLine("**Adjudication**");
  assert.match(line, /`\*\*\/\.gitignore`|\b(?:any|every|each)\s+`?\.gitignore`?|\.gitignore`?\s+(?:files?\s+)?at any depth|nested\s+`?\.gitignore/i,
    `the Adjudication gate does not name a nested .gitignore: ${line.slice(0, 160)}`);
});

// ------------------------------------------------------------ R3

test("gate-runner lists untracked files one by one, so a file in a new directory is scanned", () => {
  // The trigger. git's default untracked mode reports a new directory as one
  // entry, and the scan cannot read a directory (exit 2, NOT RUN). An agent
  // that drops the entry as "not a text file" scans nothing inside it.
  const dir = mkdtempSync(join(tmpdir(), "gate-porcelain-"));
  const git = (...args) => spawnSync("git", ["-c", "status.showUntrackedFiles=normal", "-C", dir, ...args], { encoding: "utf8" });
  assert.equal(git("init", "-q").status, 0);
  mkdirSync(join(dir, "docs/notes"), { recursive: true });
  writeFileSync(join(dir, "docs/notes/new.md"), `a ${String.fromCharCode(0x2014)} b\n`);
  assert.equal(git("status", "--porcelain").stdout.trim(), "?? docs/");
  assert.equal(git("status", "--porcelain", "--untracked-files=all").stdout.trim(), "?? docs/notes/new.md");
  assert.equal(spawnSync(process.execPath, [SCAN, join(dir, "docs/")], { encoding: "utf8" }).status, 2);
  assert.equal(spawnSync(process.execPath, [SCAN, join(dir, "docs/notes/new.md")], { encoding: "utf8" }).status, 1);
  assert.match(GATE, /--untracked-files=all|\s-uall\b|ls-files[^\n]*--others/,
    "gate-runner.md finds the change set with plain `git status --porcelain`, which hides every file inside a new directory");
});

test("gate-runner says what a change set it could not compute does to the run", () => {
  // `git diff --name-only origin/main...HEAD` fails when origin/main is absent
  // and cannot be fetched (a sandbox without egress). What is left is the
  // uncommitted files only: every committed change on the branch goes
  // unscanned, and nothing says the run is then INCOMPLETE.
  const ok = sentences(GATE).some((s) => /origin|fetch/i.test(s) && /\b(?:fails?|cannot|could not|unavailable|unreachable)\b/i.test(s) && /NOT RUN|INCOMPLETE|full run/.test(s));
  assert.ok(ok, "gate-runner.md never says what happens when origin/main cannot be fetched");
});

test("gate-runner keeps deleted paths out of the scan", () => {
  // Both change-set commands list deleted files. One deleted path makes the
  // scan exit 2 for the whole list, so any change that deletes a text file
  // outside lib/ can never scan clean.
  const dir = mkdtempSync(join(tmpdir(), "gate-deleted-"));
  writeFileSync(join(dir, "kept.md"), "clean\n");
  assert.equal(spawnSync(process.execPath, [SCAN, join(dir, "kept.md"), join(dir, "deleted.md")], { encoding: "utf8" }).status, 2);
  assert.match(GATE, /--diff-filter=[A-Za-z]*d|deleted (?:paths?|files?)[^.]*(?:not|never|skip|exclude|leave)|(?:skip|exclude|leave out|drop)[^.]*deleted/i,
    "gate-runner.md passes every changed path to the scan, deleted ones included");
});

test("gate-runner reads exit 2 as a file it could not read, too", () => {
  // The trigger: a real finding next to an unreadable path exits 2 with the
  // finding printed. gate-runner.md says exit 2 "means the scan could not load
  // its rules", so the report names the wrong cause and INCOMPLETE hides a
  // finding that is a FAIL.
  const dir = mkdtempSync(join(tmpdir(), "gate-exit2-"));
  writeFileSync(join(dir, "dash.md"), `a ${String.fromCharCode(0x2014)} b\n`);
  const r = spawnSync(process.execPath, [SCAN, join(dir, "dash.md"), join(dir, "deleted.md")], { encoding: "utf8" });
  assert.equal(r.status, 2);
  assert.match(r.stdout, /em dash/);
  assert.match(GATE, /exit 2[^.]*(?:unreadable|could not (?:be )?read|cannot read|missing|not found)/i,
    "gate-runner.md explains exit 2 only as rules that could not load");
});

// ------------------------------------------------------------ R2 in the text

// A prohibition is a negation followed directly by the verb, allowing only
// auxiliaries and articles between. The policy test allows any two words, so
// "Do not forget to <verb> both files" reads there as a prohibition.
// Verbs are assembled at runtime so this file holds no sentence the policy
// test would read as an invitation.
const C = ["com", "mit"].join("");
const OBJ = "(?:it|them|both files|the log|the decision log|the sidecar|the two files|these files)";
const PLACE = "(?:the |this |your )?(?:repository|repo|git|branch|remote)";
const ACT = new RegExp([
  `(?<![-\\w])${C}(?:s|ted|ting)?\\b`,
  "\\bgit add\\b",
  "\\bGREEN[- ]only material\\b",
  `\\bcheck(?:s|ed|ing)? ${OBJ} in(?:to)?\\b`,
  `\\bcheck(?:s|ed|ing)? in ${OBJ}\\b`,
  `\\bpush(?:es|ed|ing)? ${OBJ}\\b`,
  `\\badd(?:s|ed|ing)? ${OBJ} to ${PLACE}\\b`,
  `\\b(?:keep|store|save|put|leave|place)(?:s|ing)? ${OBJ}[^.;]{0,40}\\b(?:in|into|under|on) ${PLACE}\\b`,
  "\\btrack(?:s|ed|ing)?\\b(?! record)",
  "\\bversion(?:ed)? (?:it|them|both files|the log)\\b",
].join("|"), "gi");
const NEG_TAIL = /\b(?:never|not|no|nor|n't)(?:\s+(?:be|been|being|get|gets|got|ever|a|an|the|is|are|was|were))*\s+$/i;
const MENTIONS = /decision[- _]log|adjudication\/decisions|\.head sidecar/i;
const invitations = (p) => [...p.matchAll(ACT)].filter((m) => !NEG_TAIL.test(p.slice(Math.max(0, m.index - 60), m.index))).map((m) => m[0]);

function paragraphs(text) {
  return text.split(/\n[ \t]*\n|\n(?=[ \t]*[-*] )/)
    .map((p) => p.replace(/^[ \t]*(?:#|\/\/|\*)[ \t]?/gm, "").replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

test("no paragraph about the log invites keeping it in git, however phrased", () => {
  // The detector itself, on phrasings the policy test lets through.
  const log = "the decision log";
  for (const p of [`Do not forget to ${C} both files of ${log}.`, `Keep both files in the repository with ${log}.`,
    `Check them into git: ${log}.`, `Push the log to your branch, ${log} included.`]) {
    assert.ok(invitations(p).length > 0, `missed: ${p}`);
  }
  for (const p of [`It is never ${C}ted: ${log}.`, `${log} must not be ${C}ted.`, `use ${log} path, never a tracked path.`]) {
    assert.deepEqual(invitations(p), [], `a prohibition read as an invitation: ${p}`);
  }
  // Files that state the rule quote what it forbids.
  const skip = new Set([SELF, ".claude/tests/decision-log-policy.test.mjs"]);
  const r = spawnSync("git", ["-C", REPO_ROOT, "ls-files", "-z", "--cached", "--others", "--exclude-standard"], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  assert.equal(r.status, 0, r.stderr);
  const found = [];
  let read = 0;
  for (const rel of r.stdout.split("\0").filter((f) => f && !skip.has(f))) {
    let buf;
    try {
      if (statSync(join(REPO_ROOT, rel)).size > 4 * 1024 * 1024) continue;
      buf = readFileSync(join(REPO_ROOT, rel));
    } catch {
      continue;
    }
    if (buf.includes(0)) continue;
    read += 1;
    const text = buf.toString("utf8");
    if (!MENTIONS.test(text)) continue;
    for (const p of paragraphs(text).filter((x) => MENTIONS.test(x))) {
      for (const hit of invitations(p)) found.push(`${rel}: [${hit}] ${p.slice(0, 160)}`);
    }
  }
  assert.ok(read > 50, `expected the whole repository, read ${read} files`);
  assert.deepEqual(found, []);
});

// ------------------------------------------------------------ R4

const WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen"];
const num = (w) => (/^\d+$/.test(w) ? Number(w) : WORDS.indexOf(w.toLowerCase()));
const holders = agents.filter((a) => a.tools.includes("Bash"));
const holderNames = holders.map((a) => a.name).sort();
const isBuilder = (n) => n.endsWith("-builder");
const checkersWithBash = holders.filter((a) => !a.tools.includes("Edit") && !a.tools.includes("Write")).map((a) => a.name);
const lastWord = (n) => n.replace(/^council-/, "").split("-").at(-1);
const aliases = (n) => {
  const prose = n.replace(/^council-/, "").replace(/-/g, " ");
  return agents.filter((a) => lastWord(a.name) === lastWord(n)).length === 1 ? [prose, lastWord(n)] : [prose];
};
const named = (list) => {
  const hit = new Set(agents.filter((a) => aliases(a.name).some((al) => new RegExp(`\\b${al}\\b`, "i").test(list))).map((a) => a.name));
  if (/\bbuilders\b/i.test(list)) for (const a of agents) if (isBuilder(a.name)) hit.add(a.name);
  return [...hit].sort();
};

test("every count and list of Bash holders in the doc matches the frontmatter", () => {
  // The policy test reads the first "N agents hold Bash" only, and never the
  // list after it: "four checkers (the gate runner, claim auditor, fmea
  // engineer, and statistician)" passes it, and so does a second, stale
  // "The five checkers that hold Bash" anywhere in the doc.
  const doc = DOC.replace(/\s+/g, " ");
  const counts = [...doc.matchAll(/\b([A-Za-z]+|\d+)\s+(agents|checkers|builders)(?:\s+that)?\s+holds?\s+Bash\b/gi)];
  assert.ok(counts.length > 0, "the doc no longer counts the agents that hold Bash");
  const expected = { agents: holderNames.length, checkers: checkersWithBash.length, builders: holders.filter((a) => isBuilder(a.name)).length };
  for (const m of counts) assert.equal(num(m[1]), expected[m[2].toLowerCase()], `the doc says "${m[0]}"; the frontmatter gives ${expected[m[2].toLowerCase()]}`);
  const lists = sentences(doc).filter((s) => /\bholds? Bash:/.test(s));
  assert.ok(lists.length > 0, "the doc no longer lists the agents that hold Bash");
  for (const s of lists) {
    const list = s.slice(s.indexOf("Bash:") + 5);
    assert.deepEqual(named(list), holderNames, `the doc lists: ${list}`);
    for (const m of list.matchAll(/\b([A-Za-z]+|\d+) (builders|checkers)\b/gi)) {
      const want = m[2].toLowerCase() === "builders" ? agents.filter((a) => isBuilder(a.name)).length : checkersWithBash.length;
      assert.equal(num(m[1]), want, `"${m[0]}" in: ${list}`);
    }
  }
  for (const m of doc.matchAll(/\bThe ([a-z ]+?), [^.,]*, holds none\b/g)) {
    const who = named(m[1]);
    assert.equal(who.length, 1, `cannot tell which agent "${m[1]}" is`);
    assert.ok(!holderNames.includes(who[0]), `the doc says ${who[0]} holds no Bash`);
  }
});

test("every roster row names an agent that exists", () => {
  // Both roster tests walk the frontmatter, so a row left behind for a removed
  // or renamed agent, with Bash in its tools column, passes them.
  const rows = [...DOC.matchAll(/^\| `([a-z][a-z-]*)` \|/gm)].map((m) => m[1]);
  assert.ok(rows.length >= agents.length, `read ${rows.length} roster rows`);
  const names = new Set(agents.map((a) => a.name));
  assert.deepEqual(rows.filter((r) => !names.has(r)), []);
});

test("every checker the doc says is told to use Bash read-only is told so", () => {
  // docs/AI_AGENTS.md: "The checkers are told to use it read-only (the
  // statistician also writes the decision log through its command line)".
  if (!/checkers are told to use it read-only/i.test(DOC.replace(/\s+/g, " "))) return;
  const RULE = /\bread-only\b|\bNever edit, create, or delete\b|\bUse Bash only for\b/i;
  const untold = holders.filter((a) => checkersWithBash.includes(a.name) && !RULE.test(a.body)).map((a) => a.name);
  assert.deepEqual(untold, [], "these checkers hold Bash and are never told to use it read-only");
});
