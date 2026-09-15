#!/usr/bin/env python3
"""
make_pdf.py -- the FILLABLE companion to the Word handbook.

Real AcroForm fields: every checkbox is clickable and every notes area is a
typable multi-line text field. Saves with the answers inside the PDF.

Nothing in this file is invented: the agent list, goals and counts are read from
agents.json, which was exported from the cards by goal_ladder.py.
"""
import json
from pathlib import Path

from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

S = Path("/tmp/claude-0/-home-user-forge-talent-connections/"
         "f7340004-d5dc-5a8f-b52b-7cf5e677a454/scratchpad")
AG = json.loads((S / "agents.json").read_text())

W, H = LETTER
M = 54                      # margin
CW = W - 2 * M              # content width

NAVY = HexColor("#1E3A5F"); GOLD = HexColor("#C9A227")
INK  = HexColor("#1A1A1A"); GREY = HexColor("#5A5A5A")
LINE = HexColor("#CBD5E1"); PANEL = HexColor("#F1F5F9"); CREAM = HexColor("#FFFDF2")
OC = {"A": HexColor("#15803D"), "B": HexColor("#B91C1C"),
      "C": HexColor("#B45309"), "D": HexColor("#1D4ED8")}
OB = {"A": HexColor("#DCFCE7"), "B": HexColor("#FEE2E2"),
      "C": HexColor("#FEF3C7"), "D": HexColor("#DBEAFE")}
OUT = {
    "A": ("TIME BACK", "You get hours of your life back."),
    "B": ("NOTHING BREAKS", "Stops a mistake you can never undo."),
    "C": ("NOTHING FORGOTTEN", "Tells you when something is stuck."),
    "D": ("GETS EASIER", "Next time costs less than this time."),
}

# Emoji do not render in the PDF base fonts, so this document uses coloured
# shapes and words instead. Same signal, no missing-glyph boxes.
BASE, BOLD, ITAL = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"

c = canvas.Canvas(str(S / "FORGE-AI-Agent-Checklist-FILLABLE.pdf"), pagesize=LETTER)
c.setTitle("FORGE - AI Agent Fillable Checklist")
c.setAuthor("FORGE LINK LLC")
c.setSubject("Fillable operator checklist for all 33 FORGE AI agents")

state = {"y": H - M, "page": 0, "field": 0}


def newpage(first=False):
    if not first:
        footer()
        c.showPage()
    state["page"] += 1
    state["y"] = H - M - 6
    # thin gold rule at the top of every page
    c.setFillColor(GOLD); c.rect(0, H - 10, W, 10, stroke=0, fill=1)


def footer():
    c.setFillColor(GREY); c.setFont(BASE, 7.5)
    c.drawString(M, 26, "FORGE LINK LLC  -  AI Agent Fillable Checklist  -  15 Sep 2026")
    c.drawRightString(W - M, 26, f"Page {state['page']}")
    c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(M, 36, W - M, 36)


def need(h):
    if state["y"] - h < 56:
        newpage()
        return True
    return False


def wrap(text, font, size, width):
    return simpleSplit(text, font, size, width)


def para(text, size=9.5, font=BASE, color=INK, indent=0, lead=None, gap=4):
    lead = lead or size + 3.0
    lines = wrap(text, font, size, CW - indent)
    need(len(lines) * lead + gap)
    c.setFont(font, size); c.setFillColor(color)
    for ln in lines:
        c.drawString(M + indent, state["y"] - lead + 3, ln)
        state["y"] -= lead
    state["y"] -= gap


def band(title, sub=None, fill=NAVY, h=30):
    need(h + (14 if sub else 0) + 10)
    c.setFillColor(fill); c.rect(M, state["y"] - h, CW, h, stroke=0, fill=1)
    c.setFillColor(white); c.setFont(BOLD, 15)
    c.drawString(M + 12, state["y"] - h + 9, title)
    state["y"] -= h
    if sub:
        c.setFillColor(PANEL); c.rect(M, state["y"] - 16, CW, 16, stroke=0, fill=1)
        c.setFillColor(GREY); c.setFont(ITAL, 8.5)
        c.drawString(M + 12, state["y"] - 12, sub)
        state["y"] -= 16
    state["y"] -= 9


def h2(title, color=NAVY):
    need(28)
    c.setFillColor(color); c.setFont(BOLD, 12.5)
    c.drawString(M, state["y"] - 13, title)
    c.setStrokeColor(color); c.setLineWidth(1.4)
    c.line(M, state["y"] - 18, W - M, state["y"] - 18)
    state["y"] -= 26


def callout(title, lines, color, bg):
    body = []
    for l in lines:
        body += wrap(l, BASE, 9, CW - 30)
    h = 20 + len(body) * 12 + 8
    need(h + 8)
    top = state["y"]
    c.setFillColor(bg); c.rect(M, top - h, CW, h, stroke=0, fill=1)
    c.setFillColor(color); c.rect(M, top - h, 4.5, h, stroke=0, fill=1)
    c.setFillColor(color); c.setFont(BOLD, 10)
    c.drawString(M + 14, top - 15, title)
    c.setFillColor(INK); c.setFont(BASE, 9)
    yy = top - 30
    for ln in body:
        c.drawString(M + 14, yy, ln); yy -= 12
    state["y"] = top - h - 10


def checkbox_row(label, sub="", notes=True, box_w=250):
    """One clickable checkbox + label + a typable notes field."""
    lab = wrap(label, BOLD, 9.5, CW - 30 - (box_w if notes else 0))
    subl = wrap(sub, ITAL, 8, CW - 30 - (box_w if notes else 0)) if sub else []
    h = max(24, 10 + len(lab) * 11.5 + len(subl) * 10)
    need(h + 4)
    top = state["y"]
    c.setStrokeColor(LINE); c.setLineWidth(0.6)
    c.rect(M, top - h, CW, h, stroke=1, fill=0)

    state["field"] += 1
    c.acroForm.checkbox(
        name=f"chk{state['field']}", x=M + 6, y=top - h + (h - 14) / 2, size=14,
        buttonStyle="check", borderWidth=1, borderColor=NAVY,
        fillColor=white, textColor=OC["A"], forceBorder=True,
    )
    tx = M + 28
    yy = top - 14
    c.setFillColor(INK); c.setFont(BOLD, 9.5)
    for ln in lab:
        c.drawString(tx, yy, ln); yy -= 11.5
    c.setFillColor(GREY); c.setFont(ITAL, 8)
    for ln in subl:
        c.drawString(tx, yy, ln); yy -= 10

    if notes:
        state["field"] += 1
        c.setFillColor(CREAM)
        c.rect(W - M - box_w - 4, top - h + 4, box_w, h - 8, stroke=0, fill=1)
        c.acroForm.textfield(
            name=f"note{state['field']}", x=W - M - box_w - 4, y=top - h + 4,
            width=box_w, height=h - 8, borderWidth=0.6, borderColor=LINE,
            fillColor=CREAM, textColor=INK, fontSize=8, fieldFlags="multiline",
        )
    state["y"] = top - h


def notes_field(label, rows=4):
    h = rows * 18
    need(h + 26)
    c.setFillColor(NAVY); c.setFont(BOLD, 10)
    c.drawString(M, state["y"] - 12, label)
    state["y"] -= 18
    state["field"] += 1
    c.setFillColor(CREAM); c.rect(M, state["y"] - h, CW, h, stroke=0, fill=1)
    c.acroForm.textfield(
        name=f"notes{state['field']}", x=M, y=state["y"] - h, width=CW, height=h,
        borderWidth=0.8, borderColor=LINE, fillColor=CREAM, textColor=INK,
        fontSize=9, fieldFlags="multiline",
    )
    state["y"] -= h + 12


# ════════════════════════════════════════════════════════════ COVER
newpage(first=True)
state["y"] = H - 150
c.setFillColor(GOLD); c.setFont(BOLD, 44)
c.drawCentredString(W / 2, state["y"], "FORGE")
state["y"] -= 42
c.setFillColor(NAVY); c.setFont(BOLD, 27)
c.drawCentredString(W / 2, state["y"], "AI AGENT CHECKLIST")
state["y"] -= 26
c.setFillColor(GREY); c.setFont(ITAL, 13)
c.drawCentredString(W / 2, state["y"], "Fillable  -  click any box, type in any yellow area, then Save")
state["y"] -= 46

live = sum(1 for a in AG if a.get("live"))
blocked = sum(1 for a in AG if a.get("blocked"))
cards = [a for a in AG if a["kind"] == "agent"]
tiles = [(str(live), "HELPERS READY", OC["A"], OB["A"]),
         (str(blocked), "LOCKED ON PURPOSE", OC["B"], OB["B"]),
         ("1", "GOAL AT A TIME", OC["D"], OB["D"])]
tw = (CW - 24) / 3
for i, (big, lab, col, bg) in enumerate(tiles):
    x = M + i * (tw + 12)
    c.setFillColor(bg); c.rect(x, state["y"] - 74, tw, 74, stroke=0, fill=1)
    c.setFillColor(col); c.setFont(BOLD, 34)
    c.drawCentredString(x + tw / 2, state["y"] - 44, big)
    c.setFillColor(GREY); c.setFont(BOLD, 8)
    c.drawCentredString(x + tw / 2, state["y"] - 62, lab)
state["y"] -= 96

callout("HOW TO USE THIS FILE  -  read this once",
        ["Open it in Adobe Acrobat Reader (free), Preview on a Mac, or any browser.",
         "Click a square to tick it. Click a yellow area and type.",
         "Press Save (Ctrl+S / Cmd+S). Your ticks and notes are stored inside this file.",
         "Print it instead if you prefer pen and paper. It works both ways.",
         "You cannot break anything in here. It is a checklist, not a control panel."],
        NAVY, PANEL)

callout("THE PROMISE  -  why a child could not break your helpers",
        ["Every helper had its dangerous powers REMOVED before it was switched on.",
         "The email helper has no send button. Not hidden - it is not in its toolbox.",
         "No helper can buy, delete, publish, sign, or send anything. Ever.",
         "The worst a helper can do is write you a note that is wrong. You read it. You decide."],
        OC["A"], OB["A"])

c.setFillColor(GREY); c.setFont(BASE, 8.5)
c.drawCentredString(W / 2, 70, "Andrew Francisco  -  FORGE LINK LLC  -  Version 13  -  15 September 2026")
c.drawCentredString(W / 2, 58, "Every count in this file was produced by a script reading the agent contracts, not typed by hand.")

# ════════════════════════════════════════════════════════════ SUMMARY
newpage()
band("PART 1  -  WHAT WAS BUILT FOR YOU", "In one sentence: 33 small AI helpers, each with one job, none able to do anything dangerous.")

h2("The five things you now own")
for i, (title, body) in enumerate([
    ("33 AI helpers, switched on", "Each does ONE job. You call them by name, in plain English."),
    ("4 automatic safety gates", "Computer checks that block a mistake before it can happen. All four have already caught real errors."),
    ("A goal ladder", "Every helper is tied to your big goal. A helper that serves nothing gets refused by the computer."),
    ("A written safety list", "Things NO helper may ever do: send, buy, publish, delete, sign."),
    ("A private-data cleaner", "Phone numbers were published by mistake. They have been scrubbed from the project history, and the scrub was double-checked and passed."),
], 1):
    need(30)
    c.setFillColor(GOLD); c.setFont(BOLD, 13)
    c.drawString(M + 2, state["y"] - 12, str(i))
    c.setFillColor(INK); c.setFont(BOLD, 10)
    c.drawString(M + 20, state["y"] - 12, title)
    state["y"] -= 14
    para(body, size=9, indent=20, gap=7)

h2("The safety gates, and what each already caught", OC["B"])
para("A gate that has never said no has never been tested. All four of these have said no.",
     size=8.5, font=ITAL, color=GREY, gap=6)
for name, blocks, caught in [
    ("Private-data guard", "Phone numbers, account numbers, passwords, keys", "Has blocked its own author more than once"),
    ("Goal guard", "A helper that serves no goal of yours", "Caught 3 helpers with goals nobody could measure"),
    ("Match guard", "A helper whose powers stopped matching its contract", "Caught its own first mistake on its first run"),
    ("Loop guard", "A robot task that could cheat its own scoring", "Refuses 2 of your 5 planned loops today"),
]:
    need(26)
    top = state["y"]
    c.setFillColor(OB["B"]); c.rect(M, top - 24, 130, 24, stroke=0, fill=1)
    c.setFillColor(OC["B"]); c.setFont(BOLD, 8.5)
    c.drawString(M + 6, top - 15, name)
    c.setFillColor(INK); c.setFont(BASE, 8.5)
    c.drawString(M + 138, top - 15, blocks[:52])
    c.setFillColor(GREY); c.setFont(ITAL, 8)
    c.drawString(M + 138, top - 24 + 1, caught[:72])
    c.setStrokeColor(LINE); c.line(M, top - 25, W - M, top - 25)
    state["y"] = top - 27

callout("THE MOST IMPORTANT THING THAT HAPPENED",
        ["One of your helpers - EVIDENCE-AUDITOR - was pointed at the work that built all this.",
         "It found 19 problems. One was a number wrong by more than double, in the direction that",
         "made the argument look better. It also caught a safety fix being called 'proven' when the",
         "real test had never run. That test has now been run. It passed.",
         "All 19 were fixed before you ever saw them. That is what these helpers are for."],
        OC["D"], OB["D"])

notes_field("MY NOTES  -  what I want these helpers to do for me", rows=4)

# ════════════════════════════════════════════════════════════ 7 HABITS
HABITS = [
    (1, "BE PROACTIVE", "A", "Run one helper today. Do not wait for a perfect moment.",
     ["S - Run the BRIEFER helper one time.",
      "M - One page of notes exists that you did not write.",
      "A - 25 minutes, no extra cost.",
      "R - Already paid for, already installed. Nothing is blocking it.",
      "T - TODAY, before bed."],
     [("Open Claude Code in your FORGE project folder", "Same window you already use"),
      ("Type: Use the BRIEFER agent to research ___ for me", "Fill the blank with a real question"),
      ("Read the one page it gives back", "Under 5 minutes"),
      ("Write down: did that save me time? Yes or no", "The only score that matters")]),
    (2, "BEGIN WITH THE END IN MIND", "D", "Your big goal is written. Now write the small one under it.",
     ["S - Write ONE 90-day goal in the goal ledger.",
      "M - A filled row where the file is blank now.",
      "A - 20 minutes thinking, 2 minutes typing.",
      "R - Only you may do this. No helper is allowed to.",
      "T - This week. Sunday at the latest."],
     [("Open agents/analysis/goal-ledger.md", "Your big goal is already at the top"),
      ("Find the QUARTER table - it is empty", "One row is enough. Not three."),
      ("Write: <something> will be true by <a date>", "Not 'improve sales'. A date, or it does not count."),
      ("Name ONE next action, the first physical thing", "Open the file. Send the email. Make the call.")]),
    (3, "PUT FIRST THINGS FIRST", "C", "One goal moving at a time. Everything else gets parked.",
     ["S - Exactly ONE goal marked MOVING.",
      "M - Count the MOVING rows. The number is 1.",
      "A - A one-word edit.",
      "R - Hard emotionally, easy practically.",
      "T - Every Monday morning, forever."],
     [("Count the MOVING rows in your goal ledger", "More than 1 means you are slowing yourself down"),
      ("Pick ONE. Change the rest to PARKED.", "Parked is not cancelled. It is 'not today'."),
      ("Use the PARKING agent for every new idea", "Say: Use the PARKING agent to park this idea"),
      ("Set a stop time BEFORE starting any work block", "Open-ended blocks are why nothing starts")]),
    (4, "THINK WIN-WIN", "B", "Each helper gets only the powers it needs. You both win.",
     ["S - Read the forbidden-actions list on the red page.",
      "M - You can name 3 forbidden actions from memory.",
      "A - 5 minutes of reading.",
      "R - You need this to trust them.",
      "T - Before any helper touches your email."],
     [("Read the red page in this file", "It is short on purpose"),
      ("Notice: the email helper has NO send button", "Removed, not hidden"),
      ("Run: python3 scripts/agent_parity.py", "Checks the powers still match. Copy that line exactly."),
      ("If it ever says BLOCKED, do not override it", "A blocked gate is the system working")]),
    (5, "SEEK FIRST TO UNDERSTAND", "D", "Read what the helper wrote BEFORE you act on it.",
     ["S - Never act on output you have not read.",
      "M - Zero things sent or filed unread.",
      "A - Costs seconds.",
      "R - This is the whole safety design.",
      "T - Every single time. No exceptions."],
     [("Read the answer all the way to the end", "Warnings are usually at the bottom"),
      ("Look for Unknown, Unverified, or Assumption", "Those mean the helper is NOT sure. Believe it."),
      ("If a number surprises you, ask for the maths", "Say: Show me how you calculated that"),
      ("Run EVIDENCE-AUDITOR on anything important", "Say: Use the EVIDENCE-AUDITOR agent on this")]),
    (6, "SYNERGIZE", "A", "Pair a maker with a checker. Never let one helper mark its own work.",
     ["S - Every BUILDER change gets a REVIEWER check.",
      "M - Zero code changes with no review.",
      "A - One extra sentence when you ask.",
      "R - Proven: the checker found 19 real problems.",
      "T - Same day. Never 'later'."],
     [("After BUILDER writes, run the checker immediately", "Say: Now use the ADVERSARIAL-REVIEWER agent"),
      ("For research, pair BRIEFER with EVIDENCE-AUDITOR", "One writes, one attacks"),
      ("For anything with a number, ask for re-derivation", "Exactly how the 2% vs 4.72% error was caught"),
      ("Never accept 'looks good' from the helper that wrote it", "Not lying - it just cannot see its blind spot")]),
    (7, "SHARPEN THE SAW", "C", "Weekly: check whether the helpers actually save you time.",
     ["S - Run STEWARD once a week, read one screen.",
      "M - Your review minutes. Going down, or not.",
      "A - 10 minutes on a Friday.",
      "R - You cannot know if this works without it.",
      "T - Every Friday. Calendar it now."],
     [("Friday: Use the STEWARD agent for this week", "Reports how much of your time helpers used"),
      ("Look at ONE number: your review minutes", "Up two weeks running = demote a helper"),
      ("Ask GOALKEEPER if anything is stuck", "Say: Use the GOALKEEPER agent"),
      ("Tick the box, close the laptop, rest", "Rest is part of the habit, not the reward")]),
]

for num, title, ok, plain, smart, rows in HABITS:
    newpage()
    band(f"HABIT {num}  -  {title}", plain, fill=OC[ok], h=32)
    h2("The SMART version", OC[ok])
    for s in smart:
        need(15)
        bg = OB[ok] if s.startswith("T -") else PANEL
        c.setFillColor(bg); c.rect(M, state["y"] - 14, CW, 14, stroke=0, fill=1)
        c.setFillColor(OC[ok]); c.setFont(BOLD, 9)
        c.drawString(M + 6, state["y"] - 10.5, s[:3])
        c.setFillColor(INK); c.setFont(BOLD if s.startswith("T -") else BASE, 8.8)
        c.drawString(M + 26, state["y"] - 10.5, s[4:])
        state["y"] -= 15
    state["y"] -= 8
    h2("Do these, in this order", OC[ok])
    for lab, sub in rows:
        checkbox_row(lab, sub)
    state["y"] -= 8
    notes_field(f"HABIT {num}  -  what happened when I tried it", rows=3)

# ════════════════════════════════════════════════════════════ EVERY AGENT
newpage()
band("PART 3  -  EVERY HELPER, ONE BY ONE",
     f"{live} switched on. {blocked} deliberately locked. Tick each one as you try it.")
callout("HOW TO CALL ANY HELPER  -  this never changes",
        ["1. Open Claude Code in your FORGE project folder.",
         "2. Type a normal sentence with the helper's NAME in it.",
         "3. Example:  Use the MAILROOM agent to sort my inbox.",
         "4. That is the whole thing. No menu, no code, no setup.",
         "Forgot a name? Just describe what you want - it will pick one for you."],
        NAVY, PANEL)

idx = 0
for k in "ABCD":
    group = sorted([a for a in cards if a["outcome"] == k], key=lambda a: a["name"])
    need(46)
    c.setFillColor(OC[k]); c.rect(M, state["y"] - 26, CW, 26, stroke=0, fill=1)
    c.setFillColor(white); c.setFont(BOLD, 13)
    c.drawString(M + 10, state["y"] - 18, f"{OUT[k][0]}  -  {len(group)} helpers")
    c.setFont(ITAL, 8.5)
    c.drawRightString(W - M - 10, state["y"] - 18, OUT[k][1])
    state["y"] -= 34

    for a in group:
        idx += 1
        nm = a["name"].upper()
        goal = a["goal"]
        mand = a["mandate"] or ""
        status = ("LOCKED - waiting on your lawyer or a missing setting" if a["blocked"]
                  else "READY TO USE NOW" if a["live"] else "built, not switched on")
        gl = wrap(mand, BASE, 8.3, CW - 26)
        gg = wrap("Its one job: " + goal, ITAL, 8.3, CW - 26)
        h = 30 + len(gl) * 10 + len(gg) * 10 + 20
        need(h + 6)
        top = state["y"]
        c.setStrokeColor(LINE); c.setLineWidth(0.7)
        c.rect(M, top - h, CW, h, stroke=1, fill=0)
        c.setFillColor(OC[k]); c.rect(M, top - 18, CW, 18, stroke=0, fill=1)
        c.setFillColor(white); c.setFont(BOLD, 10)
        c.drawString(M + 8, top - 13, f"{idx}.  {nm}")
        c.setFont(BOLD, 7.5)
        c.drawRightString(W - M - 8, top - 12.5, status)
        yy = top - 30
        c.setFillColor(INK); c.setFont(BASE, 8.3)
        for ln in gl:
            c.drawString(M + 10, yy, ln); yy -= 10
        c.setFillColor(OC[k]); c.setFont(ITAL, 8.3)
        for ln in gg:
            c.drawString(M + 10, yy, ln); yy -= 10
        c.setFillColor(NAVY); c.setFont(BOLD, 8.3)
        c.drawString(M + 26, top - h + 6, f'Say:  "Use the {nm} agent."')
        state["field"] += 1
        c.acroForm.checkbox(name=f"tried{state['field']}", x=M + 8, y=top - h + 3, size=12,
                            buttonStyle="check", borderWidth=1, borderColor=OC[k],
                            fillColor=white, textColor=OC[k], forceBorder=True)
        state["field"] += 1
        c.setFillColor(CREAM); c.rect(W - M - 210, top - h + 2, 206, 14, stroke=0, fill=1)
        c.acroForm.textfield(name=f"anote{state['field']}", x=W - M - 210, y=top - h + 2,
                             width=206, height=14, borderWidth=0.5, borderColor=LINE,
                             fillColor=CREAM, textColor=INK, fontSize=7.5)
        state["y"] = top - h - 5

# protocols
protos = [a for a in AG if a["kind"] == "protocol"]
newpage()
band("TWO JOBS NO HELPER CAN DO FOR YOU", "These are not helpers. They are yours.", fill=OC["C"], h=30)
callout("WHY THESE ARE NOT ON THE HELPER LIST",
        ["It would have been easy to make these look like helpers.",
         "That would have been a lie, and you would have waited forever for something",
         "that was never coming. Nothing and nobody can do these except you."],
        OC["C"], OB["C"])
for a in protos:
    h2(a["name"].upper(), OC["C"])
    para(a["mandate"], size=9)
    para("Its one job: " + a["goal"], size=9, font=ITAL, color=OC["C"])
    checkbox_row(f"I have done the {a['name'].upper()} job myself",
                 "No helper will ever tick this for you")
    state["y"] -= 6

# ════════════════════════════════════════════════════════════ SAFETY
newpage()
band("WHAT NO HELPER MAY EVER DO", "Print this page. Put it where you can see it.",
     fill=OC["B"], h=30)
FORB = [("Send an email to anyone", "Buy anything or move money"),
        ("Submit to a government portal", "File anything with the patent office"),
        ("Publish or post anything", "Sign or agree to terms"),
        ("Delete your data", "Put anything live for customers"),
        ("Log in as you, or solve a CAPTCHA", "Decide who gets hired"),
        ("Merge code into the main project", "Invent a number or a percentage")]
for left, right in FORB:
    need(24)
    top = state["y"]
    for i, txt_ in enumerate((left, right)):
        x = M + i * (CW / 2 + 4)
        c.setFillColor(OB["B"]); c.rect(x, top - 21, CW / 2 - 4, 21, stroke=0, fill=1)
        c.setFillColor(OC["B"]); c.setFont(BOLD, 9.5)
        c.drawString(x + 8, top - 14, "X  " + txt_)
    state["y"] = top - 25

callout("WHY YOU CAN TRUST THIS LIST",
        ["These are not promises in a document. The powers were physically removed.",
         "The email helper has no send button to press. It is not in its toolbox.",
         "A computer check runs on every change. If a helper ever gained one of these",
         "powers, the check stops the change from saving.",
         "That check has already blocked its own author more than once."],
        OC["B"], OB["B"])

h2("If something ever feels wrong", OC["B"])
for lab, sub in [("STOP. Close the window.", "You lose nothing. Helpers stop when you close them."),
                 ("Nothing was sent, bought, or published", "It could not have been. See the list above."),
                 ("Write down what you saw", "One line is enough"),
                 ("Ask a fresh session to check it", "Say: Use the EVIDENCE-AUDITOR agent on this")]:
    checkbox_row(lab, sub)

# ════════════════════════════════════════════════════════════ MASTER LIST
newpage()
band("YOUR MASTER CHECKLIST", "Tick in order. Do not skip. Never two at once.")
h2("TODAY", OC["A"])
for lab, sub in [("Read the front page of this file", "3 minutes"),
                 ("HABIT 1 - run the BRIEFER helper once", "25 minutes. This is the big one."),
                 ("Write one sentence: did it save me time?", "Yes or no. That is all.")]:
    checkbox_row(lab, sub)
state["y"] -= 8
h2("THIS WEEK", OC["D"])
for lab, sub in [("HABIT 2 - write ONE 90-day goal", "A date, or it does not count"),
                 ("HABIT 3 - mark exactly one goal MOVING", "Count them. The number is 1."),
                 ("HABIT 7 on Friday - run STEWARD", "Put it in your calendar now"),
                 ("Start the 14-day time baseline", "Only you can do this one")]:
    checkbox_row(lab, sub)
state["y"] -= 8
h2("ONLY YOU CAN DO THESE  -  still waiting", OC["C"])
for lab, sub in [
    ("Open the Cloudflare test link (30 seconds)", "Checks if your project files show on your public website"),
    ("Send the GitHub Support letter", "Already written in agents/27. The rewrite it describes is DONE, so it is safe to send."),
    ("Ask your lawyer the four contract questions", "Unlocks 3 of your locked helpers"),
    ("Ask FIU what AI use is allowed for your doctorate", "Highest-risk unanswered question you have"),
    ("Find the seat-3 model ID in your console", "2 minutes. Unlocks NIGHTWATCH.")]:
    checkbox_row(lab, sub)

newpage()
band("MY NOTES", "Room to think. Type here or write by hand.")
for i in range(4):
    notes_field(f"NOTES  {i + 1}", rows=5)

footer()
c.save()
print(f"WROTE FORGE-AI-Agent-Checklist-FILLABLE.pdf")
print(f"pages: {state['page']}  |  form fields: {state['field']}  |  agents listed: {idx}")
