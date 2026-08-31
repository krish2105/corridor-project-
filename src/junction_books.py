"""
junction_books.py — one editable Excel per junction: 12 turning-movement sheets, 4-4-4.

WHAT THE REVIEWER ASKED FOR
Per junction, every one of the twelve surveyed movements on its own sheet, grouped the
way the movements group: four LEFT sheets, four STRAIGHT sheets, four RIGHT sheets.
Each sheet carries a turning-movement diagram, the movement's full vehicle-wise
distribution (96 fifteen-minute bins by ten classes, exactly as parsed from the issued
workbook), the class totals with shares, and an editable chart. Nothing synthetic: every
number is re-derived from the source cells, and the gate below reconciles each sheet's
total against the parse.

Day 2 is shown as a per-class daily total beside day 1, with the identical-to-day-1 flag,
rather than a second 96-row block - the audit showed day 2 is derived, and repeating it
row by row would present a copy as observation.

Run:  uv run python src/junction_books.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
import matplotlib.patches as mpatches

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import JUNCTIONS, JUNCTION_COORDS, OUT, SCHEME_LABEL
from src.routes import route as scheme_route
from src.spelling import fix as spell
from src.tmc_parse import CLASS_LABELS, parse_all

BOOKS = OUT / "junction_books"
IMGS = BOOKS / "_diagrams"

INK, MUTED, ACCENT = "14181A", "5C6663", "1B3A6B"
OKC, DEFECT, SUNK = "2C6249", "9E2B25", "F1F2ED"
TURN_HEX = {"Left": "#2C6249", "Straight": "#1B3A6B", "Right": "#9E2B25"}

H = Font(bold=True, size=14, color=INK)
SUBF = Font(size=9, color=MUTED)
TH = Font(bold=True, size=9, color=MUTED)
BOLD = Font(bold=True, size=10)
FILL = PatternFill("solid", start_color=SUNK)
THIN = Border(bottom=Side(style="thin", color="D5D9D4"))

# The sheet order the reviewer asked for: 4-4-4, movements grouped by turn.
GROUPS = [("Left", "L"), ("Straight", "S"), ("Right", "R")]


def diagram(arms, fi, ti, turn, path):
    """
    The movement drawn the way the dashboard draws it: tangent-derived, left-hand
    traffic, entry on the left of its arm, exit on the left of the exit arm.
    """
    import math
    fig, ax = plt.subplots(figsize=(3.4, 3.4), dpi=120)
    ax.set_xlim(-1.3, 1.3); ax.set_ylim(-1.3, 1.3)
    ax.set_aspect("equal"); ax.axis("off")
    LANE = 0.16
    for i in range(4):
        t = math.pi / 2 * i
        ox, oy = math.sin(t), math.cos(t)
        ax.plot([ox * .12, ox * 1.05], [oy * .12, oy * 1.05],
                color="#E2E4DF", lw=26, solid_capstyle="butt", zorder=1)
        ax.text(ox * 1.18, oy * 1.18, spell(arms[i]), ha="center", va="center",
                fontsize=7, color="#5C6663")

    def node(i, entering):
        t = math.pi / 2 * i
        ox, oy = math.sin(t), math.cos(t)
        px, py = math.cos(t), -math.sin(t)
        s = 1 if entering else -1
        return (ox * .55 + px * s * LANE, oy * .55 + py * s * LANE)

    x1, y1 = node(fi, True); x2, y2 = node(ti, False)
    if turn == "Straight":
        verts = [(x1, y1), (x2, y2)]; codes = [MplPath.MOVETO, MplPath.LINETO]
    else:
        # control point at the intersection of the entry/exit tangents (see VolumeFlow)
        ta = math.pi / 2 * fi; tb = math.pi / 2 * ti
        ax_, ay_ = -math.sin(ta), -math.cos(ta)     # inward along entry arm
        bx_, by_ = math.sin(tb), math.cos(tb)       # outward along exit arm
        det = ax_ * -by_ - ay_ * -bx_
        tt = ((x2 - x1) * -by_ - (y2 - y1) * -bx_) / det
        cx, cy = x1 + tt * ax_, y1 + tt * ay_
        verts = [(x1, y1), (cx, cy), (x2, y2)]
        codes = [MplPath.MOVETO, MplPath.CURVE3, MplPath.CURVE3]
    ax.add_patch(mpatches.FancyArrowPatch(path=MplPath(verts, codes),
                 arrowstyle="-|>", mutation_scale=16, lw=3.2,
                 color=TURN_HEX[turn], zorder=3))
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def sheet_for(wb, code, arms, fi, ti, turn, mv, img_path):
    frm, to = arms[fi], arms[ti]
    title = f"{turn[0]}{fi + 1} {spell(frm)[:14]}"
    ws = wb.create_sheet(title[:31])
    ws.sheet_view.showGridLines = False

    r = scheme_route(fi, ti)
    ws["A1"] = (f"{SCHEME_LABEL[code]} — {spell(frm)} → {spell(to)}  ({turn})")
    ws["A1"].font = H
    ws["A2"] = (f"Survey sheet {code} · movement V_{fi * 3 + [g for g, _ in GROUPS].index(turn) + 1} "
                f"· India drives on the left; the left turn is the next arm clockwise")
    ws["A2"].font = SUBF
    ws["A3"] = ("Under the signal-free scheme: "
                + (" → ".join(r["legs"]) if r["permitted"] == "re-routed"
                   else "unaffected — " + r["legs"][0]))
    ws["A3"].font = Font(size=9, italic=True,
                         color=DEFECT if r["permitted"] == "re-routed" else OKC)

    img = XLImage(str(img_path)); img.anchor = "L1"
    ws.add_image(img)

    # data block: 96 bins x classes, day 1, plus day-2 daily totals with the flag
    g = mv[(mv.arm_from == frm) & (mv.arm_to == to)]
    days = sorted(g.date.unique())
    d1 = g[g.date == days[0]]
    piv = d1.pivot_table(index="bin_label", columns="veh_class",
                         values="count", aggfunc="sum").fillna(0)
    classes = [c for c in CLASS_LABELS if c in piv.columns]
    piv = piv[classes]

    hdr = 5
    ws.cell(hdr, 1, "15-min bin").font = TH
    for j, c in enumerate(classes, start=2):
        cell = ws.cell(hdr, j, spell(CLASS_LABELS[c]))
        cell.font = TH; cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.fill = FILL
    ws.cell(hdr, len(classes) + 2, "Total").font = TH
    ws.cell(hdr, 1).fill = FILL; ws.cell(hdr, len(classes) + 2).fill = FILL

    for i, (lab, row) in enumerate(piv.iterrows(), start=hdr + 1):
        ws.cell(i, 1, lab).font = Font(size=9)
        for j, c in enumerate(classes, start=2):
            ws.cell(i, j, int(row[c])).font = Font(size=9)
        last = get_column_letter(len(classes) + 1)
        ws.cell(i, len(classes) + 2, f"=SUM(B{i}:{last}{i})").font = Font(size=9)

    tot_r = hdr + len(piv) + 1
    ws.cell(tot_r, 1, f"Day 1 total ({days[0]})").font = BOLD
    for j in range(2, len(classes) + 3):
        col = get_column_letter(j)
        c = ws.cell(tot_r, j, f"=SUM({col}{hdr + 1}:{col}{tot_r - 1})")
        c.font = BOLD; c.border = THIN

    day1 = d1.groupby("veh_class")["count"].sum()
    grand = day1.sum()
    ws.cell(tot_r + 1, 1, "Share of movement %").font = TH
    for j, c in enumerate(classes, start=2):
        ws.cell(tot_r + 1, j,
                round(100 * day1.get(c, 0) / grand, 2) if grand else 0).font = Font(size=9)

    if len(days) > 1:
        d2 = g[g.date == days[1]].groupby("veh_class")["count"].sum()
        ws.cell(tot_r + 2, 1, f"Day 2 total ({days[1]})").font = TH
        for j, c in enumerate(classes, start=2):
            ws.cell(tot_r + 2, j, int(d2.get(c, 0))).font = Font(size=9)
        same = sum(1 for c in classes
                   if day1.get(c, 0) > 0 or d2.get(c, 0) > 0
                   if day1.get(c, 0) == d2.get(c, 0))
        live = sum(1 for c in classes if day1.get(c, 0) > 0 or d2.get(c, 0) > 0)
        ws.cell(tot_r + 2, len(classes) + 2,
                f"{same} of {live} classes identical to day 1").font = SUBF

    ch = BarChart(); ch.type = "col"; ch.title = "Vehicle-wise distribution, day 1"
    ch.height, ch.width = 7, 16; ch.legend = None
    ch.add_data(Reference(ws, min_col=2, max_col=len(classes) + 1,
                          min_row=hdr, max_row=tot_r), from_rows=False, titles_from_data=True)
    # one series: the totals row
    ch.add_data(Reference(ws, min_col=2, max_col=len(classes) + 1,
                          min_row=tot_r, max_row=tot_r), from_rows=True)
    ch.series = ch.series[-1:]
    ch.set_categories(Reference(ws, min_col=2, max_col=len(classes) + 1,
                                min_row=hdr, max_row=hdr))
    ws.add_chart(ch, f"A{tot_r + 5}")

    ws.column_dimensions["A"].width = 15
    for j in range(2, len(classes) + 3):
        ws.column_dimensions[get_column_letter(j)].width = 11
    ws.freeze_panes = f"A{hdr + 1}"
    return int(grand)


def build():
    bins, _ = parse_all()
    mvall = bins[bins.kind == "movement"]
    BOOKS.mkdir(parents=True, exist_ok=True)
    IMGS.mkdir(exist_ok=True)

    made, checks = [], []
    for code in sorted(JUNCTIONS, key=lambda c: SCHEME_LABEL[c]):
        arms = JUNCTIONS[code]
        mv = mvall[mvall.junction == code]
        wb = Workbook(); wb.remove(wb.active)
        book_total = 0
        for turn, _tag in GROUPS:                       # 4-4-4: L, L, L, L, S ... R
            off = {"Left": 1, "Straight": 2, "Right": 3}[turn]
            for fi in range(4):
                ti = (fi + off) % 4
                img = IMGS / f"{code}_{turn[0]}{fi}.png"
                if not img.exists():
                    diagram(arms, fi, ti, turn, img)
                book_total += sheet_for(wb, code, arms, fi, ti, turn, mv, img)
        # GATE per book: the 12 sheets' day-1 totals must equal the parse's day-1 total
        days = sorted(mv.date.unique())
        parsed = int(mv[mv.date == days[0]]["count"].sum())
        checks.append((code, book_total, parsed))
        name = f"{SCHEME_LABEL[code]}_{code}_Turning_Movements.xlsx"
        wb.save(BOOKS / name)
        made.append(name)
    return made, checks


if __name__ == "__main__":
    made, checks = build()
    print("=== Junction turning-movement workbooks ===")
    print("  12 sheets per junction, grouped 4-4-4: Left x4 arms, Straight x4, Right x4.")
    print("  Every figure re-derived from the issued workbooks; nothing synthetic.\n")
    ok = 0
    for code, got, want in checks:
        match = got == want
        ok += match
        print(f"  {SCHEME_LABEL[code]}  {code}  12 sheets  "
              f"day-1 vehicles {got:>8,}  parse {want:>8,}  "
              f"{'OK' if match else 'MISMATCH'}")
    print(f"\n  GATE - books whose 12 sheets reconcile exactly with the parse: "
          f"**{ok} of {len(checks)}**")
    if ok != len(checks):
        raise SystemExit("a book does not reconcile with the parsed source")
    print(f"\nwritten: {BOOKS}/  ({len(made)} workbooks)")
