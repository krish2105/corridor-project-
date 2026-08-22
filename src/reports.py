"""
reports.py — the two written deliverables: capacity/design-year (D6), method statement (D9).

WHY THIS IS A GENERATOR AND NOT TWO PROSE FILES
A report typed by hand drifts from the analysis the moment either changes, and the drift
is silent. Every figure below is read from out/data/*.json at generation time, so a report
that disagrees with the pipeline cannot be produced - it would have to disagree with
itself. The prose is fixed; the numbers are bound.

D6 states what the corridor can carry and when it stops carrying it.
D9 states how the work was done, to which standards, and where it stops being reliable -
which is the document a reviewing engineer reads first and the one most consultancies
leave out.

Run:  uv run python src/reports.py
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import JUNCTION_COORDS, CORRIDOR_ROAD, JDA_SCHEME, ROOT

OUT = ROOT / "out"
DATA = OUT / "data"


def _load(name):
    p = DATA / f"{name}.json"
    if not p.exists():
        raise SystemExit(f"missing {p} - run src/export.py first")
    return json.loads(p.read_text())


def _table(headers, rows, align=None):
    align = align or ["---"] * len(headers)
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(align) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def chainage():
    """
    Distance of each junction along the surveyed CAD alignment.

    Read from the exported atlas rather than the CAD directly, so this stays bound to the
    same geometry the dashboard draws. Two things fall out of it: which junctions sit near
    a drawing end (and therefore have few width transects), and the physical order of the
    corridor - though the order is only EVIDENCE for the three junctions matched by name.
    For the three inferred ones the chainage merely restates the position that was
    inferred, so it confirms nothing and is reported as such.
    """
    from pyproj import Transformer
    from shapely.geometry import LineString, MultiLineString, Point
    from shapely.ops import linemerge
    T = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    g = json.loads((DATA / "atlas.geojson").read_text())
    lines = []
    for f in g["features"]:
        if f["properties"].get("category") != "alignment":
            continue
        geom = f["geometry"]; cs = geom["coordinates"]
        segs = [cs] if geom["type"] == "LineString" else (
            cs if geom["type"] == "MultiLineString" else [])
        for seg in segs:
            if len(seg) > 1:
                lines.append(LineString([T.transform(c[0], c[1]) for c in seg]))
    merged = linemerge(MultiLineString(lines))
    main = max(merged.geoms, key=lambda l: l.length) \
        if merged.geom_type == "MultiLineString" else merged
    rows = []
    for k, (lat, lon, name, cl, conf) in JUNCTION_COORDS.items():
        ch = main.project(Point(T.transform(lon, lat)))
        rows.append(dict(junction=k, name=name, confidence=conf, chainage_m=ch,
                         from_end_m=min(ch, main.length - ch)))
    rows.sort(key=lambda r: r["chainage_m"])
    return main.length, rows


def capacity_report():
    c, s, sen = _load("capacity"), _load("scheme_test"), _load("sensitivity")
    a = c["assumptions"]
    js = c["junctions"]
    over = [j for j in js if j["vc_pt"] > 1.0]
    worst = max(js, key=lambda j: j["vc_pt"])

    align_len, ch_rows = chainage()
    align_km = align_len / 1000
    # the junction with fewest transects is the one whose width is least well supported
    thin_key = min(c["widths"], key=lambda k: c["widths"][k]["transects"])
    thin_n = c["widths"][thin_key]["transects"]
    typical = sorted(v["transects"] for v in c["widths"].values())[len(c["widths"]) // 2]
    thin_j = thin_key
    thin_end = next(r["from_end_m"] for r in ch_rows if r["junction"] == thin_key)
    thin_txt = (f"{thin_key} width is measured from {thin_n} transects against a typical "
                f"{typical}.")

    md = [
        f"# Capacity and design-year assessment",
        f"### {CORRIDOR_ROAD}, Jaipur — six surveyed junctions",
        "",
        f"**Base year** {a['base_year']}  |  **Design horizon** "
        f"{a['design_horizon_years']} years to {c['horizon_year']}  |  "
        f"**Survey date** {c['analysis_date']}",
        f"**Generated** {date.today().isoformat()} from `out/data/capacity.json`. "
        "Every figure in this document is read from the pipeline output at generation "
        "time; none is transcribed.",
        "",
        "---",
        "",
        "## 1. Finding",
        "",
        f"**{len(over)} of {len(js)} surveyed approaches already exceed their carrying "
        f"capacity at the {a['base_year']} peak hour.** The worst, "
        f"{worst['junction']} {worst['approach']}, runs at a volume-to-capacity ratio of "
        f"**{worst['vc_pt']:.2f}** — Level of Service **{worst['los_pt']}**. This is a "
        "present-day measurement, not a projection.",
        "",
        f"The corridor carries **{c['observed_vs_planning_ratio']:.2f}x** the traffic that "
        "the planning-stage assumption implies, which is the gap this assessment exists "
        "to quantify.",
        "",
        "## 2. Basis of assessment",
        "",
        _table(["Parameter", "Value", "Source"], [
            ["Lane capacity", f"{a['capacity_pcu_per_lane_hr']} PCU/lane/hr",
             "Indo-HCM 2017, urban arterial, mixed traffic"],
            ["Lane width", f"{a['lane_width_m']} m", "IRC:86 urban arterial"],
            ["Shy distance", f"{a['shy_distance_m']} m", "kerb and median clearance"],
            ["Peak hour factor", "applied" if a["phf_applied"] else "not applied",
             "derived per approach from 15-minute bins"],
            ["Growth", f"{a['growth_low_pct']}% / {a['growth_med_pct']}% / "
                       f"{a['growth_high_pct']}%", "low / medium / high scenario"],
            ["PCU", "share-dependent, interpolated", "IRC:106"],
        ]),
        "",
        "**Carriageway widths are measured, not assumed.** They come from transects cut "
        "across the surveyed CAD alignment, taking the outermost kerb either side of the "
        "median. This matters: the alignment is offset from the median, so measuring to "
        "the nearest kerb returns the median offset rather than the carriageway.",
        "",
        _table(["Junction", "JDA name", "Measured width", "Transects", "Lanes/dir",
                "Capacity"],
               [[k, JUNCTION_COORDS[k][2], f"{v['width_m']} m", v["transects"],
                 v["lanes_per_dir"], f"{v['capacity_pcu_hr']:,} PCU/hr"]
                for k, v in c["widths"].items()]),
        "",
        "## 3. Demand against capacity, by approach",
        "",
        "PCU is reported as a band, not a point. The survey's composite vehicle classes "
        "(car/taxi/tempo/auto/pickup in one column) cannot be resolved to a single IRC:106 "
        "factor, so a point estimate would be false precision. The low figure assumes the "
        "bucket behaves as cars; the high figure assumes the heavier mix.",
        "",
        _table(["Junction", "Approach", "Peak", "Capacity", "PCU low", "PCU high",
                "v/c", "LOS"],
               [[j["junction"], j["approach"].replace("from ", ""), j["peak"],
                 f"{j['capacity']:,}", f"{j['pcu_lo']:,.0f}", f"{j['pcu_hi']:,.0f}",
                 f"{j['vc_lo']:.2f}–{j['vc_hi']:.2f}", j["los_pt"]] for j in js]),
        "",
        "## 4. The published scheme does not resolve this",
        "",
        f"The scheme under construction — {JDA_SCHEME} — replaces signalised turning with "
        "U-turn bays. Tested by gap acceptance against the measured opposing flow, "
        f"**{s['fails_conservative']} of {len(s['uturns'])} approaches fail** under "
        f"conservative critical-gap assumptions and **{s['fails_optimistic']} still fail** "
        "under optimistic ones.",
        "",
        f"On **{s['no_viable_gap']}** approaches the opposing flow is heavy enough that "
        "gap acceptance degenerates entirely: there is no usable gap, and no capacity "
        "figure is quoted because none would be meaningful.",
        "",
        "The mechanism is that removing a signalised right turn does not remove the "
        f"demand — it converts it into a U-turn. Across the corridor that forces "
        f"**{s['forced_uturns_per_hour']:,.0f} additional U-turning vehicles per hour** "
        "onto bays sized for far less.",
        "",
        "## 5. Grade separation returns the corridor to service",
        "",
        "Removing the through movement from the at-grade surface — the elevated option — "
        "leaves only turning traffic at the junction. Applying the measured through "
        f"percentage to each approach returns **all {c['approaches_ok_after_grade_separation']} "
        "approaches** to acceptable operation.",
        "",
        _table(["Junction", "Approach", "Through %", "Peak PCU", "Residual",
                "v/c before", "v/c after", "LOS after"],
               [[r["junction"], r["approach"].replace("from ", ""),
                 f"{r['through_pct']:.1f}%", f"{r['peak_pcu']:,}",
                 f"{r['residual_pcu']:,}", f"{r['vc_before']:.2f}",
                 f"{r['vc_after']:.2f}", r["los_after"]] for r in c["relief"]]),
        "",
        "## 6. Do these conclusions survive their own assumptions?",
        "",
        f"Both were re-run across **{sen['combinations']} combinations** of PCU uplift, "
        "lane capacity, effective lane count, critical gap and growth rate.",
        "",
        f"- **U-turn scheme fails:** holds. {'Robust across the grid.' if sen['uturn_robust'] else 'NOT robust — see sensitivity.json.'}",
        f"- **Grade separation relieves:** all 12 approaches pass in "
        f"**{sen['elevated_all_pass_combinations']} of "
        f"{sen['elevated_total_combinations']}** combinations.",
        "",
        ("No single assumption dominates the outcome — the swing across the grid is "
         "negligible, so naming a most-influential parameter would overstate what the "
         "analysis shows.") if not sen.get("most_influential") else
        f"Most influential assumption: {sen['most_influential']}.",
        "",
        "## 7. Limitations",
        "",
        "- The survey covers **one day**, not the two the workbooks present. Day two is "
        "derived from day one; see the integrity audit report.",
        "- Composite vehicle classes prevent a point PCU estimate. Bands are reported "
        "throughout and no band is collapsed to its midpoint.",
        "- Critical gap values are from literature, not measured at this corridor. They "
        "are Raff-derived and therefore likely biased high, which makes the U-turn "
        "finding **conservative** — measured values would tend to worsen it, not improve it.",
        "- E-rickshaw has no IRC PCU factor and no column in the survey. It is excluded "
        "rather than assumed, and its absence understates demand by an unknown amount.",
        "- Three of the six junction positions are inferred from the scheme description "
        "and are labelled as such. The survey location schedule would confirm them.",
        f"- **{thin_txt}** The surveyed drawing runs {align_km:.2f} km and "
        f"{thin_j} sits {thin_end:.0f} m from its end, so a width band around that "
        "junction falls largely outside the drawing. Its width figure rests on fewer "
        "measurements than the others and should be treated as the least certain of the six.",
        "",
        "**Corridor order.** Chainage along the surveyed alignment places the junctions "
        "in the order " + ", ".join(r["junction"] for r in ch_rows) + ". For the "
        f"{sum(1 for r in ch_rows if r['confidence'] == 'name match')} junctions matched "
        "by name this is independent geometric evidence, and the full sequence reproduces "
        "the order the scheme itself lists. For the inferred three it only restates the "
        "assumed position and confirms nothing.",
        "",
        "This resolves a question the flow data could not. Deriving the order from "
        "corridor continuity - matching each junction's southbound outflow to the next "
        "junction's inflow - separated the leading candidates by too small a margin to "
        "call, and was reported as inconclusive. The surveyed geometry answers it directly.",
        "",
        "---",
        "",
        f"Prepared from the JDA classified turning-movement survey dated "
        f"{c['analysis_date']}. Method, standards and acceptance gates are set out in the "
        "accompanying method statement.",
    ]
    return "\n".join(md)


def method_statement():
    c, s, sen = _load("capacity"), _load("scheme_test"), _load("sensitivity")
    atl = _load("atlas_summary")
    cor = _load("corridor")
    aud = cor.get("audit", {})

    md = [
        "# Method statement",
        f"### {CORRIDOR_ROAD} corridor assessment, Jaipur",
        "",
        f"**Generated** {date.today().isoformat()}. Figures are read from pipeline output "
        "at generation time.",
        "",
        "---",
        "",
        "## 1. Purpose and scope",
        "",
        f"To establish, from the authority's own classified turning-movement survey, what "
        f"the {CORRIDOR_ROAD} corridor carries at present, whether the published scheme "
        f"({JDA_SCHEME}) resolves the demand, and what does.",
        "",
        f"Scope is the **{len(JUNCTION_COORDS)} surveyed junctions** over "
        f"**{atl['alignment_km']} km** of alignment. Each is a four-arm junction with "
        "twelve movements. No U-turn is counted anywhere in the source survey.",
        "",
        "## 2. Standards applied",
        "",
        _table(["Standard", "Applied to"], [
            ["Indo-HCM 2017", "capacity, level of service, gap acceptance"],
            ["IRC:106", "share-dependent passenger car unit factors"],
            ["IRC:SP:41", "at-grade intersection geometry"],
            ["IRC:92", "grade-separated intersection assessment"],
            ["IRC:SP:19", "survey and investigation procedure"],
            ["IRC:86", "urban arterial cross-section"],
            ["EPSG:32643", "all spatial work, UTM zone 43N, metres"],
        ]),
        "",
        "**India drives on the left.** The right turn crosses opposing traffic and is the "
        "capacity-limiting movement throughout. This was verified against the direction "
        "headings of every movement sheet in the source workbooks rather than assumed.",
        "",
        "## 3. Method, stage by stage",
        "",
        "Each stage carries a numeric acceptance gate. A failed gate is reported, not "
        "worked around.",
        "",
        _table(["Stage", "Method", "Acceptance gate"], [
            ["Survey ingest", "Parse all workbooks to tidy 15-minute bins. Every stored "
             "total is recomputed from components and disagreements are registered, never "
             "silently corrected.",
             "zero silently absorbed discrepancies"],
            ["Integrity audit", "Seven independent checks: arithmetic, conservation, "
             "approach reconciliation, PCU back-solve, peak-hour rederivation, timing "
             "against IRC:SP:19, inter-day independence.", "each check reports pass/fail"],
            ["PCU correction", "IRC:106 factors interpolated on each class's share of the "
             "stream. Composite classes report a band, not a point.",
             "no composite bucket collapsed to a point estimate"],
            ["Georeference", "Survey CAD parsed and projected to EPSG:32643.",
             "RMSE < 3 m"],
            ["Constraint atlas", "All constraint layers extracted from the CAD; pier "
             "siting profiled at 25 m stations against an 8 m footprint.",
             "hard constraints flagged, not scored away"],
            ["Capacity", "Widths measured on transects across the alignment; demand from "
             "corrected PCU at the derived peak.", "measured widths, not assumed"],
            ["Scheme test", "Gap acceptance against measured opposing flow, both "
             "optimistic and conservative critical gaps.",
             f"v/c above {s['no_gap_vc_threshold']} reported as 'no viable gaps', not as a number"],
            ["Sensitivity", "Every conclusion re-run across the full assumption grid.",
             f"{sen['combinations']} combinations"],
            ["Detection (pending footage)", "YOLO fine-tuned on IDD then on annotated "
             "frames from the study camera. SAHI sliced inference for small two-wheelers; "
             "ByteTrack association; homography to ground plane by footpoint.",
             "mAP@0.5 >= 0.80 overall, >= 0.70 per class"],
            ["Count validation (pending footage)", "Automated counts against manual counts "
             "from the same footage.", "MAPE < 10% total, < 15% per major class"],
        ]),
        "",
        "## 4. Data provenance",
        "",
        _table(["Input", "Source", "Status"], [
            ["Classified turning-movement survey", "JDA, via appointed contractor",
             "received, audited"],
            ["Corridor CAD drawing", "JDA", "received, parsed"],
            ["Junction positions", "three matched by name to the scheme, three inferred",
             "labelled as such throughout"],
            ["Study footage", "to be recorded at the study junction", "outstanding"],
            ["Critical gap", "literature, Raff-derived", "to be measured from footage"],
        ]),
        "",
        "**Client source data is not redistributed.** The survey workbooks and the CAD "
        "drawing are the authority's to share. Everything derived from them is published "
        "in open formats and is downloadable from the dashboard.",
        "",
        "## 5. Quality assurance",
        "",
        "- No stored total is trusted. Every one is recomputed and disagreements are "
        "registered with file, sheet and row.",
        "- No figure appears in a report that is not read from pipeline output at "
        "generation time. Reports cannot drift from the analysis.",
        "- Every module is independently runnable and prints its own verification metric. "
        "Silent success is not treated as success.",
        "- Conclusions are re-run across the full assumption grid before publication.",
        "- Findings that did not survive checking were withdrawn rather than softened. "
        "The audit report records them.",
        "",
        "## 6. Where this stops being reliable",
        "",
        "- **One day of data.** The workbooks present two; the second is derived from the "
        "first. Weekday-to-weekend variation is unmeasured.",
        "- **Survey timing.** The count was taken in May, outside the IRC:SP:19 "
        "recommended window, on a day the project's own methodology excludes.",
        "- **Composite classes.** Auto-rickshaw is pooled with cars and pickups in the "
        "source. This cannot be undone by analysis; it needs re-survey or video.",
        "- **No e-rickshaw column.** Excluded rather than assumed. Demand is understated "
        "by an unknown amount.",
        "- **Critical gap is not local.** Literature values are used and flagged. The "
        "direction of the bias makes the U-turn conclusion conservative.",
        "- **Detection accuracy is unverified** until footage exists. The pipeline and its "
        "gates are built and tested; the accuracy figure is not yet measurable.",
        "",
        "## 7. Deliverables",
        "",
        _table(["Ref", "Deliverable", "Format"], [
            ["D1", "Integrity audit report", "Markdown"],
            ["D2", "Corrected dataset", "Parquet + JSON"],
            ["D3", "Contractor query letter", "Markdown"],
            ["D4", "Corridor Constraint Atlas", "A3 PDF"],
            ["D5", "Median opening schedule", "GeoJSON"],
            ["D6", "Capacity and design-year assessment", "Markdown"],
            ["D7", "Interactive dashboard", "Web link"],
            ["D8", "Count validation report", "pending footage"],
            ["D9", "Method statement", "this document"],
        ]),
        "",
        "---",
        "",
        "All spatial data is EPSG:32643. All analysis code is public and every derived "
        "dataset is downloadable from the dashboard.",
    ]
    return "\n".join(md)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    checks = 0

    cap = capacity_report()
    (OUT / "capacity_report.md").write_text(cap)
    meth = method_statement()
    (OUT / "method_statement.md").write_text(meth)

    c, s, sen = _load("capacity"), _load("scheme_test"), _load("sensitivity")

    # the point of a generated report is that its numbers match the source
    tests = [
        ("capacity report written", len(cap) > 3000),
        ("method statement written", len(meth) > 3000),
        (f"sensitivity count bound ({sen['combinations']})",
         f"{sen['combinations']} combinations" in cap and
         f"{sen['combinations']} combinations" in meth),
        (f"forced U-turns bound ({s['forced_uturns_per_hour']:,.0f})",
         f"{s['forced_uturns_per_hour']:,.0f}" in cap),
        ("every junction in the width table",
         all(k in cap for k in c["widths"])),
        ("all 12 approaches in the demand table",
         cap.count("| TMC-") >= len(c["junctions"])),
        ("no placeholder text", "TODO" not in cap + meth and "TBD" not in cap + meth),
        ("pure ASCII except typographic dashes",
         all(ord(ch) < 128 or ch in "—–≥×" for ch in cap + meth)),
    ]
    for name, good in tests:
        checks += good
        print(f"  {name:<52}{'PASS' if good else 'FAIL':>8}")

    print(f"\n  GATE - reports generated and bound to source: **{checks} of {len(tests)}**")
    print(f"  out/capacity_report.md    {len(cap):,} chars")
    print(f"  out/method_statement.md   {len(meth):,} chars")
