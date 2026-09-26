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
// args (an object; a JSON string is accepted and parsed; any other key is refused):
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
//   - Intake fails closed: nothing is spawned until the pre-commitment exists, and a
//     refusal never repeats a value that could be a credential.
//   - Every string in the ask is scanned for credential shapes, one string at a time.
//   - The operator's answer and expected outcome never reach a seat or a Chairman
//     (anti-anchoring): the fields are withheld, and an ask that repeats either of them
//     inside another field is refused.
//   - Seats run blind to each other. Chairmen see the seats anonymized as Seat A to E,
//     in identical block shapes, each Chairman in a different seeded order.
//   - The confidence ceiling is computed from the evidence packet and the run's design,
//     and every Chairman's confidence is clamped to it, including the memo's own
//     confidence line; a value outside the vocabulary fails closed to Low.
//   - The professional verification line is required at the start of the memo's
//     professional_verification field wherever the domain calls for it.
//   - Any missing or malformed stage output halts the run (resume re-runs only what is
//     missing).
//   - The harness's own words hold no percentage. Model text in the brief has its dashes
//     normalized, and any line of it holding a percentage is flagged for claim-auditor.

const DECISION_TYPES = ['factual', 'causal', 'predictive', 'strategic', 'legal_regulatory', 'tax', 'compliance', 'ethical', 'financial', 'technical', 'medical', 'interpersonal']
const PROFESSIONAL_TYPES = ['legal_regulatory', 'tax', 'compliance', 'medical']
const BEHAVIOR_TYPES = ['predictive', 'strategic', 'interpersonal']
const LEVELS = ['Low', 'Medium', 'High']
const DECISION_CLASSES = ['PROCEED', 'PROCEED WITH CONDITIONS', 'RUN A REVERSIBLE TEST', 'GATHER EVIDENCE THEN DECIDE', 'DO NOT PROCEED']
const PRO_LINE = 'professional verification required'
const CHAIRMEN = 3
const ARG_KEYS = ['question', 'why_full_council', 'operator_answer', 'premises', 'decision_types', 'green_only', 'base_rate', 'expected_without_council', 'context', 'date']
const ANCHOR_MIN_CHARS = 12 // shorter answers ("yes", "proceed") cannot be checked for containment without false alarms

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

// Credential shapes, including the five vendors this repository's panel uses.
// Each is anchored at the start of a string or after a non-identifier character
// (a newline and a tab count), without lookbehind, which not every engine has.
// Tested against every string in the ask one at a time, never against a JSON
// dump, where a newline becomes the letters \n and hides the key behind them.
const AT = '(?:^|[^A-Za-z0-9_])'
const SECRET_PATTERNS = [
  new RegExp(`${AT}sk-ant-[A-Za-z0-9_-]{8,}`), // Anthropic
  new RegExp(`${AT}sk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}`), // OpenAI, including project keys
  new RegExp(`${AT}AIza[0-9A-Za-z_-]{30,}`), // Google
  new RegExp(`${AT}xai-[A-Za-z0-9_-]{20,}`), // xAI
  new RegExp(`${AT}AKIA[0-9A-Z]{16}`), // AWS access key id
  new RegExp(`${AT}gh[opsur]_[A-Za-z0-9]{20,}`), // GitHub tokens
  new RegExp(`${AT}github_pat_[A-Za-z0-9_]{20,}`),
  new RegExp(`${AT}xox[abprs]-[A-Za-z0-9-]{10,}`), // Slack
  new RegExp(`${AT}[rs]k_live_[A-Za-z0-9]{16,}`), // Stripe
  /-----BEGIN [A-Z ]*PRIVATE KEY/, // PEM, OpenSSH, and PGP private keys
  /ADJ_SEAT_[0-9]+_API_KEY\s*[=:]\s*\S+/, // this repository's own key names (Mistral keys carry no prefix)
  /(?:API|SECRET|ACCESS|AUTH|PRIVATE)[_-]?(?:KEY|TOKEN)\s*[=:]\s*['"]?[A-Za-z0-9_\-./+=]{16,}/i,
  /(?:PASSWORD|PASSWD)\s*[=:]\s*['"]?\S{8,}/i,
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
const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v)
const SAFE_TOKEN = /^[a-z_]{1,32}$/
const SAFE_KEY = /^[A-Za-z_][A-Za-z0-9_]{0,40}$/

// Every string in a value, keys included, without recursion.
function stringsIn(value) {
  const out = []
  const stack = [value]
  while (stack.length) {
    const v = stack.pop()
    if (typeof v === 'string') out.push(v)
    else if (Array.isArray(v)) stack.push(...v)
    else if (v !== null && typeof v === 'object') {
      for (const k of Object.keys(v)) {
        out.push(k)
        stack.push(v[k])
      }
    }
  }
  return out
}

const looksLikeSecret = (s) => SECRET_PATTERNS.some((re) => re.test(s))

function isCalendarDate(s) {
  const m = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/.exec(s)
  if (!m) return false
  const y = Number(m[1])
  const mo = Number(m[2])
  const d = Number(m[3])
  if (y < 1 || mo < 1 || mo > 12 || d < 1) return false
  const leap = (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  return d <= days[mo - 1]
}

const squash = (s) => String(s).toLowerCase().replace(/\s+/g, ' ').trim()

function validate(raw) {
  let a = raw
  if (typeof a === 'string') {
    try {
      a = JSON.parse(a)
    } catch (e) {
      return { a: null, problems: ['args is a string that is not valid JSON; pass an object'] }
    }
  }
  if (!isObj(a)) {
    return { a: null, problems: ['args must be an object with question, why_full_council, operator_answer, premises, decision_types, green_only'] }
  }
  const problems = []
  const strings = stringsIn(a)
  const secretFound = strings.some(looksLikeSecret)
  if (secretFound) {
    problems.push('the ask contains a credential-shaped string; remove it (NO SECRETS). No value from the ask is repeated in these problems.')
  }
  const unknownKeys = Object.keys(a).filter((k) => !ARG_KEYS.includes(k))
  for (const k of unknownKeys) {
    problems.push(!secretFound && SAFE_KEY.test(k) ? `unknown field: ${k} (a misspelled field is refused, not ignored)` : 'an unknown field (name not shown)')
  }
  if (!isText(a.question)) problems.push('question is required')
  if (!isText(a.why_full_council)) problems.push('why_full_council is required: the Full Council is for high-stakes or hard-to-reverse decisions only (step 1)')
  if (!isText(a.operator_answer)) problems.push('operator_answer is required: write your own tentative answer before any seat runs (step 2)')
  const premises = Array.isArray(a.premises) ? a.premises : []
  if (premises.length < 1 || premises.length > 3 || !premises.every(isText)) {
    problems.push('premises must be one to three non-empty statements (step 2)')
  }
  const types = Array.isArray(a.decision_types) ? a.decision_types : []
  if (types.length === 0) problems.push(`decision_types is required, from: ${DECISION_TYPES.join(', ')} (step 3)`)
  if (!types.every((t) => typeof t === 'string')) {
    problems.push('decision_types must contain only strings')
  } else {
    const unknown = types.filter((t) => !DECISION_TYPES.includes(t))
    if (unknown.length) {
      const shown = unknown.filter((t) => !secretFound && SAFE_TOKEN.test(t))
      const hidden = unknown.length - shown.length
      problems.push(`unknown decision_types: ${[...shown, ...(hidden ? [`${hidden} value(s) not shown`] : [])].join(', ')}; allowed: ${DECISION_TYPES.join(', ')}`)
    }
  }
  if (a.green_only !== true) {
    problems.push('green_only must be true: confirm the ask holds no patent claim text, prosecution strategy, credentials, or other entities\' data')
  }
  for (const k of ['base_rate', 'expected_without_council', 'context', 'date']) {
    if (a[k] !== undefined && typeof a[k] !== 'string') problems.push(`${k} must be a string when given`)
  }
  if (typeof a.date === 'string' && !isCalendarDate(a.date)) problems.push('date must be a real date written YYYY-MM-DD when given')
  // Anti-anchoring holds only if the withheld answer is not simply repeated
  // in a field the seats do see.
  const seen = { question: a.question, why_full_council: a.why_full_council, context: a.context, base_rate: a.base_rate, premises: Array.isArray(a.premises) ? a.premises.join(' ') : '' }
  for (const [label, withheld] of [['operator_answer', a.operator_answer], ['expected_without_council', a.expected_without_council]]) {
    if (!isText(withheld) || squash(withheld).length < ANCHOR_MIN_CHARS) continue
    const hits = Object.entries(seen).filter(([, v]) => typeof v === 'string' && squash(v).includes(squash(withheld))).map(([k]) => k)
    if (hits.length) problems.push(`${label} is repeated inside ${hits.join(', ')}; remove it there, or the seats see the answer they must not be anchored by`)
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

// A source's identities: its DOI (from the link or the citation), its link with
// scheme, www, query, fragment, and trailing slash removed, and its full
// citation text. When both sources carry a DOI, the DOIs decide. Otherwise a
// shared link or an identical full citation makes them one source, so a strong
// source listed twice cannot count twice, and distinct link-less sources never
// merge on a shared prefix.
const DOI_IN = /10\.[0-9]{4,9}\/[^\s?#"'<>]+/i
function identities(s) {
  const link = String(s.doi_or_link || '').trim()
  const cite = squash(s.citation || '')
  const found = DOI_IN.exec(link) || DOI_IN.exec(cite)
  const doi = found ? found[0].toLowerCase().replace(/[.,;:)\]]+$/, '') : null
  let url = link.toLowerCase().replace(/^[a-z][a-z0-9+.-]*:\/\//, '').replace(/^www\./, '').replace(/[?#].*$/, '').replace(/\/+$/, '')
  if (!url || url.startsWith('10.') || /^(dx\.)?doi\.org\//.test(url)) url = null
  return { doi, url, cite: cite || null }
}

// Loose identity: one DOI, or (without two DOIs to compare) one link or one
// full citation. Strict identity: one DOI, else one link, and a citation only
// between two link-less sources. Loose merges a work listed twice under two
// links; strict keeps apart different files that share a generic citation.
// Each error could raise the ceiling, so the ceiling is computed both ways and
// the lower one stands.
function sameLoose(x, y) {
  if (x.doi && y.doi) return x.doi === y.doi
  return Boolean((x.url && x.url === y.url) || (x.cite && x.cite === y.cite))
}

function sameStrict(x, y) {
  if (x.doi && y.doi) return x.doi === y.doi
  if (x.url && y.url) return x.url === y.url
  if (!x.doi && !y.doi && !x.url && !y.url) return Boolean(x.cite && x.cite === y.cite)
  return false
}

function consolidate(sources, same) {
  const kept = []
  let merged = 0
  for (const s of sources) {
    const id = identities(s)
    if (kept.some((k) => same(k.id, id))) {
      merged += 1
      continue
    }
    kept.push({ s, id })
  }
  const consolidated = kept.map((k) => k.s)
  const dropped = []
  const usable = []
  for (const s of consolidated) {
    if (s.verification !== 'Verified') dropped.push({ s, why: 'not verified this session' })
    else if (s.relevance_class !== 'Direct' && s.relevance_class !== 'Indirect') dropped.push({ s, why: `relevance ${s.relevance_class}` })
    else usable.push(s)
  }
  const isStrong = (s) => s.relevance_class === 'Direct' && (s.evidence_weight === 'High' || s.evidence_weight === 'Medium')
  const external = usable.filter((s) => s.source_type !== 'project library')
  return { consolidated, merged, usable, dropped, external, strongExternal: external.filter(isStrong), strongUsable: usable.filter(isStrong) }
}

function dedupe(sources) {
  return { ...consolidate(sources, sameLoose), strict: consolidate(sources, sameStrict) }
}

function ceilingFor(ev, types) {
  const reasons = ['Single model family: every seat and Chairman in this build runs on one model family, so their agreement is not independent verification (shared-model cap, Medium at most).']
  let ceiling = 'Medium'
  const opinionOnly = ev.external.length === 0
  const mostlyWeak = (v) => v.strongExternal.length * 2 < v.external.length || v.strongUsable.length * 2 < v.usable.length
  if (opinionOnly) {
    ceiling = 'Low'
    reasons.push('No verified external evidence: the synthesis is Opinion-only (cap Low).')
  } else if (mostlyWeak(ev) || mostlyWeak(ev.strict)) {
    ceiling = 'Low'
    reasons.push(`Evidence is mostly indirect or low weight: ${ev.strongExternal.length} of ${ev.external.length} usable external sources, and ${ev.strongUsable.length} of ${ev.usable.length} usable sources overall, are Direct with High or Medium weight, counted with duplicates merged and again with only exact duplicates merged (cap Low when any count is under half, a convention).`)
  }
  const behavioral = types.filter((t) => BEHAVIOR_TYPES.includes(t))
  if (behavioral.length) reasons.push(`Decision type ${behavioral.join(', ')} caps at Medium regardless of evidence.`)
  return { ceiling, reasons, opinionOnly }
}

function clampConfidence(claimed, ceiling) {
  if (!LEVELS.includes(claimed)) {
    return { value: 'Low', why: 'the claimed confidence is outside Low, Medium, High, so it fails closed to Low' }
  }
  if (LEVELS.indexOf(claimed) <= LEVELS.indexOf(ceiling)) return { value: claimed, why: null }
  return { value: ceiling, why: `${claimed} exceeds the ${ceiling} ceiling computed for this run` }
}

function scrubRoleNames(text) {
  return String(text || '').replace(ROLE_SELF_REFERENCE, 'this seat')
}

// Model text quoted in the operator brief. The harness never endorses a
// percentage a model wrote: the line is flagged, not silently kept or cut.
const PERCENT_FLAG = ' [harness: this line quotes a percentage from model text; a percentage is valid only when computed from supplied data with the calculation shown, so check it with claim-auditor]'
function fromModel(text) {
  const t = String(text ?? '')
  return /[0-9]\s*(%|percent\b)/i.test(t) || t.includes('%') ? t + PERCENT_FLAG : t
}

// The house typography rule, applied to everything the brief shows. The dash
// characters are built from code points so this file never contains them.
const EM_DASH = new RegExp(`\\s*${String.fromCharCode(0x2014)}\\s*`, 'g')
const EN_DASH = new RegExp(String.fromCharCode(0x2013), 'g')
function undash(text) {
  return text.replace(EM_DASH, ' - ').replace(EN_DASH, '-')
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

// A result that is present but not the shape the schema promised is as
// unusable as a missing one: halting beats crashing mid-synthesis.
const scoutOk = (r) => isObj(r) && Array.isArray(r.sources) && isText(r.report)
const seatOk = (r) => isObj(r) && isText(r.report) && Array.isArray(r.key_points) && r.key_points.every((k) => typeof k === 'string')
const chairOk = (r) => isObj(r) && isText(r.report) && DECISION_CLASSES.includes(r.decision_class)
  && isObj(r.final_decision_memo) && isObj(r.assumption_test_plan)

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
if (!scoutOk(scout)) {
  log('HALTED: the Evidence Scout returned no usable packet')
  return { status: 'HALTED', stage: 'Evidence', reason: 'The Evidence Scout returned no usable packet. No seat ran. Resume to retry the Scout.', agents_run: 1 }
}

const ev = dedupe(scout.sources)
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
  `Evidence gaps: ${(Array.isArray(scout.evidence_gaps) ? scout.evidence_gaps : []).join('; ') || 'none stated'}`,
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
const missingSeats = SEATS.filter((_, i) => !seatOk(seatResults[i])).map((s) => s.title)
if (missingSeats.length) {
  log(`HALTED: missing or malformed seat output from ${missingSeats.join(', ')}`)
  return {
    status: 'HALTED',
    stage: 'Seats',
    reason: `No usable output from ${missingSeats.join(', ')}. The Chairmen did not run: synthesizing without every seat, especially the Contrarian, is the unengaged-dissent failure the protocol guards against. Resume to re-run only the missing seats.`,
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
    professionalByType ? `This decision touches ${types.filter((t) => PROFESSIONAL_TYPES.includes(t)).join(', ')}: begin the memo's professional_verification field with "${PRO_LINE}".` : null,
    '',
    brief,
    '',
    evidenceBlock,
    '',
    'SEAT OUTPUTS (anonymized; order chosen for you; every block has the same shape):',
    ...order.map((seatIndex, pos) => {
      const r = seatResults[seatIndex]
      return [
        `=== Seat ${letters[pos]} ===`,
        scrubRoleNames(r.report),
        `Zero-Defects self-check: ${scrubRoleNames(r.zero_defects_self_check)}`,
        `Seat's recommended cap: ${r.recommends_confidence_cap}`,
      ].join('\n')
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

const missingChairs = chairResults.map((r, i) => (chairOk(r) ? null : i + 1)).filter(Boolean)
if (missingChairs.length) {
  log(`HALTED: missing or malformed Chairman output from ${missingChairs.join(', ')}`)
  return {
    status: 'HALTED',
    stage: 'Chairmen',
    reason: `No usable output from Chairman ${missingChairs.join(', ')}. Resume to re-run only the missing Chairmen.`,
    seats: seatsOut,
    partial_chairmen: chairResults.filter(chairOk).map((r) => ({ decision_class: r.decision_class, recommendation: r.recommendation })),
    agents_run: 1 + SEATS.length + CHAIRMEN,
  }
}

// ---------------------------------------------------------------- enforcement

const professionalRequired = professionalByType || chairResults.some((r) => r.professional_verification_required === true)
const chairmen = chairResults.map((r, c) => {
  const clamp = clampConfidence(r.confidence, cap.ceiling)
  const memo = { ...r.final_decision_memo }
  // The memo's own confidence line is replaced by the enforced value: a memo
  // that still read "High" after the clamp would contradict its own number.
  memo.confidence_and_cap = `${clamp.value}. Ceiling ${cap.ceiling}: ${cap.reasons.join(' ')}`
  // Checked on the field itself, at its start: "No professional verification
  // required" anywhere in the memo must not switch the line off.
  const pv = String(memo.professional_verification ?? '').trim()
  let proAdded = false
  if (professionalRequired && !pv.toLowerCase().startsWith(PRO_LINE)) {
    memo.professional_verification = `${PRO_LINE}${pv ? `. ${pv}` : ''}`
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
    confidence_and_cap_as_written: r.final_decision_memo.confidence_and_cap,
    cap_applied_as_written: r.cap_applied,
    fresh_evidence_delta: r.fresh_evidence_delta,
    strongest_dissent: r.strongest_dissent,
    final_decision_memo: memo,
    professional_line_added_by_harness: proAdded,
    assumption_test_plan: r.assumption_test_plan,
    report: r.report,
    report_note: 'The report is the Chairman\'s own text; where it states a confidence, confidence_final governs.',
  }
})

const classCounts = tally(chairmen.map((c) => c.decision_class))
const topCount = Math.max(...Object.values(classCounts))
const concordance = {
  verdict: topCount === CHAIRMEN ? 'UNANIMOUS' : topCount >= 2 ? 'MAJORITY' : 'SPLIT',
  decision_classes: classCounts,
  note: 'All three Chairmen are one model family: concordance measures consistency, not independent verification. On a MAJORITY or SPLIT, read the dissenting memo first.',
}

const listOf = (v) => (Array.isArray(v) ? v : [])
const integrity = {
  sources_reviewed: ev.consolidated.length,
  usable_sources: ev.usable.length,
  project_library_sources_used: ev.usable.filter((s) => s.source_type === 'project library').length,
  pdfs_used: ev.usable.filter((s) => /\.pdf\b/i.test(`${s.doi_or_link} ${s.citation}`)).length,
  peer_reviewed_sources_used: ev.usable.filter((s) => s.source_type === 'peer-reviewed').length,
  government_sources_used: ev.usable.filter((s) => s.source_type === 'government primary').length,
  assumptions_made: uniq(chairResults.flatMap((r) => listOf(r.assumptions_made))),
  major_uncertainties: uniq(chairResults.flatMap((r) => listOf(r.major_uncertainties))),
  expiry_risks: uniq(listOf(scout.expiry_risks)),
}

const plan = (p) => `${fromModel(p.fastest_test)} (owner ${fromModel(p.owner)}, deadline ${fromModel(p.deadline)}; fail changes the decision to: ${fromModel(p.decision_change_if_failed)})`
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
    `Recommended decision: ${fromModel(c.final_decision_memo.recommended_decision)}`,
    `Strongest reason it may be wrong: ${fromModel(c.final_decision_memo.strongest_reason_wrong)}`,
    `Key assumption to test: ${fromModel(c.final_decision_memo.key_assumption_to_test)}`,
    `Safest next action: ${fromModel(c.final_decision_memo.safest_next_action)}`,
    `Assumption test: ${plan(c.assumption_test_plan)}`,
    professionalRequired ? `Professional verification: ${fromModel(c.final_decision_memo.professional_verification)}` : null,
    '',
  ]),
  `Steward verdict: ${seatsOut.steward.verdict}`,
  `Contrarian key points: ${seatsOut.contrarian.key_points.map(fromModel).join(' | ')}`,
  '',
  'Your step now (step 9): compare the memos with your pre-committed answer, engage the strongest dissent, decide, and record the decision with its ex ante score immediately (reliability-statistician, adjudication/decision_log.py record). The ex ante score is locked once written. Set the review date now.',
  '',
  `Evidence integrity: sources reviewed ${integrity.sources_reviewed}; usable ${integrity.usable_sources}; project library ${integrity.project_library_sources_used}; PDFs ${integrity.pdfs_used}; peer-reviewed ${integrity.peer_reviewed_sources_used}; government ${integrity.government_sources_used}; assumptions ${integrity.assumptions_made.length}; major uncertainties ${integrity.major_uncertainties.length}; expiry risks ${integrity.expiry_risks.length}.`,
].filter((line) => line !== null)

log(`Council complete: ${concordance.verdict}; ceiling ${cap.ceiling}`)

return {
  status: 'COMPLETE',
  protocol: 'Full Council v13, single-model adaptation',
  operator_brief: undash(briefLines.join('\n')).replace(/\n{3,}/g, '\n\n').trim(),
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
