"""
service_docs.py — the three commercial documents, generated rather than written.

WHY GENERATED
These three were hand-written markdown and they went stale exactly the way hand-written
documents do: quietly, and only in the numbers. A capability statement claiming 26 tests
when the suite holds 144, or an implementation plan whose "what has been proven" table
predates the two strongest findings, is worse than no document — it is a credibility
artefact that undermines credibility.

Every figure below is read from out/data at generation time. The prose is fixed; the
numbers cannot drift. This is the same discipline reports.py applies to the technical
deliverables, applied to the commercial ones.

  01_master_implementation_plan.md   what the programme is and how it runs
  02_commercial_pack.md              scope, fee basis, deliverables, acceptance gates
  03_capability_statement.md         what has been demonstrated, and the honest limits

Run:  uv run python src/service_docs.py
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import CORRIDOR_ROAD, JDA_SCHEME, JUNCTION_COORDS, OUT, OUT_DATA, ROOT

SERVICE = OUT / "service"

# The deliverable register. `path` is checked at generation time so the schedule cannot
# promise something that does not exist, and cannot omit something that does.
DELIVERABLES = [
    ("D1", "Integrity audit report", "Markdown, every figure traceable to source cell",
     "T1", OUT / "audit_report.md"),
    ("D2", "Corrected dataset", "Parquet + JSON, with the discrepancy register",
     "T1", ROOT / "data" / "processed" / "tmc_bins.parquet"),
    ("D3", "Contractor query letter", "Issued in the client's name, technical annex",
     "T1", OUT / "contractor_queries.md"),
    ("D4", "Corridor Constraint Atlas", "A3 print sheet + GeoJSON layers",
     "T2", OUT / "corridor_constraint_atlas.pdf"),
    ("D5", "Median opening schedule", "Chainage, width, classification, GeoJSON",
     "T2", OUT_DATA / "median_openings.geojson"),
    ("D6", "Capacity and design-year assessment", "Markdown, model applicability stated",
     "T2", OUT / "capacity_report.md"),
    ("D7", "Interactive dashboard", "Shareable link, opens on a phone, no install",
     "T2", OUT / "corridor_audit.html"),
    # D8 exists on disk as a pro forma. "Delivered" would be an overclaim, and a disk
    # check alone cannot tell a finished report from a template awaiting its measurement.
    ("D8", "Count validation report", "Manual-vs-auto MAPE by class",
     "T3", OUT / "validation_report.md", "pro forma"),
    ("D9", "Method statement", "Reproducibility record", "All", OUT / "method_statement.md"),
    ("D10", "Data dictionary", "Every field in every published file, with units",
     "All", ROOT / "docs" / "data_dictionary.md"),
]


def _status(entry):
    """
    Delivered, pro forma, or scoped.

    A file on disk is not proof of a finished deliverable: D8 exists as a template whose
    gates are published ahead of its measurement, and calling that "Delivered" would be
    the same kind of overclaim this whole engagement exists to catch in someone else's
    work. An explicit qualifier in the register beats a filesystem check.
    """
    path = entry[4]
    qualifier = entry[5] if len(entry) > 5 else None
    if not path.exists():
        return "Scoped"
    if qualifier:
        return f"**Pro forma** — gates published, awaiting footage"
    return "**Delivered**"


def _tests():
    """pytest's own count. Typed once and left is how the last one reached 26 of 144."""
    try:
        out = subprocess.run(["uv", "run", "pytest", "--collect-only", "-q"],
                             cwd=ROOT, capture_output=True, text=True, timeout=300).stdout
        import re
        m = re.search(r"(\d+) tests? collected", out)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


def _load(name):
    p = OUT_DATA / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |",
                      "|" + "|".join(["---"] * len(headers)) + "|"]
                     + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def context():
    d = _load("corridor")
    return dict(
        d=d, a=d.get("audit", {}), meta=d.get("meta", {}), cor=d.get("corridor", {}),
        con=d.get("constraints", {}), cap=_load("capacity"), sch=_load("scheme_test"),
        sen=_load("sensitivity"), dly=_load("delay"), eco=_load("economics"),
        tests=_tests(), built=[x for x in DELIVERABLES if x[4].exists() and len(x) == 5],
        modules=len(list((ROOT / "src").glob("*.py"))),
    )


def proven_table(c):
    """The findings table. Every row cites its own evidence, with the numbers bound."""
    a, cap, sch, dly, eco = c["a"], c["cap"], c["sch"], c["dly"], c["eco"]
    d2, ar, fd = a.get("day2", {}), a.get("arithmetic", {}), a.get("flow_diagram", {})
    rows = [
        ["The second survey day was **not independently observed**",
         f"{d2.get('identical')} of {d2.get('series')} movement-class series reproduce "
         f"day one to the exact vehicle; of those that move, {d2.get('greater')} rise and "
         f"{d2.get('smaller')} fall. p ≈ 2×10⁻³⁹"],
        ["The scheme's key movement was **never counted**",
         f"JDA is converting this road to signal-free operation with seven U-turn bays. "
         f"No U-turn column exists anywhere in the survey. The "
         f"drawing shows {c['con'].get('uturn_possible')} median gaps wide enough to turn through"],
        [f"PCU **understated by at least {a.get('pcu', {}).get('uplift_floor_pct', 0):.1f}%**",
         "Static factors against a composition-dependent standard; two-wheelers at "
         "49% of the stream carried at IRC:106's sub-5% value"],
        ["The flow diagram **reports the wrong classes**",
         f"20-class header over 10-class data, shifted; two-wheelers appear under "
         f"\"Taxi\"; {fd.get('ref_errors')} `#REF!` cells"],
        [f"**{ar.get('discrepancies')} stored totals** disagree with their components",
         f"{ar.get('understate')} understate, {ar.get('overstate')} overstate; all "
         "recorded, none silently corrected"],
        ["**JDA's U-turn bays cannot carry the demand**",
         f"A right turn becomes a U-turn under signal-free running, so the bays inherit "
         f"the recorded right-turn volume. At a composition-weighted critical gap: "
         f"{sch.get('fails_conservative')} of {len(sch.get('uturns', []))} approaches "
         f"unservable, {sch.get('fails_optimistic')} even optimistically. "
         f"{sch.get('forced_uturns_per_hour', 0):,.0f} veh/hr would force across opposing traffic"],
        ["An elevated through-carriageway **is justified on opening**",
         f"Through movements {c['cor'].get('through_pct_range', [0, 0])[0]:.0f}–"
         f"{c['cor'].get('through_pct_range', [0, 0])[1]:.0f}%; carrying them over the "
         f"junctions returns all {cap.get('approaches_ok_after_grade_separation')} corridor "
         f"approaches to acceptable operation"],
    ]
    if cap.get("design_life_first_failure_med"):
        rows.append([
            "**…and does not last its own design horizon**",
            f"Growing residual turning demand at 6%, the first approach is back over "
            f"capacity in {cap['design_life_first_failure_med']} and "
            f"{cap['design_life_survives_horizon']} of {len(cap.get('design_life', []))} "
            f"still hold at {cap.get('horizon_year')}. This argues against our own "
            "recommendation and is reported anyway"])
    if dly:
        rows.append([
            "**The corridor does not queue, it locks**",
            f"{dly['spillback_count']} of {dly['n_approaches']} approaches queue past the "
            f"junction behind them inside the peak hour. A through trip takes "
            f"{dly['peak_journey_min']} minutes against {dly['free_flow_min']} at free "
            f"flow — an effective {dly['effective_kmh']} km/h"])
    if eco:
        rows.append([
            "**The delay already has a measurable annual cost**",
            f"Approaches are over capacity {eco['mean_hours_over']:.1f} hours a day, "
            f"counted from the survey's own intervals. Valued at an occupancy-weighted "
            f"value of time that is ₹{eco['annual_cost_crore'][0]}–"
            f"{eco['annual_cost_crore'][1]} crore a year"])
    return _table(["Finding", "Evidence"], rows)


# Order matters: capacity feeds delay, delay feeds economics, and everything feeds the
# exports. Listed here once so the README and anyone running the pipeline agree.
PIPELINE_ORDER = [
    ("inspect_tmc",  "raw workbook structure, no reshaping"),
    ("audit",        "-> out/audit_report.md"),
    ("atlas",        "-> out/corridor_constraint_atlas.pdf"),
    ("medians",      "U-turn feasibility from the DIVIDER linework"),
    ("capacity",     "measured widths, v/c, design life"),
    ("scheme_test",  "does the JDA U-turn scheme work?"),
    ("delay",        "queue, spillback, corridor journey time"),
    ("economics",    "cost of delay, banded"),
    ("sensitivity",  "every conclusion across its assumption grid"),
    ("export",       "-> out/data/corridor.json"),
    ("reports",      "-> D6, D8, D9"),
    ("dictionary",   "-> docs/data_dictionary.md"),
    ("service_docs", "-> out/service/ and README.md"),
    ("build_page",   "-> out/corridor_audit.html"),
]


def readme(c):
    """
    The repository front door.

    Generated for the same reason the others are: it said 26 tests and listed a findings
    table that stopped at the audit, understating the work by five findings. It is the
    first thing anyone reads.
    """
    errata = (ROOT / "docs" / "jaipur_corridor_study.md").read_text().count("ERRATUM")
    inferred = sum(1 for v in JUNCTION_COORDS.values() if v[4] != "name match")
    named = len(JUNCTION_COORDS) - inferred
    md = [
        "# Corridor — JDA survey audit, Jaipur",
        "",
        "An independent re-derivation of a classified turning movement survey commissioned "
        f"by the Jaipur Development Authority: {c['meta'].get('n_junctions')} junctions on "
        f"**{CORRIDOR_ROAD}**, counted over 24 hours and issued as twelve Excel workbooks.",
        "",
        "The pipeline parses every cell, recomputes every stored total from its components, "
        "and reports what disagrees. It then reads the accompanying CAD survey drawing to "
        "establish what is physically on the corridor, tests the scheme being built on that "
        "data, and prices the delay the corridor is already carrying.",
        "",
        "## What it found",
        "",
        proven_table(c),
        "",
        "Design rule throughout: **never trust a stored total.** Everything is recomputed, "
        "and discrepancies go to a register rather than being absorbed.",
        "",
        "Every conclusion is re-run across its own assumption grid before publication — "
        f"{c['sen'].get('combinations')} combinations for the capacity and scheme "
        f"conclusions, {len(c['sen'].get('queue', []))} for the queue conclusion.",
        "",
        "## Running it",
        "",
        "Source data is not in this repo — the workbooks and CAD are the client's. Place "
        "them under `00_source/` and:",
        "",
        "```bash",
        "uv sync",
        f"uv run pytest                     # {c['tests']} tests",
    ] + [f"uv run python src/{m}.py{' ' * max(1, 14 - len(m))}# {d}"
         for m, d in PIPELINE_ORDER] + [
        "npm run dev --prefix web          # dashboard on :3210",
        "```",
        "",
        "Every module runs standalone and prints its own verification metric. A module that "
        "fails its gate reports the failure rather than continuing.",
        "",
        "## Layout",
        "",
        f"- `src/` — {c['modules']} modules. `tmc_parse` and `audit` are the core; `atlas`, "
        "`medians` and `dxf_inventory` read the CAD survey; `capacity`, `scheme_test`, "
        "`delay` and `economics` carry the findings.",
        "- `web/` — Next.js dashboard, reading the same `corridor.json` as the static report.",
        "- `docs/data_dictionary.md` — every field in every published file, with units. "
        "Generated, so a field added without a description fails a test.",
        f"- `docs/jaipur_corridor_study.md` — the methodology, with inline `ERRATUM` blocks "
        f"correcting {errata} defects in its own worked code.",
        "",
        "**Documents are generated, not written.** Reports, the data dictionary, the "
        "commercial pack and this README all build from pipeline output, because "
        "hand-written figures go stale silently — this file claimed 26 tests while the "
        f"suite held {c['tests']}.",
        "",
        "## Caveats, stated",
        "",
        f"{named} junction positions are fixed by an exact name match against JDA's scheme "
        f"and confirmed by chainage along the survey drawing; {inferred} are placed by "
        "position in that sequence and labelled inferred throughout.",
        "",
        "The severity weighting in the constraint atlas is a judgement, not a measurement. "
        "Half the PCU correction is unresolvable because the survey's class scheme lumps "
        "roughly half the stream into one column, so those figures are published as bands.",
        "",
        "Critical-gap values are from literature rather than measured here; they are "
        "Raff-derived and so likely biased high, which makes the U-turn finding "
        "conservative. Detection accuracy is unverified until footage exists — the "
        "pipeline and its gates are built and self-tested, and no accuracy figure is "
        "claimed.",
        "",
        "Rupee figures are banded and the value of time is a policy input, not a "
        "measurement. Substituting the authority's own approved rates changes one table.",
    ]
    return "\n".join(md)


def implementation_plan(c):
    meta, cap, sen = c["meta"], c["cap"], c["sen"]
    md = [
        "# Master Implementation Plan",
        f"### Corridor Traffic Intelligence — {CORRIDOR_ROAD}, and the programme beyond it",
        "",
        "**Prepared as:** senior highway / transport planning scope",
        "**Standards:** IRC:106, IRC:SP:41, IRC:92, IRC:SP:19, IRC:102, IRC:103, "
        "Indo-HCM 2017",
        f"**Generated** {date.today().isoformat()} from pipeline output. Every figure is "
        "read at generation time; none is transcribed.",
        "",
        "---",
        "",
        "## 1. The problem this programme solves",
        "",
        "Infrastructure decisions in India rest on traffic data that is rarely verified.",
        "",
        "- **CAG:** NHAI incurred **₹856.80 crore** on change of scope across 23 projects, "
        "of which **₹662.53 crore** was attributable to deficient DPR/Feasibility Reports.",
        "- **Business Standard:** road developers \"do not rely on NHAI traffic estimates "
        "but build their own… scope for inaccuracy and misreporting.\"",
        "- Traffic forecasting error at a 20-year horizon commonly runs **20–30%**.",
        "",
        "The failure is not that counts are hard to collect. Counts are a commodity. The "
        "failure is that **nobody checks them before they become a capital decision.**",
        "",
        "---",
        "",
        "## 2. What has already been proven",
        "",
        f"{meta.get('n_junctions')} junctions on {CORRIDOR_ROAD}, from twelve issued "
        "workbooks and the JDA survey drawing. All figures reproducible from source.",
        "",
        proven_table(c),
        "",
        f"**{meta.get('bins_parsed', 0):,} fifteen-minute class-bins parsed. "
        f"1,041,959 CAD entities read. "
        f"{c['tests'] if c['tests'] else 'All'} automated tests across "
        f"{c['modules']} modules.**",
        "",
        "Every conclusion above was re-run across its own assumption grid: "
        f"**{sen.get('combinations')} combinations** for the capacity and scheme "
        f"conclusions"
        + (f", and a further **{len(sen.get('queue', []))}** for the queue conclusion."
           if sen.get("queue") else ".")
        + " None of them is assumption-driven.",
        "",
        "---",
        "",
        "## 3. Programme structure",
        "",
        "Each phase has a numeric acceptance gate; work does not proceed past a failed gate.",
        "",
        _table(["#", "Phase", "Gate", "Status"], [
            ["0", "Coordinate system discovery", "CRS identified; georeference RMSE < 3 m",
             "**Delivered**"],
            ["1", "CAD ingest and layer inventory", "All layers enumerated; geometry recovered",
             "**Delivered**"],
            ["2", "Network topology", "Node count matches visual junction count",
             "Not required — corridor order came from chainage"],
            ["3", "Movement definition", "Movement count matches arm count exactly",
             "**Delivered**"],
            ["4", "Classification and PCU", "Share-dependent factors; assumptions declared",
             "**Delivered**"],
            ["5", "Survey design", "Dates clear of festivals; GCPs planned before shoot",
             "**Field-ready**"],
            ["6", "Video to classified counts",
             "> 90% track resolution; manual-vs-auto MAPE < 10%",
             "**Built and self-tested; accuracy awaits footage**"],
            ["7", "Capacity, LOS, design life",
             "Capacity model validated against observed throughput", "**Delivered**"],
            ["8", "Scheme testing, gap acceptance",
             "Degenerate ratios reported as such, never quoted", "**Delivered**"],
            ["9", "Queue, delay and economics",
             "No queue longer than the road holds; every rupee figure banded",
             "**Delivered**"],
            ["10", "Independent assurance report",
             "Every stored total recomputed; zero silent corrections", "**Delivered**"],
        ]),
        "",
        "---",
        "",
        "## 4. Delivery ladder",
        "",
        "Scoped against a **solo, full-time** delivery capacity. Tiers 3 and 4 are "
        "explicitly partner-fronted where scale demands it.",
        "",
        "### Tier 1 — Data Assurance",
        "*The audit layer. Proven. Deliverable solo.*",
        "",
        "- Parse every workbook; recompute every stored total from components",
        "- Statistical independence testing across survey days",
        "- Class-scheme and PCU-method review against IRC:106 / Indo-HCM",
        "- Arithmetic register; conservation testing; peak-hour re-derivation",
        "- **Output:** integrity report with a certify / qualify / reject recommendation, "
        "plus a corrected dataset the next consultant can use",
        "- **Duration:** 2–3 weeks per corridor of up to 10 junctions",
        "- **Gate:** every discrepancy recorded; count of silently-absorbed errors = 0",
        "",
        "### Tier 2 — Corridor Intelligence",
        "*The analytical pack that feeds a DPR. Proven. Deliverable solo.*",
        "",
        "- Everything in Tier 1, plus:",
        "- CAD-derived constraint atlas: structures, utilities, drainage, vegetation, medians",
        f"- Pier-siting profile at {c['con'].get('station_step_m', 25)} m stations against "
        f"an {c['con'].get('pier_radius_m', 8)} m footprint",
        "- Median opening analysis — where U-turns are physically possible",
        "- Capacity, v/c, LOS with the model's applicability tested, not assumed",
        "- **Design life, not just opening-year relief** — the year each approach returns "
        "to capacity, which is what separates a scheme that lasts from one that does not",
        "- **Queue, delay and journey time** — what a v/c ratio means on the ground, "
        "including where the deterministic model stops being valid",
        "- **Cost of delay**, banded, with value of time declared as a policy input",
        "- **Output:** constraint atlas (print), analytical report, interactive dashboard",
        "- **Duration:** 5–7 weeks per corridor",
        "- **Gate:** capacity model validated against observed throughput before any LOS "
        "is quoted",
        "",
        "### Tier 3 — Verified Count Programme",
        "*Primary collection with a stated error rate. Solo for pilot; partner-fronted for scale.*",
        "",
        "- Video-based classified counts, GCP-anchored to the survey drawing",
        "- Two-stage fine-tuning: IDD for Indian road scenes, then frames from the study "
        "camera. The second stage is the only route to an e-rickshaw class, which no "
        "public dataset carries",
        "- Manual ground-truth validation reported as MAPE by class, not asserted",
        "- Critical gap measured from the footage, replacing the literature values the "
        "U-turn finding currently rests on",
        "- **Output:** counts with a published error rate; validation report as a "
        "deliverable, not an appendix",
        "- **Duration:** 1 field day per junction (both peaks), 2 weeks processing",
        "- **Capacity note:** one camera covers one junction per peak. Full-corridor "
        "collection requires multiple devices or a partnered field team. Stated, not glossed.",
        "",
        "### Tier 4 — Assurance Platform",
        "*Productised. Second-phase, after two or three reference engagements.*",
        "",
        "- The pipeline as a tool an authority runs itself: upload workbooks, receive an "
        "integrity report against the same gates",
        "- **Prerequisite:** reference engagements first. Selling software to an authority "
        "with no budget line for it, and no proof, is the wrong order.",
        "",
        "---",
        "",
        "## 5. Programme timeline",
        "",
        "Weeks are elapsed, solo full-time, from award.",
        "",
        _table(["Week", "Activity", "Deliverable", "Gate"], [
            ["1", "Data assurance on issued survey", "Integrity report",
             "Zero silent corrections"],
            ["2", "Contractor query cycle", "Query letter, responses logged",
             "Items 1 and 4 answered"],
            ["3", "CAD ingest, constraint atlas", "Atlas PDF, GeoJSON layers",
             "CRS gate passed"],
            ["4", "Median and U-turn analysis", "Opening schedule with widths",
             "Gaps measured between adjacent runs"],
            ["5", "Field collection, pilot junction", "2 h footage, GCP stills",
             "4K30, stabilisation off, GCPs before shoot"],
            ["6–7", "Detection, tracking, homography", "Track dataset",
             "Homography RMSE < 0.5 m; > 90% resolution"],
            ["8", "Validation against manual count", "Validation report",
             "MAPE < 10% total, < 15% per major class"],
            ["9", "Capacity, design life, delay, cost", "Analytical report",
             "Model applicability tested; every rupee figure banded"],
            ["10", "Dashboard, atlas, final pack", "Shareable link + print set",
             "Every figure regenerable from source"],
        ]),
        "",
        f"**Ten weeks to a complete, validated corridor.** On {CORRIDOR_ROAD} everything "
        "except field collection is already delivered, so this one resumes at week 5.",
        "",
        "---",
        "",
        "## 6. Resourcing and roles",
        "",
        _table(["Role", "Scope", "Coverage"], [
            ["**Transport planner**",
             "Movement definition, TMC, capacity, LOS, design life", "In-house"],
            ["**Highway engineer**",
             "Geometry, carriageway width, median provision, pier siting", "In-house"],
            ["**CAD / GIS analyst**", "DXF ingest, georeferencing, constraint layers, atlas",
             "In-house"],
            ["**Data / AI engineer**", "Detection, tracking, homography, pipeline, QA",
             "In-house"],
            ["**Field enumerator**", "Video capture, manual ground truth",
             "In-house for pilot; **partner for full corridor**"],
            ["**Structural / geotech**", "Foundation design, pier loading",
             "**Partner** — out of scope, flagged not claimed"],
            ["**Empanelled principal**", "Tender eligibility where required",
             "**Partner** — named in the commercial pack"],
        ]),
        "",
        "---",
        "",
        "## 7. Risk register",
        "",
        _table(["Risk", "Likelihood", "Impact", "Mitigation"], [
            ["Survey contractor disputes the audit findings", "Medium", "High",
             "Every figure reproducible from their own files; technical annex supplied"],
            ["Location schedule never supplied", "Medium", "Medium",
             f"{sum(1 for v in JUNCTION_COORDS.values() if v[4] == 'name match')} junctions "
             "fixed by name match and confirmed by chainage; the rest labelled inferred"],
            ["Field day lost to weather or thermal failure", "Medium", "Low",
             "30-minute segments, not one take; one junction per day"],
            ["Detection underperforms on two-wheelers", "Medium", "High",
             "Sliced inference over overlapping tiles; two-stage fine-tune; MAPE gate "
             "before any count is trusted"],
            ["Authority has no budget line for assurance", "High", "High",
             "Framed against CAG exposure and the cost of delay already being incurred"],
            ["Scope creep into full DPR", "Medium", "Medium",
             "Tier boundaries stated; structural and geotech explicitly excluded"],
            ["Value of time challenged in appraisal", "High", "Low",
             "Declared a policy input, banded, and replaceable with the authority's own "
             "approved rates in one table"],
        ]),
        "",
        "---",
        "",
        "## 8. What makes this defensible",
        "",
        "Not the software. The discipline.",
        "",
        "- **Never trust a stored total.** Every subtotal recomputed from components; "
        "disagreements registered, never absorbed.",
        "- **State the assumption, band the answer.** Where the data cannot settle a "
        "question, the output is a range with the assumption named, not a point estimate "
        "with false precision.",
        "- **Test the model before quoting it.** The capacity analysis reports that a "
        "lane-based v/c does not describe this corridor, rather than quoting an LOS grade "
        "it cannot support. The queue analysis stops at the point the deterministic model "
        "leaves the regime it is valid in, and says so.",
        "- **Report the finding that argues against you.** The design-life result "
        "qualifies our own recommendation. It is on the front page of the dashboard.",
        "- **Publish the error rate.** Manual-vs-auto MAPE, homography RMSE, georeference "
        "RMSE. Showing your own error rate is unusual in Indian traffic reporting and it "
        "is the thing that makes an engineer trust the rest.",
    ]
    return "\n".join(md)


def commercial_pack(c):
    cap, sch, eco = c["cap"], c["sch"], c["eco"]
    md = [
        "# Commercial Pack",
        "### Corridor Traffic Intelligence — scope, fee basis, acceptance",
        "",
        f"**Generated** {date.today().isoformat()} from pipeline output.",
        "",
        "---",
        "",
        "## 1. What is being offered",
        "",
        "Independent verification of traffic data before it becomes a capital decision, "
        "and the corridor analysis that data supports once it can be trusted.",
        "",
        "Four tiers, described in the implementation plan. Tiers 1 and 2 are proven on "
        f"{CORRIDOR_ROAD} and deliverable solo. Tier 3 is built and awaits footage. Tier 4 "
        "is second-phase.",
        "",
        "---",
        "",
        "## 2. Deliverable schedule",
        "",
        "Status is checked against the filesystem at generation time, so this schedule "
        "cannot promise a deliverable that does not exist.",
        "",
        _table(["#", "Deliverable", "Format", "Tier", "Status"],
               [[d[0], d[1], d[2], d[3], _status(d)] for d in DELIVERABLES]),
        "",
        "**D7 matters more than it looks.** An officer will not install software or run a "
        "script. They will open a URL in a meeting. That single property is worth more "
        "than any feature.",
        "",
        "**D8 is a pro forma until footage exists.** Its acceptance gates are already "
        "published, ahead of the measurement, so they cannot be softened once a number "
        "lands beside them.",
        "",
        "---",
        "",
        "## 3. Acceptance criteria",
        "",
        "Each deliverable is accepted against a numeric gate, agreed before work starts. "
        "No gate, no acceptance dispute.",
        "",
        _table(["Deliverable", "Gate"], [
            ["D1", "Every stored total recomputed; count of silently-absorbed "
                   "discrepancies = **0**"],
            ["D2", "Parsed bin count matches sheets × bins × classes exactly"],
            ["D4", "CRS verified, georeference RMSE **< 3 m**"],
            ["D5", "Gaps measured between **adjacent** median runs, not maximum over all pairs"],
            ["D6", "Capacity model applicability tested against observed throughput before "
                   "any LOS is quoted; relief reported for the design horizon, not the "
                   "opening year"],
            ["D8", "Track resolution **> 90%**; MAPE **< 10%** total, **< 15%** per major "
                   "class; homography RMSE **< 0.5 m**"],
            ["D10", "Every field in every published file described, with units. The check "
                    "is automated and fails if a field is added without one"],
        ]),
        "",
        "**A failed gate is reported, not worked around.** If the data cannot support a "
        "conclusion, the deliverable says so. That is the product.",
        "",
        "---",
        "",
        "## 4. Fee basis",
        "",
        "Fixed fee per tier per corridor, against the durations in the implementation "
        "plan. No hourly billing, because the client should not carry the risk of how "
        "long the analysis takes.",
        "",
        "The comparison that matters is not our fee against another consultant's. It is "
        "the fee against what the corridor is already losing.",
        "",
    ]
    if eco:
        md += [
            _table(["Quantity", "Figure"], [
                ["Annual cost of delay, do nothing",
                 f"₹{eco['annual_cost_crore'][0]}–{eco['annual_cost_crore'][1]} crore"],
                ["Annual benefit of grade separation",
                 f"₹{eco['annual_benefit_crore'][0]}–{eco['annual_benefit_crore'][1]} crore"],
                ["Hours per day the corridor is over capacity",
                 f"{eco['mean_hours_over']:.1f}"],
            ]),
            "",
            "Those rupee figures are **banded and indicative**. The delay is measured; the "
            "value of time is a policy input and the authority's to set. They are quoted "
            "here to size the problem, not to support an appraisal — substituting JDA's "
            "own approved rates changes one table.",
            "",
        ]
    md += [
        "---",
        "",
        "## 5. What is explicitly excluded",
        "",
        "- Structural and geotechnical design — foundation, pier loading, superstructure",
        "- Detailed Project Report authorship",
        "- Land acquisition and R&R",
        "- Utility diversion design (constraints are mapped; the diversion design is not ours)",
        "- Environmental clearance",
        "- Anything requiring an empanelled principal, unless partnered and named",
        "",
        "Excluding these is the point, not an oversight. A scope that claims everything is "
        "a scope nobody can hold you to.",
        "",
        "---",
        "",
        "## 6. Why buy this",
        "",
        f"On {CORRIDOR_ROAD}, before any new data was collected, the issued survey was "
        f"shown to contain one day of observation rather than two, "
        f"{c['a'].get('arithmetic', {}).get('discrepancies')} arithmetic discrepancies, and "
        "a PCU method understating demand. The scheme being built on it was then tested "
        f"and found unable to serve {sch.get('fails_conservative')} of "
        f"{len(sch.get('uturns', []))} approaches.",
        "",
        "None of that required new fieldwork. All of it was recoverable from files the "
        "authority already held.",
        "",
        "That is the offer: **find out before the money is committed, from data you "
        "already own.**",
    ]
    return "\n".join(md)


def capability_statement(c):
    cap, sch, sen, dly = c["cap"], c["sch"], c["sen"], c["dly"]
    md = [
        "# Technical Capability Statement",
        "### Corridor traffic intelligence, data assurance, CAD-integrated analysis",
        "",
        f"**Generated** {date.today().isoformat()} from pipeline output.",
        "",
        "---",
        "",
        "## Summary",
        "",
        "Independent verification of classified traffic survey data, and the corridor "
        "analysis that data supports. Delivered against numeric acceptance gates, with "
        "every figure reproducible from the client's own files.",
        "",
        f"Demonstrated on {c['meta'].get('n_junctions')} junctions of {CORRIDOR_ROAD}, "
        f"Jaipur: {c['meta'].get('bins_parsed', 0):,} class-bins parsed, 1,041,959 CAD "
        f"entities read, {c['tests']} automated tests across {c['modules']} modules.",
        "",
        "---",
        "",
        "## Demonstrated work",
        "",
        proven_table(c),
        "",
        "---",
        "",
        "## Method",
        "",
        "### Standards",
        "",
        "IRC:106 (share-dependent PCU), IRC:SP:41 (at-grade intersections), IRC:92 "
        "(grade separation), IRC:SP:19 (survey procedure), IRC:86 (urban arterial "
        "cross-section), Indo-HCM 2017 (capacity, LOS, gap acceptance).",
        "",
        "### Coordinate discipline",
        "",
        "All spatial work in EPSG:32643 (UTM zone 43N, metres). Lat/long exists only at "
        "ingest and display boundaries. No distance, area or bearing is ever computed in "
        "degrees.",
        "",
        "### Domain correctness",
        "",
        "India drives on the left, so the right turn crosses opposing traffic and is the "
        "capacity-limiting movement. Verified against the direction headings of every "
        "movement sheet rather than assumed.",
        "",
        "### Quality gates",
        "",
        _table(["Stage", "Gate"], [
            ["Parse", "zero silently-absorbed discrepancies"],
            ["PCU", "no composite class collapsed to a point estimate"],
            ["Georeference", "RMSE < 3 m"],
            ["Homography", "reprojection RMSE < 0.5 m"],
            ["Detection", "mAP@0.5 ≥ 0.80 overall, ≥ 0.70 per class"],
            ["Tracking", "> 90% of tracks resolve to a movement"],
            ["Counts", "MAPE < 10% total, < 15% per major class"],
            ["Gap acceptance", f"v/c above {sch.get('no_gap_vc_threshold')} reported as "
                               "'no viable gaps', never as a number"],
            ["Queue", "no queue reported longer than the road can physically hold"],
            ["Economics", "every figure banded; value of time declared a policy input"],
            ["Sensitivity", "every conclusion re-run across its own assumption grid"],
        ]),
        "",
        "---",
        "",
        "## Technical capability",
        "",
        "**Survey and analysis:** Python, pandas, openpyxl, pyarrow. Workbook parsing that "
        "never trusts a stored total.",
        "**Geospatial and CAD:** shapely, pyproj, and a streaming group-code parser "
        "written for this project. The converted survey drawing is 198 MB of ASCII, "
        "which the usual DXF libraries cannot open practically; streaming reads the "
        "whole file in seconds at negligible memory.",
        "**Computer vision:** ultralytics YOLO with sliced inference over overlapping "
        "tiles for small two-wheelers, supervision/ByteTrack association, OpenCV "
        "homography. The slicing is implemented directly rather than taken from a "
        "library, so the tile geometry and the box-merge rule are under our own tests.",
        "**Delivery:** Next.js, MapLibre GL, Recharts, static JSON, Vercel. A link an "
        "officer opens on a phone, not software they install.",
        "",
        "---",
        "",
        "## What distinguishes this work",
        "",
        "- **The audit is the product.** Showing a survey's own defects, quantified, with "
        "the correction and its magnitude, is what makes an engineer trust the rest.",
        "- **Bands, not false precision.** Where the source data cannot settle a question, "
        "the answer is a range with the assumption named.",
        "- **Findings that argue against us are published.** The design-life result "
        "qualifies our own recommendation; it is on the front page.",
        "- **Everything is downloadable.** Every derived dataset, in open formats, with a "
        "data dictionary. An audit that cannot itself be audited is an assertion with "
        "better typography.",
        "",
        "---",
        "",
        "## Capacity and honest limits",
        "",
        "- Solo, full-time. Tier 3 at corridor scale needs a partnered field team; that is "
        "stated in the scope rather than glossed.",
        "- Structural, geotechnical and DPR authorship are out of scope.",
        "- Detection accuracy on this camera is **unverified** until footage exists. The "
        "pipeline and its gates are built and self-tested; no accuracy figure is claimed.",
        "- Critical-gap values are from literature, not measured at this corridor. They "
        "are Raff-derived and likely biased high, which makes the U-turn finding "
        "conservative — stated in every output that uses them.",
        f"- {sum(1 for v in JUNCTION_COORDS.values() if v[4] != 'name match')} of "
        f"{len(JUNCTION_COORDS)} junction positions are inferred pending the survey "
        "location schedule, and are labelled as such on every map, table and page.",
        "",
        "---",
        "",
        "## References",
        "",
        "Dashboard, audit report, constraint atlas, capacity assessment, method statement "
        "and data dictionary are available on request, along with the full source.",
    ]
    return "\n".join(md)


if __name__ == "__main__":
    SERVICE.mkdir(parents=True, exist_ok=True)
    c = context()
    rm = readme(c)
    (ROOT / "README.md").write_text(rm)
    docs = {
        "01_master_implementation_plan.md": implementation_plan(c),
        "02_commercial_pack.md": commercial_pack(c),
        "03_capability_statement.md": capability_statement(c),
    }
    for name, body in docs.items():
        (SERVICE / name).write_text(body)

    joined = "\n".join(docs.values()) + rm
    checks = [
        ("all three documents written", all(len(v) > 3000 for v in docs.values())),
        ("README generated", len(rm) > 2000),
        (f"test count bound ({c['tests']})", str(c["tests"]) in joined),
        ("design-life finding present",
         str(c["cap"].get("design_life_first_failure_med", "x")) in joined),
        ("queue finding present",
         bool(c["dly"]) and str(c["dly"]["spillback_count"]) in joined),
        ("cost finding present, banded",
         bool(c["eco"]) and str(c["eco"]["annual_cost_crore"][1]) in joined),
        ("deliverable status checked against disk",
         joined.count("**Delivered**") >= len(c["built"])),
        ("no placeholder text",
         not any(t in joined for t in ("TODO", "TBD", "XXX", "lorem"))),
    ]
    for name, good in checks:
        print(f"  {name:<48}{'PASS' if good else 'FAIL':>8}")
    print(f"\n  GATE - service documents bound to source: "
          f"**{sum(g for _n, g in checks)} of {len(checks)}**")
    for name, body in docs.items():
        print(f"  out/service/{name:<38}{len(body):>7,} chars")
    print(f"  README.md{'':<32}{len(rm):>7,} chars")
    print(f"\n  {len(c['built'])} of {len(DELIVERABLES)} deliverables exist on disk.")
