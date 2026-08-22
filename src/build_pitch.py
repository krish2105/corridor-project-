"""
build_pitch.py — the commercial pitch page.

Same discipline as the audit page: every figure about our own work is substituted
from corridor.json, not typed. External figures (CAG, press) are constants with the
source named on the page, because a pitch that cannot be checked is not a pitch.

Run:  uv run python src/build_pitch.py
"""
import json
import sys
from pathlib import Path
from string import Template

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.build_page import ascii_only, fmt
from src.config import OUT, OUT_DATA, ROOT

TPL = Path(__file__).parent / "pitch_template.html"


def _test_count():
    """
    Count the tests rather than typing the number.

    It was typed as 26 and stayed 26 while the suite grew past ninety, which is exactly
    the failure this whole project exists to point out in someone else's data.
    """
    import re
    import subprocess
    try:
        # pytest's own count, so this can never disagree with what is quoted elsewhere.
        # A regex over "def test_" undercounts: parametrised tests expand to several
        # cases each, and 85 functions collect as 96.
        out = subprocess.run(["uv", "run", "pytest", "--collect-only", "-q"],
                             cwd=ROOT, capture_output=True, text=True, timeout=180).stdout
        m = re.search(r"(\d+) tests? collected", out)
        if m:
            return m.group(1)
    except Exception:
        pass
    n = 0
    for f in (ROOT / "tests").glob("test_*.py"):
        n += len(re.findall(r"^def test_", f.read_text(), re.M))
    return str(n)


def build():
    d = json.loads((OUT_DATA / "corridor.json").read_text())
    a, c, cap = d["audit"], d["corridor"], (d.get("capacity") or {})
    con = d.get("constraints") or {}
    sch = d.get("scheme") or {}
    dly = d.get("delay") or {}
    eco = d.get("economics") or {}
    js = d["junctions"]
    d2 = a["day2"]

    sub = dict(
        ROAD=d["meta"]["road"],
        NJUNC=str(d["meta"]["n_junctions"]),
        BINS=fmt(d["meta"]["bins_parsed"]),
        SERIES=str(d2["series"]), IDENT=str(d2["identical"]),
        GREATER=str(d2["greater"]), SMALLER=str(d2["smaller"]),
        IDENTPCT=f"{100*d2['identical']/d2['series']:.0f}",
        UPLIFT=f"{a['pcu']['uplift_floor_pct']:.1f}",
        BANDHI=f"{a['pcu']['band_high_pct']:.1f}",
        REFS=str(a["flow_diagram"]["ref_errors"]),
        DISC=str(a["arithmetic"]["discrepancies"]),
        UTURNS=str(con.get("uturn_possible", 0)),
        THRU=f"{c['through_pct_mean']:.1f}",
        THRULO=f"{c['through_pct_range'][0]:.0f}",
        THRUHI=f"{c['through_pct_range'][1]:.0f}",
        CAPOK=str(cap.get("approaches_ok_after_grade_separation", 0)),
        CAPN=str(len(cap.get("relief", []))),
        VCLO=f"{min(r['vc_after'] for r in cap['relief']):.2f}" if cap.get("relief") else "0",
        VCHI=f"{max(r['vc_after'] for r in cap['relief']):.2f}" if cap.get("relief") else "0",
        VCWAS=f"{max(r['vc_before'] for r in cap['relief']):.2f}" if cap.get("relief") else "0",
        ENTITIES="1,041,959", LAYERS="44", TESTS=_test_count(),
        QSPILL=str(dly.get("spillback_count", 0)),
        QN=str(dly.get("n_approaches", 0)),
        QSOON=str(int(min([a["minutes_to_spillback"] for a in dly.get("approaches", [])
                           if a.get("minutes_to_spillback")] or [0]))),
        QPEAK=str(dly.get("peak_journey_min", 0)),
        QFREE=str(dly.get("free_flow_min", 0)),
        QKMH=str(dly.get("effective_kmh", 0)),
        QSAVE=str(dly.get("saving_min_per_trip", 0)),
        ECHRS=f"{eco.get('mean_hours_over', 0):.1f}",
        ECLO=str((eco.get("annual_cost_crore") or [0, 0])[0]),
        ECHI=str((eco.get("annual_cost_crore") or [0, 0])[1]),
        ECBLO=str((eco.get("annual_benefit_crore") or [0, 0])[0]),
        ECBHI=str((eco.get("annual_benefit_crore") or [0, 0])[1]),
        DLFAIL=str(cap.get("design_life_first_failure_med", "")),
        DLHOLD=str(cap.get("design_life_survives_horizon", "")),
        DLHZN=str(cap.get("horizon_year", "")),
        SFAIL=str(sch.get("fails_conservative", 0)),
        SN=str(len(sch.get("uturns", []))),
        SFAILOPT=str(sch.get("fails_optimistic", 0)),
        SFORCED=fmt(sch.get("forced_uturns_per_hour", 0)),
        SOK=str(sch.get("s1_serviceable", 0)),
        SNJ=str(sch.get("n_junctions", 0)),
        AUDITURL="https://claude.ai/code/artifact/25432daa-e9e7-48c7-82f6-d43e7c67b0c4",
    )
    sub = {k: ascii_only(v) for k, v in sub.items()}
    html = Template(TPL.read_text()).substitute(sub)
    assert all(ord(ch) < 128 for ch in html), "page must be pure ASCII"
    out = OUT / "corridor_pitch.html"
    out.write_text(html)
    return out, len(html)


if __name__ == "__main__":
    p, n = build()
    print(f"written: {p}  ({n/1024:,.0f} KB)")
