import re, sys, copy
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak,
                                Table, TableStyle, KeepTogether, Preformatted, Flowable)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

EDITION = __import__("os").environ.get("NA_EDITION", "tablet")
EMO = "/home/claude/emoji"

pdfmetrics.registerFont(TTFont("DV", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVM", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")

# ---------------------------------------------------------------- editions
CFG = {
    "mobile": dict(PW=4.5 * inch, PH=9.5 * inch, ML=0.3 * inch, MR=0.3 * inch, MT=1.08 * inch, MB=0.5 * inch,
                   body=9.8, row=9.8, h1=15.5, h2=11.5, mono=6.2, chk=20, field=27, band=0.6 * inch,
                   out="/mnt/user-data/outputs/night_agent_v11/WORKBOOKS/Night_Agent_v11_Workbook_Mobile.pdf", label="MOBILE edition"),
    "tablet": dict(PW=8.5 * inch, PH=11 * inch, ML=0.62 * inch, MR=0.62 * inch, MT=1.5 * inch, MB=0.7 * inch,
                   body=12.2, row=12.2, h1=22, h2=15, mono=8.6, chk=26, field=36, band=0.85 * inch,
                   out="/mnt/user-data/outputs/night_agent_v11/WORKBOOKS/Night_Agent_v11_Workbook_Tablet_Desktop.pdf", label="TABLET / DESKTOP edition"),
}[EDITION]
PW, PH, ML, MR, MT, MB = CFG["PW"], CFG["PH"], CFG["ML"], CFG["MR"], CFG["MT"], CFG["MB"]
CW = PW - ML - MR
CHK = CFG["chk"]
FH = CFG["field"]

# ---------------------------------------------------------------- semantic palette (dark, light)
C = {
    "blue": ("#1E40AF", "#DBEAFE"),     # instructions / information
    "green": ("#166534", "#DCFCE7"),    # completed / verified / passed
    "yellow": ("#854D0E", "#FEF3C7"),   # attention / judgement / needs review
    "orange": ("#C2410C", "#FFEDD5"),   # blocked / unresolved
    "red": ("#B91C1C", "#FEE2E2"),      # stop / failed / safety-critical
    "purple": ("#6B21A8", "#F3E8FF"),   # feedback / special review
    "gray": ("#374151", "#F3F4F6"),     # supporting information
}
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#4B5563")
WHITE = colors.white


def hx(k, i=0):
    return colors.HexColor(C[k][i])


# ---------------------------------------------------------------- styles
def ps(name, **kw):
    base = dict(fontName="DV", fontSize=CFG["body"], leading=CFG["body"] * 1.36, textColor=INK, spaceAfter=3)
    base.update(kw)
    return ParagraphStyle(name, **base)


S = {
    "title": ps("title", fontName="DVB", fontSize=CFG["h1"] * 1.5, leading=CFG["h1"] * 1.7, spaceAfter=4),
    "h1": ps("h1", fontName="DVB", fontSize=CFG["h1"], leading=CFG["h1"] * 1.2, spaceBefore=2, spaceAfter=5),
    "h2": ps("h2", fontName="DVB", fontSize=CFG["h2"], leading=CFG["h2"] * 1.25, spaceBefore=8, spaceAfter=4),
    "body": ps("body"),
    "lead": ps("lead", fontSize=CFG["body"] * 1.15, leading=CFG["body"] * 1.55, spaceAfter=6),
    "small": ps("small", fontSize=CFG["body"] * 0.84, leading=CFG["body"] * 1.1, textColor=MUTED, spaceAfter=3),
    "tiny": ps("tiny", fontSize=CFG["body"] * 0.74, leading=CFG["body"] * 0.95, textColor=MUTED, spaceAfter=0),
    "label": ps("label", fontName="DVB", fontSize=CFG["body"] * 0.78, leading=CFG["body"] * 0.98, textColor=MUTED, spaceAfter=2),
    "row": ps("row", fontSize=CFG["row"], leading=CFG["row"] * 1.27, spaceAfter=0),
    "rowsmall": ps("rowsmall", fontSize=CFG["row"] * 0.82, leading=CFG["row"] * 1.02, textColor=MUTED, spaceAfter=0),
    "mono": ps("mono", fontName="DVM", fontSize=CFG["mono"], leading=CFG["mono"] * 1.26, spaceAfter=0),
    "white": ps("white", fontName="DVB", fontSize=CFG["body"] * 1.08, leading=CFG["body"] * 1.35, textColor=WHITE, spaceAfter=0),
    "tag": ps("tag", fontName="DVB", fontSize=CFG["body"] * 0.68, leading=CFG["body"] * 0.8, textColor=WHITE, spaceAfter=0),
}

story = []
_names = {}
_section = ["start"]


def slug(t):
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_").lower()
    return t[:34].rstrip("_")


def fname(label, kind):
    base = f"{_section[0]}_{slug(label) or kind}"
    n = _names.get(base, 0) + 1
    _names[base] = n
    return base if n == 1 else f"{base}_{n}"


def E(code, size=None, dy=-3):
    size = size or CFG["body"] * 1.25
    return f'<img src="{EMO}/{code}.png" width="{size}" height="{size}" valign="{dy}"/>'


def P(text, style="body"):
    story.append(Paragraph(text, S[style]))


def H1(text, emoji=None):
    if emoji:
        text = E(emoji, CFG["h1"] * 1.05, -4) + " " + text
    story.append(Paragraph(text, S["h1"]))


def H2(text, emoji=None, color=None):
    if emoji:
        text = E(emoji, CFG["h2"] * 1.05, -3) + " " + text
    st = S["h2"] if not color else ParagraphStyle("h2c", parent=S["h2"], textColor=hx(color))
    story.append(Paragraph(text, st))


def SP(h=6):
    story.append(Spacer(1, h))


def PB():
    story.append(PageBreak())


# ---------------------------------------------------------------- header / journey machinery
JOURNEY = ["GATE", "GENERATE", "OPERATE", "REVIEW", "FINAL+VERIFY", "MORNING"]


class SetStage(Flowable):
    def __init__(self, section, emoji, color, sub, journey, nxt, prefix):
        Flowable.__init__(self)
        self.v = (section, emoji, color, sub, journey, nxt)
        self.prefix = prefix

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        self.canv._stage = self.v


class Doc(BaseDocTemplate):
    total = "?"

    def __init__(self, *a, **k):
        BaseDocTemplate.__init__(self, *a, **k)
        fr = Frame(ML, MB, CW, PH - MT - MB, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="p", frames=[fr], onPageEnd=self._deco)])

    def _deco(self, canv, doc):
        section, emoji, color, sub, journey, nxt = getattr(canv, "_stage", ("START HERE", "1f319", "blue", "", None, ""))
        band = CFG["band"]
        fs_title = CFG["body"] * 1.25
        canv.saveState()
        # band
        canv.setFillColor(hx(color))
        canv.rect(0, PH - band, PW, band, stroke=0, fill=1)
        es = band * 0.5
        canv.drawImage(f"{EMO}/{emoji}.png", ML, PH - band + (band - es) / 2, es, es, mask="auto")
        canv.setFillColor(WHITE)
        canv.setFont("DVB", fs_title)
        canv.drawString(ML + es + 8, PH - band * 0.42, section)
        canv.setFont("DV", CFG["body"] * 0.82)
        canv.drawString(ML + es + 8, PH - band * 0.75, sub)
        canv.setFont("DVB", CFG["body"] * 0.82)
        canv.drawRightString(PW - MR, PH - band * 0.42, f"page {doc.page} of {Doc.total}")
        canv.setFont("DV", CFG["body"] * 0.72)
        canv.drawRightString(PW - MR, PH - band * 0.75, CFG["label"])
        # journey strip
        y = PH - band - 4
        h = CFG["body"] * 1.55
        gap = 3
        w = (CW - gap * 5) / 6
        canv.setFont("DVB", CFG["body"] * (0.5 if EDITION == "mobile" else 0.6))
        for i, name in enumerate(JOURNEY):
            x = ML + i * (w + gap)
            cur = (journey == i)
            canv.setStrokeColor(hx("gray"))
            canv.setLineWidth(0.6)
            if cur:
                canv.setFillColor(hx(color))
                canv.roundRect(x, y - h, w, h, 4, stroke=0, fill=1)
                canv.setFillColor(WHITE)
                # marker triangle so the current stage is not color-only
                p = canv.beginPath()
                p.moveTo(x + 4, y - h / 2 + 3.2)
                p.lineTo(x + 4, y - h / 2 - 3.2)
                p.lineTo(x + 9, y - h / 2)
                p.close()
                canv.drawPath(p, stroke=0, fill=1)
                canv.drawCentredString(x + w / 2 + 4, y - h / 2 - 2.3, name)
            else:
                canv.setFillColor(hx("gray", 1))
                canv.roundRect(x, y - h, w, h, 4, stroke=1, fill=1)
                canv.setFillColor(MUTED)
                canv.drawCentredString(x + w / 2, y - h / 2 - 2.3, name)
        if journey is None:
            canv.setFillColor(MUTED)
            canv.setFont("DV", CFG["body"] * 0.66)
            canv.drawRightString(PW - MR, y - h - CFG["body"] * 0.8, "reference page, not a step")
        # footer
        canv.setFillColor(MUTED)
        canv.setFont("DV", CFG["body"] * 0.74)
        canv.drawString(ML, MB * 0.45, "Tick a box only when the step is really done.")
        if nxt:
            canv.setFont("DVB", CFG["body"] * 0.74)
            canv.drawRightString(PW - MR, MB * 0.45, "NEXT: " + nxt)
        canv.restoreState()


def STAGE(section, emoji, color, sub="", journey=None, nxt="", prefix=None):
    _section[0] = prefix or slug(section)
    story.append(SetStage(section, emoji, color, sub, journey, nxt, prefix))


# ---------------------------------------------------------------- fillable flowables
class CheckRow(Flowable):
    def __init__(self, text, color="blue", name=None, num=None, sub=None, radio=None, value=None, req=None):
        Flowable.__init__(self)
        self.text, self.color, self.num, self.sub, self.req = text, color, num, sub, req
        self.size = CHK
        self.name = name
        self.radio, self.value = radio, value
        self.pad = 4 if EDITION == "mobile" else 5

    def wrap(self, aw, ah):
        self.aw = aw
        left = self.pad + self.size + 9 + (self.size - 2 if self.num is not None else 0)
        tagw = 0
        if self.req:
            self.tagp = Paragraph(self.req, S["tag"])
            tw, th = self.tagp.wrap(200, ah)
            self.tagw = self.tagp.minWidth() + 10
            tagw = self.tagw + 6
        self.pw = aw - left - self.pad - tagw
        self.para = Paragraph(self.text, S["row"])
        w, h = self.para.wrap(self.pw, ah)
        self.ph = h
        self.sh = 0
        if self.sub:
            self.subp = Paragraph(self.sub, S["rowsmall"])
            w2, h2 = self.subp.wrap(self.pw + tagw, ah)
            self.sh = h2 + 2
        self.height = max(self.size, self.ph + self.sh) + 2 * self.pad + 2
        self.width = aw
        self.left = left
        return aw, self.height

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(hx(self.color, 1))
        c.roundRect(0, 0, self.aw, self.height, 8, stroke=0, fill=1)
        y_box = self.height - self.pad - 1 - self.size if (self.sub and self.ph + self.sh > self.size) else (self.height - self.size) / 2
        x = self.pad
        if self.num is not None:
            r = (self.size - 2) / 2
            cy = y_box + self.size / 2
            c.setFillColor(hx(self.color))
            c.circle(x + r, cy, r, stroke=0, fill=1)
            c.setFillColor(WHITE)
            c.setFont("DVB", CFG["body"] * 0.9)
            c.drawCentredString(x + r, cy - CFG["body"] * 0.32, str(self.num))
            x += self.size - 2
        if self.radio:
            c.acroForm.radio(name=self.radio, value=self.value, x=x, y=y_box, size=self.size, relative=True,
                             borderColor=hx(self.color), fillColor=WHITE, textColor=hx(self.color),
                             borderWidth=1.8, buttonStyle="circle", shape="circle", forceBorder=True)
        else:
            c.acroForm.checkbox(name=self.name, x=x, y=y_box, size=self.size, relative=True,
                                borderColor=hx(self.color), fillColor=WHITE, textColor=hx(self.color),
                                borderWidth=1.8, buttonStyle="check", forceBorder=True, fieldFlags="")
        ty = self.height - self.pad - 1 - self.ph
        self.para.drawOn(c, self.left, ty)
        if self.req:
            tx = self.aw - self.pad - self.tagw
            th = CFG["body"] * 0.95
            c.setFillColor(hx("blue") if self.req == "REQUIRED" else hx("gray"))
            c.roundRect(tx, self.height - self.pad - th, self.tagw, th, 3, stroke=0, fill=1)
            self.tagp.wrap(self.tagw, th)
            self.tagp.drawOn(c, tx + 5, self.height - self.pad - th + (th - CFG["body"] * 0.8) / 2 + 0.5)
        if self.sub:
            self.subp.drawOn(c, self.left, ty - self.sh)
        c.restoreState()


class TextField(Flowable):
    def __init__(self, label, color="blue", height=None, name=None, multiline=None, hint=None, fontsize=None,
                 maxlen=20000, req=None):
        Flowable.__init__(self)
        self.label, self.color, self.h, self.hint = label, color, height or FH, hint
        self.fs = fontsize or CFG["body"]
        self.name = name
        self.maxlen = maxlen
        self.req = req
        self.multiline = (self.h > FH + 6) if multiline is None else multiline

    def wrap(self, aw, ah):
        self.aw = aw
        lab = self.label
        if self.req:
            col = C["blue"][0] if self.req == "REQUIRED" else C["gray"][0]
            lab = f"{lab}  <font color='{col}'>[{self.req}]</font>" if lab else f"<font color='{col}'>[{self.req}]</font>"
        self.lab = Paragraph(lab, S["label"]) if lab else None
        lh = 0
        if self.lab:
            w, lh = self.lab.wrap(aw, ah)
        self.lh = lh
        self.hp = None
        hh = 0
        if self.hint:
            self.hp = Paragraph(self.hint, S["tiny"])
            w, hh = self.hp.wrap(aw, ah)
        self.hh = hh
        self.height = lh + 2 + self.h + (hh + 2 if hh else 0) + 5
        self.width = aw
        return aw, self.height

    def draw(self):
        c = self.canv
        y = self.height
        if self.lab:
            y -= self.lh
            self.lab.drawOn(c, 0, y)
        y -= 2 + self.h
        flags = "multiline" if self.multiline else ""
        try:
            _bc = hx(self.color)
        except Exception:
            raise RuntimeError(f"bad color {self.color!r} for field {self.name!r} label {self.label!r}")
        c.acroForm.textfield(name=self.name, x=0, y=y, width=self.aw, height=self.h, relative=True,
                             borderColor=_bc, fillColor=WHITE, textColor=INK, borderWidth=1.3,
                             fontName="Helvetica", fontSize=self.fs, fieldFlags=flags, maxlen=self.maxlen, forceBorder=True)
        if self.hp:
            y -= 2 + self.hh
            self.hp.drawOn(c, 0, y)


class InkBox(Flowable):
    """Plain bordered area for pen ink. Deliberately NOT a form field."""

    def __init__(self, label, height, color="gray"):
        Flowable.__init__(self)
        self.label, self.h, self.color = label, height, color

    def wrap(self, aw, ah):
        self.aw = aw
        self.lab = Paragraph(self.label, S["label"])
        w, self.lh = self.lab.wrap(aw, ah)
        self.height = self.lh + 2 + self.h + 4
        return aw, self.height

    def draw(self):
        c = self.canv
        self.lab.drawOn(c, 0, self.height - self.lh)
        c.setStrokeColor(hx(self.color))
        c.setDash(3, 3)
        c.setLineWidth(0.9)
        c.roundRect(0, 0, self.aw, self.h, 6, stroke=1, fill=0)
        c.setDash()
        c.setFillColor(hx("gray", 1))
        c.setFont("DV", CFG["body"] * 0.7)
        c.setFillColor(MUTED)
        c.drawRightString(self.aw - 6, 5, "ink area, not a typed field")


def CHECK(text, color="blue", num=None, sub=None, name=None, req=None):
    story.append(CheckRow(text, color=color, num=num, sub=sub, name=name or fname(text, "chk"), req=req))
    story.append(Spacer(1, 4))


def RADIO(group, value, text, color="blue", sub=None):
    story.append(CheckRow(text, color=color, sub=sub, radio=group, value=value))
    story.append(Spacer(1, 5))


def TEXT(label, color="blue", height=None, hint=None, name=None, maxlen=20000, req=None):
    story.append(TextField(label, color=color, height=height, hint=hint, name=name or fname(label, "txt"), maxlen=maxlen, req=req))


def FIELDS(specs, color="blue", height=None, maxlen=8, gap=8):
    """Row of small labelled text fields for counts and short entries (maxlen limits accidental essays)."""
    n = len(specs)
    w = (CW - gap * (n - 1)) / n
    cells = [TextField(l, color=color, height=height or FH, fontsize=CFG["body"], name=fname(l, "txt"), maxlen=maxlen, multiline=False) for l in specs]
    t = Table([cells], colWidths=[w] * n, hAlign="LEFT")
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), gap),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t)


def YESNO(label, color="blue"):
    """Exactly-one YES / NO radio pair on one line."""
    grp = fname(label, "yn")
    lab = Paragraph(label, S["label"])
    y = CheckRow("YES", color="green", radio=grp, value="yes")
    n = CheckRow("NO", color="gray", radio=grp, value="no")
    w = (CW - 8) / 2
    t = Table([[lab, ""], [y, n]], colWidths=[w, w])
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                           ("SPAN", (0, 0), (1, 0))]))
    story.append(t)
    story.append(Spacer(1, 4))


def INKBOX(label, height):
    story.append(InkBox(label, height))
    story.append(Spacer(1, 4))


def NOTE(text, color="gray", emoji="1f4a1"):
    p = Paragraph(E(emoji, CFG["body"] * 1.15, -3) + " " + text, S["small"])
    t = Table([[p]], colWidths=[CW])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), hx(color, 1)),
                           ("LINEBEFORE", (0, 0), (0, -1), 3, hx(color)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(t)
    story.append(Spacer(1, 5))


def BANNER(text, color, emoji=None):
    st = ParagraphStyle("bn", parent=S["white"])
    if color == "yellow":
        st = ParagraphStyle("bny", parent=S["white"], textColor=INK)
    txt = (E(emoji, CFG["body"] * 1.3, -3) + " " if emoji else "") + text
    t = Table([[Paragraph(txt, st)]], colWidths=[CW])
    bg = hx(color) if color != "yellow" else colors.HexColor("#FDE68A")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                           ("ROUNDEDCORNERS", [7, 7, 7, 7])]))
    story.append(t)
    story.append(Spacer(1, 6))


def DONOW(text):
    BANNER("<b>DO THIS NOW:</b> " + text, "blue", "1f4cc")


def DONEWHEN(text):
    p = Paragraph(E("2705", CFG["body"] * 1.2, -3) + " <b>This page is done when:</b> " + text, S["body"])
    t = Table([[p]], colWidths=[CW])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), hx("green", 1)),
                           ("BOX", (0, 0), (-1, -1), 1.2, hx("green")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("ROUNDEDCORNERS", [6, 6, 6, 6])]))
    prev = []
    while story and (isinstance(story[-1], Spacer) or len(prev) == 0):
        prev.insert(0, story.pop())
        if not isinstance(prev[0], Spacer):
            break
    story.append(KeepTogether(prev + [Spacer(1, 4), t]))


def MONO(text, color="gray"):
    pre = Preformatted(text, S["mono"])
    t = Table([[pre]], colWidths=[CW])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), hx(color, 1)),
                           ("BOX", (0, 0), (-1, -1), 0.8, hx(color)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(t)
    story.append(Spacer(1, 6))


def CARD(title, emoji, color, body):
    head = Paragraph(E(emoji, CFG["body"] * 1.3, -3) + " " + title, S["white"])
    rows = [[head]] + [[Paragraph(b, S["body"])] for b in body]
    t = Table(rows, colWidths=[CW])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), hx(color)),
                           ("BACKGROUND", (0, 1), (0, -1), hx(color, 1)),
                           ("BOX", (0, 0), (-1, -1), 0.9, hx(color)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                           ("ROUNDEDCORNERS", [6, 6, 6, 6])]))
    story.append(KeepTogether(t))
    story.append(Spacer(1, 7))


def STATUS_LEGEND():
    rows = [("2705", "green", "PASSED", "The evidence Dispatch retrieved is written beside the claim."),
            ("274c", "red", "FAILED", "The sum, link, or .gov page contradicts the claim. The claim dies. EARNED kill."),
            ("2696", "yellow", "JUDGEMENT CALL", "No sum, source, or command can check it. Goes to STILL OPEN."),
            ("1f6a7", "orange", "BLOCKED", "Paywall, timeout, rate limit. Says nothing about the claim. Goes to STILL OPEN.")]
    data = []
    for em, col, name, desc in rows:
        data.append([Paragraph(E(em, CFG["body"] * 1.3, -3), S["row"]),
                     Paragraph(f"<b>{name}</b><br/><font size='{CFG['body'] * 0.82}' color='#4B5563'>{desc}</font>", S["row"])])
    t = Table(data, colWidths=[CFG["body"] * 2.4, CW - CFG["body"] * 2.4])
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
          ("LEFTPADDING", (0, 0), (-1, -1), 6)]
    for i, (em, col, name, desc) in enumerate(rows):
        st.append(("BACKGROUND", (0, i), (-1, i), hx(col, 1)))
        st.append(("LINEBEFORE", (0, i), (0, i), 4, hx(col)))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 6))


class Flow(Flowable):
    def __init__(self, blocks):
        Flowable.__init__(self)
        self.blocks = blocks
        self.bh = CFG["body"] * 3.4
        self.gap = CFG["body"] * 1.1

    def wrap(self, aw, ah):
        self.aw = aw
        self.height = len(self.blocks) * self.bh + (len(self.blocks) - 1) * self.gap
        return aw, self.height

    def draw(self):
        c = self.canv
        y = self.height
        for i, (label, sub, emoji, color) in enumerate(self.blocks):
            y -= self.bh
            c.setFillColor(hx(color, 1))
            c.setStrokeColor(hx(color))
            c.setLineWidth(1.2)
            c.roundRect(0, y, self.aw, self.bh, 8, stroke=1, fill=1)
            es = self.bh * 0.58
            c.drawImage(f"{EMO}/{emoji}.png", 8, y + (self.bh - es) / 2, es, es, mask="auto")
            c.setFillColor(hx(color))
            c.setFont("DVB", CFG["body"] * 1.02)
            c.drawString(es + 16, y + self.bh * 0.56, label)
            c.setFillColor(INK)
            c.setFont("DV", CFG["body"] * 0.78)
            c.drawString(es + 16, y + self.bh * 0.2, sub)
            if i < len(self.blocks) - 1:
                c.setStrokeColor(MUTED)
                c.setLineWidth(1.4)
                mid = self.aw / 2
                c.line(mid, y, mid, y - self.gap + 3)
                c.setFillColor(MUTED)
                p = c.beginPath()
                p.moveTo(mid - 4, y - self.gap + 5)
                p.lineTo(mid + 4, y - self.gap + 5)
                p.lineTo(mid, y - self.gap)
                p.close()
                c.drawPath(p, stroke=0, fill=1)
            y -= self.gap


