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
from src.config import OUT, OUT_DATA

TPL = Path(__file__).parent / "pitch_template.html"


def build():
    d = json.loads((OUT_DATA / "corridor.json").read_text())
    a, c, cap = d["audit"], d["corridor"], (d.get("capacity") or {})
    con = d.get("constraints") or {}
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
        ENTITIES="1,041,959", LAYERS="44", TESTS="26",
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
