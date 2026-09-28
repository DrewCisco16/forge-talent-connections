// The DOI lookup that claim-auditor and council-evidence-scout run on a DOI
// copied from untrusted text (a web page, a search result, a document).
//
// A shell command cannot carry arbitrary pasted text safely: a pasted line
// equal to a heredoc delimiter ends the data and the shell runs whatever
// follows it, and quoting of any kind has its own escape. So the guarantee is
// structural. No agent file puts a DOI slot in a code block, both agents look
// DOIs up with WebFetch only, and the evidence scout, which reads the open
// web, holds no Bash at all.
//
// Run: node --test ".claude/tests/*.test.mjs"

import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const AGENT_DIR = join(REPO_ROOT, ".claude/agents");
const LOOKUP_AGENTS = ["claim-auditor", "council-evidence-scout"];

const agents = readdirSync(AGENT_DIR).filter((f) => f.endsWith(".md")).map((f) => {
  const text = readFileSync(join(AGENT_DIR, f), "utf8");
  const front = /^---\n([\s\S]*?)\n---\n/.exec(text)?.[1] ?? "";
  const tools = (/^tools:\s*(.+)$/m.exec(front)?.[1] ?? "").split(",").map((t) => t.trim()).filter(Boolean);
  return { name: f.replace(/\.md$/, ""), text, tools };
});
const byName = Object.fromEntries(agents.map((a) => [a.name, a]));
const codeBlocks = (text) => [...text.matchAll(/```[^\n]*\n([\s\S]*?)```/g)].map((m) => m[1]);

test("no agent file puts a DOI slot in a code block", () => {
  assert.ok(agents.length >= LOOKUP_AGENTS.length, `read only ${agents.length} agent files`);
  for (const a of agents) {
    for (const block of codeBlocks(a.text)) {
      assert.ok(!/<DOI>|\{doi\}|\$\{?DOI\b/i.test(block), `${a.name}: a code block carries a DOI slot:\n${block}`);
    }
  }
});

test("the evidence scout, which reads the open web, holds no Bash", () => {
  const scout = byName["council-evidence-scout"];
  assert.ok(scout, "missing council-evidence-scout");
  assert.ok(!scout.tools.includes("Bash"), `council-evidence-scout holds ${scout.tools.join(", ")}`);
});

test("the claim auditor keeps audited text out of its shell commands", () => {
  const auditor = byName["claim-auditor"];
  assert.ok(auditor, "missing claim-auditor");
  assert.match(auditor.text, /never paste text from the audited material into a shell command/);
});

for (const name of LOOKUP_AGENTS) {
  test(`${name}: DOIs are looked up with WebFetch only, never in a shell command`, () => {
    const a = byName[name];
    assert.ok(a, `missing ${name}`);
    assert.ok(a.tools.includes("WebFetch"), `${name} needs WebFetch for the lookup`);
    assert.match(a.text, /never put it in a shell command/, `${name} no longer forbids a DOI in a shell command`);
    assert.match(a.text, /WebFetch only/, `${name} no longer confines the lookup to WebFetch`);
    assert.ok(a.text.includes("https://api.crossref.org/works/<DOI>"), `${name}: the Crossref lookup is not named`);
    assert.ok(a.text.includes("https://doi.org/<DOI>"), `${name}: the doi.org fallback is not named`);
  });

  test(`${name}: no sentence lets a BLOCKED lookup count as verified`, () => {
    // A tripwire, not a proof: a planted "treat BLOCKED as verified" passed
    // every phrase check in this file. Any sentence that speaks of BLOCKED and
    // verification together must forbid it or send it to manual verification.
    const sentences = byName[name].text.replace(/\s+/g, " ").split(/(?<=[.!?])\s+(?=[A-Z0-9*`(])/);
    const loose = sentences.filter((s) => /BLOCKED/.test(s) && /verif/i.test(s) && !/\bnever\b|MANUAL VERIFICATION|Manual verification/.test(s));
    assert.deepEqual(loose, [], `${name}: BLOCKED near verification without a prohibition`);
  });

  test(`${name}: every lookup outcome is named, and BLOCKED is never read as absence or as verified`, () => {
    const { text } = byName[name];
    for (const outcome of ["NOT REGISTERED", "BLOCKED"]) assert.ok(text.includes(outcome), `${name} never says what ${outcome} means`);
    assert.match(text, /BLOCKED[^\n]*(?:not evidence of absence|says nothing about the paper)/, `${name}: BLOCKED must be read as not evidence of absence`);
    assert.match(text, /[Mm]anual verification required|MANUAL VERIFICATION REQUIRED/, `${name}: a blocked lookup must end in manual verification`);
  });
}
