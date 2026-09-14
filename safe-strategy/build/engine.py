"""
Layout engine for the Forgelink SAFE Strategy Playbook.

Design constraints (from the requester):
  - ADHD-friendly : short blocks, one idea per block, heavy visual anchoring,
                    predictable repeating rhythm, explicit progress markers.
  - OCD-friendly  : strict alignment grid, consistent spacing units, no ragged
                    layout, every checkbox the same size in the same column,
                    nothing half-finished on a page.
  - Fillable      : real AcroForm checkboxes and text fields.
  - Colour + emoji: real Noto Color Emoji rasterised to PNG and embedded.
"""
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageDraw, ImageFont

PAGE_W, PAGE_H = letter
ML, MR = 52, 52
MT, MB = 58, 52
CONTENT_W = PAGE_W - ML - MR

U = 4  # base spacing unit; all vertical gaps are multiples of U (OCD grid)

# ---------------------------------------------------------------- palette
INK      = HexColor("#15181E")
BODY     = HexColor("#262C38")
MUTED    = HexColor("#61697A")
RULE     = HexColor("#DCE2EC")
PAPER    = HexColor("#FFFFFF")
SOFT     = HexColor("#F5F7FB")

PARTS = {
    "start":    ("#0E7C86", "Start Here"),
    "basics":   ("#2159C9", "What A SAFE Is"),
    "risk":     ("#C2261F", "The Landmines"),
    "struct":   ("#6D28D9", "Structure"),
    "money":    ("#07795A", "The Money Map"),
    "nondil":   ("#C2570C", "Free Money First"),
    "contract": ("#3730B0", "Contracts Runway"),
    "sprint":   ("#9A5B08", "90-Day Sprints"),
    "form":     ("#334155", "The SAFE Form"),
    "check":    ("#B31D6B", "Checklists"),
    "gloss":    ("#475569", "Glossary"),
    "ref":      ("#1E293B", "References"),
}

CALLOUT = {
    "truth":  ("#7A5A00", "#FFF8E1", "\U0001F9ED"),   # compass - truth standard
    "warn":   ("#A3160F", "#FDECEA", "\U000026A0"),   # warning
    "stop":   ("#7F1D1D", "#FDE8E8", "\U0001F6D1"),   # stop sign
    "info":   ("#1E40AF", "#EAF1FE", "\U0001F4A1"),   # bulb
    "do":     ("#065F46", "#E7F6F0", "\U0001F3AF"),   # target
    "money":  ("#14532D", "#E9F7EF", "\U0001F4B0"),   # money bag
    "law":    ("#3F3F46", "#F4F4F5", "\U00002696"),   # scales
    "kid":    ("#7C2D8F", "#F8EDFB", "\U0001F9F8"),   # teddy - explain like I'm 5
    "faith":  ("#7A4B00", "#FBF3E4", "\U0001F54A"),   # dove
}

EMOJI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emoji")
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
_emoji_cache = {}


def emoji_png(ch):
    """Rasterise one emoji to a cropped transparent PNG; cached on disk."""
    if ch in _emoji_cache:
        return _emoji_cache[ch]
    os.makedirs(EMOJI_DIR, exist_ok=True)
    key = "_".join("%04x" % ord(c) for c in ch)
    path = os.path.join(EMOJI_DIR, key + ".png")
    if not os.path.exists(path):
        f = ImageFont.truetype(EMOJI_FONT, 109)
        img = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((10, 10), ch, font=f, embedded_color=True)
        bb = img.getbbox()
        if bb:
            img = img.crop(bb)
        img.save(path)
    _emoji_cache[ch] = path
    return path


def _register_fonts():
    fam = "/mnt/skills/examples/canvas-design/canvas-fonts"
    reg = {}
    cands = {
        "Display": os.path.join(fam, "BricolageGrotesque-Bold.ttf"),
        "Mono":    os.path.join(fam, "IBMPlexMono-Regular.ttf"),
        "MonoB":   os.path.join(fam, "IBMPlexMono-Bold.ttf"),
    }
    for name, p in cands.items():
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont(name, p))
                reg[name] = True
            except Exception:
                pass
    return reg


_FONTS = _register_fonts()
F_DISPLAY = "Display" if _FONTS.get("Display") else "Helvetica-Bold"
F_MONO    = "Mono" if _FONTS.get("Mono") else "Courier"
F_MONOB   = "MonoB" if _FONTS.get("MonoB") else "Courier-Bold"
F_REG, F_BOLD, F_ITAL = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


# ---------------------------------------------------------------- rich text
def parse_runs(text):
    """Split on **bold** markers into [(text, bold_bool), ...]."""
    out, buf, bold = [], "", False
    i = 0
    while i < len(text):
        if text[i:i + 2] == "**":
            if buf:
                out.append((buf, bold))
                buf = ""
            bold = not bold
            i += 2
        else:
            buf += text[i]
            i += 1
    if buf:
        out.append((buf, bold))
    return out


def wrap_runs(runs, width, size, reg=F_REG, bold=F_BOLD):
    """Word-wrap a run list into lines of runs that fit `width`."""
    lines, cur, cur_w = [], [], 0.0
    for txt, b in runs:
        fnt = bold if b else reg
        parts = txt.split(" ")
        for j, word in enumerate(parts):
            piece = word if j == 0 else " " + word
            if piece == "":
                continue
            w = pdfmetrics.stringWidth(piece, fnt, size)
            if cur and cur_w + w > width:
                lines.append(cur)
                piece = piece.lstrip()
                w = pdfmetrics.stringWidth(piece, fnt, size)
                cur, cur_w = [], 0.0
            if piece:
                cur.append((piece, b))
                cur_w += w
    if cur:
        lines.append(cur)
    return lines


class Doc:
    def __init__(self, path, collect_only=False, toc=None, toc_pages=2):
        self.path = path
        self.c = canvas.Canvas(path, pagesize=letter)
        self.c.setTitle("Forgelink SAFE Strategy Playbook")
        self.c.setAuthor("Prepared for Forge Talent Connections / Forgelink LLC")
        self.c.setSubject("Simple Agreement for Future Equity - strategy and fillable workbook")
        self.y = PAGE_H - MT
        self.page = 1
        self.part = "start"
        self.collect_only = collect_only
        self.toc_entries = []          # collected during pass 1
        self.toc = toc or []           # supplied during pass 2
        self.toc_pages = toc_pages
        self._field_names = set()
        self._chrome = True
        self.field_count = 0

    # ------------------------------------------------------------ chrome
    def _draw_chrome(self):
        if not self._chrome:
            return
        hexcol, label = PARTS[self.part]
        col = HexColor(hexcol)
        # top accent bar
        self.c.setFillColor(col)
        self.c.rect(0, PAGE_H - 20, PAGE_W, 20, stroke=0, fill=1)
        self.c.setFillColor(PAPER)
        self.c.setFont(F_BOLD, 8)
        self.c.drawString(ML, PAGE_H - 14, label.upper())
        self.c.setFont(F_REG, 8)
        self.c.drawRightString(PAGE_W - MR, PAGE_H - 14,
                               "FORGELINK LLC  |  SAFE STRATEGY PLAYBOOK")
        # footer
        self.c.setStrokeColor(RULE)
        self.c.setLineWidth(0.6)
        self.c.line(ML, MB - 14, PAGE_W - MR, MB - 14)
        self.c.setFillColor(MUTED)
        self.c.setFont(F_REG, 7.5)
        self.c.drawString(ML, MB - 26,
                          "Draft for planning. Not legal, tax, or investment advice. "
                          "Verify every citation at its source.")
        self.c.setFont(F_BOLD, 8.5)
        self.c.setFillColor(col)
        self.c.drawRightString(PAGE_W - MR, MB - 26, str(self.page))

    def new_page(self):
        self._draw_chrome()
        self.c.showPage()
        self.page += 1
        self.y = PAGE_H - MT

    def ensure(self, h):
        if self.y - h < MB:
            self.new_page()
            return True
        return False

    def gap(self, n=2):
        self.y -= U * n

    # ------------------------------------------------------------ images
    def emoji(self, ch, x, y, size=12):
        try:
            self.c.drawImage(emoji_png(ch), x, y, width=size, height=size,
                             mask="auto")
        except Exception:
            pass

    # ------------------------------------------------------------ headings
    def part_cover(self, part, number, title, kicker, emoji_ch):
        """Full-width part opener. Always starts a fresh page."""
        self.part = part
        if self.y < PAGE_H - MT:
            self.new_page()
        hexcol, _ = PARTS[part]
        col = HexColor(hexcol)
        top = self.y
        band_h = 96
        self.c.setFillColor(col)
        self.c.rect(ML, top - band_h, CONTENT_W, band_h, stroke=0, fill=1)
        self.emoji(emoji_ch, ML + 18, top - 54, 36)
        self.c.setFillColor(PAPER)
        self.c.setFont(F_BOLD, 9)
        self.c.drawString(ML + 66, top - 26, "PART %s" % number)
        self.c.setFont(F_DISPLAY, 22)
        self.c.drawString(ML + 66, top - 50, title)
        self.c.setFont(F_REG, 9.5)
        for i, ln in enumerate(wrap_runs(parse_runs(kicker), CONTENT_W - 84, 9.5)):
            self._line(ln, ML + 66, top - 68 - i * 12, 9.5, PAPER)
        self.y = top - band_h - U * 5
        self.toc_entries.append((number, title, self.page, hexcol))

    def h2(self, text, emoji_ch=None):
        self.ensure(52)
        hexcol, _ = PARTS[self.part]
        col = HexColor(hexcol)
        self.y -= U * 2
        x = ML
        if emoji_ch:
            self.emoji(emoji_ch, x, self.y - 13, 14)
            x += 20
        self.c.setFillColor(INK)
        self.c.setFont(F_BOLD, 13)
        self.c.drawString(x, self.y - 11, text)
        self.y -= 17
        self.c.setStrokeColor(col)
        self.c.setLineWidth(2)
        self.c.line(ML, self.y, ML + 38, self.y)
        self.y -= U * 3

    def h3(self, text):
        self.ensure(30)
        hexcol, _ = PARTS[self.part]
        self.c.setFillColor(HexColor(hexcol))
        self.c.setFont(F_BOLD, 10.5)
        self.c.drawString(ML, self.y - 10, text)
        self.y -= 14 + U * 2

    # ------------------------------------------------------------ text
    def _line(self, runs, x, y, size, color):
        cx = x
        for txt, b in runs:
            self.c.setFont(F_BOLD if b else F_REG, size)
            self.c.setFillColor(color)
            self.c.drawString(cx, y, txt)
            cx += pdfmetrics.stringWidth(txt, F_BOLD if b else F_REG, size)

    def body(self, text, size=9.8, color=BODY, indent=0, lead=13.2, space=2):
        w = CONTENT_W - indent
        lines = wrap_runs(parse_runs(text), w, size)
        for ln in lines:
            self.ensure(lead + 2)
            self._line(ln, ML + indent, self.y - size, size, color)
            self.y -= lead
        self.y -= U * space / 2.0

    def bullet(self, text, size=9.6, marker="•", indent=14, color=BODY):
        w = CONTENT_W - indent - 12
        lines = wrap_runs(parse_runs(text), w, size)
        for i, ln in enumerate(lines):
            self.ensure(14)
            if i == 0:
                hexcol, _ = PARTS[self.part]
                self.c.setFillColor(HexColor(hexcol))
                self.c.setFont(F_BOLD, size)
                self.c.drawString(ML + indent, self.y - size, marker)
            self._line(ln, ML + indent + 12, self.y - size, size, color)
            self.y -= 12.8
        self.y -= U * 0.6

    def kid(self, text):
        """'Explain like I'm five' block - deliberately visually distinct."""
        self.callout("kid", "SAY IT LIKE I AM FIVE", text)

    # ------------------------------------------------------------ callouts
    def callout(self, kind, title, text, size=9.4):
        fg, bg, ch = CALLOUT[kind]
        pad = 10
        inner_w = CONTENT_W - pad * 2 - 22

        def build_lines():
            out = []
            paras = [p for p in text.split("\n\n")]
            for i, para in enumerate(paras):
                if i:
                    out.append([])          # blank spacer line between paragraphs
                out.extend(wrap_runs(parse_runs(para.replace("\n", " ")),
                                     inner_w, size))
            return out

        lines = build_lines()
        h = pad * 2 + 14 + len(lines) * 12.6
        if self.y - h < MB:
            self.new_page()
            lines = build_lines()
            h = pad * 2 + 14 + len(lines) * 12.6
        top = self.y
        self.c.setFillColor(HexColor(bg))
        self.c.setStrokeColor(HexColor(fg))
        self.c.setLineWidth(0.9)
        self.c.roundRect(ML, top - h, CONTENT_W, h, 5, stroke=1, fill=1)
        self.c.setFillColor(HexColor(fg))
        self.c.rect(ML, top - h, 3.5, h, stroke=0, fill=1)
        self.emoji(ch, ML + pad + 2, top - pad - 12, 13)
        self.c.setFillColor(HexColor(fg))
        self.c.setFont(F_BOLD, 8.6)
        self.c.drawString(ML + pad + 20, top - pad - 9, title)
        yy = top - pad - 24
        for ln in lines:
            if ln:
                self._line(ln, ML + pad + 20, yy, size, HexColor(fg))
            yy -= 12.6
        self.y = top - h - U * 3

    # ------------------------------------------------------------ steps
    def step(self, n, title, emoji_ch=None):
        self.ensure(40)
        hexcol, _ = PARTS[self.part]
        col = HexColor(hexcol)
        top = self.y
        self.c.setFillColor(col)
        self.c.roundRect(ML, top - 22, 26, 22, 4, stroke=0, fill=1)
        self.c.setFillColor(PAPER)
        self.c.setFont(F_BOLD, 12)
        self.c.drawCentredString(ML + 13, top - 16, str(n))
        x = ML + 34
        if emoji_ch:
            self.emoji(emoji_ch, x, top - 18, 14)
            x += 19
        self.c.setFillColor(INK)
        self.c.setFont(F_BOLD, 11)
        self.c.drawString(x, top - 16, title)
        self.y = top - 22 - U * 2

    # ------------------------------------------------------------ fields
    def _uniq(self, name):
        base = name
        i = 2
        while name in self._field_names:
            name = "%s_%d" % (base, i)
            i += 1
        self._field_names.add(name)
        return name

    def check(self, label, name=None, indent=0, size=9.6, bold=False):
        """One fillable checkbox row. Fixed 12pt box, fixed column - OCD grid."""
        w = CONTENT_W - indent - 24
        runs = parse_runs(("**%s**" % label) if bold else label)
        lines = wrap_runs(runs, w, size)
        h = max(16, len(lines) * 12.6 + 3)
        self.ensure(h + 2)
        top = self.y
        fname = self._uniq(name or ("chk_%d" % (self.field_count + 1)))
        self.field_count += 1
        hexcol, _ = PARTS[self.part]
        if not self.collect_only:
            self.c.acroForm.checkbox(
                name=fname, x=ML + indent, y=top - 13, size=11.5,
                buttonStyle="check", borderWidth=1.0,
                borderColor=HexColor(hexcol), fillColor=HexColor("#FFFFFF"),
                textColor=HexColor(hexcol), forceBorder=True)
        yy = top - 10.5
        for ln in lines:
            self._line(ln, ML + indent + 20, yy, size, BODY)
            yy -= 12.6
        self.y = top - h

    def field(self, label, name=None, w=200, h=17, note=None, multiline=False):
        """Label above, fillable text box below."""
        need = h + 16 + (11 if note else 0)
        self.ensure(need + 4)
        top = self.y
        self.c.setFillColor(MUTED)
        self.c.setFont(F_BOLD, 7.6)
        self.c.drawString(ML, top - 8, label.upper())
        fname = self._uniq(name or ("fld_%d" % (self.field_count + 1)))
        self.field_count += 1
        if not self.collect_only:
            self.c.acroForm.textfield(
                name=fname, x=ML, y=top - 12 - h, width=w, height=h,
                borderWidth=0.8, borderColor=RULE, fillColor=SOFT,
                textColor=INK, fontSize=9.5, forceBorder=True)
        if note:
            self.c.setFillColor(MUTED)
            self.c.setFont(F_ITAL, 7.8)
            self.c.drawString(ML + w + 10, top - 12 - h + 5, note)
        self.y = top - 12 - h - U * 2

    def field_row(self, items, h=17):
        """items = [(label, name, width), ...] laid out on one aligned row."""
        self.ensure(h + 20)
        top = self.y
        x = ML
        for label, name, w in items:
            self.c.setFillColor(MUTED)
            self.c.setFont(F_BOLD, 7.6)
            self.c.drawString(x, top - 8, label.upper())
            fname = self._uniq(name)
            self.field_count += 1
            if not self.collect_only:
                self.c.acroForm.textfield(
                    name=fname, x=x, y=top - 12 - h, width=w, height=h,
                    borderWidth=0.8, borderColor=RULE, fillColor=SOFT,
                    textColor=INK, fontSize=9.5, forceBorder=True)
            x += w + 14
        self.y = top - 12 - h - U * 2

    def sigline(self, label, name, w=230):
        self.ensure(34)
        top = self.y
        fname = self._uniq(name)
        self.field_count += 1
        if not self.collect_only:
            self.c.acroForm.textfield(
                name=fname, x=ML, y=top - 20, width=w, height=18,
                borderWidth=0, borderColor=PAPER, fillColor=HexColor("#FFFFFF"),
                textColor=INK, fontSize=10, forceBorder=False)
        self.c.setStrokeColor(INK)
        self.c.setLineWidth(0.8)
        self.c.line(ML, top - 21, ML + w, top - 21)
        self.c.setFillColor(MUTED)
        self.c.setFont(F_REG, 7.8)
        self.c.drawString(ML, top - 31, label)
        self.y = top - 34 - U

    # ------------------------------------------------------------ tables
    def table(self, headers, rows, widths, size=8.6, row_h=None):
        hexcol, _ = PARTS[self.part]
        col = HexColor(hexcol)
        total = sum(widths)

        def header():
            self.ensure(24)
            top = self.y
            self.c.setFillColor(col)
            self.c.rect(ML, top - 17, total, 17, stroke=0, fill=1)
            x = ML
            self.c.setFillColor(PAPER)
            self.c.setFont(F_BOLD, size)
            for hd, w in zip(headers, widths):
                self.c.drawString(x + 5, top - 12, hd)
                x += w
            self.y = top - 17

        header()
        alt = False
        for r in rows:
            cell_lines = [wrap_runs(parse_runs(str(c)), w - 10, size)
                          for c, w in zip(r, widths)]
            h = row_h or max(15, max(len(cl) for cl in cell_lines) * 11.4 + 6)
            if self.y - h < MB:
                self.new_page()
                header()
            top = self.y
            if alt:
                self.c.setFillColor(SOFT)
                self.c.rect(ML, top - h, total, h, stroke=0, fill=1)
            alt = not alt
            self.c.setStrokeColor(RULE)
            self.c.setLineWidth(0.4)
            self.c.line(ML, top - h, ML + total, top - h)
            x = ML
            for cl, w in zip(cell_lines, widths):
                yy = top - 11
                for ln in cl:
                    self._line(ln, x + 5, yy, size, BODY)
                    yy -= 11.4
                x += w
            self.y = top - h
        self.y -= U * 3

    # ------------------------------------------------------------ misc
    def rule(self):
        self.ensure(10)
        self.c.setStrokeColor(RULE)
        self.c.setLineWidth(0.7)
        self.c.line(ML, self.y - 4, PAGE_W - MR, self.y - 4)
        self.y -= U * 3

    def label_tag(self, text, hexcol):
        """Small evidence-label pill."""
        self.ensure(16)
        w = pdfmetrics.stringWidth(text, F_BOLD, 7) + 12
        self.c.setFillColor(HexColor(hexcol))
        self.c.roundRect(ML, self.y - 12, w, 12, 3, stroke=0, fill=1)
        self.c.setFillColor(PAPER)
        self.c.setFont(F_BOLD, 7)
        self.c.drawString(ML + 6, self.y - 8.6, text)
        self.y -= 12 + U

    def save(self):
        self._draw_chrome()
        self.c.showPage()
        self.c.save()
