export const meta = {
  name: 'full-council',
  description: 'Full Council v13: evidence scout, five blinded seats, three independent chairmen, confidence caps enforced in code',
  whenToUse: 'A high-stakes or hard-to-reverse decision the operator has deliberately convened the Council for, after the operator has written a tentative answer and one to three load-bearing premises.',
  phases: [
    { title: 'Intake', detail: 'fail-closed validation; no agent runs until the operator pre-commitment is captured' },
    { title: 'Evidence', detail: 'Evidence Scout packet, then the deduplication pass in code' },
    { title: 'Seats', detail: 'Contrarian, First Principles, Expansionist, Executor, Steward, blind to each other' },
    { title: 'Chairmen', detail: 'three independent syntheses over anonymized seats in different orders' },
  ],
}

// Full Council v13, single-model adaptation, as a deterministic pipeline.
//
// args (an object; a JSON string is accepted and parsed):
//   question                 the decision, stated neutrally
//   why_full_council         why this decision warrants the full protocol
//   operator_answer          the operator's tentative answer, written BEFORE the run
//   premises                 one to three load-bearing premises
//   decision_types           one or more of DECISION_TYPES below
//   green_only               must be true: the operator confirms the ask holds no patent
//                            claim text, prosecution strategy, credentials, or other
//                            entities' data
//   base_rate                optional: base rate or comparison class
//   expected_without_council optional: the operator's expected outcome without the Council
//   context                  optional: background material the seats may use
//   date                     optional: YYYY-MM-DD, the search date for the Evidence Scout
//
// What is enforced here in code rather than left to a model:
//   - Intake fails closed: nothing is spawned until the pre-commitment exists.
//   - The operator's answer and expected outcome never reach a seat or a Chairman
//     (anti-anchoring); they come back only in the result, for the operator's own
//     comparison.
//   - Seats run blind to each other. Chairmen see the seats anonymized as Seat A to E,
//     each Chairman in a different deterministic order.
//   - The confidence ceiling is computed from the evidence packet and the run's design,
//     and every Chairman's confidence is clamped to it; a value outside the vocabulary
//     fails closed to Low.
//   - The professional verification line is added where the domain requires it.
//   - Any missing stage output halts the run (resume re-runs only what is missing).
//   - Nothing here emits a percentage.

const DECISION_TYPES = ['factual', 'causal', 'predictive', 'strategic', 'legal_regulatory', 'tax', 'compliance', 'ethical', 'financial', 'technical', 'medical', 'interpersonal']
const PROFESSIONAL_TYPES = ['legal_regulatory', 'tax', 'compliance', 'medical']
const BEHAVIOR_TYPES = ['predictive', 'strategic', 'interpersonal']
const LEVELS = ['Low', 'Medium', 'High']
const DECISION_CLASSES = ['PROCEED', 'PROCEED WITH CONDITIONS', 'RUN A REVERSIBLE TEST', 'GATHER EVIDENCE THEN DECIDE', 'DO NOT PROCEED']
const PRO_LINE = 'professional verification required'
const CHAIRMEN = 3

const SEATS = [
  { key: 'contrarian', agentType: 'council-contrarian', title: 'Contrarian', role: 'Contrarian' },
  { key: 'first_principles', agentType: 'council-first-principles', title: 'First Principles', role: 'First Principles Thinker' },
  { key: 'expansionist', agentType: 'council-expansionist', title: 'Expansionist', role: 'Expansionist' },
  { key: 'executor', agentType: 'council-executor', title: 'Executor', role: 'Executor' },
  { key: 'steward', agentType: 'council-steward', title: 'Steward', role: 'Steward' },
]

// Best-effort anonymization: only a seat naming itself ("The Steward", "the
// Contrarian's") is rewritten, on word boundaries and with the role
// capitalized, so ordinary words survive ("stewardship", "the executor of an
// estate"). Section headings can still reveal a role; the Chairman is told to
// judge content, not role.
const ROLE_SELF_REFERENCE = new RegExp(`\\b[Tt]he (${SEATS.map((s) => s.role).join('|')})\\b`, 'g')

// Credential shapes. A match refuses the run and the value is never echoed.
const SECRET_PATTERNS = [
  /sk-ant-[A-Za-z0-9_-]{8,}/,
  /\bsk-[A-Za-z0-9]{20,}/,
  /\bAKIA[0-9A-Z]{16}\b/,
  /\bghp_[A-Za-z0-9]{20,}/,
  /\bgithub_pat_[A-Za-z0-9_]{20,}/,
  /\bxox[abprs]-[A-Za-z0-9-]{10,}/,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
]

const str = { type: 'string' }
const strList = { type: 'array', items: str }

const SCOUT_SCHEMA = {
  type: 'object',
  properties: {
    report: str,
    search_disclosure: str,
    sources: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          citation: str,
          doi_or_link: str,
          year: str,
          venue: str,
          core_finding: str,
          main_limitation: str,
          evidence_weight: { type: 'string', enum: ['High', 'Medium', 'Low'] },
          relevance_class: { type: 'string', enum: ['Direct', 'Indirect', 'Background', 'Not Usable'] },
          empirical_basis: str,
          effect_on_standing_view: { type: 'string', enum: ['Confirms', 'Weakens', 'Reverses', 'Adds nuance', 'No bearing'] },
          source_type: { type: 'string', enum: ['project library', 'peer-reviewed', 'government primary', 'official technical documentation', 'other'] },
          verification: { type: 'string', enum: ['Verified', 'Manual verification required'] },
        },
        required: ['citation', 'doi_or_link', 'year', 'venue', 'core_finding', 'main_limitation', 'evidence_weight', 'relevance_class', 'empirical_basis', 'effect_on_standing_view', 'source_type', 'verification'],
      },
    },
    reason_for_stopping: str,
    evidence_gaps: strList,
    expiry_risks: strList,
    one_line_summary: str,
    overall_effect: { type: 'string', enum: ['Confirms', 'Weakens', 'Reverses', 'Complicates', 'Insufficient fresh evidence'] },
  },
  required: ['report', 'search_disclosure', 'sources', 'reason_for_stopping', 'evidence_gaps', 'expiry_risks', 'one_line_summary', 'overall_effect'],
}

const SEAT_SCHEMA = {
  type: 'object',
  properties: {
    report: str,
    key_points: { type: 'array', items: str, maxItems: 5 },
    zero_defects_self_check: str,
    recommends_confidence_cap: { type: 'string', enum: ['Low', 'Medium', 'High', 'No cap needed'] },
    steward_verdict: { type: 'string', enum: ['Proceed', 'Proceed With Conditions', 'Do Not Proceed', 'Not applicable'] },
  },
  required: ['report', 'key_points', 'zero_defects_self_check', 'recommends_confidence_cap', 'steward_verdict'],
}

const MEMO_FIELDS = ['recommended_decision', 'confidence_and_cap', 'why_best_available', 'strongest_reason_wrong', 'key_evidence', 'key_assumption_to_test', 'safest_next_action', 'professional_verification']
const PLAN_FIELDS = ['key_assumption', 'fastest_test', 'owner', 'deadline', 'pass_condition', 'fail_condition', 'decision_change_if_failed']
const objOf = (fields) => ({ type: 'object', properties: Object.fromEntries(fields.map((f) => [f, str])), required: fields })

const CHAIR_SCHEMA = {
  type: 'object',
  properties: {
    report: str,
    decision_class: { type: 'string', enum: DECISION_CLASSES },
    recommendation: str,
    confidence: { type: 'string', enum: LEVELS },
    cap_applied: str,
    fresh_evidence_delta: { type: 'string', enum: ['No change', 'Strengthened', 'Weakened', 'Reversed', 'Insufficient fresh evidence'] },
    strongest_dissent: str,
    professional_verification_required: { type: 'boolean' },
    final_decision_memo: objOf(MEMO_FIELDS),
    assumption_test_plan: objOf(PLAN_FIELDS),
    assumptions_made: strList,
    major_uncertainties: strList,
  },
  required: ['report', 'decision_class', 'recommendation', 'confidence', 'cap_applied', 'fresh_evidence_delta', 'strongest_dissent', 'professional_verification_required', 'final_decision_memo', 'assumption_test_plan', 'assumptions_made', 'major_uncertainties'],
}

// ---------------------------------------------------------------- helpers

const isText = (v) => typeof v === 'string' && v.trim().length > 0

function validate(raw) {
  let a = raw
  if (typeof a === 'string') {
    try {
      a = JSON.parse(a)
    } catch (e) {
      return { a: null, problems: ['args is a string that is not valid JSON; pass an object'] }
    }
  }
  if (!a || typeof a !== 'object' || Array.isArray(a)) {
    return { a: null, problems: ['args must be an object with question, why_full_council, operator_answer, premises, decision_types, green_only'] }
  }
  const problems = []
  if (!isText(a.question)) problems.push('question is required')
  if (!isText(a.why_full_council)) problems.push('why_full_council is required: the Full Council is for high-stakes or hard-to-reverse decisions only (step 1)')
  if (!isText(a.operator_answer)) problems.push('operator_answer is required: write your own tentative answer before any seat runs (step 2)')
  const premises = Array.isArray(a.premises) ? a.premises : []
  if (premises.length < 1 || premises.length > 3 || !premises.every(isText)) {
    problems.push('premises must be one to three non-empty statements (step 2)')
  }
  const types = Array.isArray(a.decision_types) ? a.decision_types : []
  if (types.length === 0) problems.push(`decision_types is required, from: ${DECISION_TYPES.join(', ')} (step 3)`)
  const unknown = types.filter((t) => !DECISION_TYPES.includes(t))
  if (unknown.length) problems.push(`unknown decision_types: ${unknown.join(', ')}; allowed: ${DECISION_TYPES.join(', ')}`)
  if (a.green_only !== true) {
    problems.push('green_only must be true: confirm the ask holds no patent claim text, prosecution strategy, credentials, or other entities\' data')
  }
  for (const k of ['base_rate', 'expected_without_council', 'context', 'date']) {
    if (a[k] !== undefined && typeof a[k] !== 'string') problems.push(`${k} must be a string when given`)
  }
  if (a.date !== undefined && !/^\d{4}-\d{2}-\d{2}$/.test(a.date)) problems.push('date must be YYYY-MM-DD when given')
  const allText = JSON.stringify(a)
  if (SECRET_PATTERNS.some((re) => re.test(allText))) {
    problems.push('the ask contains a credential-shaped string; remove it (NO SECRETS). The value is not repeated here.')
  }
  return { a, problems }
}

function hash32(s) {
  let h = 2166136261 >>> 0
  for (const ch of s) {
    h ^= ch.codePointAt(0)
    h = Math.imul(h, 16777619) >>> 0
  }
  return h
}

// Deterministic Fisher-Yates driven by mulberry32, so a resumed run reproduces
// the same orders (the runtime forbids Math.random). Not a bare power-of-two
// LCG: its low bits cycle with short periods, and j = x % (i + 1) reads exactly
// those bits, which made seat positions far from uniform.
function mulberry32(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6D2B79F5) >>> 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function permutation(n, seed) {
  const idx = Array.from({ length: n }, (_, i) => i)
  const rand = mulberry32(seed)
  for (let i = n - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1))
    const t = idx[i]
    idx[i] = idx[j]
    idx[j] = t
  }
  return idx
}

function chairOrders(question) {
  const orders = []
  for (let c = 0; c < CHAIRMEN; c++) {
    let order = permutation(SEATS.length, hash32(`${question}#chair${c}`))
    let bump = 0
    while (orders.some((o) => o.join() === order.join()) && bump < 16) {
      bump += 1
      order = permutation(SEATS.length, hash32(`${question}#chair${c}#${bump}`))
    }
    orders.push(order)
  }
  return orders
}

function sourceKey(s) {
  const link = (s.doi_or_link || '').trim().toLowerCase()
    .replace(/^https?:\/\/(dx\.)?doi\.org\//, '')
    .replace(/^doi:\s*/, '')
    .replace(/\/+$/, '')
  return link || (s.citation || '').trim().toLowerCase().slice(0, 80)
}

function dedupe(sources) {
  const seen = new Map()
  let merged = 0
  for (const s of sources) {
    const k = sourceKey(s)
    if (seen.has(k)) {
      merged += 1
      continue
    }
    seen.set(k, s)
  }
  const consolidated = [...seen.values()]
  const dropped = []
  const usable = []
  for (const s of consolidated) {
    if (s.verification !== 'Verified') dropped.push({ s, why: 'not verified this session' })
    else if (s.relevance_class !== 'Direct' && s.relevance_class !== 'Indirect') dropped.push({ s, why: `relevance ${s.relevance_class}` })
    else usable.push(s)
  }
  const external = usable.filter((s) => s.source_type !== 'project library')
  const strongExternal = external.filter((s) => s.relevance_class === 'Direct' && (s.evidence_weight === 'High' || s.evidence_weight === 'Medium'))
  return { consolidated, merged, usable, dropped, external, strongExternal }
}

function ceilingFor(ev, types) {
  const reasons = ['Single model family: every seat and Chairman in this build runs on one model family, so their agreement is not independent verification (shared-model cap, Medium at most).']
  let ceiling = 'Medium'
  const opinionOnly = ev.external.length === 0
  if (opinionOnly) {
    ceiling = 'Low'
    reasons.push('No verified external evidence: the synthesis is Opinion-only (cap Low).')
  } else if (ev.strongExternal.length * 2 < ev.external.length) {
    ceiling = 'Low'
    reasons.push(`Evidence is mostly indirect or low weight: ${ev.strongExternal.length} of ${ev.external.length} usable external sources are Direct with High or Medium weight (cap Low; "mostly" means more than half, a convention).`)
  }
  const behavioral = types.filter((t) => BEHAVIOR_TYPES.includes(t))
  if (behavioral.length) reasons.push(`Decision type ${behavioral.join(', ')} caps at Medium regardless of evidence.`)
  return { ceiling, reasons, opinionOnly }
}

function clampConfidence(claimed, ceiling) {
  if (!LEVELS.includes(claimed)) {
    return { value: 'Low', why: `claimed confidence ${JSON.stringify(claimed)} is outside Low, Medium, High, so it fails closed to Low` }
  }
  if (LEVELS.indexOf(claimed) <= LEVELS.indexOf(ceiling)) return { value: claimed, why: null }
  return { value: ceiling, why: `${claimed} exceeds the ${ceiling} ceiling computed for this run` }
}

function scrubRoleNames(text) {
  return String(text || '').replace(ROLE_SELF_REFERENCE, 'this seat')
}

function tally(values) {
  const counts = {}
  for (const v of values) counts[v] = (counts[v] || 0) + 1
  return counts
}

function uniq(list) {
  return [...new Set(list.filter(isText).map((s) => s.trim()))]
}

function renderSource(s, i) {
  return `${i + 1}. ${s.citation} | ${s.doi_or_link} | ${s.year} | ${s.venue} | weight ${s.evidence_weight} | ${s.relevance_class} | ${s.empirical_basis} | effect: ${s.effect_on_standing_view} | finding: ${s.core_finding} | limitation: ${s.main_limitation}`
}

// ---------------------------------------------------------------- intake

phase('Intake')
const { a, problems } = validate(args)
if (problems.length) {
  log(`REFUSED before any agent ran: ${problems.length} problem(s)`)
  return { status: 'REFUSED', stage: 'Intake', problems, agents_run: 0 }
}
const types = [...new Set(a.decision_types)]
const professionalByType = types.some((t) => PROFESSIONAL_TYPES.includes(t))

// The brief every seat and Chairman sees. The operator's tentative answer and
// expected outcome are deliberately absent.
const brief = [
  `DECISION UNDER REVIEW: ${a.question.trim()}`,
  `Decision type(s): ${types.join(', ')}`,
  'Operator-supplied load-bearing premises:',
  ...a.premises.map((p, i) => `  P${i + 1}. ${p.trim()}`),
  isText(a.base_rate) ? `Base rate or comparison class supplied by the operator: ${a.base_rate.trim()}` : 'Base rate or comparison class: not supplied.',
  isText(a.context) ? `Operator-supplied context (GREEN):\n${a.context.trim()}` : '',
].filter(Boolean).join('\n')

// ---------------------------------------------------------------- evidence

phase('Evidence')
const scout = await agent(
  [
    'Build the Evidence Packet for this Full Council run. You are the only Evidence Scout (single model family).',
    isText(a.date) ? `Date of search: ${a.date}.` : 'State the date of search.',
    '',
    brief,
    '',
    'Return every verified source in sources with all rubric fields. Mark verification Verified only for sources whose identifier you checked this session; everything else is Manual verification required and will be excluded from the consolidated set.',
  ].join('\n'),
  { label: 'Evidence Scout', phase: 'Evidence', agentType: 'council-evidence-scout', schema: SCOUT_SCHEMA },
)
if (!scout) {
  log('HALTED: the Evidence Scout returned nothing')
  return { status: 'HALTED', stage: 'Evidence', reason: 'The Evidence Scout returned no packet. No seat ran. Resume to retry the Scout.', agents_run: 1 }
}

const ev = dedupe(Array.isArray(scout.sources) ? scout.sources : [])
const cap = ceilingFor(ev, types)
const dedupOutput = [
  'Deduplication Output:',
  `- Consolidated source list: ${ev.usable.length} usable of ${ev.consolidated.length} distinct`,
  `- Duplicate sources merged: ${ev.merged}`,
  '- Overlapping findings: one packet (single model family); overlap across model families not assessable',
  '- Unique high-value sources by model family: Claude only',
  `- Sources dropped and why: ${ev.dropped.length ? ev.dropped.map((d) => `${d.s.citation} (${d.why})`).join('; ') : 'none'}`,
  '- Shared-source confidence cap triggered: Not applicable (one packet); the single-model cap applies instead',
  `- Notes for Chairman: computed ceiling ${cap.ceiling}. ${cap.reasons.join(' ')}`,
].join('\n')
log(`Evidence: ${ev.usable.length} usable (${ev.external.length} external, ${ev.strongExternal.length} strong external); ceiling ${cap.ceiling}`)

const evidenceBlock = [
  'CONSOLIDATED EVIDENCE SET (update layer):',
  ev.usable.length ? ev.usable.map(renderSource).join('\n') : '(no verified usable sources: Opinion-only)',
  `Scout summary: ${scout.one_line_summary}`,
  `Effect on the standing view: ${scout.overall_effect}`,
  `Evidence gaps: ${(scout.evidence_gaps || []).join('; ') || 'none stated'}`,
  '',
  dedupOutput,
].join('\n')

// ---------------------------------------------------------------- seats

phase('Seats')
const seatResults = await parallel(SEATS.map((seat) => () => agent(
  [
    `Run your seat for this Full Council run. You work blind to the other seats.`,
    '',
    brief,
    '',
    evidenceBlock,
  ].join('\n'),
  { label: seat.title, phase: 'Seats', agentType: seat.agentType, schema: SEAT_SCHEMA },
)))
const missingSeats = SEATS.filter((_, i) => !seatResults[i]).map((s) => s.title)
if (missingSeats.length) {
  log(`HALTED: missing seat output from ${missingSeats.join(', ')}`)
  return {
    status: 'HALTED',
    stage: 'Seats',
    reason: `No output from ${missingSeats.join(', ')}. The Chairmen did not run: synthesizing without every seat, especially the Contrarian, is the unengaged-dissent failure the protocol guards against. Resume to re-run only the missing seats.`,
    agents_run: 1 + SEATS.length,
  }
}

// ---------------------------------------------------------------- chairmen

phase('Chairmen')
const orders = chairOrders(a.question)
const letters = ['A', 'B', 'C', 'D', 'E']
const chairResults = await parallel(orders.map((order, c) => () => agent(
  [
    `You are Chairman ${c + 1} of ${CHAIRMEN}. Synthesize independently.`,
    `Computed confidence ceiling for this run: ${cap.ceiling}. ${cap.reasons.join(' ')} Any confidence above the ceiling is clamped in code.`,
    professionalByType ? `This decision touches ${types.filter((t) => PROFESSIONAL_TYPES.includes(t)).join(', ')}: include the line "${PRO_LINE}".` : null,
    '',
    brief,
    '',
    evidenceBlock,
    '',
    'SEAT OUTPUTS (anonymized; order chosen for you):',
    ...order.map((seatIndex, pos) => {
      const r = seatResults[seatIndex]
      return [
        `=== Seat ${letters[pos]} ===`,
        scrubRoleNames(r.report),
        `Zero-Defects self-check: ${scrubRoleNames(r.zero_defects_self_check)}`,
        `Seat's recommended cap: ${r.recommends_confidence_cap}`,
        r.steward_verdict !== 'Not applicable' ? `Seat verdict: ${r.steward_verdict}` : null,
      ].filter((line) => line !== null).join('\n')
    }),
  ].filter((line) => line !== null).join('\n'),
  { label: `Chairman ${c + 1}`, phase: 'Chairmen', agentType: 'council-chairman', schema: CHAIR_SCHEMA },
)))

const seatsOut = Object.fromEntries(SEATS.map((seat, i) => [seat.key, {
  title: seat.title,
  key_points: seatResults[i].key_points,
  recommends_confidence_cap: seatResults[i].recommends_confidence_cap,
  verdict: seatResults[i].steward_verdict,
  report: seatResults[i].report,
  zero_defects_self_check: seatResults[i].zero_defects_self_check,
}]))

const missingChairs = chairResults.map((r, i) => (r ? null : i + 1)).filter(Boolean)
if (missingChairs.length) {
  log(`HALTED: missing Chairman output from ${missingChairs.join(', ')}`)
  return {
    status: 'HALTED',
    stage: 'Chairmen',
    reason: `No output from Chairman ${missingChairs.join(', ')}. Resume to re-run only the missing Chairmen.`,
    seats: seatsOut,
    partial_chairmen: chairResults.filter(Boolean).map((r) => ({ decision_class: r.decision_class, recommendation: r.recommendation })),
    agents_run: 1 + SEATS.length + CHAIRMEN,
  }
}

// ---------------------------------------------------------------- enforcement

const professionalRequired = professionalByType || chairResults.some((r) => r.professional_verification_required === true)
const chairmen = chairResults.map((r, c) => {
  const clamp = clampConfidence(r.confidence, cap.ceiling)
  const memo = { ...r.final_decision_memo }
  let proAdded = false
  if (professionalRequired && !JSON.stringify(memo).toLowerCase().includes(PRO_LINE)) {
    memo.professional_verification = `${PRO_LINE}${isText(memo.professional_verification) ? `. ${memo.professional_verification}` : ''}`
    proAdded = true
  }
  return {
    chairman: c + 1,
    seat_order_seen: orders[c].map((seatIndex, pos) => `Seat ${letters[pos]} = ${SEATS[seatIndex].title}`),
    decision_class: r.decision_class,
    recommendation: r.recommendation,
    confidence_claimed: r.confidence,
    confidence_final: clamp.value,
    confidence_clamp_reason: clamp.why,
    cap_applied: r.cap_applied,
    fresh_evidence_delta: r.fresh_evidence_delta,
    strongest_dissent: r.strongest_dissent,
    final_decision_memo: memo,
    professional_line_added_by_harness: proAdded,
    assumption_test_plan: r.assumption_test_plan,
    report: r.report,
  }
})

const classCounts = tally(chairmen.map((c) => c.decision_class))
const topCount = Math.max(...Object.values(classCounts))
const concordance = {
  verdict: topCount === CHAIRMEN ? 'UNANIMOUS' : topCount >= 2 ? 'MAJORITY' : 'SPLIT',
  decision_classes: classCounts,
  note: 'All three Chairmen are one model family: concordance measures consistency, not independent verification. On a MAJORITY or SPLIT, read the dissenting memo first.',
}

const integrity = {
  sources_reviewed: ev.consolidated.length,
  usable_sources: ev.usable.length,
  project_library_sources_used: ev.usable.filter((s) => s.source_type === 'project library').length,
  pdfs_used: ev.usable.filter((s) => /\.pdf\b/i.test(`${s.doi_or_link} ${s.citation}`)).length,
  peer_reviewed_sources_used: ev.usable.filter((s) => s.source_type === 'peer-reviewed').length,
  government_sources_used: ev.usable.filter((s) => s.source_type === 'government primary').length,
  assumptions_made: uniq(chairResults.flatMap((r) => r.assumptions_made || [])),
  major_uncertainties: uniq(chairResults.flatMap((r) => r.major_uncertainties || [])),
  expiry_risks: uniq(scout.expiry_risks || []),
}

const briefLines = [
  '# Full Council result',
  '',
  `Decision: ${a.question.trim()}`,
  `Your pre-committed answer (not shown to any seat): ${a.operator_answer.trim()}`,
  isText(a.expected_without_council) ? `Your expected outcome without the Council: ${a.expected_without_council.trim()}` : null,
  '',
  `Chairmen concordance: ${concordance.verdict} (${Object.entries(classCounts).map(([k, v]) => `${k} x${v}`).join(', ')}). ${concordance.note}`,
  `Confidence ceiling: ${cap.ceiling}. ${cap.reasons.join(' ')}`,
  professionalRequired ? `This decision requires the line: ${PRO_LINE}.` : null,
  '',
  ...chairmen.flatMap((c) => [
    `## Chairman ${c.chairman}: ${c.decision_class}`,
    `Confidence: ${c.confidence_final}${c.confidence_clamp_reason ? ` (clamped: ${c.confidence_clamp_reason})` : ''}`,
    `Recommended decision: ${c.final_decision_memo.recommended_decision}`,
    `Strongest reason it may be wrong: ${c.final_decision_memo.strongest_reason_wrong}`,
    `Key assumption to test: ${c.final_decision_memo.key_assumption_to_test}`,
    `Safest next action: ${c.final_decision_memo.safest_next_action}`,
    `Assumption test: ${c.assumption_test_plan.fastest_test} (owner ${c.assumption_test_plan.owner}, deadline ${c.assumption_test_plan.deadline}; fail changes the decision to: ${c.assumption_test_plan.decision_change_if_failed})`,
    professionalRequired ? `Professional verification: ${c.final_decision_memo.professional_verification}` : null,
    '',
  ]),
  `Steward verdict: ${seatsOut.steward.verdict}`,
  `Contrarian key points: ${seatsOut.contrarian.key_points.join(' | ')}`,
  '',
  'Your step now (step 9): compare the memos with your pre-committed answer, engage the strongest dissent, decide, and record the decision with its ex ante score immediately (reliability-statistician, adjudication/decision_log.py record). The ex ante score is locked once written. Set the review date now.',
  '',
  `Evidence integrity: sources reviewed ${integrity.sources_reviewed}; usable ${integrity.usable_sources}; project library ${integrity.project_library_sources_used}; PDFs ${integrity.pdfs_used}; peer-reviewed ${integrity.peer_reviewed_sources_used}; government ${integrity.government_sources_used}; assumptions ${integrity.assumptions_made.length}; major uncertainties ${integrity.major_uncertainties.length}; expiry risks ${integrity.expiry_risks.length}.`,
].filter((line) => line !== null)

log(`Council complete: ${concordance.verdict}; ceiling ${cap.ceiling}`)

return {
  status: 'COMPLETE',
  protocol: 'Full Council v13, single-model adaptation',
  operator_brief: briefLines.join('\n').replace(/\n{3,}/g, '\n\n').trim(),
  operator_precommitment: {
    operator_answer: a.operator_answer.trim(),
    premises: a.premises.map((p) => p.trim()),
    base_rate: a.base_rate || null,
    expected_without_council: a.expected_without_council || null,
  },
  decision_types: types,
  enforced: {
    confidence_ceiling: cap.ceiling,
    ceiling_reasons: cap.reasons,
    opinion_only: cap.opinionOnly,
    professional_verification_required: professionalRequired,
  },
  concordance,
  chairmen,
  seats: seatsOut,
  evidence: {
    dedup_output: dedupOutput,
    usable_sources: ev.usable,
    dropped_sources: ev.dropped.map((d) => ({ citation: d.s.citation, why: d.why })),
    scout_summary: scout.one_line_summary,
    overall_effect: scout.overall_effect,
    evidence_gaps: scout.evidence_gaps,
    search_disclosure: scout.search_disclosure,
    reason_for_stopping: scout.reason_for_stopping,
    scout_report: scout.report,
  },
  evidence_integrity: integrity,
  agents_run: 1 + SEATS.length + CHAIRMEN,
}
