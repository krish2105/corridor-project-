"""
build_page.py — corridor.json -> a self-contained audit page.

Every figure on the page is substituted from the pipeline output rather than typed,
so the page cannot drift from the numbers the code actually produced.

Run:  uv run python src/build_page.py
"""
import json
import sys
from pathlib import Path
from string import Template

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import OUT, OUT_DATA

TPL = Path(__file__).parent / "page_template.html"


def fmt(n, dp=0):
    return f"{n:,.{dp}f}"


def ascii_only(s):
    """
    Non-ASCII -> numeric entities. The published page has no charset declaration of
    its own, so a host that serves it as Latin-1 would mojibake any raw UTF-8. Entities
    render correctly under any charset.
    """
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in s)


def build():
    d = json.loads((OUT_DATA / "corridor.json").read_text())
    a, c = d["audit"], d["corridor"]
    js = d["junctions"]
    d2, pcu = a["day2"], a["pcu"]

    tot_veh = sum(j["daily_veh"] for j in js)
    tot_surv = sum(j["pcu_surveyed"] for j in js)
    tot_corr = sum(j["pcu_corrected"] for j in js)
    tw = next(f for f in pcu["factors"] if f["cls"] == "TWO_W")
    car = next(f for f in pcu["factors"] if f["cls"] == "CAR_BUCKET")

    # data the page's charts render from
    con = d.get("constraints") or {}
    capd = d.get("capacity") or {}
    sch = d.get("scheme") or {}
    sen = d.get("sensitivity") or {}
    chart = dict(
        constraints=con,
        capacity=capd,
        scheme=sch,
        sensitivity=sen,
        profiles=[dict(code=j["code"], peak=j["peak_start"],
                       v=[p["v"] for p in j["profile"]],
                       t=[p["t"] for p in j["profile"]]) for j in js],
        day2=dict(identical=d2["identical"], greater=d2["greater"], smaller=d2["smaller"]),
        junctions=[dict(code=j["code"], arms=j["arms"], daily=j["daily_veh"],
                        peak=j["peak_start"], peakveh=j["peak_veh"], phf=j["phf"],
                        thru=j["through_pct"], surv=j["pcu_surveyed"],
                        corr=j["pcu_corrected"], up=j["uplift_pct"],
                        matrix=j["matrix_veh"], lat=j["lat"], lon=j["lon"],
                        jda=j["jda_name"], conf=j["location_confidence"]) for j in js],
        factors=pcu["factors"],
    )

    sub = dict(
        DATA=json.dumps(chart, separators=(",", ":")),
        CORRIDOR=d["meta"]["corridor"], CITY=d["meta"]["city"],
        DATE1=d["meta"]["survey_dates"][0], DATE2=d["meta"]["survey_dates"][1],
        NJUNC=str(d["meta"]["n_junctions"]), BINS=fmt(d["meta"]["bins_parsed"]),
        TOTVEH=fmt(tot_veh),
        # finding 1
        SERIES=str(d2["series"]), IDENT=str(d2["identical"]),
        IDENTPCT=f"{100*d2['identical']/d2['series']:.0f}",
        GREATER=str(d2["greater"]), SMALLER=str(d2["smaller"]),
        # finding 2
        UPLIFT=f"{pcu['uplift_floor_pct']:.1f}",
        BANDLO=f"{pcu['band_low_pct']:.1f}", BANDHI=f"{pcu['band_high_pct']:.1f}",
        TWSHARE=f"{100*tw['share']:.1f}", CARSHARE=f"{100*car['share']:.1f}",
        TOTSURV=fmt(tot_surv), TOTCORR=fmt(tot_corr),
        # finding 3
        REFS=str(a["flow_diagram"]["ref_errors"]),
        REFSPER=str(a["flow_diagram"]["ref_errors"] // 12),
        # finding 4
        DISC=str(a["arithmetic"]["discrepancies"]),
        UNDER=str(a["arithmetic"]["understate"]), OVER=str(a["arithmetic"]["overstate"]),
        NETGT=fmt(a["arithmetic"]["net_grand_total"]),
        # what holds
        THRU=f"{c['through_pct_mean']:.1f}",
        THRULO=f"{c['through_pct_range'][0]:.1f}", THRUHI=f"{c['through_pct_range'][1]:.1f}",
        ORDER=" &rarr; ".join(x.replace("TMC-", "") for x in c["order_best"]),
        MARGIN=f"{c['order_margin_pct']:.1f}",
        CELLS=fmt(a["derived_sheets"]["cells_checked"]),
        ROAD=d["meta"].get("road", ""), SCHEME=d["meta"].get("jda_scheme", ""),
        CKM=f"{con.get('corridor_km', 0):.2f}", CSTN=str(con.get("stations", 0)),
        CFREE=str(con.get("hard_free", 0)),
        CFREEPCT=f"{con.get('hard_free_pct', 0):.0f}",
        CRUN1=fmt(con.get("longest_clear_runs_m", [0])[0]),
        CRUN2=fmt(con.get("longest_clear_runs_m", [0, 0])[1]),
        UTURNS=str(con.get("uturn_possible", 0)),
        UTPERKM=f"{con.get('uturn_per_km', 0):.1f}",
        UTTYP=str(con.get("opening_classes", {}).get("typical opening", 0)),
        UTMOUTH=str(con.get("opening_classes", {}).get("wide / junction mouth", 0)),
        UTMARG=str(con.get("opening_classes", {}).get("marginal", 0)),
        NAMEMATCH=str(sum(1 for j in js if j["location_confidence"] == "name match")),
        SFAIL=str(sch.get("fails_conservative", 0)),
        SFAILOPT=str(sch.get("fails_optimistic", 0)),
        SN=str(len(sch.get("uturns", []))),
        SNOGAP=str(sch.get("no_viable_gap", 0)),
        SFORCED=fmt(sch.get("forced_uturns_per_hour", 0)),
        SOK=str(sch.get("s1_serviceable", 0)),
        SNJ=str(sch.get("n_junctions", 0)),
        SENSN=str(sen.get("combinations", 0)),
        SENSUOPT=str((sen.get("uturn") or {}).get("optimistic", {}).get("fails", 0)),
        SENSUOF=str((sen.get("uturn") or {}).get("optimistic", {}).get("of", 0)),
        SENSEOK=str(sen.get("elevated_all_pass_combinations", 0)),
        SENSETOT=str(sen.get("elevated_total_combinations", 0)),
        CAPRATIO=f"{capd.get('observed_vs_planning_ratio', 0):.2f}",
        CAPOK=str(capd.get("approaches_ok_after_grade_separation", 0)),
        CAPN=str(len(capd.get("relief", []))),
        CAPYEAR=str(capd.get("horizon_year", "")),
        CAPMULT=f"{(capd.get('growth') or [{},{'multiple':0}])[1].get('multiple', 0):.2f}",
        CAPW=f"{list((capd.get('widths') or {}).values())[0].get('width_m', 0):.1f}"
             if capd.get("widths") else "0",
    )
    sub = {k: ascii_only(v) for k, v in sub.items()}
    html = Template(TPL.read_text()).substitute(sub)
    assert all(ord(c) < 128 for c in html), "page must be pure ASCII"
    out = OUT / "corridor_audit.html"
    out.write_text(html)
    return out, len(html)


if __name__ == "__main__":
    p, n = build()
    print(f"written: {p}  ({n/1024:,.0f} KB)")
