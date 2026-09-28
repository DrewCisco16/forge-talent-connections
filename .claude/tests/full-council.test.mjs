// Tests for .claude/workflows/full-council.js, run with stubbed agents.
// Run: node --test ".claude/tests/*.test.mjs"

import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { REPO_ROOT } from "../tools/scan-copy.mjs";
import { extractMeta, readWorkflow, runWorkflow } from "./lib/workflow-harness.mjs";

const SRC = readWorkflow(join(REPO_ROOT, ".claude/workflows/full-council.js"));

const ROLE_BY_TYPE = {
  "council-contrarian": "Contrarian",
  "council-first-principles": "First Principles Thinker",
  "council-expansionist": "Expansionist",
  "council-executor": "Executor",
  "council-steward": "Steward",
};

const GOOD_ARGS = Object.freeze({
  question: "Should the company open a paid sponsor tier next quarter?",
  why_full_council: "A public pricing commitment that is hard to reverse",
  operator_answer: "OPERATOR-ANSWER-SENTINEL: proceed with a small pilot",
  premises: ["PREMISE-ONE sponsors will pay for verified collaboration", "Pilot costs are bounded"],
  decision_types: ["strategic", "financial"],
  green_only: true,
  expected_without_council: "EXPECTED-SENTINEL modest uptake",
  context: "Fixture context for tests.",
  date: "2026-09-26",
});

// Each distinct source gets its own citation, derived from its link, because
// identical citations are one source to the deduplication pass.
function source(over = {}) {
  const link = over.doi_or_link ?? "10.1000/test.1";
  return {
    citation: `Author, A. (2025). A study at ${link}. Venue.`,
    doi_or_link: link,
    year: "2025",
    venue: "Venue",
    core_finding: "finding",
    main_limitation: "limitation",
    evidence_weight: "High",
    relevance_class: "Direct",
    empirical_basis: "field data",
    effect_on_standing_view: "Confirms",
    source_type: "peer-reviewed",
    verification: "Verified",
    ...over,
  };
}

function scout(sources) {
  return {
    report: "scout report",
    search_disclosure: "databases and terms",
    sources,
    reason_for_stopping: "no further relevant sources",
    evidence_gaps: ["gap"],
    expiry_risks: ["pricing data ages within a year"],
    one_line_summary: "summary",
    overall_effect: "Confirms",
  };
}

function seat(role) {
  return {
    report: `REPORT-OF-${role}. As The ${role}, I weigh stewardship and the executor of an estate.`,
    key_points: [`${role} point`],
    zero_defects_self_check: "checked",
    recommends_confidence_cap: "Medium",
    steward_verdict: role === "Steward" ? "Proceed With Conditions" : "Not applicable",
  };
}

function chair(over = {}) {
  return {
    report: "chair report",
    decision_class: "RUN A REVERSIBLE TEST",
    recommendation: "Run a bounded pilot",
    confidence: "Medium",
    cap_applied: "shared-model cap",
    fresh_evidence_delta: "Strengthened",
    strongest_dissent: "demand may be thin",
    professional_verification_required: false,
    final_decision_memo: {
      recommended_decision: "pilot",
      confidence_and_cap: "Medium, shared-model cap",
      why_best_available: "reversible",
      strongest_reason_wrong: "thin demand",
      key_evidence: "source 1",
      key_assumption_to_test: "sponsors pay",
      safest_next_action: "offer the tier to three sponsors",
      professional_verification: "none",
    },
    assumption_test_plan: {
      key_assumption: "sponsors pay",
      fastest_test: "offer to three sponsors",
      owner: "operator to assign",
      deadline: "2026-10-31",
      pass_condition: "two accept",
      fail_condition: "none accept",
      decision_change_if_failed: "do not proceed",
    },
    assumptions_made: ["A1"],
    major_uncertainties: ["U1"],
    ...over,
  };
}

function responder({ scoutOut, seats = {}, chairs } = {}) {
  const s = scoutOut === undefined ? scout([source(), source({ doi_or_link: "10.1000/test.2" })]) : scoutOut;
  const c = chairs ?? [chair(), chair(), chair()];
  return (prompt, opts) => {
    if (opts.agentType === "council-evidence-scout") return s;
    if (opts.agentType === "council-chairman") {
      const n = Number(/Chairman (\d)/.exec(opts.label)[1]);
      return c[n - 1];
    }
    const role = ROLE_BY_TYPE[opts.agentType];
    if (!role) throw new Error(`unexpected agentType ${opts.agentType}`);
    return opts.agentType in seats ? seats[opts.agentType] : seat(role);
  };
}

const run = (args = GOOD_ARGS, opts) => runWorkflow(SRC, args, responder(opts));

test("meta is a pure literal whose phases match every phase() call", async () => {
  const { value } = extractMeta(SRC);
  assert.equal(value.name, "full-council");
  assert.ok(value.description.length > 0);
  const titles = value.phases.map((p) => p.title);
  const { phases } = await run();
  assert.deepEqual([...new Set(phases)], titles);
});

const REFUSALS = [
  ["missing operator_answer", { operator_answer: undefined }, /operator_answer/],
  ["blank operator_answer", { operator_answer: "   " }, /operator_answer/],
  ["no premises", { premises: [] }, /premises/],
  ["four premises", { premises: ["a", "b", "c", "d"] }, /premises/],
  ["blank premise", { premises: ["a", " "] }, /premises/],
  ["missing question", { question: "" }, /question/],
  ["missing why_full_council", { why_full_council: undefined }, /why_full_council/],
  ["unknown decision type", { decision_types: ["strategic", "vibes"] }, /unknown decision_types: vibes/],
  ["no decision types", { decision_types: [] }, /decision_types is required/],
  ["green_only not confirmed", { green_only: "yes" }, /green_only/],
  ["bad date", { date: "26/09/2026" }, /date must be a real date/],
  ["impossible month", { date: "2026-99-99" }, /date must be a real date/],
  ["year zero", { date: "0000-00-00" }, /date must be a real date/],
  ["February 30", { date: "2026-02-30" }, /date must be a real date/],
  ["non-string decision type", { decision_types: [{ toString: 1 }] }, /decision_types must contain only strings/],
  ["misspelled optional field", { expected_without_counsel: "x" }, /unknown field: expected_without_counsel/],
  ["operator answer repeated in context", { context: "Background. OPERATOR-ANSWER-SENTINEL: proceed with a small pilot. More." }, /operator_answer is repeated inside context/],
  ["operator answer repeated in a premise", { premises: ["We think operator-answer-sentinel:   proceed with a small PILOT is right"] }, /operator_answer is repeated inside premises/],
  ["expected outcome repeated in the question", { question: "Will EXPECTED-SENTINEL modest uptake happen if we launch?" }, /expected_without_council is repeated inside question/],
  ["non-string context", { context: 42 }, /context must be a string/],
];

for (const [name, patch, pattern] of REFUSALS) {
  test(`refuses before any agent runs: ${name}`, async () => {
    const { result, calls } = await run({ ...GOOD_ARGS, ...patch });
    assert.equal(result.status, "REFUSED");
    assert.equal(calls.length, 0);
    assert.ok(result.problems.some((p) => pattern.test(p)), result.problems.join(" | "));
  });
}

test("refuses a credential-shaped string without echoing it", async () => {
  // Built at runtime so no key-shaped literal sits in the repository.
  const secret = ["sk", "ant", "api03", "abcdefghijklmnop"].join("-");
  const { result, calls } = await run({ ...GOOD_ARGS, context: `key ${secret}` });
  assert.equal(result.status, "REFUSED");
  assert.equal(calls.length, 0);
  assert.ok(!JSON.stringify(result).includes(secret));
});

test("refuses args that are not an object or valid JSON", async () => {
  for (const bad of ["{not json", null, 7, ["a"]]) {
    const { result, calls } = await run(bad);
    assert.equal(result.status, "REFUSED");
    assert.equal(calls.length, 0);
  }
});

test("accepts args passed as a JSON string", async () => {
  const { result } = await run(JSON.stringify(GOOD_ARGS));
  assert.equal(result.status, "COMPLETE");
});

test("happy path runs one scout, five seats, three chairmen, all defined agents", async () => {
  const { result, calls } = await run();
  assert.equal(result.status, "COMPLETE");
  assert.equal(calls.length, 9);
  const types = calls.map((c) => c.opts.agentType);
  assert.equal(types.filter((t) => t === "council-evidence-scout").length, 1);
  assert.equal(types.filter((t) => t === "council-chairman").length, 3);
  for (const t of Object.keys(ROLE_BY_TYPE)) assert.equal(types.filter((x) => x === t).length, 1);
  for (const t of new Set(types)) {
    assert.ok(existsSync(join(REPO_ROOT, ".claude/agents", `${t}.md`)), `no agent file for ${t}`);
  }
  for (const c of calls) assert.ok(c.opts.schema, `${c.opts.label} ran without a schema`);
});

test("the operator's answer and expected outcome never reach a seat or chairman", async () => {
  const { result, calls } = await run();
  for (const c of calls) {
    assert.ok(!c.prompt.includes("OPERATOR-ANSWER-SENTINEL"), `${c.opts.label} saw the operator answer`);
    assert.ok(!c.prompt.includes("EXPECTED-SENTINEL"), `${c.opts.label} saw the expected outcome`);
  }
  assert.ok(result.operator_brief.includes("OPERATOR-ANSWER-SENTINEL"));
  assert.equal(result.operator_precommitment.operator_answer, GOOD_ARGS.operator_answer);
});

test("seats see the premises and the evidence, but never another seat's output", async () => {
  const { calls } = await run();
  const seatCalls = calls.filter((c) => c.opts.agentType in ROLE_BY_TYPE);
  for (const c of seatCalls) {
    assert.ok(c.prompt.includes("PREMISE-ONE"));
    assert.ok(c.prompt.includes("CONSOLIDATED EVIDENCE SET"));
    assert.ok(!c.prompt.includes("REPORT-OF-"), `${c.opts.label} saw a seat report`);
  }
});

test("chairmen see all five seats anonymized, each in a different order, words intact", async () => {
  const { calls, result } = await run();
  const chairCalls = calls.filter((c) => c.opts.agentType === "council-chairman");
  const orders = chairCalls.map((c) => [...c.prompt.matchAll(/REPORT-OF-([A-Za-z ]+?)\./g)].map((m) => m[1]));
  for (const [i, order] of orders.entries()) {
    assert.equal(order.length, 5);
    assert.deepEqual([...order].sort(), Object.values(ROLE_BY_TYPE).sort());
    for (const letter of ["A", "B", "C", "D", "E"]) assert.ok(chairCalls[i].prompt.includes(`=== Seat ${letter} ===`));
    assert.ok(!/\b[Tt]he (Contrarian|First Principles Thinker|Expansionist|Executor|Steward)\b/.test(chairCalls[i].prompt));
    assert.ok(chairCalls[i].prompt.includes("stewardship"), "anonymization corrupted an ordinary word");
    assert.ok(chairCalls[i].prompt.includes("the executor of an estate"), "anonymization corrupted an ordinary phrase");
  }
  assert.equal(new Set(orders.map((o) => o.join())).size, 3);
  for (const c of result.chairmen) assert.equal(c.seat_order_seen.length, 5);
});

// Oracle copies of the workflow's order functions, used only to FIND a question
// whose first-choice orders collide, so the collision guard is exercised
// rather than assumed (with fixed fixture questions it never fires).
function hash32(s) {
  let h = 2166136261 >>> 0;
  for (const ch of s) {
    h ^= ch.codePointAt(0);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}
function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function permutation(n, seed) {
  const idx = Array.from({ length: n }, (_, i) => i);
  const rand = mulberry32(seed);
  for (let i = n - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [idx[i], idx[j]] = [idx[j], idx[i]];
  }
  return idx;
}

test("chairmen get distinct orders even when first-choice orders collide", async () => {
  let question = null;
  for (let k = 0; k < 20000 && question === null; k++) {
    const q = `Collision probe ${k}?`;
    const [a, b, c] = [0, 1, 2].map((i) => permutation(5, hash32(`${q}#chair${i}`)).join());
    if (a === b || a === c || b === c) question = q;
  }
  assert.ok(question, "no colliding question found in the search window");
  const { result } = await run({ ...GOOD_ARGS, question });
  assert.equal(result.status, "COMPLETE");
  assert.equal(new Set(result.chairmen.map((c) => c.seat_order_seen.join())).size, 3);
});

// The purpose of randomizing order is that no seat is systematically read
// first. Deterministic over fixed questions, so this cannot flake: 1,200 runs,
// expected 240 first places per seat, bounds at roughly four standard
// deviations.
test("no seat is systematically first across many questions", async () => {
  const firsts = {};
  for (let k = 0; k < 1200; k++) {
    const { result } = await run({ ...GOOD_ARGS, question: `Uniformity probe ${k}?` });
    const first = result.chairmen[0].seat_order_seen[0].split(" = ")[1];
    firsts[first] = (firsts[first] || 0) + 1;
  }
  assert.equal(Object.keys(firsts).length, 5);
  for (const [seatTitle, count] of Object.entries(firsts)) {
    assert.ok(count > 180 && count < 300, `${seatTitle} was first ${count} of 1200 times`);
  }
});

test("orders are deterministic across runs (resume-safe)", async () => {
  const one = await run();
  const two = await run();
  assert.deepEqual(one.result.chairmen.map((c) => c.seat_order_seen), two.result.chairmen.map((c) => c.seat_order_seen));
});

test("a claimed High is clamped to the Medium ceiling with the reason recorded", async () => {
  const { result } = await run(GOOD_ARGS, { chairs: [chair({ confidence: "High" }), chair(), chair()] });
  assert.equal(result.enforced.confidence_ceiling, "Medium");
  const c1 = result.chairmen[0];
  assert.equal(c1.confidence_claimed, "High");
  assert.equal(c1.confidence_final, "Medium");
  assert.match(c1.confidence_clamp_reason, /exceeds the Medium ceiling/);
  assert.equal(result.chairmen[1].confidence_clamp_reason, null);
});

test("a confidence outside the vocabulary fails closed to Low", async () => {
  const { result } = await run(GOOD_ARGS, { chairs: [chair({ confidence: "95%" }), chair(), chair()] });
  assert.equal(result.chairmen[0].confidence_final, "Low");
  assert.match(result.chairmen[0].confidence_clamp_reason, /fails closed to Low/);
});

test("no verified external evidence makes the run Opinion-only at Low", async () => {
  const sources = [
    source({ source_type: "project library" }),
    source({ doi_or_link: "10.1000/x", verification: "Manual verification required" }),
  ];
  const { result } = await run(GOOD_ARGS, { scoutOut: scout(sources) });
  assert.equal(result.enforced.confidence_ceiling, "Low");
  assert.equal(result.enforced.opinion_only, true);
  assert.equal(result.chairmen[0].confidence_final, "Low");
  assert.ok(result.evidence.dropped_sources.some((d) => /not verified/.test(d.why)));
});

test("mostly indirect or low-weight evidence caps at Low; mostly strong does not", async () => {
  const weak = [source(), source({ doi_or_link: "a", relevance_class: "Indirect" }), source({ doi_or_link: "b", evidence_weight: "Low" })];
  const strong = [source(), source({ doi_or_link: "a" }), source({ doi_or_link: "b", relevance_class: "Indirect" })];
  assert.equal((await run(GOOD_ARGS, { scoutOut: scout(weak) })).result.enforced.confidence_ceiling, "Low");
  assert.equal((await run(GOOD_ARGS, { scoutOut: scout(strong) })).result.enforced.confidence_ceiling, "Medium");
});

test("exactly half strong is not mostly weak (boundary)", async () => {
  const half = [source(), source({ doi_or_link: "a", relevance_class: "Indirect" })];
  assert.equal((await run(GOOD_ARGS, { scoutOut: scout(half) })).result.enforced.confidence_ceiling, "Medium");
});

test("duplicate sources are merged across link spellings", async () => {
  const dup = [source({ doi_or_link: "https://doi.org/10.1000/SAME" }), source({ doi_or_link: "10.1000/same" })];
  const { result } = await run(GOOD_ARGS, { scoutOut: scout(dup) });
  assert.match(result.evidence.dedup_output, /Duplicate sources merged: 1/);
  assert.equal(result.evidence.usable_sources.length, 1);
});

test("professional verification is enforced for regulated domains and never duplicated", async () => {
  const args = { ...GOOD_ARGS, decision_types: ["legal_regulatory"] };
  const withLine = chair({ final_decision_memo: { ...chair().final_decision_memo, professional_verification: "Professional verification required before filing." } });
  const { result } = await run(args, { chairs: [chair(), withLine, chair()] });
  assert.equal(result.enforced.professional_verification_required, true);
  assert.match(result.chairmen[0].final_decision_memo.professional_verification, /^professional verification required/);
  assert.equal(result.chairmen[0].professional_line_added_by_harness, true);
  assert.equal(result.chairmen[1].professional_line_added_by_harness, false);
  assert.match(result.operator_brief, /professional verification required/);
});

test("a chairman flagging professional verification triggers it for the run", async () => {
  const { result } = await run(GOOD_ARGS, { chairs: [chair({ professional_verification_required: true }), chair(), chair()] });
  assert.equal(result.enforced.professional_verification_required, true);
  assert.ok(result.chairmen.every((c) => /professional verification required/.test(JSON.stringify(c.final_decision_memo))));
});

test("a missing scout halts before any seat", async () => {
  const { result, calls } = await run(GOOD_ARGS, { scoutOut: null });
  assert.equal(result.status, "HALTED");
  assert.equal(result.stage, "Evidence");
  assert.equal(calls.length, 1);
});

test("a missing seat halts before any chairman", async () => {
  const { result, calls } = await run(GOOD_ARGS, { seats: { "council-contrarian": null } });
  assert.equal(result.status, "HALTED");
  assert.equal(result.stage, "Seats");
  assert.match(result.reason, /Contrarian/);
  assert.equal(calls.filter((c) => c.opts.agentType === "council-chairman").length, 0);
});

test("a missing chairman halts with the partial results kept", async () => {
  const { result, calls } = await run(GOOD_ARGS, { chairs: [chair(), null, chair()] });
  assert.equal(result.status, "HALTED");
  assert.equal(result.stage, "Chairmen");
  assert.equal(calls.length, 9);
  assert.equal(result.partial_chairmen.length, 2);
  assert.ok(result.seats.contrarian.report.includes("REPORT-OF-Contrarian"));
});

test("concordance reports unanimous, majority, and split", async () => {
  const cls = (d) => chair({ decision_class: d });
  const u = await run(GOOD_ARGS, { chairs: [cls("PROCEED"), cls("PROCEED"), cls("PROCEED")] });
  const m = await run(GOOD_ARGS, { chairs: [cls("PROCEED"), cls("PROCEED"), cls("DO NOT PROCEED")] });
  const s = await run(GOOD_ARGS, { chairs: [cls("PROCEED"), cls("RUN A REVERSIBLE TEST"), cls("DO NOT PROCEED")] });
  assert.equal(u.result.concordance.verdict, "UNANIMOUS");
  assert.equal(m.result.concordance.verdict, "MAJORITY");
  assert.equal(s.result.concordance.verdict, "SPLIT");
});

test("the harness-written brief contains no percentage and no dashes", async () => {
  const { result } = await run();
  assert.ok(!/\d\s*%/.test(result.operator_brief), result.operator_brief);
  const dashes = new RegExp(`[${String.fromCharCode(0x2013, 0x2014)}]`);
  assert.ok(!dashes.test(result.operator_brief));
  assert.ok(!/\n{3,}/.test(result.operator_brief));
});

test("evidence integrity counts come from the packet", async () => {
  const sources = [source(), source({ doi_or_link: "https://www.bls.gov/x", source_type: "government primary" }), source({ doi_or_link: "docs/x.pdf", source_type: "project library" })];
  const { result } = await run(GOOD_ARGS, { scoutOut: scout(sources) });
  const i = result.evidence_integrity;
  assert.equal(i.sources_reviewed, 3);
  assert.equal(i.peer_reviewed_sources_used, 1);
  assert.equal(i.government_sources_used, 1);
  assert.equal(i.project_library_sources_used, 1);
  assert.equal(i.pdfs_used, 1);
  assert.deepEqual(i.assumptions_made, ["A1"]);
});

test("the harness itself rejects forbidden nondeterminism", async () => {
  const bad = 'export const meta = { name: "x", description: "y" }\nreturn Math.random()';
  await assert.rejects(runWorkflow(bad, {}, () => null), /Math.random/);
  const bad2 = 'export const meta = { name: "x", description: "y" }\nreturn Date.now()';
  await assert.rejects(runWorkflow(bad2, {}, () => null), /Date.now/);
});

// ------------------------------------------------------------ review findings

// Every credential shape is built at runtime so no key-shaped literal sits in
// the repository, and each is tested inline, after a newline, and after a tab,
// because a pasted .env block puts a key at the start of a line.
const KEYS = {
  anthropic: ["sk", "ant", "api03", "a".repeat(24)].join("-"),
  openai_legacy: ["sk", "b".repeat(40)].join("-"),
  openai_project: ["sk", "proj", "c".repeat(40)].join("-"),
  google: "AIza" + "d".repeat(35),
  xai: ["xai", "e".repeat(40)].join("-"),
  aws: "AKIA" + "IOSFODNN7EXAMPLE",
  github_classic: "ghp_" + "f".repeat(36),
  github_oauth: "gho_" + "g".repeat(36),
  github_pat: "github_pat_" + "h".repeat(30),
  slack: ["xoxb", "1234567890", "abcdefghij"].join("-"),
  stripe: ["sk", "live", "i".repeat(24)].join("_"),
  pem: ["-----BEGIN", "PGP PRIVATE KEY BLOCK-----"].join(" "),
  seat_env_line: "ADJ_SEAT_3_API_KEY=" + "j".repeat(32),
  mistral_env_line: "MISTRAL_API_KEY=" + "k".repeat(32),
};

for (const [name, key] of Object.entries(KEYS)) {
  for (const [where, text] of [["inline", `note ${key} end`], ["after a newline", `note\n${key}\nend`], ["after a tab", `note\t${key}`]]) {
    test(`refuses a ${name} credential ${where}, echoing nothing`, async () => {
      const { result, calls } = await run({ ...GOOD_ARGS, context: text });
      assert.equal(result.status, "REFUSED");
      assert.equal(calls.length, 0);
      assert.ok(!JSON.stringify(result).includes(key));
    });
  }
}

test("ordinary words that contain key prefixes are not credentials", async () => {
  const { result } = await run({ ...GOOD_ARGS, context: "A risk-adjusted-return-on-capital model; the task-force-reviewed plan." });
  assert.equal(result.status, "COMPLETE");
});

test("a credential placed where values are echoed is never echoed", async () => {
  const key = KEYS.github_classic;
  const { result } = await run({ ...GOOD_ARGS, decision_types: ["strategic", key], [key]: 1 });
  assert.equal(result.status, "REFUSED");
  assert.ok(!JSON.stringify(result).includes(key));
  assert.ok(result.problems.some((p) => /value\(s\) not shown|name not shown/.test(p)));
});

test("a short operator answer is not policed for containment", async () => {
  const { result } = await run({ ...GOOD_ARGS, operator_answer: "Proceed", context: "We could proceed or wait." });
  assert.equal(result.status, "COMPLETE");
});

test("a real leap day is accepted", async () => {
  const { result } = await run({ ...GOOD_ARGS, date: "2024-02-29" });
  assert.equal(result.status, "COMPLETE");
});

test("model text in the brief: dashes normalized, percentages flagged, harness words percentage-free", async () => {
  const em = String.fromCharCode(0x2014);
  const loud = chair({
    confidence: "Unrecognized",
    final_decision_memo: { ...chair().final_decision_memo, recommended_decision: `Proceed ${em} an 80% chance of success`, strongest_reason_wrong: "Churn could reach 40 percent" },
  });
  const { result } = await run(GOOD_ARGS, { chairs: [loud, chair(), chair()] });
  const lines = result.operator_brief.split("\n");
  assert.ok(!result.operator_brief.includes(em));
  for (const line of lines.filter((l) => /%|[0-9]\s*percent/i.test(l))) {
    assert.match(line, /\[harness: this line quotes a percentage from model text/, line);
  }
  assert.ok(lines.some((l) => l.startsWith("Recommended decision: Proceed - an 80% chance")));
  const clampLine = lines.find((l) => l.startsWith("Confidence: Low (clamped"));
  assert.ok(clampLine && !clampLine.includes("Unrecognized"), "the clamp must not echo the rejected value");
});

test("the memo's own confidence line carries the enforced value", async () => {
  const bold = chair({ confidence: "High", final_decision_memo: { ...chair().final_decision_memo, confidence_and_cap: "High: no cap applies" } });
  const { result } = await run(GOOD_ARGS, { chairs: [bold, chair(), chair()] });
  const c1 = result.chairmen[0];
  assert.equal(c1.confidence_final, "Medium");
  assert.match(c1.final_decision_memo.confidence_and_cap, /^Medium\. Ceiling Medium/);
  assert.equal(c1.confidence_and_cap_as_written, "High: no cap applies");
});

test("a negated professional line elsewhere in the memo does not switch the line off", async () => {
  const sly = chair({ final_decision_memo: { ...chair().final_decision_memo, strongest_reason_wrong: "No professional verification required here", professional_verification: "none" } });
  const { result } = await run({ ...GOOD_ARGS, decision_types: ["legal_regulatory", "tax"] }, { chairs: [sly, chair(), chair()] });
  assert.match(result.chairmen[0].final_decision_memo.professional_verification, /^professional verification required\. none$/);
  assert.equal(result.chairmen[0].professional_line_added_by_harness, true);
});

test("one source under many link spellings counts once", async () => {
  const spellings = [
    "https://doi.org/10.1000/SAME", "https://www.doi.org/10.1000/same", "doi.org/10.1000/same",
    "http://dx.doi.org/10.1000/same?utm=x", "doi:10.1000/same", "10.1000/same.",
  ];
  const strongTwiceOver = [
    ...spellings.map((l) => source({ doi_or_link: l, citation: `Variant citation ${l}` })),
    source({ doi_or_link: "10.1000/weak.1", relevance_class: "Indirect" }),
    source({ doi_or_link: "10.1000/weak.2", relevance_class: "Indirect" }),
  ];
  const { result } = await run(GOOD_ARGS, { scoutOut: scout(strongTwiceOver) });
  assert.match(result.evidence.dedup_output, /Duplicate sources merged: 5/);
  assert.equal(result.enforced.confidence_ceiling, "Low");
});

test("the same work under a publisher link and a citation DOI counts once; two DOIs decide", async () => {
  const a = source({ doi_or_link: "https://publisher.example/article/42?ref=x", citation: "Author, A. (2025). Title. doi:10.1000/pub.42" });
  const b = source({ doi_or_link: "10.1000/pub.42" });
  const c = source({ doi_or_link: "10.1000/other", citation: a.citation.replace("doi:10.1000/pub.42", "") });
  const d = source({ doi_or_link: "10.1000/third", citation: c.citation });
  const { result } = await run(GOOD_ARGS, { scoutOut: scout([a, b, c, d]) });
  assert.match(result.evidence.dedup_output, /Duplicate sources merged: 1/);
});

test("link-less sources with a long shared prefix stay distinct", async () => {
  const stem = "Author, A. (2025). An extended study title that runs long enough to share an eighty character prefix";
  const three = [source({ doi_or_link: "", citation: `${stem} (strong).` }),
    source({ doi_or_link: "", citation: `${stem} (weak one).`, relevance_class: "Indirect" }),
    source({ doi_or_link: "", citation: `${stem} (weak two).`, relevance_class: "Indirect" })];
  const { result } = await run(GOOD_ARGS, { scoutOut: scout(three) });
  assert.match(result.evidence.dedup_output, /Duplicate sources merged: 0/);
  assert.equal(result.enforced.confidence_ceiling, "Low");
});

test("weak project-library evidence caps at Low even beside strong external evidence", async () => {
  const mix = [source(), ...[1, 2, 3].map((i) => source({ doi_or_link: `lib/${i}.md`, source_type: "project library", relevance_class: "Indirect" }))];
  const { result } = await run(GOOD_ARGS, { scoutOut: scout(mix) });
  assert.equal(result.enforced.confidence_ceiling, "Low");
});

test("every seat block has the same shape, so no harness line marks the Steward", async () => {
  const { calls } = await run();
  for (const c of calls.filter((x) => x.opts.agentType === "council-chairman")) {
    assert.ok(!c.prompt.includes("Seat verdict:"));
    const blocks = c.prompt.split(/=== Seat [A-E] ===\n/).slice(1);
    assert.equal(blocks.length, 5);
    for (const b of blocks) assert.equal(b.split("\n").filter((l) => /^(Zero-Defects self-check|Seat's recommended cap):/.test(l)).length, 2);
  }
});

for (const [stage, opts] of [
  ["Evidence", { scoutOut: {} }],
  ["Seats", { seats: { "council-contrarian": {} } }],
  ["Seats", { seats: { "council-executor": { report: "r", key_points: "not a list" } } }],
  ["Chairmen", { chairs: [chair(), {}, chair()] }],
  ["Chairmen", { chairs: [chair(), chair({ decision_class: "MAYBE" }), chair()] }],
]) {
  test(`a malformed ${stage} result halts instead of crashing (${JSON.stringify(opts).slice(0, 60)})`, async () => {
    const { result } = await run(GOOD_ARGS, opts);
    assert.equal(result.status, "HALTED");
    assert.equal(result.stage, stage);
  });
}

test("the workflow source reaches for no clock, randomness, or host API", () => {
  const code = SRC.replace(/\/\/.*$/gm, "");
  for (const banned of [/Date\.now/, /new Date\(\s*\)/, /Math\.random/, /\bcrypto\b/, /\bperformance\b/, /\bprocess\./, /\brequire\(/, /\bimport\(/]) {
    assert.ok(!banned.test(code), `workflow source uses ${banned}`);
  }
});

test("the harness closes every other road to time and randomness", async () => {
  for (const body of ["return globalThis.Date.now()", "return new globalThis.Date().getTime()", "return globalThis.Math.random()",
    "return crypto.randomUUID()", "return performance.now()", "return process.hrtime()"]) {
    await assert.rejects(runWorkflow(`export const meta = { name: "x", description: "y" }\n${body}`, {}, () => null), /unavailable in workflows/, body);
  }
});

test("weak files sharing a generic citation cannot merge their way to a higher ceiling", async () => {
  const generic = "Project library document.";
  const mix = [source(), ...[1, 2, 3].map((i) => source({ doi_or_link: `docs/file-${i}.md`, citation: generic, source_type: "project library", relevance_class: "Indirect" }))];
  const { result } = await run(GOOD_ARGS, { scoutOut: scout(mix) });
  assert.equal(result.enforced.confidence_ceiling, "Low");
});

test("a strong work listed under two links cannot count twice toward the ceiling", async () => {
  const cite = "Author, B. (2025). The one strong study. Venue.";
  const twice = [source({ doi_or_link: "https://publisher.example/a", citation: cite }), source({ doi_or_link: "https://mirror.example/a.pdf", citation: cite }),
    source({ doi_or_link: "10.1000/weak.1", relevance_class: "Indirect" }), source({ doi_or_link: "10.1000/weak.2", relevance_class: "Indirect" })];
  const { result } = await run(GOOD_ARGS, { scoutOut: scout(twice) });
  assert.equal(result.enforced.confidence_ceiling, "Low");
});

test("this repository's own key names are refused even for a short or odd value", async () => {
  const line = ["ADJ", "SEAT", "3", "API", "KEY=ab!cd"].join("_");
  const { result, calls } = await run({ ...GOOD_ARGS, context: `pasted:\n${line}` });
  assert.equal(result.status, "REFUSED");
  assert.equal(calls.length, 0);
});

test("plain links match across scheme, www, query, fragment, and trailing slash", async () => {
  const one = source({ doi_or_link: "https://www.example.org/report?utm=a#part", citation: "Agency (2025). Report, first listing." });
  const two = source({ doi_or_link: "http://example.org/report/", citation: "Agency (2025). Report, second listing." });
  const { result } = await run(GOOD_ARGS, { scoutOut: scout([one, two]) });
  assert.match(result.evidence.dedup_output, /Duplicate sources merged: 1/);
});
