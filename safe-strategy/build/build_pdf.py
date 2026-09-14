# -*- coding: utf-8 -*-
"""Builds the Forgelink SAFE Strategy Playbook (fillable PDF). Two-pass for TOC."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import *
from reportlab.lib.colors import HexColor

EV = {  # evidence-label pill colours
    "gov":   ("#0B5D1E", "GOVERNMENT SOURCE"),
    "emp":   ("#0B3B8C", "EMPIRICAL FINDING"),
    "inf":   ("#7A4B00", "EVIDENCE-BASED INFERENCE"),
    "asm":   ("#6B2D8F", "ASSUMPTION - REPLACE WITH YOUR NUMBER"),
    "unk":   ("#8A1C1C", "UNKNOWN - DO NOT GUESS"),
    "pro":   ("#334155", "PROFESSIONAL VERIFICATION REQUIRED"),
}


def tag(d, *kinds):
    for k in kinds:
        col, txt = EV[k]
        d.label_tag(txt, col)


# =====================================================================  COVER
def cover(d):
    d._chrome = False
    c = d.c
    c.setFillColor(HexColor("#0B1220"))
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    for i, hx in enumerate(["#0E7C86", "#2159C9", "#6D28D9", "#07795A",
                            "#C2570C", "#B31D6B"]):
        c.setFillColor(HexColor(hx))
        c.rect(0, PAGE_H - 16 - i * 0, PAGE_W / 6.0 * i, 0, stroke=0, fill=1)
    c.setFillColor(HexColor("#0E7C86"))
    c.rect(0, PAGE_H - 10, PAGE_W, 10, stroke=0, fill=1)

    d.emoji("\U0001F6E1", ML, PAGE_H - 150, 54)          # shield
    c.setFillColor(HexColor("#7FE3D8"))
    c.setFont(F_BOLD, 10)
    c.drawString(ML + 68, PAGE_H - 112, "FORGE TALENT CONNECTIONS  /  FORGELINK LLC")
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont(F_DISPLAY, 40)
    c.drawString(ML, PAGE_H - 210, "The SAFE Playbook")
    c.setFont(F_DISPLAY, 19)
    c.setFillColor(HexColor("#9FB3D9"))
    c.drawString(ML, PAGE_H - 240, "How to raise money for Forgelink")
    c.drawString(ML, PAGE_H - 264, "without losing the company or the calling")

    c.setStrokeColor(HexColor("#2A3550"))
    c.setLineWidth(1)
    c.line(ML, PAGE_H - 288, PAGE_W - MR, PAGE_H - 288)

    sub = ("A fillable strategy workbook on Simple Agreements for Future Equity, "
           "written in plain words, built on U.S. government primary sources and "
           "peer-reviewed legal scholarship.")
    c.setFont(F_REG, 11)
    for i, ln in enumerate(wrap_runs(parse_runs(sub), CONTENT_W - 120, 11)):
        d._line(ln, ML, PAGE_H - 312 - i * 15, 11, HexColor("#C8D4EA"))

    # promise boxes
    box_y = 300
    items = [("\U0001F9F8", "Explained like\nyou are five"),
             ("\U00002705", "Real fillable\ncheckboxes"),
             ("\U0001F3AF", "90-day sprints\nto Summer 2027"),
             ("\U0001F4DA", "APA sources\nwith links")]
    bw = (CONTENT_W - 3 * 10) / 4.0
    for i, (em, txt) in enumerate(items):
        x = ML + i * (bw + 10)
        c.setFillColor(HexColor("#131C2E"))
        c.setStrokeColor(HexColor("#2A3550"))
        c.setLineWidth(0.8)
        c.roundRect(x, box_y, bw, 74, 6, stroke=1, fill=1)
        d.emoji(em, x + bw / 2 - 11, box_y + 44, 22)
        c.setFillColor(HexColor("#DCE6F7"))
        c.setFont(F_BOLD, 8.4)
        for j, l in enumerate(txt.split("\n")):
            c.drawCentredString(x + bw / 2, box_y + 28 - j * 11, l)

    # truth panel
    c.setFillColor(HexColor("#1A1406"))
    c.setStrokeColor(HexColor("#8A6A12"))
    c.roundRect(ML, 150, CONTENT_W, 128, 6, stroke=1, fill=1)
    d.emoji("\U0001F9ED", ML + 14, 244, 18)
    c.setFillColor(HexColor("#F0C14B"))
    c.setFont(F_BOLD, 10)
    c.drawString(ML + 40, 248, "READ THIS BEFORE ANYTHING ELSE")
    warn = ("This playbook will **not** promise you a contract or a dollar. No plan can. "
            "What it does is show you the exact rules, the exact traps, and the exact "
            "order of moves. Three numbers you may expect to see are deliberately left "
            "blank, because the honest answer is **I do not know them** and guessing "
            "would cost you more than waiting. Every blank is marked. "
            "**Nothing here is legal, tax, or investment advice.**")
    for i, ln in enumerate(wrap_runs(parse_runs(warn), CONTENT_W - 54, 9)):
        d._line(ln, ML + 40, 232 - i * 12, 9, HexColor("#E8D9A8"))

    c.setFillColor(HexColor("#8FA3C4"))
    c.setFont(F_REG, 8.5)
    c.drawString(ML, 118, "Prepared for: Andrew  |  andrew@forgetalentconnections.com")
    c.drawString(ML, 104, "Entities in scope: Forgelink LLC  |  Deterministic Governance LLC (Wyoming, IP holding)")
    c.drawString(ML, 90, "Horizon: deployment by Summer 2027  |  Compiled 14 September 2026")
    c.setFont(F_ITAL, 8.5)
    c.setFillColor(HexColor("#6F84A8"))
    c.drawString(ML, 66, "\"Whatever you do, work heartily, as for the Lord and not for men.\"  Colossians 3:23")
    c.showPage()
    d.page += 1
    d.y = PAGE_H - MT
    d._chrome = True


# ==============================================================  HOW TO USE
def how_to_use(d):
    d.part = "start"
    d.h2("How to use this workbook", "\U0001F5FA")
    d.body("This document is built for a brain that wants **every loose end closed** and "
           "a brain that **loses the thread if a page is boring**. Those are not the same "
           "brain, so the layout serves both on purpose.")
    d.gap(1)

    d.table(
        ["The design choice", "Why it is there"],
        [["Every part has its own colour and never changes colour",
          "You can find your place by colour alone. No hunting."],
         ["Every checkbox is the same size, in the same column, always",
          "Nothing looks uneven. You can scan a page and see instantly what is open."],
         ["One idea per block. Short blocks.",
          "You can stop anywhere and restart without re-reading."],
         ["Grey boxes marked SAY IT LIKE I AM FIVE",
          "The plain-words version of the paragraph above it. Read only these if tired."],
         ["Blanks are fillable fields, not lines to print",
          "Type into this PDF. It saves. You never lose the work."],
         ["Claims carry a coloured label",
          "You always know whether something is proven, inferred, or unknown."]],
        [214, CONTENT_W - 214])

    d.h3("The six labels you will see on claims")
    for k in ["gov", "emp", "inf", "asm", "unk", "pro"]:
        col, txt = EV[k]
        d.label_tag(txt, col)
    d.gap(1)
    d.body("**Government source** means a .gov primary document. **Empirical finding** means "
           "peer-reviewed or official statistical research with real data. **Inference** is my "
           "reasoning from those sources, clearly not a quote. **Assumption** is a placeholder "
           "number you must replace. **Unknown** means nobody told me and I refuse to invent it. "
           "**Professional verification required** means a lawyer or CPA must sign off.")

    d.callout("truth",
              "THE ONE RULE THIS DOCUMENT WILL NOT BREAK",
              "Where I could not verify something, I say so and leave it blank. You will find "
              "at least three deliberate blanks, including one federal dollar threshold where "
              "three government sources disagreed with each other. I did not pick a favourite. "
              "A wrong number in a funding plan is worse than a missing one, because a missing "
              "number gets checked and a wrong number gets trusted.")

    d.callout("faith", "STEWARDSHIP FRAME",
              "You said wealth is stewardship, not consumption, and that you want ownership over "
              "income. That is not decoration here - it changes the recommendation. This playbook "
              "puts **non-dilutive money first** and treats selling equity as the **last** lever, "
              "not the first. Money you do not have to give ownership for is money that stays in "
              "the family line. That is Part 5, and it is the most important part of this document.")

    d.ensure(118)
    d.h3("If you only have ten minutes")
    d.check("Read Part 2. It contains three traps that can quietly end this plan.", "q_p2")
    d.check("Read Part 5. It is how you stop burning your own money.", "q_p5")
    d.check("Fill in the six boxes on the Money Map worksheet in Part 4.", "q_p4")
    d.check("Book the two professional calls listed at the end of Part 2.", "q_calls")


# =====================================================================  TOC
def toc_render(d):
    d.part = "start"
    if d.y < PAGE_H - MT:
        d.new_page()
    d.h2("Table of contents", "\U0001F4D1")
    if not d.toc:
        # pass 1 - reserve exactly the same space pass 2 will use
        d.new_page()
        return
    start_page = d.page
    for num, title, pg, hexcol in d.toc:
        d.ensure(20)
        top = d.y
        d.c.setFillColor(HexColor(hexcol))
        d.c.roundRect(ML, top - 15, 22, 14, 3, stroke=0, fill=1)
        d.c.setFillColor(PAPER)
        d.c.setFont(F_BOLD, 8)
        d.c.drawCentredString(ML + 11, top - 11.5, str(num))
        d.c.setFillColor(INK)
        d.c.setFont(F_BOLD, 10)
        d.c.drawString(ML + 30, top - 11.5, title)
        tw = pdfmetrics.stringWidth(title, F_BOLD, 10)
        d.c.setStrokeColor(RULE)
        d.c.setLineWidth(0.5)
        d.c.setDash(1, 2)
        d.c.line(ML + 34 + tw, top - 11.5, PAGE_W - MR - 20, top - 11.5)
        d.c.setDash()
        d.c.setFillColor(HexColor(hexcol))
        d.c.setFont(F_BOLD, 10)
        d.c.drawRightString(PAGE_W - MR, top - 11.5, str(pg))
        d.y = top - 20
    while d.page < start_page + 1:
        d.new_page()


# ==========================================  PART 1 - WHAT A SAFE ACTUALLY IS
def part1(d):
    d.part_cover("basics", 1, "What a SAFE actually is",
                 "Before strategy, the object itself. Five minutes here saves you a year later.",
                 "\U0001F4DC")

    d.kid("Imagine you sell a ticket that says: **you gave me money today, and later, when a "
          "real investor shows up and sets a price, this ticket turns into a slice of my "
          "company.** That ticket is a SAFE. It is not a slice yet. It is a promise of a "
          "slice, and the promise only comes true if something specific happens.")

    d.h2("The official warning, word for word", "\U000026A0")
    d.body("The U.S. Securities and Exchange Commission's Office of Investor Education and "
           "Advocacy published a bulletin on SAFEs. It is unusually blunt for a government "
           "document, and every founder should read the four points below as written.")
    tag(d, "gov")
    d.bullet("A SAFE is **not** common stock and **not** a current equity stake. It is an "
             "agreement to provide a future equity stake **if and only if** a triggering "
             "event occurs.")
    d.bullet("SAFEs convert **only** if certain triggering events occur, so it matters "
             "enormously what those triggers are.")
    d.bullet("There may be scenarios where the triggers are never activated and the SAFE "
             "is not converted, **\"leaving you with nothing.\"**")
    d.bullet("**\"Despite its name, a SAFE may not be 'simple' or 'safe.'\"**")
    d.callout("stop", "WHY THE SEC SAYS THIS AND WHY IT MATTERS TO YOU",
              "That warning is aimed at investors, but read it as a seller and it becomes a "
              "sales problem: you are asking someone to hand over cash for a ticket the SEC "
              "openly describes as possibly worthless. If you cannot explain, in one sentence, "
              "what makes your trigger likely to fire, you will not close the raise. Part 2 "
              "shows why Forgelink's trigger is the weakest link in the whole plan.")

    d.h2("The four dials on a SAFE", "\U0001F39B")
    d.body("Almost every SAFE argument is about four settings. Learn these and you can read "
           "any SAFE on the table.")
    d.table(
        ["Dial", "In plain words", "What it does to you"],
        [["**Valuation cap**",
          "The highest company price the investor's money will ever convert at.",
          "Lower cap = investor gets more of your company. This is the main number you negotiate."],
         ["**Discount**",
          "A percentage off whatever price the next real round sets.",
          "Stacks on top of, or instead of, the cap. More dilution."],
         ["**Most Favoured Nation (MFN)**",
          "If you later give someone better terms, this investor automatically gets them too.",
          "Lets an early believer invest now without setting a price. Costs you flexibility later."],
         ["**Pro rata**",
          "The right - not the duty - to put more money in later to keep their percentage.",
          "Usually lives in a side letter. Watch it: side letters can create control rights."]],
        [96, 200, CONTENT_W - 296])

    d.h2("Pre-money vs post-money: the one distinction worth your time", "\U0001F9EE")
    d.body("On a **post-money** SAFE, the investor's percentage is fixed the moment they sign: "
           "**investment divided by the post-money valuation cap**. On a pre-money SAFE it is "
           "not fixed, and later SAFEs dilute earlier ones in ways founders routinely "
           "miscalculate.")
    tag(d, "inf")
    d.callout("info", "THE FOUNDER TRAP IN ONE LINE",
              "With post-money SAFEs, **every additional dollar you raise dilutes you, not the "
              "earlier investors.** Stack four post-money SAFEs without modelling them together "
              "and founders regularly discover they gave away far more than they thought. "
              "Model the stack **before** you sign the first one. Part 4 gives you the worksheet.")

    d.h2("What the research actually shows", "\U0001F52C")
    d.body("Coyle and Green surveyed **more than 300 startup lawyers** across **32 U.S. states "
           "and four Canadian provinces**, in partnership with Thomson Reuters Practical Law, "
           "in 2018. It was the first systematic attempt to document how far the deferred "
           "equity agreement had spread across North America.")
    tag(d, "emp")
    d.body("Their earlier work is the one that should worry you, and it is the single most "
           "relevant academic finding for Forgelink specifically. In **Crowdfunding and the "
           "Not-So-Safe SAFE**, they argue that widespread SAFE use may **frustrate investors' "
           "ability to share in the upside**, for a structural reason: the SAFE was designed "
           "for companies that **expect to raise institutional venture capital later**, and "
           "many issuers **never will**.")
    tag(d, "emp")

    d.callout("warn", "APPLY THAT FINDING DIRECTLY TO FORGELINK",
              "A govtech company selling to cities and federal agencies may build a genuinely "
              "valuable, profitable business and **never do a classic priced VC round**. If your "
              "SAFE only converts on an equity financing, and you never raise equity, the SAFE "
              "may never convert. Your investor is left holding the SEC's \"nothing\", and you "
              "are left with an unresolved instrument sitting on your balance sheet forever. "
              "**This is not a hypothetical for you. It is the most likely path.** "
              "The fix is in Part 8: you must widen the conversion triggers.")


# ==================================================  PART 2 - THE LANDMINES
def part2(d):
    d.part_cover("risk", 2, "The three landmines",
                 "Each of these can quietly end the plan. None of them are obvious. "
                 "Read this part twice.",
                 "\U0001F4A3")

    d.callout("stop", "WHY THIS PART COMES BEFORE THE STRATEGY",
              "Every one of these three is cheap to fix **before** you take money and "
              "expensive or impossible to fix **after**. The ordering of this document is "
              "deliberate: traps first, tactics second.")

    # ---- landmine 1
    d.h2("Landmine 1: A SAFE is built for a corporation. Forgelink is an LLC.",
         "\U0001F3DB")
    d.kid("A SAFE promises to turn into **stock**. LLCs do not have stock. They have "
          "**membership units**. So the standard paperwork promises to hand over something "
          "your company does not own and cannot make.")
    d.body("Standard SAFEs and convertible notes are drafted to convert into **preferred stock "
           "of a C-corporation**. An LLC issues membership interests. If a priced round closes "
           "while the company is still an LLC, there is a structural problem that must be "
           "resolved before closing.")
    tag(d, "inf", "pro")
    d.body("There is a second, quieter problem. An LLC is a pass-through: investors receive a "
           "**Schedule K-1** rather than simple stock. Many institutional funds will not accept "
           "K-1s, because it creates tax filing obligations for their own limited partners.")
    d.body("There is a third. Internal Revenue Code **Section 1202** - the qualified small "
           "business stock exclusion - requires a **C corporation**, stock acquired at "
           "**original issuance**, and a holding period of **more than five years**. An LLC "
           "cannot issue QSBS. Every month you stay an LLC is a month the five-year clock is "
           "not running.")
    tag(d, "gov", "pro")
    d.callout("money", "THE STEWARDSHIP READ ON SECTION 1202",
              "You told me tax efficiency and generational transfer matter. QSBS is one of the "
              "largest legal tax exclusions available to a founder on an eventual sale. It "
              "requires a C-corp and a five-year hold. If Forgelink deploys in Summer 2027 and "
              "a liquidity event is even conceivable in the 2030s, **the conversion decision you "
              "make this quarter is worth more than the entire SAFE raise.** Take this one to a "
              "CPA before you take it anywhere else.")

    d.h3("Your three options, honestly compared")
    d.table(
        ["Option", "What it gives you", "What it costs you"],
        [["**A. Convert to a C-corporation first**, then raise",
          "Standard paperwork. Investors say yes. QSBS clock starts. Clean cap table for "
          "employee options when you hire.",
          "Conversion cost and tax analysis. Franchise tax. Corporate-level tax on profits. "
          "Takes weeks, not days."],
         ["**B. Stay an LLC**, use a SAFE rewritten for units",
          "Cheaper today. Keeps pass-through treatment. No conversion event now.",
          "Legal uncertainty in drafting. Sophisticated investors may walk. K-1 burden. "
          "No QSBS. You likely convert later anyway and redo the paperwork."],
         ["**C. Raise at the Wyoming holdco level**",
          "Feels tidy - money lands where the IP lives.",
          "**Read Landmine 2 before considering this.** It is the option most likely to "
          "destroy your federal funding eligibility."]],
        [140, 190, CONTENT_W - 330])
    d.callout("do", "MY RECOMMENDATION, AND THE CONDITION ON IT",
              "**Option A, if and only if the Part 4 worksheet shows you actually need outside "
              "equity.** Convert before you raise, not after. But do not convert on my say-so - "
              "convert because a CPA has modelled your specific numbers. If Part 5 covers the "
              "gap, you may not need to raise at all this year, and then Option A can wait.")
    tag(d, "inf", "pro")

    # ---- landmine 2
    d.h2("Landmine 2: SAFE money can disqualify you from the free money.",
         "\U0001F6A8")
    d.callout("stop", "THIS IS THE MOST IMPORTANT PAGE IN THE DOCUMENT",
              "If you read nothing else, read this. It is the direct collision between the two "
              "things you asked for: raising SAFE money, and winning federal money.")
    d.kid("The government's best startup money has a rule: **real live people who are American "
          "must own more than half the company.** And when they check, they count **not just "
          "who owns shares today, but everyone who is promised shares later.** Your SAFE "
          "tickets count. Sell too many and you fail the test.")
    d.body("To be eligible for SBIR and STTR awards, a concern must be **more than 50% directly "
           "owned and controlled** by one or more **individuals** who are citizens or permanent "
           "resident aliens of the United States - or by other small business concerns that are "
           "themselves more than 50% directly owned and controlled by such individuals - or an "
           "Indian tribe, ANC or NHO, or any combination of these.")
    tag(d, "gov", "pro")
    d.bullet("**\"Individual\" means an actual person.** It does not mean a company or any "
             "other legal entity.")
    d.bullet("**SBA reviews equity ownership on a fully diluted basis.** This is the sentence "
             "that matters. Convertible instruments are counted.")
    d.bullet("The awardee **together with its affiliates** must not exceed **500 employees**.")
    d.callout("warn", "WHAT 'FULLY DILUTED' DOES TO A SAFE STACK",
              "A SAFE is a convertible instrument. On a fully diluted analysis it is counted as "
              "though it has already converted. So the question is not \"who owns Forgelink "
              "today\" - it is **\"who would own Forgelink if every SAFE and option converted "
              "right now.\"** Raise enough SAFE money and you cross below 50% individual "
              "ownership **without a single share changing hands**, and the SBIR door closes.")
    d.callout("do", "THE DESIGN RULE THIS GIVES YOU",
              "**Size the SAFE raise so that, fully diluted and fully converted, U.S.-individual "
              "ownership stays comfortably above 50% - with margin for the employee option pool "
              "you will need when you hire.** Part 4 turns this into an actual ceiling in "
              "dollars. This single constraint should drive the size of your raise. Not your "
              "burn rate. Not your ambition. This.")
    tag(d, "inf")

    d.h3("The holdco question, stated precisely")
    d.body("Note the clause carefully: ownership by **other small business concerns, each of "
           "which is itself more than 50% directly owned and controlled by qualifying "
           "individuals**, also counts. On its face, a Wyoming holding company that is majority "
           "owned by you personally, and that qualifies as a small business concern, may be "
           "capable of satisfying the chain. **On its face.**")
    tag(d, "gov")
    d.callout("warn", "WHY I WILL NOT TELL YOU THIS WORKS",
              "I could not read the full regulation in this session - the government text sites "
              "were blocked by this environment's network policy. I retrieved this language "
              "through search extracts of the real regulation, not from memory, but I have not "
              "read 13 CFR 121.702 end to end, and the word **\"directly\"** in that sentence is "
              "doing heavy lifting that only full text and counsel can settle. "
              "**Do not restructure ownership based on this page.** Take this exact question, in "
              "these exact words, to a government contracts attorney. It is question 1 on your "
              "call list.")
    tag(d, "unk", "pro")

    # ---- landmine 3
    d.h2("Landmine 3: Investor rights can make you 'not small' anymore.",
         "\U0001F517")
    d.kid("If someone can tell you **no** about big decisions, the government may treat their "
          "company and your company as **one company**. Then their size counts as your size, "
          "and you are too big to be the little guy who gets the set-aside contracts.")
    d.body("Under SBA's affiliation rules, concerns are affiliates when one **controls or has "
           "the power to control** the other, or a third party controls both. **It does not "
           "matter whether the control is actually exercised, so long as the power exists.**")
    tag(d, "gov")
    d.bullet("Power to control is presumed at **50% or more** ownership.")
    d.bullet("It **may also exist with considerably less than 50%**, by contractual arrangement.")
    d.bullet("SBA weighs ownership, management, previous relationships and ties, and "
             "**contractual relationships**.")
    d.bullet("In sizing you, SBA counts the receipts or employees of **the concern and all of "
             "its domestic and foreign affiliates**.")
    d.callout("warn", "WHERE THIS BITES A SAFE ROUND: THE SIDE LETTER",
              "The SAFE itself is usually harmless here. **The side letter is where founders get "
              "hurt.** Consent rights, board observer seats, veto rights over budgets, hiring, "
              "new debt, or a sale - these are **negative control**, and negative control is "
              "control. Give an investor a veto and you may have handed them affiliation, "
              "and with it your small business status and every set-aside contract that "
              "depends on it.")
    d.callout("do", "THE DRAFTING RULE",
              "**No investor consent rights. No board seats. No vetoes. Information rights only.** "
              "If an investor insists on control terms, price that demand against the federal "
              "contracts it may cost you, and be willing to decline the cheque. A smaller "
              "cheque with clean terms is worth more than a larger cheque that ends your "
              "eligibility.")
    tag(d, "inf", "pro")

    d.h2("Your two professional calls. Book these this week.", "\U0000260E")
    d.body("These are not optional and they are not expensive relative to what they protect.")
    d.check("**Call 1 - Government contracts attorney.** Agenda: (a) Does the Wyoming holdco "
            "chain satisfy 13 CFR 121.702 direct-ownership? (b) Will our planned SAFE terms "
            "create affiliation under 13 CFR 121.103? (c) Review the side letter, if any.",
            "l3_call1")
    d.check("**Call 2 - Startup CPA plus tax counsel.** Agenda: (a) LLC vs C-corp conversion "
            "modelling on our actual numbers. (b) Section 1202 QSBS clock and whether to start "
            "it now. (c) Tax characterisation of the SAFE itself - this is genuinely unsettled.",
            "l3_call2")
    d.field_row([("Attorney - name", "atty_name", 190), ("Call booked for", "atty_date", 110),
                 ("Cost quoted", "atty_cost", 90)])
    d.field_row([("CPA / tax counsel - name", "cpa_name", 190), ("Call booked for", "cpa_date", 110),
                 ("Cost quoted", "cpa_cost", 90)])
    d.callout("info", "ON THE TAX TREATMENT OF SAFES - AN HONEST UNKNOWN",
              "The tax characterisation of a SAFE is **not settled**. It is commonly analysed "
              "either as a variable prepaid forward contract or as equity, and which one applies "
              "affects the holding period and therefore QSBS. I found no authoritative government "
              "ruling resolving it. Commentary exists from major accounting firms, but that "
              "commentary does not clear your own source standard, so I have not built any "
              "recommendation on it. **Treat this as open. Ask your CPA directly.**")
    tag(d, "unk", "pro")


# =============================================  PART 3 - STRUCTURE
def part3(d):
    d.part_cover("struct", 3, "Getting the structure right",
                 "Two companies, one licence, and the question that decides everything else.",
                 "\U0001F3D7")

    d.h2("What I know, what I do not, and why it matters", "\U00002753")
    d.body("You have described two entities: **Forgelink LLC**, which holds sole licences to the "
           "software technologies, and **Deterministic Governance LLC**, a Wyoming IP holding "
           "company. Separating operations from intellectual property is a recognised and "
           "defensible structure. It can isolate the crown jewels from operating liability.")
    d.callout("stop", "THE SINGLE FACT THAT CHANGES THE WHOLE ANALYSIS",
              "**Does Deterministic Governance LLC OWN Forgelink LLC, or does it only LICENSE IP "
              "to Forgelink?** These are completely different worlds for federal eligibility. "
              "A licence between two companies you happen to control is one thing. A parent "
              "entity owning the awardee is another, and it runs straight into the "
              "\"individuals\" and \"directly owned\" language from Landmine 2. "
              "**I do not know which one is true, and I will not assume.** Fill it in below.")
    tag(d, "unk")
    d.field("Deterministic Governance LLC's relationship to Forgelink LLC", "struct_rel", w=CONTENT_W - 4,
            note=None)
    d.field_row([("Who owns Forgelink LLC, and what %", "struct_own", 250),
                 ("State of formation", "struct_state", 120)])
    d.field_row([("Who owns Deterministic Governance LLC, and what %", "struct_own2", 250),
                 ("Andrew: US citizen or PR?", "struct_cit", 120)])

    d.h2("The IP licence is a document, not a handshake", "\U0001F4C4")
    d.body("If Forgelink holds \"sole licences,\" the licence agreement itself becomes a "
           "load-bearing asset. An investor's lawyer will read it before they wire money, and a "
           "contracting officer may ask whether you actually have the rights to perform. "
           "Write down the answers to these now, because you will be asked.")
    d.check("**Scope** - exactly which technologies, and is it truly exclusive?", "ip_scope")
    d.check("**Field of use** - all markets, or only government? Does it cover city and federal?",
            "ip_field")
    d.check("**Term** - how long, and what happens at expiry?", "ip_term")
    d.check("**Royalty** - what does Forgelink pay the holdco, and is it arm's length? "
            "Related-party pricing draws scrutiny from both the IRS and contracting officers.",
            "ip_royalty")
    d.check("**Termination** - can the holdco pull the licence? If yes, an investor is funding "
            "a company that can be hollowed out overnight. Expect them to demand this be fixed.",
            "ip_term2")
    d.check("**Change of control** - what happens to the licence if Forgelink is sold?", "ip_coc")
    d.check("**Sublicensing and government rights** - can Forgelink grant the government the "
            "licences a contract will require?", "ip_sub")
    d.callout("warn", "THE INVESTOR-SIDE PROBLEM WITH A TERMINABLE LICENCE",
              "If the holdco can terminate the licence, then buying a SAFE in Forgelink means "
              "buying a slice of a company whose only real asset can be withdrawn by its owner. "
              "Sophisticated investors will either refuse, or require the licence to be made "
              "irrevocable, or insist on investing in the holdco instead - which reopens "
              "Landmine 2. **Resolve this before you open a conversation with any investor.**")
    tag(d, "inf", "pro")

    d.h2("Which entity should the money land in?", "\U0001F4E5")
    d.table(
        ["Money lands in", "Argument for", "Argument against"],
        [["**Forgelink** (the operating company)",
          "It is the entity that will hold the contracts, do the hiring, and win SBIR awards. "
          "Investors fund operations. Keeps the awardee's ownership chain shortest.",
          "Dilutes the operating company - the exact entity whose fully-diluted ownership the "
          "SBA will test."],
         ["**Deterministic Governance** (the holdco)",
          "Money sits with the IP. Feels protective.",
          "An entity owner sits between individuals and the awardee. Runs directly into the "
          "\"individuals\" / \"directly owned\" language. **Highest eligibility risk.**"],
         ["**Neither - do not raise this year**",
          "Part 5 may cover the gap without dilution at all. Costs you nothing to test first.",
          "Slower. Depends on winning competitive awards you do not control."]],
        [122, 200, CONTENT_W - 322])
    d.callout("do", "PROVISIONAL RECOMMENDATION",
              "**Raise into Forgelink, not the holdco - and only after Part 5 proves you still "
              "need to.** This is an inference from the ownership language, not a legal opinion, "
              "and it is explicitly subject to Call 1 in Part 2. If your attorney says otherwise, "
              "your attorney is right and this page is wrong.")
    tag(d, "inf", "pro")


# =============================================  PART 4 - THE MONEY MAP
def part4(d):
    d.part_cover("money", 4, "The money map",
                 "How much to raise, where the ceiling is, and the arithmetic that sets it.",
                 "\U0001F4B0")

    d.kid("Before you ask anyone for money, you need two numbers: **how much you actually need**, "
          "and **the most you are allowed to sell before you break the free-money rule.** "
          "Then you take the smaller one.")

    d.h2("Step 1 - What does it actually cost to get to Summer 2027?", "\U0001F9EE")
    d.body("Fill these in. I do not know any of them, and a funding plan built on invented "
           "numbers is worse than no plan.")
    tag(d, "unk")
    d.step(1, "Cost to finish the software", "\U0001F4BB")
    d.field_row([("Engineering to complete build", "m_eng", 150),
                 ("Security / compliance work", "m_sec", 150),
                 ("Infrastructure & tooling", "m_infra", 130)])
    d.step(2, "Cost to pilot and deploy", "\U0001F680")
    d.field_row([("Pilot delivery cost", "m_pilot", 150),
                 ("Deployment & support", "m_deploy", 150),
                 ("Certifications / audits", "m_cert", 130)])
    d.step(3, "Cost of the people you hire before 2027", "\U0001F465")
    d.field_row([("Number of hires planned", "m_heads", 150),
                 ("Fully loaded cost each", "m_cost", 150),
                 ("Months employed by S2027", "m_months", 130)])
    d.step(4, "Your runway and your line in the sand", "\U0001F6E9")
    d.field_row([("Current monthly burn", "m_burn", 150),
                 ("Months of runway left", "m_runway", 150),
                 ("Personal money already in", "m_own", 130)])
    d.callout("faith", "SET THE LINE BEFORE YOU NEED IT",
              "You said you are tired of burning your own money. Then write the number down "
              "**now**, while you are calm, and treat it as a covenant rather than a preference. "
              "A limit chosen under pressure is not a limit.")
    d.field("The maximum additional personal money I will put in, full stop", "m_limit", w=180,
            note="Write it. Date it. Tell your spouse.")

    d.h2("Step 2 - The ceiling the government sets for you", "\U0001F6D1")
    d.body("This is the constraint from Landmine 2, turned into arithmetic. On a post-money "
           "SAFE, an investor's percentage is **investment divided by the post-money valuation "
           "cap**. So the total you can sell is bounded by how much dilution you can absorb "
           "while keeping U.S.-individual ownership above 50% fully diluted.")
    tag(d, "inf")
    d.callout("money", "THE CEILING FORMULA",
              "**Maximum SAFE dollars  =  Valuation cap  x  ( 1  -  your individual-ownership "
              "floor  -  your employee option pool )**\n\n"
              "Use a floor **above** 50%, not at it. 50% is the cliff edge, not the target.")
    d.h3("Worked example - every number below is invented for illustration")
    tag(d, "asm")
    d.table(
        ["Input", "Illustrative value", "Note"],
        [["Post-money valuation cap", "$8,000,000",
          "**Assumption.** I have no basis to value Forgelink. Do not use this number."],
         ["Individual-ownership floor", "55%",
          "5 points of margin above the 50% cliff. Your choice of margin."],
         ["Employee option pool reserved", "15%",
          "You said you want to hire well before 2027. The pool must be counted."],
         ["**Maximum SAFE raise**", "**$8,000,000 x (1 - 0.55 - 0.15) = $2,400,000**",
          "The ceiling. Not a target."],
         ["If you raised $750,000 instead", "9.375% to investors",
          "750,000 / 8,000,000. Leaves wide margin. Much safer."]],
        [136, 150, CONTENT_W - 286])
    d.callout("warn", "READ THE EXAMPLE CORRECTLY",
              "That $8M cap is **fabricated for arithmetic demonstration only**. I have no "
              "revenue, no comparables, and no basis to value your company, and I am not going "
              "to invent one. I also looked for a peer-reviewed or government dataset of current "
              "SAFE valuation-cap benchmarks to anchor it honestly. **There does not appear to "
              "be one.** Benchmark data exists, but it is published by private cap-table vendors "
              "- proprietary, not peer-reviewed, not government - which does not meet the source "
              "standard you set for this document. So I left it out rather than quietly lower "
              "the bar. Your cap comes from negotiation and from your CPA, not from this page.")
    tag(d, "unk")

    d.h3("Now do it with your own numbers")
    d.field_row([("A. Your valuation cap", "c_cap", 150),
                 ("B. Individual floor %", "c_floor", 130),
                 ("C. Option pool %", "c_pool", 130)])
    d.field_row([("D. Ceiling = A x (1 - B - C)", "c_ceiling", 200),
                 ("E. Actual need from Step 1", "c_need", 190)])
    d.field("F. YOUR RAISE = the smaller of D and E", "c_raise", w=200,
            note="If E is bigger than D, do not raise more. Cut scope or win more non-dilutive.")

    d.h2("Step 3 - Model the whole stack before you sign the first one", "\U0001F4CA")
    d.callout("info", "THE POST-MONEY STACKING TRAP, AGAIN",
              "With post-money SAFEs, later SAFEs dilute **you**, not the earlier investors. "
              "Four separate $200,000 SAFEs at four different caps do not behave like one "
              "$800,000 SAFE. Build the full conversion table **before** the first signature, "
              "and update it after every single one.")
    d.table(["#", "Investor", "Amount", "Cap", "% at conversion", "Running total %"],
            [[str(i), "", "", "", "", ""] for i in range(1, 7)],
            [18, 130, 80, 80, 90, CONTENT_W - 398], row_h=20)
    d.field_row([("Total raised", "s_tot", 120), ("Total investor %", "s_pct", 120),
                 ("Option pool %", "s_pool", 110), ("Individuals left %", "s_ind", 110)])
    d.check("**Individuals-left figure is above my floor.** If it is not, the raise is too big. "
            "Stop and re-cut.", "s_check")


# =====================================  PART 5 - NON-DILUTIVE FIRST
def part5(d):
    d.part_cover("nondil", 5, "Free money first",
                 "The part that actually answers 'stop burning my own money.' "
                 "Do this before you sell a single percent.",
                 "\U0001F381")

    d.callout("faith", "WHY THIS PART OUTRANKS THE SAFE",
              "You said you value ownership over income, and asymmetric upside. There is no "
              "better expression of that than money you receive **without giving up any "
              "ownership at all**. Every dollar won here is a dollar you do not have to dilute "
              "for. This is the highest-leverage part of the document. The SAFE exists only to "
              "fill whatever gap is left after this.")

    d.h2("SBIR and STTR - what the government says it is", "\U0001F1FA")
    d.body("SBIR and STTR are described by SBIR.gov as **America's Seed Fund**, coordinated by "
           "the Small Business Administration and funded through **11 participating federal "
           "agencies**. The programs award **non-dilutive** funding to develop technology and "
           "chart a path toward commercialisation - meaning companies receive funding "
           "**without giving up equity ownership**.")
    tag(d, "gov")
    d.table(
        ["", "What it is", "Money", "Time"],
        [["**Phase I**", "Proof of concept. Establish feasibility.",
          "**$50,000 - $275,000**", "6 - 12 months"],
         ["**Phase II**", "Technology development. The real build money.",
          "**$750,000 - $1,800,000**", "~24 months"],
         ["**Phase III**", "Commercialisation. Funded with **non-SBIR** funds - "
          "typically a real government contract.",
          "**No SBIR limit**", "Agency dependent"]],
        [60, 232, 118, CONTENT_W - 410])
    d.body("Note the amounts against your own Step 1 numbers. A Phase I plus a Phase II is a "
           "meaningful fraction of what it costs most software companies to finish a build and "
           "run a pilot - and it costs you **zero equity**.")
    tag(d, "inf")
    d.callout("info", "AGENCY AMOUNTS VARY",
              "Those ranges are the general program figures. Individual agencies set their own "
              "ceilings and some exceed these. Check the specific solicitation, always.")

    d.h2("Phase III is the closest thing to what you actually asked for", "\U0001F3C6")
    d.kid("If the government pays you to prove an idea, and then pays you to build it, then "
          "when they want to buy the finished thing **they are allowed to just buy it from you** "
          "without running a fresh competition against everybody else.")
    d.body("You asked how to **ensure** you get federal contracts. No one can ensure a "
           "competitive award. But Phase III is the one federal pathway with an explicit "
           "statutory basis for sole-source follow-on award to the firm that did the work:")
    tag(d, "gov")
    d.bullet("A Phase III award must **derive from, extend, or complete** prior SBIR/STTR effort, "
             "and is funded with **non-SBIR funds**.")
    d.bullet("An agency funding a Phase III award **\"is not required to conduct another "
             "competition ... in order to satisfy statutory competition requirements.\"**")
    d.bullet("The authority cited is **15 U.S.C. 638(r)(4)**.")
    d.bullet("The government **must award Phase III to the SBIR firm that developed the "
             "technology \"to the greatest extent practicable.\"**")
    d.callout("do", "THIS IS THE SPINE OF THE PLAN",
              "Phase I -> Phase II -> Phase III is: non-dilutive money, then non-dilutive money, "
              "then a contract that can be awarded to you **without a competition**. It is slower "
              "than a SAFE and it is competitive at Phase I. But it is the only route on the "
              "board that pays you to build the thing **and** ends in a defensible sole-source "
              "position. **Build the plan around this. Use the SAFE to survive the gaps in it.**")
    tag(d, "inf")

    d.h2("Eligibility - check yourself against this before you write anything", "\U00002705")
    d.check("For-profit entity located in the **United States**.", "e_us")
    d.check("**Fewer than 500 employees**, counted together with all affiliates.", "e_500")
    d.check("**More than 50% directly owned and controlled** by individuals who are U.S. "
            "citizens or permanent residents (or qualifying small business concerns). "
            "**Fully diluted.** This is Landmine 2.", "e_own")
    d.check("For **STTR only**: formal partnership with a research institution, with the small "
            "business performing **at least 40%** and the research institution **at least 30%** "
            "of the work.", "e_sttr")
    d.check("Registered and current in SAM.gov and on SBIR.gov.", "e_reg")

    d.h2("The IP protection nobody tells you about", "\U0001F510")
    d.callout("money", "SBIR DATA RIGHTS ARE A GIFT TO YOUR HOLDCO THESIS",
              "A common fear is that taking government money means losing your IP. For SBIR, "
              "the opposite is closer to true - **if you follow the marking rules.**")
    d.bullet("SBA set a uniform **20-year** SBIR/STTR data protection period, **beginning at the "
             "date of award** (effective May 2, 2019).")
    d.bullet("During that period the government has a **limited, nonexclusive licence** and "
             "**cannot disclose your SBIR data outside the government**.")
    d.bullet("On expiry, the government obtains **government purpose rights**, which do not expire.")
    d.bullet("Protection applies across **Phase I, II and III**.")
    d.bullet("Relevant clauses: **FAR 52.227-20**, **DFARS 252.227-7018**, **DFARS 227.7104-2**.")
    tag(d, "gov", "pro")
    d.callout("stop", "THE WAY COMPANIES LOSE THIS",
              "Protection depends on the data being **properly marked** with the SBIR/STTR data "
              "rights legend. Unmarked deliverables are the standard way firms hand away rights "
              "they were entitled to keep. **Set up your marking discipline before your first "
              "deliverable, not after.** Put one named person in charge of it.")
    d.check("A named person owns SBIR data marking from day one.", "dr_owner")
    d.field_row([("That person is", "dr_person", 200), ("Backup", "dr_backup", 180)])

    d.h2("Other non-dilutive lines worth an hour each", "\U0001F50D")
    d.bullet("**State and local economic development grants** - many states fund software and "
             "job creation directly. Check your state's commerce department.")
    d.bullet("**State SBIR matching programs** - several states match federal Phase I awards.")
    d.bullet("**Customer-funded development** - a city paying for a pilot is non-dilutive "
             "revenue **and** past performance. See Part 6.")
    d.bullet("**Prime subcontracting** - revenue and past performance without winning a prime "
             "contract first.")
    tag(d, "inf")


# =====================================  PART 6 - CONTRACTS RUNWAY
def part6(d):
    d.part_cover("contract", 6, "The contracts runway",
                 "City and federal work: what is controllable, what is not, and the honest "
                 "correction to the goal.",
                 "\U0001F3DB")

    d.callout("stop", "AN HONEST CORRECTION TO THE REQUEST",
              "You asked for a strategy that will **ensure** city and federal contracts within "
              "the year. I have to tell you plainly: **no strategy can ensure a contract award.** "
              "Award depends on competition, agency budget cycles, evaluation judgement, and "
              "protest risk - none of which you control. Any document that promises you a "
              "contract is selling you something.\n\n"
              "What you **can** control is whether you are eligible, registered, findable, "
              "credible, and responsive. So this part converts your goal into **leading "
              "indicators you fully control** - and the one pathway (Phase III, Part 5) with a "
              "statutory basis for sole-source award.")

    d.h2("The gate you must pass before anything else", "\U0001F6AA")
    d.body("Before you can bid, you need a **Unique Entity Identifier (UEI)** - a 12-character "
           "alphanumeric value - obtained by registering at **SAM.gov**. Registration and the "
           "UEI are **free**.")
    tag(d, "gov")
    d.bullet("**Full registration** is required to bid on contracts as a prime awardee and to "
             "apply for federal assistance.")
    d.bullet("**UEI-only** is available if you just need the identifier - it requires only legal "
             "business name and physical address.")
    d.bullet("In most cases registration must be **active when you submit an offer, at time of "
             "award, and throughout the life of the contract**.")
    d.bullet("**Renew every 365 days** or it lapses. A lapsed registration at the wrong moment "
             "makes you ineligible for award.")
    d.callout("warn", "THE MOST COMMON UNFORCED ERROR IN THIS WHOLE DOCUMENT",
              "Companies lose awards because their SAM registration silently expired. Put the "
              "renewal date in a calendar with a **60-day advance reminder**, assign it to a "
              "named person, and never let it be nobody's job.")
    d.field_row([("Our UEI", "gc_uei", 170), ("CAGE code", "gc_cage", 120),
                 ("Registration expires", "gc_exp", 120)])
    d.field_row([("Renewal reminder set for", "gc_rem", 170), ("Owner of this task", "gc_own", 250)])

    d.h2("Pick your NAICS codes deliberately", "\U0001F3F7")
    d.body("Your NAICS codes determine which size standard applies to you and which "
           "solicitations you match. For software, **NAICS 541511 - Custom Computer Programming "
           "Services** is the common primary code. A retrieved figure puts its size standard at "
           "**$34.0 million** in average annual receipts.")
    tag(d, "gov")
    d.callout("info", "VERIFY THIS NUMBER BEFORE RELYING ON IT",
              "Receipts-based size standards are periodically adjusted, and I retrieved this "
              "figure through search rather than by reading SBA's table directly - this "
              "environment blocked access to sba.gov. Confirm against SBA's official Table of "
              "Size Standards. At your current stage you are comfortably small either way, so "
              "this affects planning, not eligibility, today.")
    d.field_row([("Primary NAICS", "gc_naics1", 130), ("Secondary", "gc_naics2", 130),
                 ("Third", "gc_naics3", 130)])

    d.h2("Where the first dollar realistically comes from", "\U0001F4B5")
    d.body("Do not start by chasing a large competitive award. Start where the procedural "
           "burden on the government is lowest, because that is where a small unknown vendor "
           "can actually get bought.")
    d.table(
        ["Route", "What it is", "Why it is your entry point"],
        [["**Micro-purchase**", "Purchases at or below the micro-purchase threshold, which "
          "**increased to $15,000 effective 1 October 2025**.",
          "Lowest procedural burden on the buyer. This is how an unknown vendor gets a first "
          "paid engagement and first past performance."],
         ["**Simplified acquisition**", "Streamlined procedures below the simplified "
          "acquisition threshold.",
          "Far less paperwork than a full competition. **See the warning below on this number.**"],
         ["**Small business set-aside**", "Under the **Rule of Two** (FAR 19.502-2), an "
          "acquisition is set aside when there is a reasonable expectation of offers from "
          "**two or more** responsible small business concerns at fair market prices.",
          "Removes large primes from the competition entirely. Your small size is the asset."],
         ["**Subcontract to a prime**", "Deliver under someone else's contract.",
          "Revenue and past performance without winning a prime award first. Fastest credible "
          "start."],
         ["**SBIR Phase I/II -> III**", "See Part 5.",
          "The only route with statutory backing for a **sole-source** follow-on."]],
        [116, 196, CONTENT_W - 312])
    d.callout("warn", "A NUMBER I AM DELIBERATELY LEAVING BLANK",
              "I tried to give you the current **simplified acquisition threshold** and found "
              "**three government sources that disagreed with each other** - one indicating "
              "$250,000, another describing an increase from $250,000 to $350,000, and a third "
              "referencing a different figure entirely. The micro-purchase threshold of $15,000 "
              "was corroborated twice, so I state it. The SAT was not, so **I am not going to "
              "guess it.**\n\n"
              "Confirm it yourself at **acquisition.gov/threshold-changes** and write it here. "
              "It takes two minutes and it will be right, which is more than I can promise you "
              "from this desk.")
    tag(d, "unk")
    d.field_row([("Current SAT (you verify)", "gc_sat", 160),
                 ("Commercial threshold", "gc_sat2", 160),
                 ("Date you checked", "gc_satdate", 110)])

    d.h2("The bridge to CITY contracts", "\U0001F309")
    d.body("You asked specifically about city work. The structural bridge is the GSA "
           "**Multiple Award Schedule (MAS)** - a long-term governmentwide contract - combined "
           "with the **Cooperative Purchasing Program**, which allows **state, local and tribal "
           "governments** to buy from MAS.")
    tag(d, "gov")
    d.bullet("More than half of GSA's industry partners are **small businesses**.")
    d.bullet("Ordering activities may set aside orders and blanket purchase agreements for "
             "small business when market research shows **at least three capable firms**.")
    d.bullet("Small firms commonly succeed on MAS through **Contractor Team Arrangements (CTAs)** "
             "and **Blanket Purchase Agreements (BPAs)**.")
    d.callout("info", "A REALISTIC NOTE ON TIMING",
              "Getting a MAS contract is a project in itself, not a quick form. If your horizon "
              "is city revenue **within the year**, run direct city procurement and "
              "subcontracting in parallel rather than waiting on MAS. Cities also run their own "
              "procurement portals with their own small/local business preferences - those are "
              "often faster than anything federal.")
    d.check("Identified our 3 target cities and found each one's procurement portal.", "cty_portal")
    d.check("Checked each city's local / small / minority business preference programs.", "cty_pref")
    d.check("Registered as a vendor with each target city.", "cty_reg")
    d.field_row([("Target city 1", "cty1", 150), ("City 2", "cty2", 150), ("City 3", "cty3", 130)])

    d.h2("Certifications worth checking your eligibility for", "\U0001F396")
    d.body("These are set-aside programs. Each one narrows the field of competitors against you. "
           "**I do not know whether you qualify for any of them** - that depends on facts about "
           "you that I do not have.")
    tag(d, "unk")
    d.table(["Program", "Core requirement as retrieved"],
            [["**8(a) Business Development**",
              "Majority owned and controlled by socially disadvantaged individuals. Certain "
              "groups are presumed socially disadvantaged; others may qualify case-by-case by "
              "demonstrating bias of a chronic and substantial nature."],
             ["**HUBZone**", "At least 51% owned and controlled by U.S. citizens (or listed "
              "entity types); **principal office** located in a designated HUBZone; employ staff "
              "who reside in a HUBZone."],
             ["**WOSB / EDWOSB**", "Owned and controlled by one or more women. EDWOSB adds an "
              "economic disadvantage test (a retrieved personal-assets figure of $6.5 million "
              "or less - verify)."],
             ["**VOSB / SDVOSB**", "At least 51% owned and controlled by one or more veterans; "
              "SDVOSB requires a VA service-disabled rating."]],
            [136, CONTENT_W - 136])
    d.body("Applications are made through **certifications.sba.gov**.")
    d.check("Checked eligibility for each of the four programs above.", "cert_check")
    d.field("Programs we appear to qualify for (if any)", "cert_list", w=CONTENT_W - 4)

    d.h2("Your controllable scoreboard", "\U0001F4C8")
    d.body("Track these instead of tracking \"did we win a contract.\" These you control. "
           "Awards follow from them, or they do not - but you will have done the work.")
    d.table(["Leading indicator", "Target this quarter", "Actual"],
            [["SAM.gov registration active and current", "", ""],
             ["Capability statement delivered to named buyers", "", ""],
             ["Solicitations reviewed", "", ""],
             ["Bids / quotes actually submitted", "", ""],
             ["Primes approached for subcontracting", "", ""],
             ["SBIR solicitations screened for fit", "", ""],
             ["SBIR Phase I proposals submitted", "", ""],
             ["City procurement registrations completed", "", ""]],
            [250, 130, CONTENT_W - 380], row_h=19)


# =====================================  PART 7 - 90-DAY SPRINTS
def part7(d):
    d.part_cover("sprint", 7, "90-day sprints to Summer 2027",
                 "A ten-year horizon executed in 90-day blocks. Here are the next four.",
                 "\U0001F5D3")

    d.callout("faith", "THE BASE RATE, STATED HONESTLY",
              "U.S. Bureau of Labor Statistics data on establishment survival: about **20% of "
              "new establishments do not survive year one**, about **32% do not survive two "
              "years**, roughly **44% are still operating after four years**, and about **half "
              "do not survive five years**. The largest single drop happens in the **first six "
              "months**. Survival varies by sector, from about **53%** to **74%** across "
              "two-digit NAICS sectors.\n\n"
              "This is not a prediction about Forgelink. It is the base rate you are planning "
              "against, and the reason the sequencing below puts **cash survival ahead of "
              "product ambition**.")
    tag(d, "emp")

    sprints = [
        ("SPRINT 1", "Now - Dec 2026", "Stop the bleeding. Get legal clarity.", "\U0001F6E1",
         ["Book and complete **Call 1** (government contracts attorney) and **Call 2** "
          "(CPA / tax counsel) from Part 2.",
          "Get a written answer on the **holdco ownership chain** question.",
          "Decide **LLC vs C-corp** on modelled numbers, not instinct.",
          "Complete **SAM.gov** registration; obtain UEI and CAGE; set the renewal reminder.",
          "Fill in every blank in the **Part 4 Money Map**. Compute your real ceiling.",
          "Write down your **personal-money line in the sand** and stop crossing it.",
          "Document the **IP licence terms** between the holdco and Forgelink."]),
        ("SPRINT 2", "Jan - Mar 2027", "Go get the free money.", "\U0001F381",
         ["Screen **SBIR/STTR solicitations** across the 11 participating agencies for fit.",
          "Submit at least one **Phase I proposal**. Submitting is the controllable act.",
          "Stand up **SBIR data-marking discipline** with a named owner - before any deliverable.",
          "Build the **capability statement** and deliver it to named buyers, not inboxes.",
          "Register as a vendor with your **three target cities**.",
          "Approach **three primes** about subcontracting.",
          "Only if the ceiling worksheet says you must: open the **SAFE raise**."]),
        ("SPRINT 3", "Apr - Jun 2027", "First revenue. First past performance.", "\U0001F4B5",
         ["Pursue **micro-purchase** scale work - the realistic first paid engagement.",
          "Convert one pilot conversation into a **paid** pilot. Paid changes everything.",
          "If a SAFE round is open, close it on **clean terms** - no consent rights, no vetoes.",
          "Begin hiring against funded work only. **Never hire against hope.**",
          "Track the Part 6 leading indicators weekly, not quarterly."]),
        ("SPRINT 4", "Jul - Sep 2027", "Deploy, and convert proof into position.", "\U0001F680",
         ["Complete pilot testing and **deploy**.",
          "If Phase I was won, submit **Phase II**. This is the real build money.",
          "Convert delivered work into **written past performance references**.",
          "Position deliberately for **Phase III** sole-source follow-on.",
          "Re-run the whole Money Map. The numbers have changed."]),
    ]
    for name, window, goal, em, items in sprints:
        d.ensure(190)
        d.h2("%s  |  %s" % (name, window), em)
        d.callout("do", "SPRINT GOAL", goal)
        for it in items:
            d.check(it, None)
        d.field_row([("Sprint owner", None, 150), ("Review date", None, 130),
                     ("Status", None, 130)])
        d.rule()

    d.callout("warn", "THE HONEST RISK TO THE SUMMER 2027 DATE",
              "This plan depends on competitive awards you do not control and professional "
              "answers you have not yet received. If Phase I is not won and no SAFE closes, "
              "Summer 2027 deployment is at risk. **The correct response to that is to cut "
              "scope, not to cross your personal-money line.** Decide now, in writing, which "
              "features are genuinely required for a first deployment and which are not.")
    d.field("Minimum feature set genuinely required to deploy", "min_feat", w=CONTENT_W - 4)
    d.field("What I will cut first if funding slips", "cut_first", w=CONTENT_W - 4)


# =====================================  PART 8 - THE SAFE FORM
def part8(d):
    d.part_cover("form", 8, "The example SAFE agreement",
                 "A fillable, plain-language starting point. Built to be marked up by your "
                 "lawyer - not signed as-is.",
                 "\U0001F4DD")

    d.callout("stop", "READ BEFORE YOU FILL THIS IN",
              "This is a **drafting starting point written in plain language so you can "
              "understand every clause before you pay a lawyer to argue about it.** It is not a "
              "law firm product and it is not legal advice.\n\n"
              "It is deliberately **not** a copy of any standard market form. Two clauses below "
              "are intentionally **non-standard**, because Part 1's research finding says the "
              "standard form has a structural failure mode for a company like yours. Those "
              "clauses are flagged. Your counsel may disagree with them, and your counsel "
              "outranks this document.")

    d.callout("warn", "ENTITY TYPE - RESOLVE THIS FIRST",
              "This form says **Equity Securities**, not **Preferred Stock**, on purpose - so it "
              "can work for either a corporation or an LLC. But a real SAFE must name what it "
              "actually converts into. If Forgelink is still an LLC when you use this, Landmine "
              "1 in Part 2 has **not** been solved by this wording. It has only been postponed.")

    d.h2("Cover terms", "\U0001F4CB")
    d.field_row([("Company legal name", "sf_co", 250), ("Entity type", "sf_type", 120),
                 ("State", "sf_state", 80)])
    d.field_row([("Investor legal name", "sf_inv", 250), ("Date", "sf_date", 120),
                 ("Instrument no.", "sf_no", 80)])
    d.field_row([("Purchase amount (US$)", "sf_amt", 160),
                 ("Post-money valuation cap (US$)", "sf_cap", 200),
                 ("Discount rate (%)", "sf_disc", 110)])
    d.field_row([("Investor email", "sf_email", 250), ("Investor address", "sf_addr", 260)])

    d.h2("The agreement", "\U00002696")
    d.body("**THIS CERTIFIES THAT** in exchange for the Purchase Amount stated above, "
           "**[Investor]** (the \"Investor\") is entitled to certain rights to Equity Securities "
           "of **[Company]** (the \"Company\"), subject to the terms below.")

    d.h3("1.  What this is, and what it is not")
    d.body("1.1  This instrument is **not** a loan. It carries **no interest** and **no maturity "
           "date on which money must be repaid**.")
    d.body("1.2  This instrument is **not** currently equity. The Investor is **not** a "
           "shareholder or member, has **no voting rights**, and holds **no ownership interest** "
           "in the Company unless and until this instrument converts under Section 2.")
    d.body("1.3  The Investor acknowledges the Company has told them, in writing, that this "
           "instrument may **never** convert, in which case the Investor may receive **nothing**.")
    d.callout("info", "WHY 1.3 IS IN HERE",
              "The SEC's own bulletin warns that triggers may never activate, \"leaving you with "
              "nothing.\" Putting that in the document, in plain sight, is both fair dealing and "
              "your best protection against a later claim that the risk was not disclosed.")

    d.h3("2.  How it turns into ownership (Conversion Events)")
    d.body("2.1  **Equity Financing.** If the Company closes a priced round of Equity Securities "
           "raising at least the Qualifying Amount below, this instrument automatically converts "
           "into Equity Securities of that round. The conversion price is the **lower** of "
           "(a) the price implied by the Post-Money Valuation Cap, and (b) the round price less "
           "the Discount Rate.")
    d.field_row([("Qualifying Amount (minimum round size)", "sf_qual", 220),
                 ("Conversion share class", "sf_class", 200)])
    d.body("2.2  **Liquidity Event.** On a change of control, sale of substantially all assets, "
           "or public listing, the Investor receives, at their election, either "
           "(a) the Purchase Amount back, or (b) the value they would receive had this "
           "instrument converted at the Post-Money Valuation Cap immediately prior.")
    d.body("2.3  **Dissolution.** If the Company winds up, the Investor is entitled to the "
           "Purchase Amount back, ranking **ahead of** holders of common equity and **behind** "
           "all creditors, to the extent assets remain.")

    d.callout("warn", "NON-STANDARD CLAUSE 2.4 - THIS IS THE FIX FOR THE RESEARCH FINDING",
              "Coyle and Green's central finding is that SAFEs fail when the issuer **never "
              "raises institutional venture capital** - the trigger simply never fires. For a "
              "govtech company funded by contracts and SBIR rather than VC, that is not an edge "
              "case; it is the likely path. Clause 2.4 gives the instrument a way to resolve "
              "**without** a priced round. It is non-standard. Some investors will like it "
              "because it removes their worst outcome. Some will resist it. **Discuss it with "
              "counsel deliberately - do not delete it silently.**")
    d.body("2.4  **Backstop Conversion Date.** If no event in 2.1 to 2.3 has occurred by the "
           "Backstop Date below, the Investor may, by written notice, elect to convert this "
           "instrument into Equity Securities of the Company at the Post-Money Valuation Cap, "
           "on the Company's then-existing terms for its most senior class of equity.")
    d.field_row([("Backstop Date", "sf_backstop", 160),
                 ("Notice window (days)", "sf_notice", 140),
                 ("Governing valuation basis", "sf_basis", 170)])
    d.body("2.5  **Optional Company Repurchase.** At any time before conversion, the Company "
           "may, at its sole option and subject to legally available funds, repurchase this "
           "instrument for the Purchase Amount multiplied by the Repurchase Multiple below. "
           "This is an option of the Company, **not** an obligation, and **not** a debt.")
    d.field_row([("Repurchase Multiple", "sf_mult", 150),
                 ("Earliest repurchase date", "sf_repdate", 180)])
    d.callout("law", "WHY 2.5 EXISTS AND WHY IT NEEDS COUNSEL",
              "A repurchase option gives a profitable, non-VC-track company a clean way to "
              "retire the instrument from cash flow - which fits a stewardship-driven, "
              "ownership-preserving business far better than an unresolved instrument sitting "
              "on the balance sheet indefinitely. **But:** a repayment-like feature can push a "
              "SAFE toward being characterised as debt, with consequences for tax and for "
              "investor protections. This clause is exactly the kind of thing Call 2 in Part 2 "
              "exists for.")

    d.h3("3.  Company representations")
    d.body("3.1  The Company is duly organised, validly existing, and in good standing in its "
           "state of formation.")
    d.body("3.2  Execution of this instrument has been duly authorised and does not conflict "
           "with the Company's governing documents or any material agreement - **including any "
           "intellectual property licence on which the Company's business depends.**")
    d.body("3.3  The Company will deliver to the Investor, at least annually, an unaudited "
           "statement of financial position and a capitalisation summary.")

    d.h3("4.  Investor representations")
    d.body("4.1  The Investor is acquiring this instrument for their **own account**, for "
           "investment, and not with a view to distribution.")
    d.body("4.2  The Investor is an **accredited investor** as defined under Regulation D, and "
           "will provide the Company with information reasonably requested to establish this.")
    d.body("4.3  The Investor can bear the **complete loss** of the Purchase Amount.")
    d.body("4.4  The Investor has had the opportunity to ask questions of the Company and to "
           "consult their own legal, tax and financial advisers.")
    d.check("Accredited investor status established and **documented in the file**.", "sf_acc")
    d.check("Investor received the risk disclosure in Section 1.3 **in writing**.", "sf_risk")

    d.h3("5.  Transfer restrictions")
    d.body("5.1  This instrument may **not** be transferred without the Company's prior written "
           "consent, except to the Investor's affiliates or by operation of law.")
    d.callout("do", "KEEP THIS CLAUSE TIGHT",
              "Transfer control is how you keep your cap table clean, keep your fully-diluted "
              "ownership analysis knowable, and avoid waking up affiliated with someone you "
              "never chose. Do not soften this clause to close a deal.")

    d.h3("6.  What is deliberately NOT in this document")
    d.body("The following are **intentionally absent**, for the reasons given in Landmine 3:")
    d.bullet("**No investor consent or veto rights** over budgets, hiring, debt, or sale.")
    d.bullet("**No board seat and no board observer seat.**")
    d.bullet("**No control over ordinary-course operations.**")
    d.callout("stop", "IF AN INVESTOR ASKS FOR ANY OF THESE, STOP",
              "Under SBA's affiliation rules, the **power** to control is enough - it does not "
              "have to be exercised. Negative control is control. Granting a veto may make that "
              "investor's company your affiliate, and may cost you your small business status "
              "and every set-aside contract that depends on it. **Price that against the cheque "
              "before you agree.** This is a term worth losing a deal over.")

    d.h3("7.  General")
    d.body("7.1  Governing law: the laws of the state named below, without regard to conflicts "
           "of law principles.")
    d.body("7.2  This instrument is the entire agreement between the parties on this subject and "
           "may be amended only in a writing signed by both.")
    d.body("7.3  This instrument may be executed in counterparts, including electronically.")
    d.field_row([("Governing law - state", "sf_law", 170),
                 ("Dispute venue", "sf_venue", 180),
                 ("Side letter? Y/N", "sf_side", 110)])

    d.h2("Signatures", "\U0000270D")
    d.body("**Do not sign this version.** Sign the version your attorney has reviewed and "
           "returned. These blocks exist so you can circulate a complete-looking draft for "
           "comment.")
    d.gap(2)
    d.h3("COMPANY")
    d.sigline("Authorised signature", "sig_co")
    d.field_row([("Print name", "sig_co_name", 200), ("Title", "sig_co_title", 150),
                 ("Date", "sig_co_date", 110)])
    d.gap(2)
    d.h3("INVESTOR")
    d.sigline("Signature", "sig_inv")
    d.field_row([("Print name", "sig_inv_name", 200), ("Title / capacity", "sig_inv_title", 150),
                 ("Date", "sig_inv_date", 110)])


# =====================================  PART 9 - CHECKLISTS
def part9(d):
    d.part_cover("check", 9, "Checklists and trackers",
                 "Everything open, in one place, in a fixed order. Tick it and it is closed.",
                 "\U00002705")

    d.h2("Securities compliance - do not skip a single line", "\U00002696")
    d.callout("law", "THE THING FOUNDERS FORGET",
              "**A SAFE is a security.** Selling one means complying with federal and state "
              "securities law. This is not paperwork you can do afterwards - the exemption you "
              "rely on constrains **how you are allowed to talk about the raise** from the very "
              "first conversation.")
    d.h3("Choose your exemption before you speak to anyone")
    d.table(["", "Rule 506(b)", "Rule 506(c)"],
            [["Amount you can raise", "Unlimited", "Unlimited"],
             ["**General solicitation**",
              "**Not permitted.** No public advertising of the raise.",
              "**Permitted.** You may advertise."],
             ["Who may invest",
              "Unlimited accredited investors, plus up to **35** non-accredited "
              "**sophisticated** investors in any 90-day period.",
              "**Accredited investors only.**"],
             ["Verification burden",
              "Issuer needs a **reasonable belief** the investor is accredited.",
              "Issuer must take **reasonable steps to verify** - e.g. IRS forms for income, "
              "documentation dated within the prior 3 months for net worth, or written "
              "confirmation from a registered broker-dealer, SEC-registered investment adviser, "
              "licensed attorney, or CPA."]],
            [104, 196, CONTENT_W - 300])
    tag(d, "gov")
    d.callout("warn", "THE TRAP IN ONE SENTENCE",
              "If you choose **506(b)** and then post \"we're raising\" on social media, at a "
              "demo day, or in a newsletter, **you may have blown the exemption**. Decide "
              "first. Then brief everyone who speaks for the company.")
    d.check("**Exemption chosen** and written down before any investor conversation.", "sc_ex")
    d.check("Everyone who speaks for the company has been briefed on the solicitation rule.", "sc_brief")
    d.check("**Form D filed within 15 days after the first sale.** No SEC filing fee.", "sc_formd")
    d.check("**State notice filings and fees** handled. NSMIA preempts state *registration* for "
            "Rule 506 covered securities, but states keep **anti-fraud authority** and may "
            "require notice filings and fees.", "sc_state")
    d.check("Accreditation evidence **collected and filed** for every investor.", "sc_accfile")
    d.check("Written risk disclosure delivered to every investor.", "sc_disc")
    d.check("Asked counsel about **disqualification provisions** applicable to the offering.", "sc_bad")
    d.field_row([("Exemption relied on", "sc_which", 150), ("First sale date", "sc_first", 130),
                 ("Form D due", "sc_due", 130)])

    d.h2("Before you take the first dollar", "\U0001F6A6")
    d.check("Attorney call complete; holdco ownership-chain question answered **in writing**.", "b_1")
    d.check("CPA call complete; LLC vs C-corp decision made on modelled numbers.", "b_2")
    d.check("Entity conversion executed, **if** that was the decision.", "b_3")
    d.check("IP licence terms documented and the **termination problem** resolved.", "b_4")
    d.check("Money Map complete; ceiling computed; raise size = smaller of need and ceiling.", "b_5")
    d.check("Fully-diluted model shows U.S.-individual ownership **above my floor**, "
            "option pool included.", "b_6")
    d.check("SAFE reviewed and returned by counsel.", "b_7")
    d.check("Exemption chosen; Form D calendared.", "b_8")
    d.check("**No consent rights, no board seats, no vetoes** in any document or side letter.", "b_9")
    d.check("SAM.gov registration active; renewal reminder set with a named owner.", "b_10")

    d.h2("Investor pipeline", "\U0001F91D")
    d.table(["Name", "Amount", "Accredited?", "Docs sent", "Signed", "Funds in"],
            [["", "", "", "", "", ""] for _ in range(8)],
            [150, 78, 84, 78, 70, CONTENT_W - 460], row_h=20)

    d.h2("Data room - what investors will ask for", "\U0001F4C1")
    for lbl in ["Formation documents and operating agreement / bylaws",
                "Cap table, fully diluted, including all convertible instruments",
                "**The IP licence agreement** - they will read this one closely",
                "IP schedule: patents, applications, trademarks, key trade secrets",
                "Financial statements and current monthly burn",
                "Customer or pilot agreements, letters of intent, and any past performance",
                "SAM.gov registration confirmation and UEI",
                "Any SBIR/STTR awards, submissions, or debriefs",
                "Key employee and contractor agreements, with IP assignment clauses",
                "Insurance certificates"]:
        d.check(lbl, None)
    d.callout("warn", "THE IP ASSIGNMENT LINE IS NOT FILLER",
              "If any developer, contractor, or co-founder ever wrote code without a signed IP "
              "assignment, the company may not own what it thinks it owns. That is a "
              "deal-ending discovery in diligence and a genuine risk to a federal contract "
              "where you certify rights to perform. **Audit this before an investor does.**")


# =====================================  GLOSSARY
def glossary(d):
    d.part_cover("gloss", 10, "Glossary",
                 "Every term in this document, in plain words. No shame in using it.",
                 "\U0001F4D6")
    terms = [
        ("Accredited investor", "A person or entity meeting SEC income, net worth, or "
         "professional-credential tests, permitted to buy in private offerings."),
        ("Affiliation", "SBA's test for whether two businesses count as one. Turns on control, "
         "or the **power** to control, exercised or not."),
        ("Blue sky laws", "State securities laws. NSMIA preempts state registration for Rule 506 "
         "covered securities, but states keep anti-fraud authority and may require notice filings."),
        ("CAGE code", "Commercial and Government Entity code. An identifier assigned during "
         "federal registration."),
        ("Cap (valuation cap)", "The highest company valuation at which an investor's money will "
         "convert. Lower cap = investor gets more."),
        ("Conversion event", "The specific trigger that turns a SAFE into actual ownership. If "
         "it never happens, the SAFE may never convert."),
        ("C corporation", "A corporation taxed separately from its owners. Required for QSBS "
         "under IRC Section 1202. Issues stock."),
        ("Discount", "A percentage off the next round's price, given to the SAFE holder."),
        ("Dilution", "Your ownership percentage shrinking as new equity is issued."),
        ("Form 8832", "IRS Entity Classification Election - how an LLC elects to be taxed as a "
         "corporation. Effective date limits: no more than 75 days before, or 12 months after, filing."),
        ("Form D", "Brief SEC notice filed within **15 days after the first sale** in a "
         "Regulation D offering. No SEC filing fee."),
        ("Fully diluted", "Counting all shares as if every convertible instrument and option had "
         "already converted. **This is how SBA reviews SBIR ownership.**"),
        ("General solicitation", "Publicly advertising a securities offering. Forbidden under "
         "Rule 506(b); allowed under 506(c) if all buyers are verified accredited."),
        ("Government purpose rights", "Rights the government obtains in SBIR data after the "
         "protection period expires. They do not expire."),
        ("HUBZone", "SBA program for firms with a principal office in a designated zone that "
         "employ residents of such zones."),
        ("K-1 (Schedule K-1)", "The tax form a pass-through entity issues to its owners. A "
         "reason many institutional investors avoid LLCs."),
        ("LLC", "Limited liability company. Issues **membership units**, not stock. Default tax "
         "treatment is disregarded (single member) or partnership (multi-member)."),
        ("MAS (Multiple Award Schedule)", "GSA's long-term governmentwide contract. Combined with "
         "Cooperative Purchasing, it lets state and local governments buy from it."),
        ("MFN", "Most Favoured Nation. If you later give better terms to someone else, this "
         "investor automatically gets them too."),
        ("Micro-purchase threshold", "The federal purchase level with the lowest procedural "
         "burden. **Increased to $15,000 effective 1 October 2025.**"),
        ("NAICS code", "Industry classification code. Determines which SBA size standard applies "
         "to you and which solicitations you match."),
        ("Non-dilutive funding", "Money received without giving up ownership. Grants, SBIR/STTR "
         "awards, and revenue. **The best kind.**"),
        ("Post-money SAFE", "A SAFE where the investor's percentage is fixed at signing: "
         "investment divided by the post-money cap. Later SAFEs dilute **you**, not them."),
        ("Pro rata right", "The right, not the obligation, to invest again later to maintain "
         "percentage ownership. Usually in a side letter."),
        ("QSBS / Section 1202", "Qualified small business stock. Requires a **C corporation**, "
         "original issuance, and a holding period of **more than five years**."),
        ("Rule of Two", "FAR 19.502-2. An acquisition is set aside for small business when offers "
         "are reasonably expected from **two or more** responsible small business concerns."),
        ("SAFE", "Simple Agreement for Future Equity. An agreement to provide equity later if a "
         "trigger fires. Not stock. Not a loan. Not necessarily safe."),
        ("SAM.gov", "The federal registration system. Source of the UEI. **Renew every 365 days.**"),
        ("SBIR / STTR", "Federal non-dilutive R&D funding across 11 agencies. Phase I proves "
         "feasibility; Phase II builds; Phase III commercialises and may be **sole-sourced**."),
        ("Side letter", "A separate agreement alongside the SAFE. **Where control rights hide.** "
         "Read it as carefully as the SAFE itself."),
        ("Simplified acquisition threshold", "The ceiling for streamlined federal buying "
         "procedures. **Verify the current figure - my sources conflicted.**"),
        ("Sole source", "An award made without full competition. SBIR Phase III has explicit "
         "statutory backing for this, under 15 U.S.C. 638(r)(4)."),
        ("UEI", "Unique Entity Identifier. A 12-character alphanumeric value from SAM.gov. "
         "Required before bidding."),
        ("VPFC", "Variable prepaid forward contract - one of the competing tax characterisations "
         "of a SAFE. **Unsettled.**"),
    ]
    d.table(["Term", "What it means"], [[("**%s**" % t), v] for t, v in terms],
            [140, CONTENT_W - 140])


# =====================================  REFERENCES
def ref(d, text, url):
    """APA entry with hanging indent and a full, wrapped, clickable URL."""
    size = 8.8
    lines = wrap_runs(parse_runs(text), CONTENT_W - 16, size)

    # split the URL across as many lines as needed - never truncate it
    avail = CONTENT_W - 16
    url_lines, rest = [], url
    while rest:
        cut = len(rest)
        while cut > 1 and pdfmetrics.stringWidth(rest[:cut], F_MONO, 7.6) > avail:
            cut -= 1
        url_lines.append(rest[:cut])
        rest = rest[cut:]

    need = len(lines) * 11.6 + len(url_lines) * 10.2 + U * 3
    d.ensure(need)
    for i, ln in enumerate(lines):
        d._line(ln, ML + (0 if i == 0 else 16), d.y - size, size, BODY)
        d.y -= 11.6
    d.c.setFont(F_MONO, 7.6)
    d.c.setFillColor(HexColor("#1D4ED8"))
    for ul in url_lines:
        d.c.drawString(ML + 16, d.y - 7.6, ul)
        w = pdfmetrics.stringWidth(ul, F_MONO, 7.6)
        try:
            d.c.linkURL(url, (ML + 16, d.y - 10, ML + 16 + w, d.y + 0.5),
                        relative=0, thickness=0)
        except Exception:
            pass
        d.y -= 10.2
    d.y -= U * 2


def references(d):
    d.part_cover("ref", 11, "References",
                 "APA 7th style. Every link live. Verify anything you plan to act on.",
                 "\U0001F4DA")

    d.callout("truth", "HOW TO READ THIS LIST - AND ONE LIMITATION YOU SHOULD KNOW",
              "Every source below was **actually retrieved during this research session**. None "
              "were recalled from memory.\n\n"
              "**The limitation:** this environment's network policy blocked full-document "
              "access to sec.gov, sba.gov, sbir.gov, ecfr.gov, investor.gov and one law review "
              "server. I retrieved substantive extracts of those real documents through search, "
              "but I could **not** read the underlying regulations end to end. That is why "
              "regulatory citations in this document say \"verify at source.\" It is a real "
              "constraint, not a disclaimer. **Open the links before you act on any of it.**")

    d.h2("Peer-reviewed and scholarly sources", "\U0001F393")
    ref(d, "Coyle, J. F., & Green, J. M. (2018). The SAFE, the KISS, and the note: A survey of "
           "startup seed financing contracts. *Minnesota Law Review Headnotes, 103*, 42. "
           "[Empirical: survey of 300+ startup lawyers across 32 U.S. states and 4 Canadian "
           "provinces, conducted with Thomson Reuters Practical Law.]",
        "https://www.minnesotalawreview.org/wp-content/uploads/2019/02/Coyle_Final.pdf")
    ref(d, "Green, J. M., & Coyle, J. F. (2016). Crowdfunding and the not-so-safe SAFE. "
           "*Virginia Law Review Online, 102*, 168. [The finding this playbook's Clause 2.4 "
           "responds to.]",
        "https://virginialawreview.org/articles/crowdfunding-and-not-so-safe-safe/")
    ref(d, "Green, J. M., & Coyle, J. F. (2016). Crowdfunding and the not-so-safe SAFE "
           "[Preprint]. *SSRN*. Abstract no. 2830213.",
        "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2830213")
    ref(d, "Coyle, J. F., & Green, J. M. (2020). Contract as swag. *Penn State Law Review, "
           "124*(2), 353.",
        "https://www.pennstatelawreview.org/wp-content/uploads/2020/04/2-Coyle-Green-Contract-as-Swag.pdf")
    ref(d, "Polsky Center for Entrepreneurship and Innovation. (2023). *Simple agreement for "
           "future equity: FAQ*. University of Chicago. [Institutional guidance, not "
           "peer-reviewed.]",
        "https://polsky.uchicago.edu/wp-content/uploads/2024/03/Polsky-SAFE-FAQ-10-31-23.pdf")

    d.h2("U.S. Securities and Exchange Commission", "\U0001F3DB")
    ref(d, "U.S. Securities and Exchange Commission, Office of Investor Education and Advocacy. "
           "(n.d.). *Investor bulletin: Be cautious of SAFEs in crowdfunding*. Investor.gov.",
        "https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-52")
    ref(d, "U.S. Securities and Exchange Commission. (n.d.). *Exempt offerings*.",
        "https://www.sec.gov/resources-small-businesses/exempt-offerings")
    ref(d, "U.S. Securities and Exchange Commission. (n.d.). *Private placements - Rule 506(b)*.",
        "https://www.sec.gov/resources-small-businesses/exempt-offerings/private-placements-rule-506b")
    ref(d, "U.S. Securities and Exchange Commission. (n.d.). *General solicitation - Rule 506(c)*.",
        "https://www.sec.gov/resources-small-businesses/exempt-offerings/general-solicitation-rule-506c")
    ref(d, "U.S. Securities and Exchange Commission. (n.d.). *Assessing accredited investors "
           "under Regulation D*.",
        "https://www.sec.gov/resources-small-businesses/capital-raising-building-blocks/assessing-accredited-investors-under-regulation-d")
    ref(d, "U.S. Securities and Exchange Commission. (n.d.). *Regulation crowdfunding: A small "
           "entity compliance guide for issuers*.",
        "https://www.sec.gov/resources-small-businesses/small-business-compliance-guides/regulation-crowdfunding-small-entity-compliance-guide-issuers")
    ref(d, "U.S. Securities and Exchange Commission. (2020, November 2). *SEC harmonizes and "
           "improves \"patchwork\" exempt offering framework* (Press Release No. 2020-273).",
        "https://www.sec.gov/newsroom/press-releases/2020-273")
    ref(d, "U.S. Securities and Exchange Commission. (n.d.). *Form D*.",
        "https://www.sec.gov/files/formd.pdf")

    d.h2("Small Business Administration, SBIR/STTR, and size regulations", "\U0001F4BC")
    ref(d, "Small Business Size Regulations, 13 C.F.R. § 121.103 (n.d.). *How does SBA determine "
           "affiliation?* Electronic Code of Federal Regulations.",
        "https://www.ecfr.gov/current/title-13/chapter-I/part-121/subpart-A/subject-group-ECFRd133f03f6d8398b/section-121.103")
    ref(d, "Small Business Size Regulations, 13 C.F.R. § 121.702 (n.d.). *What size and "
           "eligibility standards are applicable to the SBIR and STTR programs?* Electronic Code "
           "of Federal Regulations.",
        "https://www.ecfr.gov/current/title-13/chapter-I/part-121/subpart-A/subject-group-ECFRb7921b3fcf04228/section-121.702")
    ref(d, "Small Business Administration. (n.d.). *SBIR/STTR eligibility requirements* [FAQ]. "
           "SBIR.gov.", "https://www.sbir.gov/faq/eligibility-requirements")
    ref(d, "Small Business Administration. (n.d.). *About SBIR and STTR*. SBIR.gov.",
        "https://www.sbir.gov/about")
    ref(d, "Small Business Administration. (n.d.). *What makes Phase III so valuable?* "
           "[Data rights tutorial 4]. SBIR.gov.",
        "https://www.sbir.gov/tutorials/data-rights/tutorial-4")
    ref(d, "Small Business Administration. (n.d.). *SBIR data rights* [Tutorial series]. SBIR.gov.",
        "https://www.sbir.gov/tutorials/data-rights")
    ref(d, "Small Business Administration. (n.d.). *Guide to SBIR/STTR program eligibility and "
           "size compliance*. SBIR.gov.",
        "https://www.sbir.gov/sites/default/files/elig_size_compliance_guide.pdf")
    ref(d, "Small Business Administration. (2019). *SBIR/STTR policy directive*. SBIR.gov.",
        "https://www.sbir.gov/sites/default/files/SBIR-STTR_Policy_Directive_2019.pdf")
    ref(d, "Small Business Administration. (n.d.). *Basic requirements for federal contracting*.",
        "https://www.sba.gov/federal-contracting/contracting-guide/basic-requirements")
    ref(d, "Small Business Administration. (n.d.). *Size standards*.",
        "https://www.sba.gov/federal-contracting/contracting-guide/size-standards")
    ref(d, "Small Business Administration. (n.d.). *Table of size standards*.",
        "https://www.sba.gov/document/support-table-size-standards")
    ref(d, "Small Business Administration. (n.d.). *SBA business certifications: 8(a), WOSB, "
           "HUBZone, SDVOSB*.", "https://www.sba.gov/certifications/")

    d.h2("Federal acquisition and registration", "\U0001F4DC")
    ref(d, "General Services Administration. (n.d.). *Entity registration*. SAM.gov.",
        "https://sam.gov/entity-registration")
    ref(d, "Federal Acquisition Regulation, 48 C.F.R. § 2.101 (n.d.). *Definitions*. "
           "Acquisition.gov.", "https://www.acquisition.gov/far/2.101")
    ref(d, "Federal Acquisition Regulation, 48 C.F.R. § 19.502-2 (n.d.). *Total small business "
           "set-asides*. Acquisition.gov.", "https://www.acquisition.gov/far/19.502-2")
    ref(d, "Federal Acquisition Regulation, 48 C.F.R. § 52.227-20 (n.d.). *Rights in data - SBIR "
           "program*. Acquisition.gov.", "https://www.acquisition.gov/far/52.227-20")
    ref(d, "Defense Federal Acquisition Regulation Supplement, 48 C.F.R. § 252.227-7018 (n.d.). "
           "*Rights in other than commercial technical data and computer software - SBIR/STTR*.",
        "https://www.acquisition.gov/dfars/252.227-7018-rights-other-commercial-technical-data-and-computer-software%E2%80%94small-business-innovation-research-program-and-small-business-technology-transfer-program.")
    ref(d, "General Services Administration. (n.d.). *Threshold changes - October 1st, 2025*. "
           "Acquisition.gov. **[Verify the simplified acquisition threshold here - sources "
           "conflicted.]**", "https://www.acquisition.gov/threshold-changes")
    ref(d, "Office of Federal Procurement Policy, Department of Defense, General Services "
           "Administration, & National Aeronautics and Space Administration. (2025, August 27). "
           "*Federal Acquisition Regulation: Inflation adjustment of acquisition-related "
           "thresholds* (FR Doc. 2025-16412). *Federal Register, 90*(164).",
        "https://www.federalregister.gov/documents/2025/08/27/2025-16412/federal-acquisition-regulation-inflation-adjustment-of-acquisition-related-thresholds")
    ref(d, "General Services Administration. (2025). *Effective October 1, 2025, FAR amendment: "
           "Micro-purchase threshold limit increased to $15,000* (Smart Bulletin No. 002). "
           "GSA SmartPay.", "https://smartpay.gsa.gov/guidance-and-audits/smart-bulletins/002/")
    ref(d, "General Services Administration. (n.d.). *Multiple Award Schedule*.",
        "https://www.gsa.gov/buy-through-us/purchasing-programs/multiple-award-schedule")

    d.h2("Internal Revenue Service and tax authority", "\U0001F4B5")
    ref(d, "Internal Revenue Service. (n.d.). *About Form 8832, entity classification election*.",
        "https://www.irs.gov/forms-pubs/about-form-8832")
    ref(d, "Internal Revenue Service. (n.d.). *LLC filing as a corporation or partnership*.",
        "https://www.irs.gov/businesses/small-businesses-self-employed/llc-filing-as-a-corporation-or-partnership")
    ref(d, "Internal Revenue Service. (2020). *Publication 3402: Taxation of limited liability "
           "companies*.", "https://www.irs.gov/publications/p3402")
    ref(d, "Partial exclusion for gain from certain small business stock, 26 U.S.C. § 1202. "
           "U.S. Government Publishing Office.",
        "https://www.govinfo.gov/content/pkg/USCODE-2022-title26/pdf/USCODE-2022-title26-subtitleA-chap1-subchapP-partI-sec1202.pdf")

    d.h2("Bureau of Labor Statistics - survival base rates", "\U0001F4CA")
    ref(d, "U.S. Bureau of Labor Statistics. (n.d.). *Table 7. Survival of private sector "
           "establishments by opening year*. Business Employment Dynamics.",
        "https://www.bls.gov/bdm/us_age_naics_00_table7.txt")
    ref(d, "U.S. Bureau of Labor Statistics. (2024). *Business Employment Dynamics twentieth "
           "anniversary* [Spotlight on Statistics].",
        "https://www.bls.gov/spotlight/2024/business-employment-dynamics-twentieth-anniversary/home.htm")
    ref(d, "U.S. Bureau of Labor Statistics. (2024). *1-year survival rates for new business "
           "establishments by year and location*. The Economics Daily.",
        "https://www.bls.gov/opub/ted/2024/1-year-survival-rates-for-new-business-establishments-by-year-and-location.htm")

    d.h2("Primary instrument source", "\U0001F4C4")
    ref(d, "Y Combinator. (n.d.). *The SAFE: The open standard for startup fundraising* "
           "[Document set]. [Cited only as the authoritative location of the instrument itself. "
           "Not relied upon for any empirical or legal claim in this document.]",
        "https://www.ycombinator.com/documents")

    # ---------------- integrity footer
    d.new_page()
    d.h2("Evidence integrity statement", "\U0001F9ED")
    d.body("**What is grounded.** Every regulatory and statistical claim in this document traces "
           "to a named government document or peer-reviewed source listed above, retrieved during "
           "this session.")
    d.body("**What is inference.** The strategic recommendations - raise into the operating "
           "company rather than the holdco; sequence non-dilutive funding ahead of equity; cap "
           "the raise using the fully-diluted ownership formula; widen the SAFE's conversion "
           "triggers - are **my reasoning from those sources**, labelled as inference throughout. "
           "They are not quotations and they are not legal opinions.")
    d.body("**What is assumption.** Every dollar figure in the Part 4 worked example is invented "
           "for arithmetic demonstration and labelled as such. The $8,000,000 valuation cap is "
           "**not** a valuation of Forgelink.")
    d.body("**What is unknown, and stayed unknown.** The current simplified acquisition "
           "threshold (three government sources conflicted). The tax characterisation of a SAFE "
           "(genuinely unsettled). Whether the Wyoming holdco ownership chain satisfies the "
           "direct-ownership requirement. Whether Forgelink qualifies for any socioeconomic "
           "certification. Every fact about Forgelink's actual finances, cap table, and "
           "contracts. **None of these were filled with a guess.**")
    d.body("**What was excluded on principle.** You set a source standard of peer-reviewed "
           "scholarship and government primary sources. Current SAFE valuation-cap benchmark "
           "data exists, but it is published by private cap-table vendors - proprietary and not "
           "peer-reviewed. **It does not meet your standard, so I did not use it**, and Part 4 "
           "says so plainly rather than quietly lowering the bar.")
    d.callout("truth", "CALIBRATED CONFIDENCE",
              "**High confidence:** that a SAFE is a security; that SBIR ownership is assessed "
              "fully diluted; that affiliation turns on the power to control; that Phase III "
              "carries sole-source authority; that QSBS requires a C corporation.\n\n"
              "**Medium confidence:** the specific structuring recommendations, which depend on "
              "facts about your entities that I do not have.\n\n"
              "**Low confidence / not asserted:** any specific dollar threshold I flagged as "
              "conflicting, and the tax treatment of the instrument.\n\n"
              "**For every legal, tax, and regulatory item in this document: professional "
              "verification required.**")
    d.rule()
    d.body("*Prepared 14 September 2026. This document is a planning aid. It is not legal, tax, "
           "or investment advice, and no attorney-client or advisory relationship is created by "
           "it.*", size=8.6, color=MUTED)


# =====================================  MAIN
def build(path, collect_only=False, toc=None):
    d = Doc(path, collect_only=collect_only, toc=toc)
    cover(d)
    how_to_use(d)
    toc_render(d)
    for fn in (part1, part2, part3, part4, part5, part6, part7, part8, part9,
               glossary, references):
        fn(d)
    d.save()
    return d


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "output/Forgelink-SAFE-Playbook.pdf"
    tmp = "/tmp/claude-0/-home-user-forge-talent-connections/13fb280a-0bf6-5fdb-ba22-6095b6418d47/scratchpad/_pass1.pdf"
    p1 = build(tmp, collect_only=True)
    d2 = build(out, collect_only=False, toc=p1.toc_entries)
    print("PAGES: %d   FORM FIELDS: %d   TOC ENTRIES: %d"
          % (d2.page - 1, d2.field_count, len(p1.toc_entries)))
