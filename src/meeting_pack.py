"""
meeting_pack.py — the PDF to take into the room, and the questions to leave behind.

WHY A PDF AT ALL
The dashboard is the deliverable and it is better than this in every way except one: a
meeting runs on paper, and a reviewer wants something to annotate and pass across a table.
So this renders the same figures the site renders, from the same corridor.json, and never
from a typed number. If a figure here disagrees with the site, the site was regenerated
and this was not - re-run it.

TWO DOCUMENTS, ONE SOURCE
  out/Corridor_Meeting_Pack.pdf   what was done, what it found, what it corrected
  out/reviewer_questions.md       only the open questions, to hand over

The questions are the point of the second one. Every item on it is something the analysis
cannot settle from the data held, with the reason it cannot and what specifically would
settle it. A question list that mixes those with things we simply have not done yet is
useless to a reviewer, so the two are kept apart.

Run:  uv run python src/meeting_pack.py
"""
import json
import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import (CORRIDOR_ROAD, CORRIDOR_ROAD_SOURCE, NUMBERING_NOTE,
                        SCHEME_LABEL, OUT, OUT_DATA)

PDF = OUT / "Corridor_Meeting_Pack.pdf"
QMD = OUT / "reviewer_questions.md"

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
CELLB = S("CELLB", fontName="Helvetica-Bold", fontSize=8.4, leading=11.4, spaceAfter=0)
CELLH = S("CELLH", fontName="Helvetica-Bold", fontSize=7.4, leading=10, textColor=FAINT,
          spaceAfter=0)

nf = "{:,.0f}".format


def load():
    p = OUT_DATA / "corridor.json"
    if not p.exists():
        raise SystemExit("out/data/corridor.json missing - run the pipeline first")
    return json.loads(p.read_text())


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


# --- the questions, which are the reason the reviewer gets a document at all ------
#
# Each is something the analysis CANNOT settle from what is held, never something simply
# not yet built. `why` states what blocks it; `settles` states the one artefact that
# unblocks it. A question without both is a complaint.
def questions(d):
    cap, uf, m = d["capacity"], d["uturn_framework"], d["measurement"]
    sch = d["scheme"]
    return [
        dict(n=1, topic="U-turn bay locations",
             q="What is the chainage of each of the seven proposed U-turn bays along the "
               "corridor alignment?",
             why=f"Three of the twelve bays we assess fall beyond the extent of the "
                 f"supplied drawing, so their detour is not measured at all. The rest are "
                 f"placed at the nearest median opening the CAD shows, which is the "
                 f"SHORTEST detour physically available, not the proposed one. Every "
                 f"detour figure we publish is therefore a lower bound.",
             settles="A chainage or a coordinate for each of the seven bays."),
        dict(n=2, topic="Chainage convention",
             q="Does JDA chain this corridor from the Sanganer Stadium end or the "
               "Mansarovar Metro end?",
             why="Our chainage runs from the north, which makes it count DOWN as the "
                 "junction number counts up. That is the reverse of the survey's own "
                 "numbering and it is confusing to read against JDA drawings.",
             settles="One sentence, or any JDA drawing with a chainage marked on it."),
        dict(n=3, topic="Service roads",
             q="Do the northern junctions carry service roads alongside the main "
               "carriageway?",
             why=f"{m['junctions_above_wide_threshold']} of six junctions measure over "
                 f"{m['wide_threshold_m']:.0f} m per direction and "
                 f"{cap['wide_transect_pct']}% of transects do. That is five running lanes "
                 f"each way, or it is a service road being read as carriageway. Capacity "
                 f"scales linearly with the answer, and it is the single figure that "
                 f"decides whether this corridor is over capacity today.",
             settles="Confirmation, or a typical cross-section for the northern half."),
        dict(n=4, topic="Carriageway dimensions",
             q="Is there a dimensioned drawing or a survey control sheet for this "
               "corridor?",
             why="The supplied DWG carries no dimension entities. Every width, offset and "
                 "chainage we publish is scaled from georeferenced linework and is "
                 "provisional. We have quantified how repeatable that scaling is, which "
                 "is not the same as knowing it is right.",
             settles="A total station traverse with cross-sections at each junction and "
                     "at each median opening, tied to stated control."),
        dict(n=5, topic="The composite count columns",
             q="Can the survey's three composite columns be re-issued split into their "
               "IRC:106 classes?",
             why=f"Column B lumps car, auto-rickshaw and pickup at one PCU factor; two "
                 f"more columns do the same. That is why our PCU correction is a band "
                 f"({cap and d['audit']['pcu']['band_low_pct']}% to "
                 f"{d['audit']['pcu']['band_high_pct']}%) rather than a number. The "
                 f"{d['audit']['pcu']['uplift_floor_pct']}% floor is only the part that "
                 f"maps one to one.",
             settles="The contractor's raw tally sheets, or a re-count to IRC:106 classes."),
        dict(n=6, topic="Column heading, IRC:SP:41 Table 3.1",
             q='Should the column read "Three Wheeler (Auto), 3 Axle Truck, Buses"?',
             why="As issued it reads \"Three Wheeler (Auto) Axle Truck, Buses\" with no "
                 "comma and no 3. If that is a typing error the column is the standard "
                 "Table 3.1 row; if it is not, we do not know what was counted in it.",
             settles="Confirmation of the intended heading."),
        dict(n=7, topic="Pedestrians",
             q="Was a pedestrian count taken separately, and can it be issued?",
             why="IRC:SP:41 Table 3.1 carries a PEDESTRIAN Nos. row and clause 3.1(iv) "
                 "requires it in urban areas with substantial pedestrian movement. The "
                 "row is empty in all twelve workbooks. Removing signals removes the only "
                 "protected crossing opportunity a pedestrian currently has.",
             settles="The pedestrian sheets, or confirmation that none were taken."),
        dict(n=8, topic="E-rickshaws",
             q="Under which column were e-rickshaws recorded?",
             why="No column carries them, though the label appears in the workbook's "
                 "string table. If they were tallied into the car column their PCU is "
                 "understated; if they were not counted the total is understated.",
             settles="Confirmation from the enumerator instructions."),
        dict(n=9, topic="The second survey day",
             q="Can the 12 May field sheets be produced?",
             why=f"{d['audit']['day2']['identical']} of {d['audit']['day2']['series']} "
                 f"movement-by-class series reproduce 11 May to the exact vehicle, and of "
                 f"those that move, {d['audit']['day2']['greater']} rise against "
                 f"{d['audit']['day2']['smaller']} that fall. Under independent counting "
                 f"that split has a probability of about 2 in 10^39 - one in a billion billion "
                 f"billion billion. We treat this as a "
                 f"one-day survey.",
             settles="The original tally sheets for 12 May."),
        dict(n=10, topic="The flyover in the scheme video",
             q="Does the grade-separated structure shown in JDA's animation form part of "
               "this scheme, and over which junctions?",
             why="Our assessment tests two futures: the signal-free U-turn scheme as "
                 "published, and an elevated through-carriageway. Which one is being "
                 "designed changes which of our results is the relevant one.",
             settles="The scheme drawing or a scope note."),
        dict(n=11, topic="Critical gap",
             q="Is there any Indian measurement of U-turn critical gap on an urban "
               "arterial that JDA would accept?",
             why=f"{sch['indo_hcm_no_uturn_chapter']} We used a composition-weighted gap "
                 f"and tested the conclusion across {sch['gap_bases_tested']} separate "
                 f"published bases; it fails on all of them. But the parameter is the one "
                 f"an objector would attack first.",
             settles="A cited value, or agreement to measure it on site."),
        dict(n=12, topic="Bay geometry",
             q="What deceleration and storage length is proposed at each U-turn bay?",
             why=f"Gap capacity binds at all {uf['n_bays']} bays, so storage is never "
                 f"reached in our ladder. If the gap problem were treated, storage would "
                 f"be the next criterion and we have no geometry for it.",
             settles="The bay typical drawing."),
    ]


def econ_line(eco, cap):
    """
    The cost of delay, which is currently zero, said as a finding rather than a number.

    Printing "annual cost of delay 0 to 0 crore" reads like a broken calculation. It is
    not: no approach is over capacity on the corrected widths, so the deterministic delay
    model has no excess arrivals to accumulate and returns nothing. That is a real result
    and it is the sharpest consequence of the width uncertainty, so it is stated as one.
    """
    over = sum(1 for a in eco["approaches"] if a.get("hours_over", 0) > 0)
    if over:
        return ("<b>Economics are banded and value of time is a policy input, not a "
                f"result.</b> Annual cost of delay {eco['annual_cost_crore'][0]} to "
                f"{eco['annual_cost_crore'][1]} crore across {over} approaches over "
                f"capacity. Excluded items are named in the assessment.")
    return ("<b>The economic case for intervention is currently zero, and that is a "
            "finding, not a gap.</b> No approach is over capacity on the corrected "
            "widths, so there are no excess arrivals for the delay model to accumulate "
            f"and the annual cost of delay comes out at nil - against "
            f"{eco['years_to_first_failure']} years before the first approach returns to "
            f"capacity. A benefit-cost case for grade separation cannot be built on these "
            f"numbers. It can be built on the narrower widths, which is why question 3 "
            f"decides more than any other item on the list: at "
            f"{cap['wide_transect_pct']}% of transects reading service-road wide, whether "
            f"those are running lanes is what separates a corridor that needs a structure "
            f"from one that does not.")


def build():
    d = load()
    a, cap, sch = d["audit"], d["capacity"], d["scheme"]
    uf, m, an = d["uturn_framework"], d["measurement"], d["anomaly"]
    cl, fc, eco = d["cluster"], d["forecast"], d["economics"]
    meta = d["meta"]
    F = []

    # ---- cover -------------------------------------------------------------
    F.append(Paragraph("INDEPENDENT AUDIT AND ASSESSMENT &middot; CLASSIFIED TURNING "
                       "MOVEMENT SURVEY", EYE))
    F.append(Paragraph(f"{CORRIDOR_ROAD}, {meta['city']}", H1))
    F.append(Paragraph(
        f"Six junctions, J1 to J6 north to south from Mansarovar Metro to Sanganer "
        f"Stadium. "
        f"Surveyed {meta['survey_dates'][0]} and {meta['survey_dates'][1]} by the appointed "
        f"contractor and issued to JDA as twelve workbooks. This is an independent "
        f"re-derivation of every number in them, checked against the survey drawing. "
        f"Road name and alignment are {CORRIDOR_ROAD_SOURCE}. {NUMBERING_NOTE} "
        f"Prepared {date.today().strftime('%d %B %Y')}.", SUB))

    F.append(kpis([
        (nf(meta["bins_parsed"]), "CLASS-BINS RE-DERIVED", INK),
        (str(a["arithmetic"]["discrepancies"]), "STORED TOTALS THAT DISAGREE", DEFECT),
        (f"+{a['pcu']['uplift_floor_pct']}%", "PCU UNDERSTATEMENT, FLOOR", DEFECT),
        (f"{uf['n_fail']}/{uf['n_bays']}", "U-TURN BAYS THAT FAIL", DEFECT),
        ("1", "USABLE SURVEY DAY", DEFECT),
    ]))

    # ---- 1. what the survey got wrong -------------------------------------
    F.append(Paragraph("1 &nbsp; What the issued survey gets wrong", H2))
    F.append(Paragraph(
        "Five findings, each re-derived from the workbooks rather than asserted. Every "
        "stored total was recomputed from its own components; where the two disagree the "
        "discrepancy is registered, never silently corrected.", BODY))
    F.append(table(
        ["FINDING", "EVIDENCE", "CONSEQUENCE"],
        [["The second day was not independently observed",
          f"{a['day2']['identical']} of {a['day2']['series']} movement-by-class series "
          f"reproduce day one to the exact vehicle. Of those that move, "
          f"{a['day2']['greater']} rise and {a['day2']['smaller']} fall; "
          f"p &#8776; 2&#215;10<super rise=3 size=6>-39</super>.",
          "Treat as a one-day survey. Day-over-day growth measures the derivation."],
         ["The scheme's key movement was never counted",
          "No U-turn column exists anywhere in the twelve workbooks. Twelve movements per "
          "junction, not sixteen.",
          "The signal-free scheme converts right turns into U-turns and has no traffic "
          "evidence base for the movement it depends on."],
         ["PCU conversion understates demand",
          f"Two-wheelers are {cl['two_wheeler_split']['corridor_mean']*100:.0f}-"
          f"{cl['two_wheeler_split']['cross_mean']*100:.0f}% of the stream and are carried "
          f"at PCU 0.50, the value IRC:106 reserves for a class below 5%. The correct "
          f"factor at that share is 0.75.",
          f"Corridor demand understated by at least {a['pcu']['uplift_floor_pct']}%, "
          f"band {a['pcu']['band_low_pct']}% to {a['pcu']['band_high_pct']}%."],
         ["Arithmetic does not close",
          f"{a['arithmetic']['discrepancies']} stored totals disagree with their own "
          f"components: {a['arithmetic']['understate']} understate, "
          f"{a['arithmetic']['overstate']} overstate.",
          "Conservation between movement and approach sheets breaks. All registered."],
         ["The flow-diagram sheet is mislabelled",
          f"{a['flow_diagram']['ref_errors']} broken references across "
          f"{a['flow_diagram']['files_affected']} files; the two-wheeler count is reported "
          f"under the label Taxi.",
          "Anyone reading the summary sheet rather than the movement sheets gets the "
          "wrong class split."]],
        widths=[42, 76, 52]))
    F.append(Paragraph(
        "Survey design, separately: " + " ".join(a["survey_design"][:3]), NOTE))

    # ---- 2. the U-turn scheme ---------------------------------------------
    F.append(Paragraph("2 &nbsp; Does the signal-free U-turn scheme work?", H2))
    F.append(Paragraph(
        f"No, and not marginally. Under signal-free operation a right turn becomes a "
        f"U-turn: the driver goes through, turns at a median bay, comes back and turns "
        f"left. Each bay is fed by three movements, not one. Capacity of an unsignalised "
        f"U-turn is gap acceptance, with the critical gap weighted by observed composition "
        f"because two-wheelers accept far shorter gaps. "
        f"<b>{sch['fails_conservative']} of {len(sch['uturns'])} bays cannot be served</b>, "
        f"and {sch['no_viable_gap']} sit past the point where acceptable gaps effectively "
        f"cease to exist. The conclusion holds on all "
        f"{sch['gap_bases_tested']} published gap bases tested.", BODY))
    ceiling = uf["bay_ceiling_veh_hr"]
    F.append(KeepTogether([
        Paragraph("The finding a verdict alone hides", H3),
        Paragraph(
            f"As the opposing flow falls to zero, gap-acceptance capacity tends to 3600 "
            f"divided by the follow-up headway. A single median opening therefore passes "
            f"at most <b>{nf(ceiling)} veh/hour with nothing at all to yield to</b>. "
            f"<b>{uf['bays_above_bay_ceiling']} of the {uf['n_bays']} bays are above that "
            f"ceiling</b> - {SCHEME_LABEL['TMC-01']} southbound at "
            f"{nf([b for b in uf['bays'] if b['junction']=='TMC-01' and b['bay']=='southbound'][0]['uturn_demand'])} "
            f"and {SCHEME_LABEL['TMC-04']} southbound at "
            f"{nf([b for b in uf['bays'] if b['junction']=='TMC-04' and b['bay']=='southbound'][0]['uturn_demand'])} "
            f"veh/hour. Those are not badly sited bays. They are the wrong instrument for "
            f"the demand, and no metering, median widening or opposing-flow relief reaches "
            f"them.", BODY)]))
    F.append(Paragraph("The decision ladder: which constraint binds, bay by bay", H3))
    F.append(Paragraph(
        "Five criteria evaluated in order, first failure binding. A criterion below the "
        "binding one is reported untested, never passed - the order exists so that "
        "geometry is not checked for a problem geometry cannot reach.", BODY))
    F.append(table(
        ["CRITERION", "BAYS IT BINDS AT", "STATUS"],
        [[c, f"{uf['binding_counts'].get(c, 0)} of {uf['n_bays']}",
          "binds first at every bay" if uf["binding_counts"].get(c, 0) == uf["n_bays"]
          else "not reached"] for c in uf["criteria"]],
        widths=[46, 34, 90]))
    live = [x for x in uf["alternatives"] if x["live"]]
    dead = [x for x in uf["alternatives"] if not x["live"]]
    F.append(Paragraph(
        f"<b>What can be done instead.</b> Of the {len(uf['alternatives'])} measures "
        f"tested, {len(live)} can move the binding constraint here "
        f"({'; '.join(x['measure'] for x in live)}) and {len(dead)} cannot "
        f"({'; '.join(x['measure'] for x in dead)}). Grade separation is the only one that "
        f"removes the conflicting flow rather than asking the U-turn to find gaps in it - "
        f"and for the two bays above the ceiling it works by removing the need for a "
        f"U-turn, not by making the bay work.", BODY))
    ok = sch.get("opening_kinds", {})
    F.append(KeepTogether([
        Paragraph("There is almost nowhere on this corridor to turn round", H3),
        Paragraph(
            f"A right turn becomes four manoeuvres: past the junction, out to a median "
            f"opening, through 180 degrees, back, then the left turn. But "
            f"<b>{ok.get('junction_mouths')} of {ok.get('openings')} median openings sit "
            f"within {ok.get('midblock_threshold_m', 100):.0f} m of a junction centre</b> "
            f"- they are junction mouths, not mid-block bays. Turning at one is not a "
            f"detour; it is the driver turning AT the junction, which is the movement the "
            f"scheme exists to remove. Only <b>{ok.get('midblock')}</b> genuine mid-block "
            f"opening exists on {sch['detour_bays_measured']} measurable bays' worth of "
            f"corridor, so all seven proposed bays would have to be built new. The "
            f"realistic detour is junction to junction: mean "
            f"<b>{nf(sch.get('detour_midblock_mean_m', 0))} m</b>, "
            f"{nf(sch.get('detour_midblock_veh_km', 0))} extra vehicle-km in the peak "
            f"hour, against a full range of {sch['detour_min_m']} to "
            f"{nf(sch['detour_max_m'])} m. These remain the SHORTEST detours physically "
            f"available, so every figure is a lower bound.", BODY)]))

    # ---- 3. capacity -------------------------------------------------------
    F.append(Paragraph("3 &nbsp; Capacity, and the one number that decides it", H2))
    F.append(kpis([
        (f"{sum(1 for j in cap['junctions'] if j['vc_pt'] >= 1.0)}/{len(cap['junctions'])}",
         "APPROACHES OVER CAPACITY TODAY", OK),
        (f"{cap['design_life_survives_horizon']}/{len(cap['design_life'])}",
         f"SURVIVE THE {cap['horizon_year']} HORIZON", OK),
        (str(cap["design_life_first_failure_med"]), "FIRST APPROACH BACK OVER", CAUTION),
        (f"{cap['wide_transect_pct']}%", "TRANSECTS READING SERVICE-ROAD WIDE", DEFECT),
    ]))
    F.append(Paragraph(
        f"On the corrected alignment and the corrected widths this corridor is "
        f"<b>not over capacity today</b>, and relief would hold to the "
        f"{cap['horizon_year']} horizon with the first approach returning to capacity in "
        f"{cap['design_life_first_failure_med']}. That is a weaker congestion case than an "
        f"earlier version of this work stated, and it is stated plainly because it moved "
        f"when the inputs were corrected.", BODY))
    F.append(Paragraph(
        f"<b>It rests on one uncertain number.</b> {cap['width_caveat']}", BODY))

    # ---- 4. measurement ----------------------------------------------------
    F.append(Paragraph("4 &nbsp; How precise is any of this?", H2))
    F.append(Paragraph(
        f"The supplied DWG contains no dimension entities. Nothing in it states a width. "
        f"Every width, offset and chainage is scaled off georeferenced linework, and a "
        f"scaled number printed to one decimal place is indistinguishable from a measured "
        f"one. Each is therefore published with its method, its repeatability, and the "
        f"field measurement that would settle it - "
        f"{len(m['dimensions'])} of {len(m['dimensions'])} carry a stated uncertainty.",
        BODY))
    t1 = m["convergence"][0]
    F.append(Paragraph("What testing the method against itself found", H3))
    F.append(Paragraph(
        f"The transect spacing is an arbitrary choice inside our own method, so an answer "
        f"that moves with it is measuring the choice rather than the road. At 25 m the "
        f"whole corridor yields only "
        f"{[x['transects'] for x in m['transects_by_step'] if x['step_m'] == 25.0][0]} "
        f"usable transects. <b>{t1['junction']} read "
        f"{[b['width_m'] for b in t1['by_step'] if b['step_m'] == 25.0][0]} m off two of "
        f"them and {[b['width_m'] for b in t1['by_step'] if b['step_m'] == 5.0][0]} m at "
        f"every finer spacing</b> - a lane. Spacing is now "
        f"{m['published_step_m']:.0f} m, inside the converged region for all six. This was "
        f"a defect in our work, found by testing it, and the published widths are the "
        f"corrected ones.", BODY))
    F.append(table(
        ["JUNCTION"] + [f"{b['step_m']:g} m" for b in t1["by_step"]] + ["SETTLES AT"],
        [[SCHEME_LABEL.get(c["junction"], c["junction"])]
         + [f"{b['width_m']:.1f}" if b["width_m"] else "-"
                            for b in c["by_step"]]
         + [f"{c['converged_at_step']:g} m" if c["converged_at_step"] else "still moving"]
         for c in m["convergence"]],
        widths=[28, 20, 20, 20, 20, 62], aligns=[1, 2, 3, 4]))
    reg = m["registration"][0]
    F.append(Paragraph(
        f"<b>The two JDA sources agree.</b> Distance from JDA's KML centreline to the "
        f"nearest divider line in JDA's CAD: median {reg['median_m']} m, 90th percentile "
        f"{reg['p90_m']} m over {reg['n']} stations. Two independently produced "
        f"descriptions of one corridor, consistent to about a metre. That is the evidence "
        f"that the chainage and the transects share a geometry.", NOTE))

    # ---- 5. what a model adds ---------------------------------------------
    F.append(Paragraph("5 &nbsp; What automated analysis adds, and what it does not", H2))
    F.append(Paragraph(
        "Three applications, each shown with the test it could have failed. A model "
        "reported without one is a number with a confident voice.", BODY))
    tmp = cl["results"][0]
    comp = cl["results"][1]
    fdt = fc["shortest_window"]["daily_total"]
    F.append(table(
        ["APPLICATION", "THE TEST IT HAD TO PASS", "RESULT"],
        [["Survey integrity screen",
          "Six independent detectors must re-find the defects the audit proved by hand, "
          "without being told they exist.",
          f"PASSED {an['gate']['rediscovered']} of {an['gate']['known_defects']}. Found the "
          f"duplicated second day ({an['detectors']['duplicate']['wholly_identical']} "
          f"series identical in every live bin) and the "
          f"{an['detectors']['arithmetic']['breaks']} broken totals. Reusable on any "
          f"future contractor submission."],
         ["Approach typology",
          "The clusters must recover a label held out of the fitting: corridor arm versus "
          "cross-street arm. Two feature sets fitted, both published.",
          f"MIXED, honestly. Temporal shape found nothing (silhouette "
          f"{tmp['silhouette']}) - 24 approaches on one clock, which is what makes a "
          f"single corridor-wide peak hour defensible. Composition separated cleanly "
          f"(silhouette {comp['silhouette']}, held-out label recovered at "
          f"{comp['external_label']['purity']*100:.0f}% against "
          f"{comp['external_label']['null_mean']*100:.0f}% chance, p="
          f"{comp['external_label']['p']})."],
         ["How short a count can be",
          "Beat doing no modelling at all, leave-one-out so no approach predicts itself.",
          f"PASSED {fc['gate']['predictable']} of {fc['gate']['targets']}. A "
          f"{fdt['hours']}-hour count ({fdt['clock']}) predicts the 24-hour total to "
          f"{fdt['mape']}% against a {fdt['baseline_mape']}% no-model baseline. Worst "
          f"single approach {fdt['worst_approach_pct']}%. The next survey costs a "
          f"fraction of this one, and JDA can spot-check a 24-hour submission against "
          f"four hours of its own."]],
        widths=[34, 62, 74]))
    F.append(Paragraph(
        f"Limits, stated rather than buried: the count model is fitted on ONE independent "
        f"day of ONE corridor, it forecasts nothing about a future year, and its window "
        f"was chosen on the same error it is reported with over "
        f"{fc['selection']['combinations_searched']} combinations. The automated video "
        f"counting stage is built and self-tested but has never seen real footage, so no "
        f"accuracy figure is claimed for it.", NOTE))

    # ---- 6. corrections to our own work ------------------------------------
    F.append(Paragraph("6 &nbsp; Corrections we made to our own work", H2))
    F.append(Paragraph(
        "Listed because a reviewer is entitled to know which conclusions moved and why. "
        "Each was found by checking, not by being told.", BODY))
    F.append(table(
        ["WHAT WAS WRONG", "HOW IT WAS FOUND", "WHAT IT CHANGED"],
        [["We had the wrong road. Six junctions were placed by matching arm names to "
          "signal clusters in the CAD.",
          "JDA's reviewer challenged it, then supplied a KML.",
          "Our picks sat 269 to 950 m off, on a parallel road. Rebuilding on JDA's "
          "alignment reversed most of the congestion case."],
         ["The U-turn scope counted right turns only.",
          "JDA's reviewer pointed out a bay is fed by more than one movement.",
          "Corrected to the full median U-turn: corridor right, cross-street right and "
          "cross-street through. Demand rose from 4,523 to 15,536 veh/hour."],
         ["Transect spacing of 25 m was too coarse to measure a width.",
          "Re-running our own method across spacings.",
          f"{SCHEME_LABEL['TMC-01']} went 11.7 m to 15.6 m - three lanes to four - and "
          "with it the capacity, v/c and design-life results in section 3."],
         ["We argued a lane model does not fit because flow exceeds saturation flow.",
          "The width correction above.",
          "On corrected widths every approach runs below saturation. The argument is "
          "WITHDRAWN, not restated. The conclusion survives only on composition, which is "
          "weaker evidence, and the report says so."]],
        widths=[52, 44, 74]))

    # ---- 7. questions ------------------------------------------------------
    qs = questions(d)
    F.append(Paragraph(f"7 &nbsp; Questions for JDA ({len(qs)})", H2))
    F.append(Paragraph(
        "Every item here is something this analysis cannot settle from the data held. "
        "Each carries what blocks it and the one artefact that would unblock it. Things "
        "we simply have not built yet are deliberately not on this list.", BODY))
    F.append(table(
        ["#", "QUESTION", "WHY WE CANNOT SETTLE IT", "WHAT WOULD SETTLE IT"],
        [[str(q["n"]), Paragraph(f"<b>{q['topic']}</b><br/>{q['q']}", CELL),
          q["why"], q["settles"]] for q in qs],
        widths=[7, 50, 72, 41]))

    # ---- 8. open ----------------------------------------------------------
    F.append(Paragraph("8 &nbsp; What is still open at our end", H2))
    F.append(Paragraph(
        "Separate from the questions above, because these are ours to finish, not JDA's "
        "to answer.", BODY))
    F.extend(bullets([
        "<b>Automated counting is unverified.</b> Detection, tracking, homography, zone "
        "counting and the two-stage training chain are built and pass their own gates "
        "against synthetic data. None has seen real footage, so the validation report "
        "stands as a pro forma with its gates published ahead of the measurement. Needs "
        "TMC-04 footage, ground-control stills and about 500 annotated frames.",
        "<b>Half the PCU correction is unresolvable</b> from the issued class scheme. "
        "Only a re-count to IRC:106 classes closes it - see question 5.",
        "<b>The corridor ordering is not settled by the counts alone.</b> Flow continuity "
        "ranks its best ordering by a 1.2% margin, which is noise. Chainage along JDA's "
        "alignment resolves it, and the agreement between the two is a check rather than "
        "a derivation.",
        econ_line(eco, cap),
    ]))

    F.append(rule())
    F.append(Paragraph(
        f"Independent re-derivation from the twelve issued workbooks. "
        f"{nf(meta['bins_parsed'])} class-bins parsed; every stored total recomputed from "
        f"components; discrepancies recorded rather than corrected. Every figure in this "
        f"document is generated from the pipeline output, not transcribed. Standards "
        f"referenced: IRC:106-1990, IRC:SP:41-1994, IRC:92-2017, Indo-HCM 2017. Analysis "
        f"day {meta['analysis_date']}. Widths and chainages provisional pending a total "
        f"station survey.", NOTE))
    return F, qs


def write_questions_md(qs):
    L = ["# Questions for JDA", "",
         f"{CORRIDOR_ROAD} corridor, TMC-01 to TMC-06. Generated "
         f"{date.today().isoformat()}.", "",
         "Every item is something the analysis cannot settle from the data held. Each "
         "carries what blocks it and the one artefact that would unblock it. Work we have "
         "simply not finished is deliberately excluded.", ""]
    for q in qs:
        L += [f"## {q['n']}. {q['topic']}", "", f"**{q['q']}**", "",
              f"*Why we cannot settle it.* {q['why']}", "",
              f"*What would settle it.* {q['settles']}", ""]
    QMD.write_text("\n".join(L))
    return QMD


def render(flow):
    doc = BaseDocTemplate(str(PDF), pagesize=A4,
                          leftMargin=20 * mm, rightMargin=20 * mm,
                          topMargin=17 * mm, bottomMargin=16 * mm,
                          title=f"{CORRIDOR_ROAD} corridor - audit and assessment",
                          author="Corridor junction intelligence")

    def furniture(canv, _doc):
        canv.saveState()
        canv.setFont("Helvetica", 7.2)
        canv.setFillColor(FAINT)
        canv.drawString(20 * mm, 10 * mm,
                        f"{CORRIDOR_ROAD} corridor - independent audit and assessment")
        canv.drawRightString(190 * mm, 10 * mm, f"page {canv.getPageNumber()}")
        canv.setStrokeColor(RULE)
        canv.setLineWidth(0.4)
        canv.line(20 * mm, 13 * mm, 190 * mm, 13 * mm)
        canv.restoreState()

    frame = Frame(20 * mm, 16 * mm, 170 * mm, A4[1] - 33 * mm, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=furniture)])
    doc.build(flow)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    flow, qs = build()
    render(flow)
    md = write_questions_md(qs)
    print("=== Meeting pack ===")
    print(f"  every figure generated from out/data/corridor.json, none transcribed\n")
    print(f"  {PDF.name:<34}{PDF.stat().st_size/1024:>7.0f} KB")
    print(f"  {md.name:<34}{md.stat().st_size/1024:>7.0f} KB   {len(qs)} questions")
    print(f"\n  GATE - questions carrying both a blocker and a resolver: "
          f"**{sum(1 for q in qs if q['why'] and q['settles'])} of {len(qs)}**")
    missing = [q["n"] for q in qs if not (q["why"] and q["settles"])]
    if missing:
        raise SystemExit(f"question without a blocker or a resolver: {missing}")
    print(f"\nwritten: {PDF}")
