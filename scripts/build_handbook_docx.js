const fs = require('fs');
const M = require('./make_docx.js');
const {
  kids, AG, C, OUT, order, byOutcome, nice, live, blocked,
  H1, H2, H3, txt, table, cell, box, gap, notesBlock, checkTable, checkRow,
  agentBlock, PageBreak, Paragraph, Document, Packer, AlignmentType,
  WidthType, ShadingType, BorderStyle, TableRow, HeadingLevel, t, CHK,
} = M;
const S = '/tmp/claude-0/-home-user-forge-talent-connections/f7340004-d5dc-5a8f-b52b-7cf5e677a454/scratchpad';
const br = () => new Paragraph({ children: [new PageBreak()] });

// ══ PART 2 — THE 7 HABITS ═════════════════════════════════════════════════
kids.push(br(), H1('🌱', 'PART 2 — YOUR 7 HABITS'));
kids.push(txt('These are the seven habits from Stephen Covey’s "The 7 Habits of Highly Effective People", used here as the shape of your week. One habit, one thing to do, one box to tick.', { size: 22, italics: true, color: C.grey }));
kids.push(...box('🧠', 'HOW TO USE THIS PART (for a busy brain)', [
  'Do Habit 1 TODAY. It takes 10 minutes. Do not read ahead.',
  'Do ONE habit at a time. Never two. Two is how nothing finishes.',
  'Tick the box when it is done. A ticked box is the only proof that counts.',
  'If you skip a week, start again at the habit you were on. Do not start over.',
], C.navy, C.panel));

const HABITS = [
  { n: 1, emo: '🚀', title: 'BE PROACTIVE', col: C.A, bg: C.Abg,
    plain: 'Do not wait for the perfect moment. Run one helper today.',
    why: 'You have 33 helpers and, until today, almost none had ever run. A helper that has never run is only a promise.',
    smart: ['S — Run the BRIEFER helper one time.', 'M — One page of notes exists that you did not write.',
            'A — 25 minutes. It costs nothing extra.', 'R — You have already paid for this. Nothing is blocking it.',
            'T — TODAY. Before you go to bed.'],
    rows: [['Open Claude Code in your FORGE project folder', 'It is the same window you already use'],
           ['Type: "Use the BRIEFER agent to research ___ for me."', 'Fill the blank with any real question you have'],
           ['Read the one page it gives you', 'Under 5 minutes'],
           ['Ask yourself: did that save me time? Write yes or no →', 'This is the only score that matters']] },
  { n: 2, emo: '🎯', title: 'BEGIN WITH THE END IN MIND', col: C.D, bg: C.Dbg,
    plain: 'You already wrote your big goal. Now write the small one under it.',
    why: 'Your big goal is a 10-year goal. A 10-year goal with nothing under it cannot get stuck in a way you would notice — nothing is due soon enough.',
    smart: ['S — Write ONE 90-day goal in the goal ledger file.', 'M — The file has a filled-in row where it is blank now.',
            'A — 20 minutes of thinking, 2 minutes of typing.', 'R — Only you can do this. No helper is allowed to.',
            'T — This week. Sunday at the latest.'],
    rows: [['Open agents/analysis/goal-ledger.md', 'Your big goal is already at the top'],
           ['Find the QUARTER table. It is empty.', 'One row is enough. Not three.'],
           ['Write: "<something> will be true by <a date>"', 'NOT "improve sales". A date, or it does not count.'],
           ['Name ONE next action — the first physical thing', 'Open the file. Send the email. Make the call.']] },
  { n: 3, emo: '1️⃣', title: 'PUT FIRST THINGS FIRST', col: C.C, bg: C.Cbg,
    plain: 'One goal moving at a time. Everything else goes in the parking lot.',
    why: 'This is arithmetic, not opinion. If you work on 5 things at once, each takes 5 times longer to finish. You do not finish more. You finish later.',
    smart: ['S — Exactly ONE goal is marked MOVING.', 'M — Count the MOVING rows. The number is 1.',
            'A — It is a one-word edit.', 'R — Hard emotionally, easy practically.',
            'T — Every Monday morning, forever.'],
    rows: [['Look at your goal ledger. Count the MOVING rows.', 'If it is more than 1, you are slowing yourself down'],
           ['Pick the ONE. Change the others to PARKED.', 'Parked is not cancelled. It is "not today".'],
           ['Use the PARKING agent for every new idea this week', 'Say: "Use the PARKING agent to park this idea."'],
           ['Set a stop time before you start any work block', 'An open-ended block is why nothing has started for days']] },
  { n: 4, emo: '🤝', title: 'THINK WIN-WIN', col: C.B, bg: C.Bbg,
    plain: 'Give each helper only the powers it needs. Both of you win.',
    why: 'A helper with too much power is a risk. A helper with too little is useless. Each of yours was set once, on purpose, and a computer check keeps it that way.',
    smart: ['S — Read the "what no helper may ever do" list in Part 5.', 'M — You can name 3 forbidden actions from memory.',
            'A — 5 minutes of reading.', 'R — You need this to trust them.',
            'T — Before you let any helper touch your email.'],
    rows: [['Read Part 5 of this book, the red page', 'It is short on purpose'],
           ['Notice: the email helper has NO SEND BUTTON', 'Removed, not hidden'],
           ['Run: python3 scripts/agent_parity.py', 'It checks the powers still match. Copy that line exactly.'],
           ['If it ever says BLOCKED, do not override it. Ask first.', 'A blocked gate is the system working']] },
  { n: 5, emo: '👂', title: 'SEEK FIRST TO UNDERSTAND', col: C.D, bg: C.Dbg,
    plain: 'Read what the helper gave you BEFORE you act on it.',
    why: 'Helpers make mistakes. Yours already caught ME making 19 of them. The helper writes; you decide. Always that order.',
    smart: ['S — Never act on a helper’s output without reading it.', 'M — Zero things sent or filed unread.',
            'A — Costs seconds.', 'R — This is the whole safety design.',
            'T — Every single time. No exceptions, ever.'],
    rows: [['Read the helper’s answer all the way to the end', 'The warnings are usually at the bottom'],
           ['Look for the words Unknown, Unverified or Assumption', 'Those mean: the helper is NOT sure. Believe it.'],
           ['If a number looks surprising, ask it to show the maths', 'Say: "Show me how you calculated that."'],
           ['Use EVIDENCE-AUDITOR on anything important', 'Say: "Use the EVIDENCE-AUDITOR agent on this document."']] },
  { n: 6, emo: '🧩', title: 'SYNERGIZE', col: C.A, bg: C.Abg,
    plain: 'Pair a maker with a checker. Never let one helper mark its own work.',
    why: 'A helper that both writes and checks has a reason to say its own work is fine. Two helpers, opposite jobs, is how you get the truth.',
    smart: ['S — Every time BUILDER writes code, REVIEWER checks it.', 'M — Zero code changes with no review.',
            'A — One extra sentence when you ask.', 'R — Already proven: the checker found 19 real problems.',
            'T — Same day. Never "later".'],
    rows: [['When BUILDER writes something, immediately run the checker', 'Say: "Now use the ADVERSARIAL-REVIEWER agent on that."'],
           ['For research, pair BRIEFER with EVIDENCE-AUDITOR', 'One writes, one attacks'],
           ['For anything with a number in it, ask for re-derivation', 'That is exactly how my 2% vs 4.72% error was caught'],
           ['Never accept "looks good to me" from the helper that wrote it', 'It is not lying. It just cannot see its own blind spot.']] },
  { n: 7, emo: '🪚', title: 'SHARPEN THE SAW', col: C.C, bg: C.Cbg,
    plain: 'Once a week, check whether the helpers are actually saving you time.',
    why: 'If your review time is not going DOWN, the helpers are a tax, not a tool. This is the one number that can prove the whole thing was a bad idea. Keep it honest.',
    smart: ['S — Run STEWARD once a week and read one screen.', 'M — Minutes you spent reviewing. Going down, or not.',
            'A — 10 minutes on a Friday.', 'R — You cannot know if this works without it.',
            'T — Every Friday. Put it in your calendar now.'],
    rows: [['Friday: say "Use the STEWARD agent for this week."', 'It reports how much of your time the helpers used'],
           ['Look at ONE number: your review minutes', 'Up two weeks in a row = demote a helper'],
           ['Ask GOALKEEPER if anything is stuck', 'Say: "Use the GOALKEEPER agent."'],
           ['Tick this box, close the laptop, rest', 'Rest is part of the habit, not a reward for finishing it']] },
];

HABITS.forEach(h => {
  kids.push(br());
  kids.push(new Paragraph({
    children: [t(`${h.emo}  HABIT ${h.n} — ${h.title}`, { size: 38, bold: true, color: C.white })],
    shading: { type: ShadingType.CLEAR, fill: h.col }, spacing: { before: 200, after: 0 },
    indent: { left: 140, right: 140 }, heading: HeadingLevel.HEADING_2,
  }));
  kids.push(new Paragraph({
    children: [t(h.plain, { size: 26, bold: true, color: h.col })],
    shading: { type: ShadingType.CLEAR, fill: h.bg }, spacing: { before: 0, after: 160 },
    indent: { left: 140, right: 140 },
  }));
  kids.push(H3('🤔  Why this one matters', h.col));
  kids.push(txt(h.why, { size: 22 }));
  kids.push(H3('🎯  The SMART version', h.col));
  kids.push(table([9360], h.smart.map(s => new TableRow({ children: [
    cell(txt(s, { size: 21, bold: s.startsWith('T —') }), { w: 9360, shade: s.startsWith('T —') ? h.bg : undefined })]}))));
  kids.push(H3('✅  Do these, in this order', h.col));
  kids.push(checkTable(h.rows.map(r => checkRow(r[0], r[1]))));
  kids.push(...notesBlock(3, `📝  HABIT ${h.n} — WHAT HAPPENED WHEN I TRIED IT`));
});

// ══ PART 3 — EVERY AGENT ══════════════════════════════════════════════════
kids.push(br(), H1('🤖', 'PART 3 — EVERY HELPER, ONE BY ONE'));
kids.push(txt(`You have ${live} helpers switched on. ${blocked} of them are deliberately locked. Here is every single one.`, { size: 24, bold: true, color: C.navy }));
kids.push(...box('💬', 'HOW TO CALL ANY HELPER — this never changes', [
  '1. Open Claude Code in your FORGE project folder.',
  '2. Type a normal sentence with the helper’s NAME in it.',
  '3. Example: "Use the MAILROOM agent to sort my inbox."',
  '4. That is the whole thing. There is no menu, no code, no setup.',
  'If you forget a name, just describe what you want — it will pick one for you.',
], C.navy, C.panel));

let n = 0;
order.forEach(k => {
  const list = byOutcome(k);
  kids.push(br());
  kids.push(new Paragraph({
    children: [t(`${OUT[k].emo}  ${OUT[k].name}  —  ${list.length} helpers`, { size: 34, bold: true, color: C.white })],
    shading: { type: ShadingType.CLEAR, fill: C[k] }, spacing: { before: 200, after: 0 },
    indent: { left: 140, right: 140 }, heading: HeadingLevel.HEADING_2,
  }));
  kids.push(new Paragraph({
    children: [t(OUT[k].plain, { size: 24, bold: true, color: C[k] })],
    shading: { type: ShadingType.CLEAR, fill: C[k + 'bg'] }, spacing: { before: 0, after: 150 },
    indent: { left: 140, right: 140 },
  }));
  list.forEach(a => { n += 1; kids.push(...agentBlock(a, n)); });
});

// protocols
const protos = AG.filter(a => a.kind === 'protocol');
kids.push(br(), H2('🙋  TWO THINGS NO HELPER CAN DO FOR YOU', C.navy));
kids.push(...box('⚠️', 'THESE ARE NOT HELPERS. THEY ARE JOBS FOR YOU.', [
  'It would have been easy to make these look like helpers. That would have been a lie, and you would have waited forever for something that was never coming.',
  'Nothing and nobody can do these two except you.',
], C.C, C.Cbg));
protos.forEach(a => {
  kids.push(H3(`🙋 ${nice(a.name)}`, C.C));
  kids.push(txt(a.mandate, { size: 22 }));
  kids.push(txt(`Its one job: ${a.goal}`, { size: 21, italics: true }));
  kids.push(checkTable([checkRow(`I have done the ${nice(a.name)} job myself`, 'No helper will ever tick this for you')]));
});

// ══ PART 4 — SMART PLAN ═══════════════════════════════════════════════════
kids.push(br(), H1('📅', 'PART 4 — YOUR 30 / 90 / 365 PLAN'));
kids.push(txt('Specific · Measurable · Attainable · Realistic · Time-Bound. Nothing here needs new money or new tools.', { size: 22, italics: true, color: C.grey }));
[['🌅 NEXT 30 DAYS', C.A, C.Abg, [
    ['S', 'Run 5 different helpers at least once each'],
    ['M', 'Five ticked boxes in Part 3 of this book'],
    ['A', 'About 20 minutes a day'],
    ['R', 'They are installed and working today. Nothing is in the way.'],
    ['T', 'By 15 October 2026'],
  ]],
 ['🌤️ NEXT 90 DAYS', C.D, C.Dbg, [
    ['S', 'One 90-day goal written, and the Friday review done 12 weeks running'],
    ['M', '12 ticked Friday boxes; review minutes trending DOWN'],
    ['A', '10 minutes every Friday'],
    ['R', 'The helpers do the measuring. You only read it.'],
    ['T', 'By 14 December 2026'],
  ]],
 ['🌞 NEXT 365 DAYS', C.C, C.Cbg, [
    ['S', 'Helpers handle your inbox sorting and your first-draft research'],
    ['M', 'Hours returned per week — a real number, not a feeling'],
    ['A', 'Only if the 30- and 90-day steps happened first'],
    ['R', 'Honest answer: UNKNOWN until the 14-day time baseline is done. No promise is made here.'],
    ['T', 'Reviewed 15 September 2027'],
  ]],
].forEach(([title, col, bg, rows]) => {
  kids.push(H2(title, col));
  kids.push(table([900, 8460], rows.map(r => new TableRow({ children: [
    cell(txt(r[0], { bold: true, size: 26, color: col, align: AlignmentType.CENTER }), { w: 900, shade: bg }),
    cell(txt(r[1], { size: 22 }), { w: 8460 })]}))));
});
kids.push(...box('🙏', 'ONE HONEST SENTENCE ABOUT YOUR BIG GOAL', [
  'Your goal is to become a Christian billionaire philanthropist, in U.S. dollars.',
  'These helpers give you back hours and stop you making mistakes you cannot undo.',
  'They do NOT make you a billionaire, and no number in this book claims a chance of it.',
  'What they can do is make sure no hour is wasted and no mistake is permanent. What you build with those hours is yours.',
  'And the giving part does not wait for the billion — FIRSTFRUITS measures it from the first dollar.',
], C.gold, 'FFFBEB'));

// ══ PART 5 — SAFETY ═══════════════════════════════════════════════════════
kids.push(br(), H1('🛡️', 'PART 5 — WHAT NO HELPER MAY EVER DO'));
kids.push(txt('Print this page. Put it where you can see it.', { size: 24, bold: true, color: C.B }));
kids.push(table([4680, 4680], [
  ['📧 Send an email to anyone', '💳 Buy anything or move money'],
  ['📤 Submit to a government portal', '📜 File anything with the patent office'],
  ['🌐 Publish or post anything', '✍️ Sign or agree to terms'],
  ['🗑️ Delete your data', '🚀 Put anything live for customers'],
  ['🔑 Log in as you, or solve a CAPTCHA', '👤 Decide who gets hired'],
  ['🔀 Merge code into the main project', '📊 Invent a number or a percentage'],
].map(r => new TableRow({ children: [
  cell(txt(r[0], { size: 22, bold: true, color: C.B }), { w: 4680, shade: C.Bbg }),
  cell(txt(r[1], { size: 22, bold: true, color: C.B }), { w: 4680, shade: C.Bbg })]}))));
kids.push(...box('🔒', 'WHY YOU CAN TRUST THIS LIST', [
  'These are not promises written in a document. The powers were physically removed.',
  'The email helper does not have a send button to press. It is not in its toolbox.',
  'A computer check runs on every change. If a helper ever gained one of these powers, the check stops the change from saving.',
  'That check has already blocked its own author more than once.',
], C.B, C.Bbg));
kids.push(H2('🚨  If something ever feels wrong', C.B));
kids.push(checkTable([
  checkRow('STOP. Close the window.', 'You lose nothing. Helpers do not keep working when you close them.'),
  checkRow('Nothing was sent, bought, or published', 'It could not have been. See the list above.'),
  checkRow('Write down what you saw', 'One line is enough'),
  checkRow('Ask a fresh session to check it', 'Say: "Use the EVIDENCE-AUDITOR agent on this."'),
]));

// ══ PART 6 — MASTER CHECKLIST ═════════════════════════════════════════════
kids.push(br(), H1('🗒️', 'PART 6 — YOUR MASTER CHECKLIST'));
kids.push(txt('Tick these in order. Do not skip. Do not do two at once.', { size: 24, bold: true, color: C.navy }));
kids.push(H2('☀️  TODAY', C.A));
kids.push(checkTable([
  checkRow('Read Part 0 of this book', '3 minutes'),
  checkRow('Do HABIT 1 — run the BRIEFER helper once', '25 minutes. This is the big one.'),
  checkRow('Write one sentence: did it save me time?', 'Yes or no. That is all.'),
]));
kids.push(H2('📆  THIS WEEK', C.D));
kids.push(checkTable([
  checkRow('Do HABIT 2 — write ONE 90-day goal', 'A date, or it does not count'),
  checkRow('Do HABIT 3 — mark exactly one goal MOVING', 'Count them. The number is 1.'),
  checkRow('Do HABIT 7 on Friday — run STEWARD', 'Put it in your calendar now'),
  checkRow('Start the 14-day time baseline', 'Only you can do this one'),
]));
kids.push(H2('⏳  ONLY YOU CAN DO THESE — still waiting', C.C));
kids.push(checkTable([
  checkRow('Open the Cloudflare test link (30 seconds)', 'Checks whether your project files are visible on your public website'),
  checkRow('Send the GitHub Support letter', 'It is already written for you in agents/27. The history rewrite it describes is now DONE, so it is safe to send.'),
  checkRow('Ask your lawyer the four contract questions', 'This unlocks 3 of your locked helpers'),
  checkRow('Ask FIU what AI use is allowed for your doctorate', 'Highest-risk unanswered question you have'),
  checkRow('Find the seat-3 model ID in your console', '2 minutes. Unlocks NIGHTWATCH.'),
]));
kids.push(...notesBlock(6, '📝  MY BIG NOTES PAGE'));
kids.push(br());
kids.push(H2('📝  NOTES', C.navy));
kids.push(...notesBlock(18, ''));

// ══ BUILD ═════════════════════════════════════════════════════════════════
const doc = new Document({
  creator: 'FORGE LINK LLC', title: 'FORGE — Your AI Agent Handbook',
  description: 'Plain-English operator handbook for all 33 FORGE AI agents.',
  styles: { default: { document: { run: { font: 'Calibri', size: 22, color: C.ink } } } },
  sections: [{
    properties: { page: {
      size: { width: 12240, height: 15840 },
      margin: { top: 1150, right: 1440, bottom: 1150, left: 1440 },
    }},
    children: kids,
  }],
});
Packer.toBuffer(doc).then(b => {
  fs.writeFileSync(S + '/FORGE-AI-Agent-Handbook.docx', b);
  console.log('WROTE FORGE-AI-Agent-Handbook.docx  ' + b.length + ' bytes');
  console.log('agents documented: ' + n + '  |  live: ' + live + '  |  blocked: ' + blocked);
});
