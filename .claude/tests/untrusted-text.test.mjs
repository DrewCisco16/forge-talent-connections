// Adversarial review of R1: what doi-check.test.mjs does not reach.
//
// R1: a DOI, or any other text taken from a web page, a search result, or an
// audited document, never reaches a shell or is executed, whatever characters
// it contains; the lookup still tells registered from unregistered from
// blocked, and each outcome leads to a stated verdict in both agents.
//
// Each test below failed against the first WebFetch version of the lookup and
// passes once the gap it names is closed; "a DOI slot appears only inside a
// lookup URL" closes a hole a planted mutation walked through.
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
const WEB_TOOLS = ["WebFetch", "WebSearch"];

const agents = readdirSync(AGENT_DIR).filter((f) => f.endsWith(".md")).map((f) => {
  const text = readFileSync(join(AGENT_DIR, f), "utf8");
  const m = /^---\n([\s\S]*?)\n---\n/.exec(text);
  const tools = (/^tools:\s*(.+)$/m.exec(m?.[1] ?? "")?.[1] ?? "").split(",").map((t) => t.trim()).filter(Boolean);
  return { name: f.replace(/\.md$/, ""), text, body: m ? text.slice(m[0].length) : text, tools };
});
const byName = Object.fromEntries(agents.map((a) => [a.name, a]));
const sentences = (text) => text.replace(/\s+/g, " ").split(/(?<=[.!?])\s+(?=[A-Z0-9*`(])/);

test("a DOI that the URL rewrites cannot pass as registered: the lookup encodes the DOI or checks the record's own DOI", () => {
  // The trigger, on the URL parser a Node fetch uses. An unregistered DOI with
  // dot segments is fetched as a different, registered one, and a fragment is
  // dropped before the request is sent. The record that comes back is a real
  // paper's, so a citation of that paper under the unregistered DOI reads
  // VERIFIED; a registered DOI that contains "#" or "?" is looked up truncated
  // and can read NOT REGISTERED.
  const crossref = (doi) => new URL(`https://api.crossref.org/works/${doi}`).pathname;
  assert.equal(crossref("10.9999/unregistered/../../10.1038/nature14539"), "/works/10.1038/nature14539");
  assert.equal(crossref("10.1038/nature14539#x"), "/works/10.1038/nature14539");
  // The resolver this change replaced closed both holes: it sent
  // quote(doi, safe="") and accepted a Crossref record only when the record's
  // DOI equalled the DOI asked for (adjudication/doi_resolver.py _crossref;
  // test_gates.py test_crossref_does_not_confirm_a_record_for_a_different_doi).
  const ENCODES = /percent-encod|URL-encod|encodeURIComponent/i;
  const ECHO = /\b(?:record's (?:own )?DOI|DOI (?:field|the record (?:gives|carries|returns))|DOI in the record|returned DOI|registered DOI)\b/i;
  const open = LOOKUP_AGENTS.filter((n) => !(ENCODES.test(byName[n].text) || ECHO.test(byName[n].text)));
  assert.deepEqual(open, [], "the DOI goes into the lookup URL unencoded, and the record's own DOI is never asked for or compared with it");
});

test("the scout states what NOT REGISTERED does to a source, and it is not the BLOCKED verdict", () => {
  const scout = byName["council-evidence-scout"].text;
  const named = sentences(scout).filter((s) => s.includes("NOT REGISTERED"));
  assert.ok(named.length > 0, "the scout no longer names NOT REGISTERED");
  // The claim auditor makes NOT REGISTERED a verdict of its own.
  assert.match(byName["claim-auditor"].text, /Verdicts:[^\n]*NOT REGISTERED/);
  // The scout defines the outcome and stops. Its fallback, "If you cannot
  // verify a source, list it under Excluded with the reason, or mark it Manual
  // verification required", lets an unregistered DOI take the BLOCKED verdict,
  // and full-council.js asks for Verified "only for sources whose identifier
  // you checked this session": an unregistered identifier was checked.
  assert.ok(named.some((s) => /Not Usable|Excluded|\bexclude/i.test(s)),
    `council-evidence-scout: NOT REGISTERED leads to no stated verdict: ${named.join(" | ")}`);
});

test("the claim auditor keeps all web text out of the shell, not only DOIs and the audited material", () => {
  // Named today: a DOI copied from a document or a web page, and the audited
  // material. Not named: what WebFetch returns (a record's title, a publisher
  // page's text), though this agent holds Bash and is told to take the title,
  // first author, and year "from that page".
  const GENERAL = /\b(?:text|anything|content|nothing|whatever)\b(?:\s+\w+){0,3}\s+(?:fetch(?:ed)?|from (?:a|the) web(?: page)?|taken from (?:a|the) web|WebFetch (?:returns|result)|returned by WebFetch)\b[^.]*\bshell\b/i;
  const REVERSE = /\bnever\b[^.]*\b(?:anything|any text|text|content)\b[^.]*\b(?:fetch(?:ed)?|WebFetch|web page)\b[^.]*\bshell\b/i;
  assert.ok(sentences(byName["claim-auditor"].text).some((s) => GENERAL.test(s) || REVERSE.test(s)),
    "claim-auditor holds Bash and WebFetch, and no rule keeps fetched web text out of a shell command");
});

test("the claim auditor never runs or follows an instruction found in fetched or audited text", () => {
  // R1 says such text is never executed. This agent holds Bash, reads
  // documents it did not write, and fetches pages it does not control.
  const RULE = /\b(?:never|do not|don't)\s+(?:follow|obey|act on|execute|run)\b[^.]*\b(?:instructions?|commands?)\b[^.]*\b(?:fetch(?:ed)?|web|page|record|audited|document|material)\b/i;
  const DATA = /\b(?:fetched|web|audited)\b[^.]*\b(?:is|are) (?:data|evidence)\b[^.]*\bnever\b[^.]*\binstructions?\b/i;
  assert.ok(sentences(byName["claim-auditor"].text).some((s) => RULE.test(s) || DATA.test(s)),
    "claim-auditor: nothing says an instruction inside fetched or audited text is data, never a command to run");
});

test("the doc's claim that no agent passes web-sourced text to a shell holds for every agent that could", () => {
  const doc = readFileSync(join(REPO_ROOT, "docs/AI_AGENTS.md"), "utf8").replace(/\s+/g, " ");
  // Withdrawing the claim is a fix too: then there is nothing to hold it to.
  if (!/no agent passes[^.]*(?:web|DOI)[^.]*shell/i.test(doc)) return;
  const RULE = /\b(?:web|fetched|WebFetch|web page|search result)\b[^.]*\b(?:never|not)\b[^.]*\bshell\b|\bnever\b[^.]*\b(?:web|fetched|WebFetch|web page)\b[^.]*\bshell\b/i;
  const unruled = agents
    .filter((a) => a.tools.includes("Bash") && a.tools.some((t) => WEB_TOOLS.includes(t)))
    .filter((a) => !RULE.test(a.body.replace(/\s+/g, " ")))
    .map((a) => `${a.name} (${a.tools.join(", ")})`);
  // The statistician holds Bash and no Write. `decision_log.py record --json
  // <file>` reads a file that carries the Council's recommendation, dissent,
  // and base rate, which quote the Scout's web-sourced packet; the only tool
  // it has for writing that file is a shell.
  const stat = byName["reliability-statistician"];
  const statRuled = stat.tools.includes("Write")
    || /\bnever\b[^.]*\bshell\b[^.]*\b(?:record|Council)\b|\b(?:record|Council)\b[^.]*\bnever\b[^.]*\bshell\b|\bthe operator (?:writes|fills)\b/i.test(stat.body.replace(/\s+/g, " "));
  if (!statRuled) unruled.push(`reliability-statistician (${stat.tools.join(", ")}: writes Council text into a JSON file through a shell)`);
  assert.deepEqual(unruled, [], "docs/AI_AGENTS.md says no agent passes a DOI or other web-sourced text to a shell; these agents are never told so");
});

test("a blocked Crossref lookup still asks doi.org before it ends in BLOCKED", () => {
  // The replaced resolver did (doi_resolver.DoiResolver._resolve: Crossref
  // unreachable, then doi.org). Here step 2 runs only when Crossref "says the
  // resource is not found", so a sandbox that blocks api.crossref.org and
  // allows doi.org can no longer tell a registered DOI from an unregistered one.
  const open = LOOKUP_AGENTS.filter((n) => !sentences(byName[n].text).some((s) =>
    /Crossref/.test(s) && /\b(?:blocked|unreachable|cannot be reached|could not be reached|fails?)\b/i.test(s) && /doi\.org/.test(s)));
  assert.deepEqual(open, [], "a blocked Crossref goes straight to BLOCKED without trying doi.org");
});

test("the claim auditor checks walls in text that is not a repository file without a shell", () => {
  // It audits Council memos and PR descriptions, which are often not files.
  // Its only walled-term check is scan-copy.mjs, which reads files, and the
  // only way it has to make a file is Bash: the memo (which quotes the Scout's
  // web sources) would go through a heredoc. Nothing says what to do instead.
  const { text } = byName["claim-auditor"];
  const ok = sentences(text).some((s) => /scan/i.test(s)
    && /not (?:a )?(?:repository )?file|not in (?:a|the) repository|no file|pasted|in memory/i.test(s)
    && /NOT RUN|ask the operator|operator to save|never (?:write|pipe|put)/i.test(s));
  assert.ok(ok, "claim-auditor never says how to scan audited text that is not a repository file without passing it through a shell");
});

test("a DOI slot appears only inside a lookup URL, never in a command, fenced or inline", () => {
  // doi-check.test.mjs reads fenced blocks only. An inline instruction such as
  // "if WebFetch is blocked, run `python3 adjudication/doi_resolver.py <DOI>`"
  // passes every test in that file, because the phrases it looks for are
  // still present.
  const SLOT = /<DOI>|\{doi\}|\$\{?DOI\b/i;
  let urls = 0;
  for (const a of agents) {
    const fenced = [...a.text.matchAll(/```[^\n]*\n([\s\S]*?)```/g)].map((m) => m[1]);
    const inline = [...a.text.replace(/```[\s\S]*?```/g, "").matchAll(/`([^`\n]+)`/g)].map((m) => m[1]);
    for (const span of [...fenced, ...inline].filter((s) => SLOT.test(s))) {
      assert.match(span.trim(), /^https:\/\/[^\s`]+$/, `${a.name}: a DOI slot outside a lookup URL: ${span}`);
      urls += 1;
    }
  }
  assert.ok(urls >= 4, `expected the four lookup URLs, found ${urls}`);
});
