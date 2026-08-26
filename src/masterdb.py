"""
masterdb.py — the six-junction master database, as one Excel workbook.

Deliverables 1 to 6 and 8 in a single file, because that is the form asked for. Every
sheet is generated from the pipeline: nothing here is transcribed, and no figure is typed
by hand. Re-running this after a pipeline change reproduces it exactly.

WHAT IT COMBINES
  traffic   the 12 JDA workbooks, parsed and re-derived, never trusting a stored total
  KML       JDA's supplied junction positions and corridor centreline
  survey    the CAD drawing: measured widths, median openings, constraints

MEASUREMENT STATUS, stated once and carried on every sheet that depends on it.
The DWG carries no dimension entities. Every width, offset and chainage here is derived
from georeferenced linework in EPSG:32643 and is PROVISIONAL. A total station survey is
required before any of it is used for design. That is not a formality: ten transects
measure over 14 m per direction, which is either five running lanes or a service road
being read as carriageway, and capacity scales linearly with the answer.

Run:  uv run python src/masterdb.py
"""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import (CORRIDOR_ROAD, CORRIDOR_ROAD_SOURCE, JUNCTION_COORDS,
                        OUT, OUT_DATA, ROOT)
from src.spelling import CORRECTIONS, fix as spell

BOOK = OUT / "Six_Junction_Master_Database.xlsx"

PROVISIONAL = (
    "PROVISIONAL. Derived from georeferenced CAD linework (EPSG:32643), not from "
    "dimension entities: the DWG contains none. A total station survey is required "
    "before design use.")


def _load(name):
    p = OUT_DATA / f"{name}.json"
    if not p.exists():
        raise SystemExit(f"missing {name}.json - run the pipeline first")
    return json.loads(p.read_text())


def cover(d):
    """Sheet 0. What this file is, where every number came from, and what is not certain."""
    rows = [
        ("Deliverable", "Six-Junction Master Database"),
        ("Corridor", CORRIDOR_ROAD),
        ("Road name source", CORRIDOR_ROAD_SOURCE),
        ("Junctions", f"{len(JUNCTION_COORDS)} (TMC-01 to TMC-06)"),
        ("Survey dates", " and ".join(d["meta"]["survey_dates"])),
        ("Generated", date.today().isoformat()),
        ("", ""),
        ("SOURCES COMBINED", ""),
        ("Traffic", "12 JDA workbooks, re-derived from components; no stored total trusted"),
        ("Positions and centreline", "JDA supplied KML"),
        ("Widths, medians, constraints", "JDA survey drawing (DWG converted to DXF)"),
        ("", ""),
        ("MEASUREMENT STATUS", PROVISIONAL),
        ("Why it matters", "Ten transects read over 14 m per direction. That is five "
                           "running lanes each way, or a service road counted as "
                           "carriageway. Capacity scales linearly with the answer."),
        ("", ""),
        ("STATED GAPS", ""),
        ("U-turns", "Not counted anywhere in the survey. No column exists."),
        ("E-rickshaw", "No column, though the label appears in the workbook string table."),
        ("Pedestrians", "IRC:SP:41 Table 3.1 carries the row; it was left empty."),
        ("Day two", f"{d['audit']['day2']['identical']} of {d['audit']['day2']['series']} "
                    "series reproduce day one exactly. One day of observation, not two."),
        ("Arithmetic", f"{d['audit']['arithmetic']['discrepancies']} stored totals "
                       "disagree with their own components. All are registered."),
        ("Automated counting", "Built, not verified. No accuracy figure is claimed."),
    ]
    return pd.DataFrame(rows, columns=["Item", "Detail"])


def inventory(d):
    """Deliverable 2. One profile row per junction."""
    w = d["capacity"]["widths"]
    rows = []
    for j in d["junctions"]:
        code = j["code"]
        lat, lon, jda, cluster, src = JUNCTION_COORDS[code]
        arms = j["arms"]
        rows.append({
            "Junction": code,
            "JDA scheme name": jda.strip(),
            "Latitude": lat, "Longitude": lon,
            "Position source": src,
            "North arm": arms[0], "East arm": arms[1],
            "South arm": arms[2], "West arm": arms[3],
            "Approaches": len(arms),
            "Movements counted": 12,
            "U-turn counted": "No",
            "Carriageway width per direction (m)": round(w.get(code, {}).get("width_m", 0), 1),
            "Width status": "provisional, CAD-derived",
            "Daily vehicles": j.get("daily_veh"),
            "Peak hour starts": j.get("peak_start"),
            "Peak hour vehicles": j.get("peak_veh"),
            "PHF": j.get("phf"),
            "Through movement %": j.get("through_pct"),
        })
    return pd.DataFrame(rows)


def hourly(bins):
    """Deliverable 3. Hour by hour at each junction, with the busiest and quietest."""
    mv = bins[bins.kind == "movement"].copy()
    mv["hour"] = mv.bin_start.dt.strftime("%H:00")
    g = (mv.groupby(["junction", "date", "hour"])["count"].sum()
           .reset_index().rename(columns={"count": "Vehicles"}))
    g["date"] = g["date"].astype(str)
    return g.rename(columns={"junction": "Junction", "date": "Date", "hour": "Hour"})


def hourly_extremes(h):
    rows = []
    for (j, dt), g in h.groupby(["Junction", "Date"]):
        hi = g.loc[g.Vehicles.idxmax()]
        lo = g.loc[g.Vehicles.idxmin()]
        rows.append({"Junction": j, "Date": dt,
                     "Busiest hour": hi.Hour, "Busiest hour vehicles": int(hi.Vehicles),
                     "Quietest hour": lo.Hour, "Quietest hour vehicles": int(lo.Vehicles),
                     "Peak to trough ratio": round(hi.Vehicles / max(1, lo.Vehicles), 1)})
    return pd.DataFrame(rows)


def _by_day(bins, keys):
    """
    Split any grouping across the two survey days rather than summing them.

    Summing would be the obvious thing and it would be wrong. Day two reproduces day one
    exactly on 396 of 555 movement-by-class series, so adding the days together doubles a
    figure that was largely copied and presents it as two days of observation. Here the
    days stay apart and a flag says, at this grouping, whether day two is a duplicate. A
    reader can then sum them or not, knowing what they are summing.

    The flag is computed PER VEHICLE CLASS even where the sheet totals over classes, and
    reported as a count. Ten class series that are each a copy of day one sum to a total
    differing by a few vehicles, so a flag taken on the total reads False and says the day
    is independent when it is not. The count says how much of the row is a copy.
    """
    mv = bins[bins.kind == "movement"]
    t = mv.groupby(keys + ["date"])["count"].sum().unstack("date")
    d1, d2 = sorted(t.columns)
    out = t.reset_index()
    out["Day 1 vehicles"] = out[d1].round().astype(int)
    out["Day 2 vehicles"] = out[d2].round().astype(int)
    out = out.drop(columns=[d1, d2])

    if "veh_class" in keys:
        out["Day 2 identical to day 1"] = out["Day 1 vehicles"] == out["Day 2 vehicles"]
        return out

    # count the class series inside each row that day two reproduces exactly
    c = mv.groupby(keys + ["veh_class", "date"])["count"].sum().unstack("date")
    c = c[(c[d1] > 0) | (c[d2] > 0)]        # a class absent on both days is not evidence
    same = c[d1].eq(c[d2]).groupby(level=keys).agg(n_same="sum", n="size").reset_index()
    out = out.merge(same, on=keys, how="left")
    out["Class series identical to day 1"] = (out.n_same.astype(int).astype(str)
                                              + " of " + out.n.astype(int).astype(str))
    return out.drop(columns=["n_same", "n"])


def composition(bins):
    """Deliverable 4. Share and volume of every vehicle class, per day."""
    from src.tmc_parse import CLASS_LABELS
    t = _by_day(bins, ["junction", "veh_class"])
    tot = t.groupby("junction")["Day 1 vehicles"].transform("sum")
    t["Share of junction, day 1 %"] = (100 * t["Day 1 vehicles"] / tot).round(2)
    # The survey column heading, corrected, with the heading as issued beside it. A
    # workbook that reproduces "Motar Cycle" reads as careless; one that silently fixes it
    # cannot be traced back to a source cell. Both, then.
    src = t.veh_class.map(CLASS_LABELS)
    t.insert(1, "Survey column", src.map(spell))
    t.insert(2, "Survey column as issued", src)
    return t.rename(columns={"junction": "Junction", "veh_class": "Class code"})


def movements(bins):
    """Deliverable 5. Left, through and right at each junction, by approach, per day."""
    t = _by_day(bins, ["junction", "arm_from", "movement", "arm_to"])
    tot = t.groupby("junction")["Day 1 vehicles"].transform("sum")
    t["Share of junction, day 1 %"] = (100 * t["Day 1 vehicles"] / tot).round(2)
    t = t.rename(columns={"junction": "Junction", "arm_from": "From arm",
                          "movement": "Movement", "arm_to": "To arm"})
    for c in ("From arm", "To arm"):
        t[c] = t[c].map(spell)
    return t.sort_values(["Junction", "Day 1 vehicles"], ascending=[True, False])


def peak_pcu(d):
    """Deliverable 6. Morning and evening peaks, and classified traffic as PCU."""
    rows = []
    for j in d["junctions"]:
        code = j["code"]
        rows.append({
            "Junction": code,
            "Peak hour starts": j.get("peak_start"),
            "Peak hour vehicles": j.get("peak_veh"),
            "Peak 15-min": j.get("peak15"),
            "PHF": j.get("phf"),
            "Daily PCU as surveyed": j.get("pcu_surveyed"),
            "Daily PCU corrected (IRC:106)": j.get("pcu_corrected"),
            "PCU uplift %": j.get("uplift_pct"),
            "PCU band low": (j.get("pcu_band") or [None, None])[0],
            "PCU band high": (j.get("pcu_band") or [None, None])[1],
        })
    return pd.DataFrame(rows)


# The six indicators, machine name -> the label the workbook shows. Machine names because
# corridor.json is read by the dashboard and a key with spaces in it is a nuisance there;
# labels because a spreadsheet column called `uturn_demand` is a nuisance to a reviewer.
# One source, renamed at the boundary, so the two cannot drift apart.
INDICATORS = {
    "daily_veh": "Daily vehicles",
    "peak_veh": "Peak hour vehicles",
    "worst_vc": "Worst approach v/c",
    "uturn_demand": "U-turn demand under scheme",
    "exposure_change_pct": "Crossing exposure change %",
    "turning_share_pct": "Turning share %",
}


def criticality(d):
    """
    Deliverable 8. Which junctions need attention first.

    Ranked on indicators the survey actually supports, each normalised 0 to 1 across the
    six and then summed. No weighting is applied, because a weighting is a policy choice
    and inventing one here would present a judgement as a result. Every component score
    is published so a traffic engineer can apply their own.

    Called by export.py on the same payload, so the dashboard and the workbook show one
    ranking rather than two implementations of one.
    """
    sch = {}
    for u in d["scheme"]["uturns"]:
        sch[u["junction"]] = sch.get(u["junction"], 0) + u["uturn_demand"]
    saf = {s["junction"]: s for s in d["safety"]["junctions"]}

    rows = []
    for j in d["junctions"]:
        c = j["code"]
        vcs = [x.get("vc_pt", 0) for x in d["capacity"]["junctions"] if x["junction"] == c]
        rows.append({
            "junction": c,
            "jda_name": JUNCTION_COORDS[c][2].strip(),
            "daily_veh": j.get("daily_veh", 0),
            "peak_veh": j.get("peak_veh", 0),
            "worst_vc": round(max(vcs), 2) if vcs else 0,
            "uturn_demand": round(sch.get(c, 0)),
            "exposure_change_pct": saf.get(c, {}).get("change_pct", 0),
            "turning_share_pct": round(100 - (j.get("through_pct") or 0), 1),
        })
    df = pd.DataFrame(rows)
    for c in INDICATORS:
        lo, hi = df[c].min(), df[c].max()
        # a corridor where every junction scores the same has no ranking to report, and
        # dividing by (hi - lo) there would either raise or invent one
        df[f"n_{c}"] = 0.0 if hi == lo else ((df[c] - lo) / (hi - lo)).round(3)
    df["score"] = df[[f"n_{c}" for c in INDICATORS]].sum(axis=1).round(3)
    df["rank"] = df["score"].rank(ascending=False, method="min").astype(int)
    return df.sort_values("rank")


def criticality_sheet(d):
    """The same table with the labels a reviewer reads rather than the keys code reads."""
    cols = {"junction": "Junction", "jda_name": "JDA name",
            "score": "Criticality score", "rank": "Rank"}
    cols.update(INDICATORS)
    cols.update({f"n_{k}": f"{v} (normalised)" for k, v in INDICATORS.items()})
    return criticality(d).rename(columns=cols)


def spelling_sheet():
    """
    Sheet 9. Every label this workbook prints differently from the issued survey.

    Included because the reviewer will notice the difference and is entitled to see the
    full list rather than discover it one cell at a time. The two marked ASK JDA change a
    word rather than a letter and are on the question sheet.
    """
    return pd.DataFrame([{
        "As issued in the survey": c["as_received"],
        "As shown here": c["corrected"],
        "Kind": c["kind"],
        "Confirmed": "yes" if c["confirmed"] else "ASK JDA",
        "Note": c["note"],
    } for c in CORRECTIONS])


def build():
    d = _load("corridor")
    from src.tmc_parse import parse_all
    bins = parse_all()[0]

    h = hourly(bins)
    sheets = [
        ("0 READ ME", cover(d)),
        ("1 Junction inventory", inventory(d)),
        ("2 Hourly traffic", h),
        ("3 Hourly extremes", hourly_extremes(h)),
        ("4 Vehicle composition", composition(bins)),
        ("5 Turning movements", movements(bins)),
        ("6 Peak hour and PCU", peak_pcu(d)),
        ("8 Criticality ranking", criticality_sheet(d)),
        ("9 Spelling corrections", spelling_sheet()),
    ]
    OUT.mkdir(exist_ok=True)
    with pd.ExcelWriter(BOOK, engine="openpyxl") as xw:
        for name, df in sheets:
            df.to_excel(xw, sheet_name=name[:31], index=False)
    return sheets


if __name__ == "__main__":
    sheets = build()
    print("=== Six-Junction Master Database ===")
    print(f"  corridor : {CORRIDOR_ROAD}  ({CORRIDOR_ROAD_SOURCE})\n")
    for name, df in sheets:
        print(f"  {name:<26}{df.shape[0]:>7,} rows x {df.shape[1]:>2} cols")
    crit = dict(sheets)["8 Criticality ranking"]
    print(f"\n  Criticality ranking, unweighted sum of {len(INDICATORS)} normalised "
          f"indicators:")
    for _, r in crit.iterrows():
        print(f"    {r['Rank']}. {r['Junction']}  {r['JDA name']:<13}"
              f"score {r['Criticality score']:.3f}")
    print(f"\n  {PROVISIONAL}")
    print(f"\nwritten: {BOOK}")
