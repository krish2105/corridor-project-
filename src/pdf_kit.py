"""
pdf_kit.py — the house style for every PDF this project issues.

Extracted when the second document needed it. Two PDFs going to the same reviewer in the
same week should not drift apart because their styles were copied rather than shared, and
copying eighty lines of ParagraphStyle to get one more report is how that starts.

The palette is the dashboard's, so a figure looks the same wherever a reviewer meets it.
"""
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Table,
                                TableStyle)

INK = colors.HexColor("#14181A")
MUTED = colors.HexColor("#4A5350")
FAINT = colors.HexColor("#77817D")
ACCENT = colors.HexColor("#1B3A6B")
DEFECT = colors.HexColor("#9E2B25")
OK = colors.HexColor("#2C6249")
CAUTION = colors.HexColor("#82600F")
RULE = colors.HexColor("#D8DCD6")
SUNK = colors.HexColor("#F1F2ED")


def S(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9.4, leading=13.6, textColor=INK,
                spaceAfter=5, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(name, **base)


H1 = S("H1", fontName="Helvetica-Bold", fontSize=19, leading=22, spaceAfter=2)
SUB = S("SUB", fontSize=9.6, textColor=MUTED, leading=13.6, spaceAfter=12)
H2 = S("H2", fontName="Helvetica-Bold", fontSize=12, leading=15, spaceBefore=15,
       spaceAfter=5, textColor=ACCENT)
H3 = S("H3", fontName="Helvetica-Bold", fontSize=9.8, leading=13, spaceBefore=8,
       spaceAfter=2)
BODY = S("BODY")
NOTE = S("NOTE", fontSize=8.5, leading=12, textColor=MUTED, spaceAfter=4)
BUL = S("BUL", fontSize=9.2, leading=13.2, leftIndent=10, spaceAfter=2.5)
EYE = S("EYE", fontName="Helvetica-Bold", fontSize=7.4, leading=10, textColor=FAINT,
        spaceAfter=2)
CELL = S("CELL", fontSize=8.4, leading=11.4, spaceAfter=0)
CELLH = S("CELLH", fontName="Helvetica-Bold", fontSize=7.4, leading=10, textColor=FAINT,
          spaceAfter=0)

nf = "{:,.0f}".format


def rule(space=6):
    t = Table([[""]], colWidths=[170 * mm], rowHeights=[0.5])
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.5, RULE),
                           ("TOPPADDING", (0, 0), (-1, -1), space),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), space)]))
    return t


def kpis(rows):
    """A band of headline numbers. Value on top, label under, tone in the value."""
    cells = [[Paragraph(f'<font color="{t.hexval()}">{v}</font>',
                        S("K", fontName="Helvetica-Bold", fontSize=15, leading=17,
                          spaceAfter=1)) for v, _l, t in rows],
             [Paragraph(l, S("L", fontSize=7.2, leading=9.4, textColor=FAINT,
                             spaceAfter=0)) for _v, l, _t in rows]]
    w = 170 * mm / len(rows)
    t = Table(cells, colWidths=[w] * len(rows))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SUNK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
    ]))
    return t


def table(header, rows, widths, aligns=None):
    data = [[Paragraph(h, CELLH) for h in header]]
    for r in rows:
        data.append([c if hasattr(c, "wrap") else Paragraph(str(c), CELL) for c in r])
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    style = [
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, RULE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in (aligns or []):
        style.append(("ALIGN", (i, 0), (i, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def bullets(items):
    return [Paragraph(f"&bull;&nbsp;&nbsp;{s}", BUL) for s in items]


def render(path, flow, title, footer, author="Corridor junction intelligence"):
    """Build the document, with a running footer and a page number on every page."""
    doc = BaseDocTemplate(str(path), pagesize=A4,
                          leftMargin=20 * mm, rightMargin=20 * mm,
                          topMargin=17 * mm, bottomMargin=16 * mm,
                          title=title, author=author)

    def furniture(canv, _doc):
        canv.saveState()
        canv.setFont("Helvetica", 7.2)
        canv.setFillColor(FAINT)
        canv.drawString(20 * mm, 10 * mm, footer)
        canv.drawRightString(190 * mm, 10 * mm, f"page {canv.getPageNumber()}")
        canv.setStrokeColor(RULE)
        canv.setLineWidth(0.4)
        canv.line(20 * mm, 13 * mm, 190 * mm, 13 * mm)
        canv.restoreState()

    frame = Frame(20 * mm, 16 * mm, 170 * mm, A4[1] - 33 * mm, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=furniture)])
    doc.build(flow)
