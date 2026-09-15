const fs = require('fs');
const d = require('docx');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, PageBreak,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, PageOrientation,
  LevelFormat, convertInchesToTwip,
} = d;

const S = '/tmp/claude-0/-home-user-forge-talent-connections/f7340004-d5dc-5a8f-b52b-7cf5e677a454/scratchpad';
const AG = JSON.parse(fs.readFileSync(S + '/agents.json', 'utf8'));

// ── palette: one colour per outcome, used identically everywhere ──────────
const C = {
  navy: '1E3A5F', gold: 'C9A227', ink: '1A1A1A', grey: '5A5A5A',
  A: '15803D', Abg: 'DCFCE7',   // green  – time returned
  B: 'B91C1C', Bbg: 'FEE2E2',   // red    – nothing irreversible
  C: 'B45309', Cbg: 'FEF3C7',   // amber  – no stalls
  D: '1D4ED8', Dbg: 'DBEAFE',   // blue   – compounds
  panel: 'F1F5F9', line: 'CBD5E1', white: 'FFFFFF',
};
const OUT = {
  A: { emo: '⏱️', name: 'TIME BACK',       plain: 'You get hours of your life back.' },
  B: { emo: '🛡️', name: 'NOTHING BREAKS',  plain: 'Stops a mistake you can never undo.' },
  C: { emo: '🔔', name: 'NOTHING FORGOTTEN',plain: 'Tells you when something is stuck.' },
  D: { emo: '📈', name: 'GETS EASIER',     plain: 'Next time costs less than this time.' },
};
const W = 9360; // usable width, US Letter, 1.1" margins

const t = (text, o = {}) => new TextRun({ text, font: 'Calibri', size: o.size || 22,
  bold: o.bold, italics: o.italics, color: o.color || C.ink, highlight: o.hl });
const p = (runs, o = {}) => new Paragraph({
  children: Array.isArray(runs) ? runs : [runs],
  alignment: o.align, spacing: { before: o.before ?? 60, after: o.after ?? 60, line: 276 },
  indent: o.indent, border: o.border, shading: o.shade ? { type: ShadingType.CLEAR, fill: o.shade } : undefined,
  numbering: o.numbering, keepNext: o.keepNext, pageBreakBefore: o.pbb,
});
const txt = (s, o = {}) => p(t(s, o), o);
const gap = (n = 1) => Array.from({ length: n }, () => new Paragraph({ children: [t('')], spacing: { after: 40 } }));

const H1 = (emo, s) => new Paragraph({
  children: [t(`${emo}  ${s}`, { size: 40, bold: true, color: C.white })],
  shading: { type: ShadingType.CLEAR, fill: C.navy },
  spacing: { before: 260, after: 200 }, heading: HeadingLevel.HEADING_1,
  indent: { left: 120, right: 120 },
});
const H2 = (s, col = C.navy) => new Paragraph({
  children: [t(s, { size: 30, bold: true, color: col })],
  spacing: { before: 260, after: 110 }, heading: HeadingLevel.HEADING_2,
  border: { bottom: { style: BorderStyle.SINGLE, size: 10, color: col, space: 4 } },
});
const H3 = (s, col = C.navy) => new Paragraph({
  children: [t(s, { size: 25, bold: true, color: col })],
  spacing: { before: 190, after: 70 }, heading: HeadingLevel.HEADING_3,
});

const cell = (kids, o = {}) => new TableCell({
  children: Array.isArray(kids) ? kids : [kids],
  width: { size: o.w, type: WidthType.DXA },
  shading: o.shade ? { type: ShadingType.CLEAR, fill: o.shade } : undefined,
  margins: { top: 90, bottom: 90, left: 130, right: 130 },
  columnSpan: o.span, verticalAlign: 'center',
});
const table = (widths, rows) => new Table({
  columnWidths: widths, width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  rows,
  borders: {
    top:{style:BorderStyle.SINGLE,size:6,color:C.line}, bottom:{style:BorderStyle.SINGLE,size:6,color:C.line},
    left:{style:BorderStyle.SINGLE,size:6,color:C.line}, right:{style:BorderStyle.SINGLE,size:6,color:C.line},
    insideHorizontal:{style:BorderStyle.SINGLE,size:6,color:C.line},
    insideVertical:{style:BorderStyle.SINGLE,size:6,color:C.line},
  },
});

// A coloured callout box
const box = (emo, title, lines, col, bg) => [
  new Paragraph({
    children: [t(`${emo}  ${title}`, { bold: true, size: 24, color: col })],
    shading: { type: ShadingType.CLEAR, fill: bg }, spacing: { before: 180, after: 0 },
    indent: { left: 120, right: 120 },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: col, space: 6 } },
  }),
  ...lines.map((l, i) => new Paragraph({
    children: [t(l, { size: 21 })],
    shading: { type: ShadingType.CLEAR, fill: bg },
    spacing: { before: 40, after: i === lines.length - 1 ? 150 : 40 },
    indent: { left: 120, right: 120 },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: col, space: 6 } },
  })),
];

// Fillable check box row
const CHK = '☐';
const checkRow = (label, sub) => new TableRow({ children: [
  cell(txt(CHK, { size: 32, bold: true }), { w: 620 }),
  cell([txt(label, { bold: true, size: 22 }), ...(sub ? [txt(sub, { size: 19, color: C.grey, italics: true })] : [])], { w: 5340 }),
  cell(txt('', { size: 20 }), { w: 3400, shade: 'FFFDF2' }),
]});
const checkTable = (rows) => table([620, 5340, 3400], [
  new TableRow({ tableHeader: true, children: [
    cell(txt('✔', { bold: true, color: C.white, size: 22 }), { w: 620, shade: C.navy }),
    cell(txt('DO THIS', { bold: true, color: C.white, size: 22 }), { w: 5340, shade: C.navy }),
    cell(txt('MY NOTES (write here)', { bold: true, color: C.white, size: 22 }), { w: 3400, shade: C.navy }),
  ]}),
  ...rows,
]);

const notesBlock = (n = 5, title = '📝  MY NOTES') => [
  txt(title, { bold: true, size: 23, color: C.navy, before: 200 }),
  ...Array.from({ length: n }, () => new Paragraph({
    children: [t('')],
    spacing: { before: 150, after: 150 },
    border: { bottom: { style: BorderStyle.DOTTED, size: 8, color: C.line, space: 6 } },
  })),
];

// ── agent ordering ────────────────────────────────────────────────────────
const order = ['A', 'B', 'C', 'D'];
const byOutcome = (o) => AG.filter(a => a.outcome === o && a.kind === 'agent')
                          .sort((a, b) => a.name.localeCompare(b.name));
const nice = (s) => s.toUpperCase();
const live = AG.filter(a => a.live).length;
const blocked = AG.filter(a => a.blocked).length;

const agentBlock = (a, idx) => {
  const col = C[a.outcome], bg = C[a.outcome + 'bg'], o = OUT[a.outcome];
  const status = a.blocked ? '⛔ LOCKED — waiting on your lawyer or a missing setting'
               : a.live ? '✅ READY TO USE RIGHT NOW' : '⚪ built, not switched on';
  return [
    new Paragraph({
      children: [t(`${o.emo}  ${idx}.  ${nice(a.name)}`, { size: 28, bold: true, color: C.white })],
      shading: { type: ShadingType.CLEAR, fill: col }, spacing: { before: 260, after: 0 },
      indent: { left: 120, right: 120 }, keepNext: true, heading: HeadingLevel.HEADING_3,
    }),
    new Paragraph({
      children: [t(status, { size: 20, bold: true, color: col })],
      shading: { type: ShadingType.CLEAR, fill: bg }, spacing: { before: 0, after: 90 },
      indent: { left: 120, right: 120 },
    }),
    table([2100, 7260], [
      new TableRow({ children: [
        cell(txt('WHAT IT DOES', { bold: true, size: 19, color: col }), { w: 2100, shade: bg }),
        cell(txt(a.mandate || '—', { size: 21 }), { w: 7260 })]}),
      new TableRow({ children: [
        cell(txt('ITS ONE JOB', { bold: true, size: 19, color: col }), { w: 2100, shade: bg }),
        cell(txt(a.goal, { size: 21, italics: true }), { w: 7260 })]}),
      new TableRow({ children: [
        cell(txt('HOW YOU WIN', { bold: true, size: 19, color: col }), { w: 2100, shade: bg }),
        cell(txt(`${o.emo} ${o.name} — ${o.plain}`, { size: 21 }), { w: 7260 })]}),
      new TableRow({ children: [
        cell(txt('SAY THIS', { bold: true, size: 19, color: col }), { w: 2100, shade: bg }),
        cell(txt(`"Use the ${nice(a.name)} agent."`, { size: 21, bold: true, color: C.navy }), { w: 7260 })]}),
      new TableRow({ children: [
        cell(txt('☐ TRIED IT', { bold: true, size: 19, color: col }), { w: 2100, shade: 'FFFDF2' }),
        cell(txt('Notes: ', { size: 19, color: C.grey }), { w: 7260, shade: 'FFFDF2' })]}),
    ]),
  ];
};

// ═══════════════════════════════════════════════════════════════════════════
const kids = [];

// ── COVER ──────────────────────────────────────────────────────────────────
kids.push(
  ...gap(3),
  txt('🔥  FORGE  🔥', { size: 60, bold: true, color: C.gold, align: AlignmentType.CENTER }),
  txt('YOUR AI AGENT HANDBOOK', { size: 56, bold: true, color: C.navy, align: AlignmentType.CENTER }),
  ...gap(1),
  txt('The Plain-English Guide to All 33 Helpers', { size: 30, color: C.grey, align: AlignmentType.CENTER, italics: true }),
  ...gap(2),
  table([3120, 3120, 3120], [new TableRow({ children: [
    cell([txt('33', { size: 56, bold: true, color: C.A, align: AlignmentType.CENTER }),
          txt('HELPERS READY', { size: 18, bold: true, align: AlignmentType.CENTER, color: C.grey })], { w: 3120, shade: C.Abg }),
    cell([txt('4', { size: 56, bold: true, color: C.B, align: AlignmentType.CENTER }),
          txt('SAFETY GATES', { size: 18, bold: true, align: AlignmentType.CENTER, color: C.grey })], { w: 3120, shade: C.Bbg }),
    cell([txt('1', { size: 56, bold: true, color: C.D, align: AlignmentType.CENTER }),
          txt('RULE: ONE AT A TIME', { size: 18, bold: true, align: AlignmentType.CENTER, color: C.grey })], { w: 3120, shade: C.Dbg }),
  ]})]),
  ...gap(2),
  ...box('👋', 'READ THIS FIRST — 30 seconds', [
    'This book explains every AI helper you now own, in simple words.',
    'You do NOT need to understand computers to use them.',
    'You cannot break anything. Every helper is locked so it cannot send, buy, delete, or publish.',
    'If you only do ONE thing: go to Page 1 of Part 2 and follow Habit 1.',
  ], C.navy, C.panel),
  ...gap(1),
  txt('Andrew Francisco  ·  FORGE LINK LLC  ·  Built 15 September 2026',
      { size: 20, color: C.grey, align: AlignmentType.CENTER }),
  txt('Version 13  ·  Every number in this book was produced by a script, not typed by hand.',
      { size: 18, color: C.grey, align: AlignmentType.CENTER, italics: true }),
);

// ── PART 0 — HOW TO READ ───────────────────────────────────────────────────
kids.push(new Paragraph({ children: [new PageBreak()] }));
kids.push(H1('🗺️', 'PART 0 — HOW TO READ THIS BOOK'));
kids.push(txt('Everything in this book uses the same four colours. Learn them once and the whole book makes sense.', { size: 23 }));
kids.push(table([900, 2400, 6060], [
  new TableRow({ tableHeader: true, children: [
    cell(txt('', { size: 20 }), { w: 900, shade: C.navy }),
    cell(txt('COLOUR MEANS', { bold: true, color: C.white, size: 21 }), { w: 2400, shade: C.navy }),
    cell(txt('IN PLAIN WORDS', { bold: true, color: C.white, size: 21 }), { w: 6060, shade: C.navy })]}),
  ...order.map(k => new TableRow({ children: [
    cell(txt(OUT[k].emo, { size: 34, align: AlignmentType.CENTER }), { w: 900, shade: C[k + 'bg'] }),
    cell(txt(OUT[k].name, { bold: true, size: 22, color: C[k] }), { w: 2400, shade: C[k + 'bg'] }),
    cell(txt(OUT[k].plain, { size: 21 }), { w: 6060 })]})),
]));
kids.push(...gap(1));
kids.push(H2('The three symbols you will see'));
kids.push(table([1300, 8060], [
  new TableRow({ children: [cell(txt('✅', { size: 30, align: AlignmentType.CENTER }), { w: 1300, shade: C.Abg }),
    cell(txt('READY. You can use this helper today. Nothing is stopping you.', { size: 22 }), { w: 8060 })]}),
  new TableRow({ children: [cell(txt('⛔', { size: 30, align: AlignmentType.CENTER }), { w: 1300, shade: C.Bbg }),
    cell(txt('LOCKED. It will refuse and tell you why. That is on purpose — it is waiting on your lawyer, or on one missing setting. It is NOT broken.', { size: 22 }), { w: 8060 })]}),
  new TableRow({ children: [cell(txt('☐', { size: 30, align: AlignmentType.CENTER }), { w: 1300, shade: 'FFFDF2' }),
    cell(txt('A BOX FOR YOU. Tick it with a pen, or click it in the PDF version. Nobody else fills these in.', { size: 22 }), { w: 8060 })]}),
]));
kids.push(...box('🧒', 'THE PROMISE — why a child could not break this', [
  'Every helper had its powers taken away before it was switched on.',
  'The email helper has NO SEND BUTTON. Not hidden — removed. It literally cannot send.',
  'No helper can buy anything, delete anything, publish anything, or sign anything.',
  'The worst a helper can do is write you a note that is wrong. You read it, and you decide.',
  'A computer check runs every time anything changes. If a helper ever got a power it should not have, the check stops it.',
], C.A, C.Abg));
kids.push(...notesBlock(3, '📝  WHAT I WANT THESE HELPERS TO DO FOR ME'));

// ── PART 1 — WHAT WAS BUILT ────────────────────────────────────────────────
kids.push(new Paragraph({ children: [new PageBreak()] }));
kids.push(H1('🏗️', 'PART 1 — WHAT WAS BUILT FOR YOU'));
kids.push(txt('In one sentence: you now own 33 small AI helpers, each with exactly one job, each unable to do anything dangerous.', { size: 24, bold: true, color: C.navy }));
kids.push(H2('The five things that were built'));
kids.push(table([620, 3300, 5440], [
  new TableRow({ tableHeader: true, children: [
    cell(txt('#', { bold: true, color: C.white, size: 20 }), { w: 620, shade: C.navy }),
    cell(txt('THE THING', { bold: true, color: C.white, size: 21 }), { w: 3300, shade: C.navy }),
    cell(txt('WHAT IT MEANS FOR YOU', { bold: true, color: C.white, size: 21 }), { w: 5440, shade: C.navy })]}),
  ...[
    ['1', '33 AI helpers, switched on', 'Each does ONE job. You call them by name in plain English.'],
    ['2', '4 automatic safety gates', 'Computer checks that block a mistake before it can happen. They have each already caught real errors.'],
    ['3', 'A goal ladder', 'Every helper is tied to your big goal. If a helper serves nothing, the computer refuses to keep it.'],
    ['4', 'A written safety list', 'A list of things NO helper may ever do — send, buy, publish, delete, sign.'],
    ['5', 'A private-data cleaner', 'Someone’s phone numbers were published by mistake. They have now been scrubbed out of the project history and the scrub was double-checked.'],
  ].map(r => new TableRow({ children: [
    cell(txt(r[0], { bold: true, size: 22, align: AlignmentType.CENTER, color: C.gold }), { w: 620, shade: C.panel }),
    cell(txt(r[1], { bold: true, size: 21 }), { w: 3300 }),
    cell(txt(r[2], { size: 21 }), { w: 5440 })]})),
]));
kids.push(H2('The safety gates, and what each one already caught'));
kids.push(txt('A safety gate that has never said "no" has never been tested. All four of these have said no.', { size: 21, italics: true, color: C.grey }));
kids.push(table([2700, 3330, 3330], [
  new TableRow({ tableHeader: true, children: [
    cell(txt('GATE', { bold: true, color: C.white, size: 20 }), { w: 2700, shade: C.B }),
    cell(txt('WHAT IT BLOCKS', { bold: true, color: C.white, size: 20 }), { w: 3330, shade: C.B }),
    cell(txt('WHAT IT REALLY CAUGHT', { bold: true, color: C.white, size: 20 }), { w: 3330, shade: C.B })]}),
  ...[
    ['🔒 Private-data guard', 'Phone numbers, account numbers, passwords, secret keys', 'It has blocked its own author more than once'],
    ['🎯 Goal guard', 'A helper that serves no goal of yours', 'Caught 3 helpers with goals nobody could measure'],
    ['🔗 Match guard', 'A helper whose powers stopped matching its written contract', 'Caught its own first mistake on its first run'],
    ['🧪 Loop guard', 'A robot task that could cheat its own scoring', 'Refuses 2 of your 5 planned loops today'],
  ].map(r => new TableRow({ children: [
    cell(txt(r[0], { bold: true, size: 20 }), { w: 2700, shade: C.Bbg }),
    cell(txt(r[1], { size: 20 }), { w: 3330 }),
    cell(txt(r[2], { size: 20, italics: true }), { w: 3330 })]})),
]));
kids.push(...box('🔍', 'THE MOST IMPORTANT THING THAT HAPPENED', [
  'One of your helpers — the EVIDENCE-AUDITOR — was pointed at MY OWN work.',
  'It found 19 problems. One was a number I had got wrong by more than double, in the direction that made my own argument look better.',
  'It also caught me saying a safety fix was "proven" when the real test had never been run. That test has now been run, and it passed.',
  'THAT is what these helpers are for. Every one of them was fixed before you ever saw it.',
], C.D, C.Dbg));
kids.push(...notesBlock(3, '📝  QUESTIONS I HAVE ABOUT WHAT WAS BUILT'));

fs.writeFileSync(S + '/part1.flag', 'ok');
module.exports = { kids, AG, C, OUT, order, byOutcome, nice, live, blocked,
  H1, H2, H3, txt, p, t, table, cell, box, gap, notesBlock, checkTable, checkRow,
  agentBlock, PageBreak, Paragraph, TextRun, Document, Packer, AlignmentType,
  WidthType, ShadingType, BorderStyle, TableRow, TableCell, HeadingLevel, W, CHK };
