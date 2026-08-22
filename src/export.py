"""
export.py — pipeline results -> static JSON for the dashboards.

No backend. One file, read directly by the Artifact page and the Next.js app, so
both render identical figures from identical numbers.

Run:  uv run python src/export.py
"""
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.analyse import (composition, corridor_order, movements, peak_hours,
                         through_vs_turning, tmc_matrix)
from src.config import (CORRIDOR_NAME, CORRIDOR_ROAD, JDA_SCHEME, JUNCTIONS,
                        JUNCTION_COORDS, OUT_DATA, SURVEY_DATES)
from src.pcu import SURVEYED, convert, factor_band
from src.tmc_parse import CLASS_LABELS, parse_all


def jsonable(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError(type(o))


def _constraints():
    """Atlas and median findings, if those stages have been run."""
    prof_p = OUT_DATA / "constraint_profile.json"
    med_p = OUT_DATA / "median_openings.geojson"
    if not prof_p.exists() or not med_p.exists():
        return None
    prof = json.loads(prof_p.read_text())
    med = json.loads(med_p.read_text())["features"]
    # full drawing inventory, not just what falls inside a pier footprint
    sum_p = OUT_DATA / "atlas_summary.json"
    inv = json.loads(sum_p.read_text())["categories"] if sum_p.exists() else {}
    cats = {k: v["features"] for k, v in inv.items()
            if k not in ("carriageway", "median", "alignment")}
    cats = dict(sorted(cats.items(), key=lambda kv: -kv[1]))
    hard_free = [r for r in prof if r["hard"] == 0]
    runs, cur = [], None
    for r in prof:
        if r["hard"] == 0:
            cur = cur if cur is not None else r["chainage_m"]
        elif cur is not None:
            runs.append(r["chainage_m"] - cur); cur = None
    if cur is not None:
        runs.append(prof[-1]["chainage_m"] - cur)
    turnable = [f["properties"] for f in med if f["properties"]["uturn_possible"]]
    by_class = {}
    for f in med:
        c = f["properties"]["classification"]
        by_class[c] = by_class.get(c, 0) + 1
    return dict(
        corridor_km=round(prof[-1]["chainage_m"] / 1000, 2),
        stations=len(prof), pier_radius_m=8, station_step_m=25,
        hard_free=len(hard_free),
        hard_free_pct=round(100 * len(hard_free) / len(prof), 1),
        longest_clear_runs_m=sorted(runs, reverse=True)[:3],
        totals=cats,
        layers={k: v["layers"] for k, v in inv.items()},
        median_openings=len(med), uturn_possible=len(turnable),
        uturn_per_km=round(len(turnable) / (prof[-1]["chainage_m"] / 1000), 1),
        opening_classes=by_class,
    )


def build():
    bins, mism = parse_all()
    day = sorted(bins.date.unique())[0]
    day2 = sorted(bins.date.unique())[1]

    ph = peak_hours(bins, day).set_index("junction")
    tv = through_vs_turning(bins, day).set_index("junction")
    comp = composition(bins, day)
    pcu_df, shares = convert(bins)
    pcu_day = pcu_df[pcu_df.date == day].set_index("junction")
    best, cost, top, margin, links = corridor_order(bins, day)

    mv = movements(bins, day)

    # --- day-2 derivation evidence, recomputed here so the page can cite it ----
    piv = (bins[bins.kind == "movement"]
           .groupby(["junction", "sheet", "veh_class", "date"])["count"].sum()
           .unstack("date").dropna())
    piv = piv[(piv[day] > 0) | (piv[day2] > 0)]
    d2 = dict(series=int(len(piv)),
              identical=int((piv[day2] == piv[day]).sum()),
              greater=int((piv[day2] > piv[day]).sum()),
              smaller=int((piv[day2] < piv[day]).sum()))

    junctions = []
    for code in JUNCTIONS:
        veh, pcu = tmc_matrix(bins, day, code)
        g = mv[mv.junction == code]
        profile = (g.groupby("bin_start")["count"].sum().sort_index())
        c = comp[comp.junction == code].sort_values("count", ascending=False)
        lat, lon, jda_name, cluster, conf = JUNCTION_COORDS[code]
        junctions.append(dict(
            code=code,
            arms=list(JUNCTIONS[code]),
            lat=lat, lon=lon, jda_name=jda_name,
            signal_cluster=cluster, location_confidence=conf,
            daily_veh=int(ph.loc[code, "daily_veh"]),
            peak_start=ph.loc[code, "peak_start"].strftime("%H:%M"),
            peak_veh=int(ph.loc[code, "peak_veh"]),
            peak15=int(ph.loc[code, "peak15"]),
            phf=float(ph.loc[code, "phf"]),
            through_pct=float(tv.loc[code, "through_pct"]),
            corridor_through_pct=float(tv.loc[code, "corridor_through_pct"]),
            pcu_surveyed=int(pcu_day.loc[code, "pcu_surveyed"]),
            pcu_corrected=int(pcu_day.loc[code, "pcu_corrected_floor"]),
            pcu_band=[int(pcu_day.loc[code, "pcu_band_low"]),
                      int(pcu_day.loc[code, "pcu_band_high"])],
            uplift_pct=round(float(pcu_day.loc[code, "uplift_floor_pct"]), 1),
            matrix_veh=[[int(v) for v in row] for row in veh.values],
            matrix_pcu=[[round(float(v), 1) for v in row] for row in pcu.values],
            composition=[dict(cls=r.veh_class, label=CLASS_LABELS[r.veh_class],
                              count=int(r["count"]), share=round(float(r.share), 5))
                         for _, r in c.iterrows()],
            profile=[dict(t=t.strftime("%H:%M"), v=int(v)) for t, v in profile.items()],
        ))

    # factor table at corridor-wide shares
    corridor_share = (mv.groupby("veh_class")["count"].sum())
    corridor_share = corridor_share / corridor_share.sum()
    factors = []
    for cls, sh in corridor_share.sort_values(ascending=False).items():
        lo, pt, hi = factor_band(cls, sh)
        factors.append(dict(cls=cls, label=CLASS_LABELS[cls], share=round(float(sh), 5),
                            surveyed=SURVEYED[cls], irc_low=round(lo, 2),
                            irc_point=(round(pt, 2) if pt is not None else None),
                            irc_high=round(hi, 2), composite=pt is None))

    payload = dict(
        meta=dict(corridor=CORRIDOR_NAME, road=CORRIDOR_ROAD, jda_scheme=JDA_SCHEME,
                  city="Jaipur",
                  survey_dates=list(SURVEY_DATES), analysis_date=str(day),
                  n_junctions=len(JUNCTIONS), bins_parsed=int(len(bins)),
                  note="Day 2 excluded from analysis: see audit finding F."),
        audit=dict(
            arithmetic=dict(discrepancies=int(len(mism)),
                            understate=int((mism.delta < 0).sum()), overstate=int((mism.delta > 0).sum()),
                            net_grand_total=int(-mism[mism.field == 'Grand Total (Nos.)'].delta.sum())),
            derived_sheets=dict(cells_checked=92160, exact=92160,
                                conclusion="IN_/OUT_/TOTAL_ are formula views of the 12 V_ sheets"),
            day2=d2,
            pcu=dict(factors=factors,
                     uplift_floor_pct=round(float(pcu_df.uplift_floor_pct.mean()), 1),
                     band_low_pct=round(100 * float((pcu_df.pcu_band_low - pcu_df.pcu_surveyed).sum()
                                                    / pcu_df.pcu_surveyed.sum()), 1),
                     band_high_pct=round(100 * float((pcu_df.pcu_band_high - pcu_df.pcu_surveyed).sum()
                                                     / pcu_df.pcu_surveyed.sum()), 1)),
            flow_diagram=dict(ref_errors=960, files_affected=12,
                              mislabelled=[["Taxi", 19012, "Motar Cycle, Scooter (two-wheelers)"],
                                           ["TW", 305, "Agriculture Tractor, LCV Mini Bus"],
                                           ["E-Rickshaw", 9, "Hand Cart"],
                                           ["Others", 268, "Horse Drawn"]]),
            survey_design=[
                "11 May 2026 is a Monday; the methodology specifies Tue/Wed/Thu and excludes Monday.",
                "May is pre-monsoon peak heat; recommended windows are Oct-Nov or Feb-Mar.",
                "No weekend day surveyed; the stated minimum is three days including Sat and Sun.",
                "U-turns were never counted. Twelve movements per junction, not sixteen.",
            ],
        ),
        constraints=_constraints(),
        junctions=junctions,
        corridor=dict(
            through_pct_mean=round(float(tv.through_pct.mean()), 1),
            through_pct_range=[float(tv.through_pct.min()), float(tv.through_pct.max())],
            order_best=list(best), order_cost=round(float(cost), 4),
            order_margin_pct=round(float(margin), 1),
            order_conclusive=bool(margin >= 10),
            order_candidates=[dict(cost=c, order=list(p)) for c, p in top],
            links=[{k: (v if not hasattr(v, "item") else v.item()) for k, v in r.items()}
                   for r in links.to_dict("records")],
        ),
    )
    return payload


if __name__ == "__main__":
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    p = build()
    path = OUT_DATA / "corridor.json"
    blob = json.dumps(p, indent=1, default=jsonable)
    path.write_text(blob)
    # the Next.js app reads the same file, so both dashboards render identical figures
    web = OUT_DATA.parent.parent / "web" / "public"
    if web.parent.exists():
        web.mkdir(parents=True, exist_ok=True)
        (web / "corridor.json").write_text(blob)
    kb = path.stat().st_size / 1024
    print(f"written : {path}  ({kb:,.0f} KB)")
    print(f"junctions      : {len(p['junctions'])}")
    print(f"profile points : {sum(len(j['profile']) for j in p['junctions'])}")
    print(f"through mean   : {p['corridor']['through_pct_mean']}%")
    print(f"PCU uplift     : +{p['audit']['pcu']['uplift_floor_pct']}% floor, "
          f"band +{p['audit']['pcu']['band_low_pct']}% to +{p['audit']['pcu']['band_high_pct']}%")
    print(f"day2 identical : {p['audit']['day2']['identical']}/{p['audit']['day2']['series']} series")
    print(f"order          : {' -> '.join(p['corridor']['order_best'])} "
          f"(conclusive={p['corridor']['order_conclusive']})")
