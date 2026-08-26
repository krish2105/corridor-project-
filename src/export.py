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
from src.config import (CHAINAGE_FROM, CHAINAGE_ZERO_AT,
                        OUT, ROOT, CORRIDOR_NAME, CORRIDOR_ROAD, CORRIDOR_ROAD_SOURCE,
                        JDA_SCHEME, JUNCTIONS,
                        JUNCTION_COORDS, OUT_DATA, SURVEY_DATES)
# The criticality ranking is computed HERE as well as in the workbook, by calling the
# same function on the same payload, so the dashboard and the Excel file cannot disagree.
# Recomputing it in the browser from the published components would be a second
# implementation of a scoring rule, and two implementations of a scoring rule drift.
from src.masterdb import criticality
from src.pcu import SURVEYED, convert, factor_band
from src.spelling import fix as spell
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


def _capacity():
    """Phase 7 results, if that stage has been run."""
    p = OUT_DATA / "capacity.json"
    return json.loads(p.read_text()) if p.exists() else None


def _delay():
    """Queue, delay and journey time, if that stage has been run."""
    p = OUT_DATA / "delay.json"
    return json.loads(p.read_text()) if p.exists() else None


def _economics():
    """Cost of delay, if that stage has been run."""
    p = OUT_DATA / "economics.json"
    return json.loads(p.read_text()) if p.exists() else None


def _standards():
    p = OUT_DATA / "standards.json"
    return json.loads(p.read_text()) if p.exists() else None


def _safety():
    p = OUT_DATA / "safety.json"
    return json.loads(p.read_text()) if p.exists() else None


def _section(name):
    """A generated dataset, published as-is. None when it has not been generated yet."""
    p = OUT_DATA / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


# corridor.json is fetched on every page view, so it carries SUMMARIES only. The heavy
# per-bin series - 1,116 LOS cells, 96-step cumulative curves, 576 raster cells and five
# continuity series - are split into files the page fetches when a reader opens the
# exhibit that needs them. Keeping them inline took corridor.json from 84 KB to 265 KB,
# which is three times the payload for data most readers never scroll to.
HEAVY = {"profiles": ("los_grid", "cumulative"),
         "exhibits": ("flow_raster", "continuity", "volume_flow")}


def _split(name):
    """Return (summary, heavy) for a dataset, or (None, None)."""
    p = OUT_DATA / f"{name}.json"
    if not p.exists():
        return None, None
    d = json.loads(p.read_text())
    heavy = {k: d[k] for k in HEAVY[name] if k in d}
    summary = {k: v for k, v in d.items() if k not in heavy}
    # keep a light shape hint so the page knows what it can lazily fetch
    summary["series_available"] = sorted(heavy)
    return summary, heavy


def _profiles():
    return _split("profiles")[0]


def _exhibits():
    return _split("exhibits")[0]


def _scheme():
    """Phase 8 scheme test, if that stage has been run."""
    p = OUT_DATA / "scheme_test.json"
    return json.loads(p.read_text()) if p.exists() else None


def _simplify(coords, tol_deg=0.0000045):
    """Douglas-Peucker. tol is ~0.5 m at this latitude."""
    if len(coords) < 3:
        return coords
    def rdp(pts):
        if len(pts) < 3:
            return pts
        (x0, y0), (x1, y1) = pts[0], pts[-1]
        dx, dy = x1 - x0, y1 - y0
        n = (dx * dx + dy * dy) ** .5 or 1e-12
        worst, wi = 0.0, 0
        for i in range(1, len(pts) - 1):
            px, py = pts[i]
            d = abs(dy * px - dx * py + x1 * y0 - y1 * x0) / n
            if d > worst:
                worst, wi = d, i
        if worst <= tol_deg:
            return [pts[0], pts[-1]]
        return rdp(pts[:wi + 1])[:-1] + rdp(pts[wi:])
    import sys as _s
    lim = _s.getrecursionlimit()
    _s.setrecursionlimit(max(lim, 10000))
    try:
        return rdp(coords)
    finally:
        _s.setrecursionlimit(lim)


def _write_basemap(webdir):
    """
    A basemap built from the survey drawing itself, replacing the OSM raster tiles.

    The map previously pulled tiles from tile.openstreetmap.org. That breaches the OSM
    Tile Usage Policy for a production or commercial deliverable, and the practical risk
    is worse than the licensing one: OSM rate-limits or blocks abusive clients without
    warning, and this map is the centrepiece of the constraints section. A basemap that
    can disappear mid-meeting is not a basemap.

    We already own better. The drawing carries 949 carriageway edges, 1,015 building
    footprints, the medians and the alignment - surveyed geometry rather than a generic
    tile layer, which is also the more defensible backdrop for a survey deliverable.
    No third party, no API key, no policy to breach, and nothing to rate-limit.

    Simplified harder than the analysis layers (2 m rather than 0.5 m) because this is
    context, not measurement. Nothing is measured off the basemap.
    """
    src = OUT_DATA / "atlas.geojson"
    if not src.exists() or not webdir.parent.exists():
        return None
    webdir.mkdir(parents=True, exist_ok=True)
    g = json.loads(src.read_text())
    BASE = {"carriageway", "structures", "alignment", "median"}
    COARSE = 0.000018          # ~2 m at this latitude
    feats = []
    for f in g["features"]:
        cat = f["properties"].get("category")
        if cat not in BASE:
            continue
        geom = f["geometry"]
        if geom["type"] == "LineString":
            c = _simplify([tuple(p) for p in geom["coordinates"]], tol_deg=COARSE)
            if len(c) < 2:
                continue
            geom = dict(type="LineString", coordinates=[[round(x, 6), round(y, 6)]
                                                        for x, y in c])
        feats.append(dict(type="Feature", geometry=geom,
                          properties=dict(category=cat)))
    out = webdir / "basemap.geojson"
    out.write_text(json.dumps(dict(type="FeatureCollection", features=feats),
                              separators=(",", ":")))
    return len(feats), out.stat().st_size


def _write_chainage_markers(webdir, every=500.0):
    """
    Chainage posts along JDA's centreline, every `every` metres.

    Computed here in EPSG:32643 rather than in the browser. The map is in WGS84 and a
    kilometre reckoned in degrees at this latitude is out by enough to put a post on the
    wrong side of a junction - and the project rule is that no distance is ever computed
    in degrees.

    Each post carries its chainage and a bearing, so the map can show which way the
    numbering runs rather than leaving a reader to infer it from two labels.
    """
    import math
    from pyproj import Transformer
    from src.config import CHAINAGE_FROM, CHAINAGE_ZERO_AT, CORRIDOR_CENTRELINE
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    to_geo = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
    pts = [to_utm.transform(lon, lat) for lon, lat in CORRIDOR_CENTRELINE]

    feats, acc, target = [], 0.0, 0.0
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        seg = math.dist((ax, ay), (bx, by))
        if seg == 0:
            continue
        brg = (math.degrees(math.atan2(bx - ax, by - ay)) + 360) % 360
        while target <= acc + seg:
            f = (target - acc) / seg
            lon, lat = to_geo.transform(ax + f * (bx - ax), ay + f * (by - ay))
            feats.append(dict(type="Feature",
                              geometry=dict(type="Point", coordinates=[lon, lat]),
                              properties=dict(ch=int(round(target)),
                                              km=round(target / 1000, 1),
                                              major=int(round(target)) % 1000 == 0,
                                              bearing=round(brg, 1))))
            target += every
        acc += seg
    out = webdir / "chainage.geojson"
    out.write_text(json.dumps(dict(
        type="FeatureCollection",
        properties=dict(interval_m=every, chainage_from=CHAINAGE_FROM,
                        zero_at=CHAINAGE_ZERO_AT, total_m=round(acc)),
        features=feats), separators=(",", ":")))
    return len(feats), round(acc)


def _write_web_layers(webdir):
    """Constraint atlas + junction candidates, simplified for the browser."""
    src = OUT_DATA / "atlas.geojson"
    if not src.exists() or not webdir.parent.exists():
        return
    webdir.mkdir(parents=True, exist_ok=True)
    g = json.loads(src.read_text())
    keep = {"structures", "vegetation", "drainage", "electrical", "telecom",
            "gas", "geotech", "water", "religious", "rail", "median", "alignment"}
    feats = []
    for f in g["features"]:
        cat = f["properties"].get("category")
        if cat not in keep:
            continue
        geom = f["geometry"]
        if geom["type"] == "LineString":
            c = _simplify([tuple(p) for p in geom["coordinates"]])
            if len(c) < 2:
                continue
            geom = dict(type="LineString", coordinates=[list(p) for p in c])
        feats.append(dict(type="Feature", geometry=geom,
                          properties=dict(category=cat, layer=f["properties"].get("layer"))))
    # JDA's own centreline, so the map draws THEIR geometry rather than joining our pins
    from src.config import CORRIDOR_CENTRELINE
    (webdir / "centreline.geojson").write_text(json.dumps({
        "type": "Feature", "properties": {"source": "JDA KML"},
        "geometry": {"type": "LineString",
                     "coordinates": [[lo, la] for lo, la in CORRIDOR_CENTRELINE]}},
        separators=(",", ":")))

    (webdir / "atlas.geojson").write_text(
        json.dumps(dict(type="FeatureCollection", features=feats), separators=(",", ":")))
    # deliverables a reviewer can pull straight off the page. Cross-verification is the
    # product; making someone email for the data defeats it.
    import shutil as _sh
    missing = []
    for src_f in (OUT / "audit_report.md", OUT / "corridor_constraint_atlas.pdf",
                  OUT / "capacity_report.md", OUT / "method_statement.md",
                  OUT / "validation_report.md", ROOT / "docs" / "data_dictionary.md",
                  OUT_DATA / "median_openings.geojson", OUT_DATA / "scheme_test.json",
                  OUT_DATA / "capacity.json", OUT_DATA / "sensitivity.json",
                  OUT_DATA / "delay.json", OUT_DATA / "economics.json",
                  OUT_DATA / "safety.json", OUT_DATA / "profiles.json",
                  OUT_DATA / "exhibits.json",
                  # atlas_summary is read by reports.py and was the last generated input
                  # with no committed copy, so five report tests could not run in CI.
                  OUT_DATA / "atlas_summary.json",
                  # not client data - our own test count, and committing it is what
                  # lets a clean checkout render the same README the repo carries.
                  OUT_DATA / "testcount.json",
                  OUT_DATA / "standards.json",
                  OUT_DATA / "anomaly.json", OUT_DATA / "cluster.json",
                  OUT_DATA / "forecast.json",
                  OUT_DATA / "uturn_framework.json",
                  OUT_DATA / "measurement.json"):
        if src_f.exists():
            _sh.copy(src_f, webdir / src_f.name)
        else:
            # Silently skipping is how four dead download links reached the dashboard.
            # The panel advertises each of these by name, so a missing one is a broken
            # promise to the reader, not an optional extra.
            missing.append(src_f.name)

    if missing:
        print(f"  WARNING - {len(missing)} advertised deliverable(s) were not on disk and")
        print(f"  the dashboard will link to nothing for them: {', '.join(missing)}")
        print("  run the producing module first; see PIPELINE_ORDER in service_docs.py")

    cand = OUT_DATA / "junction_candidates.geojson"
    if cand.exists():
        (webdir / "junction_candidates.geojson").write_text(
            json.dumps(json.loads(cand.read_text()), separators=(",", ":")))
    prof = OUT_DATA / "constraint_profile.json"
    if prof.exists():
        rows = json.loads(prof.read_text())
        (webdir / "constraint_profile.json").write_text(json.dumps(
            [dict(ch=round(r["chainage_m"]), score=r["score"], hard=r["hard"]) for r in rows],
            separators=(",", ":")))


def _sensitivity():
    p = OUT_DATA / "sensitivity.json"
    return json.loads(p.read_text()) if p.exists() else None


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
            composition=[dict(cls=r.veh_class, label=spell(CLASS_LABELS[r.veh_class]),
                              label_as_received=CLASS_LABELS[r.veh_class],
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
        factors.append(dict(cls=cls, label=spell(CLASS_LABELS[cls]),
                            label_as_received=CLASS_LABELS[cls],
                            share=round(float(sh), 5),
                            surveyed=SURVEYED[cls], irc_low=round(lo, 2),
                            irc_point=(round(pt, 2) if pt is not None else None),
                            irc_high=round(hi, 2), composite=pt is None))

    payload = dict(
        meta=dict(corridor=CORRIDOR_NAME, road=CORRIDOR_ROAD,
                  road_source=CORRIDOR_ROAD_SOURCE, jda_scheme=JDA_SCHEME,
                  chainage_from=CHAINAGE_FROM, chainage_zero_at=CHAINAGE_ZERO_AT,
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
        capacity=_capacity(),
        scheme=_scheme(),
        sensitivity=_sensitivity(),
        delay=_delay(),
        economics=_economics(),
        safety=_safety(),
        standards=_standards(),
        profiles=_profiles(),
        exhibits=_exhibits(),
        anomaly=_section("anomaly"),
        cluster=_section("cluster"),
        forecast=_section("forecast"),
        uturn_framework=_section("uturn_framework"),
        measurement=_section("measurement"),
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
    payload["criticality"] = criticality(payload).to_dict("records")
    payload["spelling"] = _spelling_section()
    # Correct spelling ONCE, at the publishing boundary, rather than at a dozen call
    # sites. Every module below writes the survey's labels as issued - which is right,
    # because those files are the check-the-work artefacts - and the dashboard reads only
    # this payload, so this is the single place a reader's copy is produced.
    return spell_payload(payload)


def spell_payload(obj):
    """
    Apply the correction register to every string in the payload, recursively.

    Skips anything under a key that records provenance, because correcting the field
    whose whole job is to preserve the source spelling would erase the evidence for the
    correction. That is not hypothetical: `label_as_received` sits two lines from `label`
    in the same dict.
    """
    if isinstance(obj, dict):
        return {k: (v if (k == "as_received" or k.endswith("_as_received"))
                    else spell_payload(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [spell_payload(v) for v in obj]
    return spell(obj) if isinstance(obj, str) else obj


def _spelling_section():
    from src.spelling import CORRECTIONS, unconfirmed
    return dict(
        policy=("source labels are left exactly as issued; correction happens at the "
                "publishing boundary and both spellings are published"),
        corrections=CORRECTIONS, n_corrections=len(CORRECTIONS),
        n_unconfirmed=len(unconfirmed()))


if __name__ == "__main__":
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    p = build()
    path = OUT_DATA / "corridor.json"
    blob = json.dumps(p, indent=1, default=jsonable)
    path.write_text(blob)
    # web-sized constraint layers. The full atlas is 4.5 MB, most of it vertex noise on
    # building outlines; simplifying to 0.5 m and dropping single-point clutter keeps
    # every feature JDA needs to cross-check while staying loadable on a phone.
    _write_web_layers(OUT_DATA.parent.parent / "web" / "public")
    webdir = OUT_DATA.parent.parent / "web" / "public"
    for name in ("profiles", "exhibits"):
        _s, heavy = _split(name)
        if heavy:
            f = webdir / f"{name}_series.json"
            f.write_text(json.dumps(heavy, separators=(",", ":")))
            print(f"{name+'_series':<15}: {f.stat().st_size/1024:.0f} KB, lazily fetched")
    ch_n, ch_len = _write_chainage_markers(webdir)
    print(f"chainage       : {ch_n} posts over {ch_len:,} m, "
          f"zero at the {CHAINAGE_ZERO_AT}")
    bm = _write_basemap(webdir)
    if bm:
        print(f"basemap        : {bm[0]:,} surveyed features, {bm[1]/1024:.0f} KB "
              f"(replaces OSM tiles)")

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
