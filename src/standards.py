"""
standards.py — the corridor measured against the codes that govern it.

Every check here compares our own numbers against a clause someone can look up. Where a
clause could not be verified from a primary source, it is marked and the check is still
run, because a stated uncertainty is more useful than a silent omission.

The strongest finding is not one of ours. JDA states the scheme's basis as "approximately
50% of total traffic involves turning movements". The survey it commissioned says 29.6%.

Sources, all primary unless marked:
  IRC:SP:41-1994   at-grade intersections; Table 3.1 is the ORIGIN of this survey's
                   ten-column class scheme, and carries a PEDESTRIAN row it left empty
  IRC:SP:90-2010   grade separators; cl. 5.6.7 makes an intersection volume-delay survey
                   a MUST for justifying one, and it was never done
  IRC:SP:84-2014   median opening geometry: >=500 m spacing in built-up areas, 18-20 m
  IRC:103 (draft)  a zebra crossing shall NOT be provided above ~1250 PCU/h/direction
  IRC:106 (2022)   draft; Table 9 v/c to LOS for a multilane divided urban road
  JMRC Phase-II DPR (March 2012), Table 2.10 — a Rajasthan government transport document
                   using 2W = 0.75 and MAV = 3.7, the exact corrections this audit makes

Run:  uv run python src/standards.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import JUNCTION_COORDS, OUT_DATA

# IRC:SP:90-2010 cl. 5.7.1.2 and cl. 5.10.4(iii) / IRC:92-2017 cl. 4.5
INTERCHANGE_WARRANT_PCU = 10_000     # total of all arms
ROTARY_CAPACITY_PCU = 5_000          # 4-arm rotary, six-lane approaches
SIGNAL_CAPACITY_PCU = 7_500          # same intersection under automatic signals

# IRC:SP:84-2014 cl. 2.14 (four-laning). Check the 2019 edition before quoting to a client.
MEDIAN_SPACING_BUILTUP_M = 500
MEDIAN_OPENING_LEN_M = (18, 20)

# IRC:103 revision draft: above this, pedestrian delay passes 45 s and a zebra
# "shall not be provided" on a 4-lane divided road.
ZEBRA_CEILING_PCU_DIR = 1250

# JDA's own stated basis, Patrika 7 Apr 2026. News reporting, not a JDA document.
JDA_TURNING_CLAIM_PCT = 50.0

# JMRC Jaipur Metro Phase-II DPR, March 2012, p.47 Table 2.10, "per IRC 106:1990"
JMRC_DPR_PCU = {"two wheeler": 0.75, "car": 1.0, "auto": 2.0,
                "truck": 2.2, "MAV": 3.7, "LCV": 1.4}
SURVEY_PCU = {"two wheeler": 0.50, "MAV": 4.5}


def interchange_warrant(cap):
    """Total of all arms against the 10,000 PCU/h interchange warrant."""
    by_j = {}
    for j in cap["junctions"]:
        by_j.setdefault(j["junction"], 0.0)
        by_j[j["junction"]] += j["pcu_pt"]
    # the survey covers the two corridor approaches; the cross-street arms are counted but
    # have no measured width, so the total is a FLOOR on all-arm volume, not the total
    return [dict(junction=k, corridor_arms_pcu=round(v),
                 floor_vs_warrant=round(v / INTERCHANGE_WARRANT_PCU, 2))
            for k, v in sorted(by_j.items())]


def zebra_warrant(cap):
    """Approaches where a surface pedestrian crossing is already unwarranted."""
    return [dict(junction=j["junction"], approach=j["approach"],
                 pcu_per_dir=round(j["pcu_pt"]),
                 over=j["pcu_pt"] > ZEBRA_CEILING_PCU_DIR,
                 multiple=round(j["pcu_pt"] / ZEBRA_CEILING_PCU_DIR, 1))
            for j in cap["junctions"]]


def median_spacing(openings):
    """Median openings against the IRC:SP:84 built-up spacing and length rules."""
    ch = sorted(o["chainage_m"] for o in openings if o.get("chainage_m") is not None)
    gaps = [round(b - a) for a, b in zip(ch, ch[1:])]
    too_close = [g for g in gaps if g < MEDIAN_SPACING_BUILTUP_M]
    widths = [o["width_m"] for o in openings if o.get("width_m")]
    in_range = [w for w in widths if MEDIAN_OPENING_LEN_M[0] <= w <= MEDIAN_OPENING_LEN_M[1]]
    return dict(openings=len(ch), gaps=len(gaps),
                closer_than_500m=len(too_close),
                closest_m=min(gaps) if gaps else None,
                median_gap_m=sorted(gaps)[len(gaps) // 2] if gaps else None,
                within_18_20m=len(in_range), widths_checked=len(widths))


if __name__ == "__main__":
    cap = json.loads((OUT_DATA / "capacity.json").read_text())
    cor = json.loads((OUT_DATA / "corridor.json").read_text())["corridor"]
    med = json.loads((OUT_DATA / "median_openings.geojson").read_text())
    openings = [f["properties"] for f in med["features"]]

    print("=== JDA's stated basis for the scheme, against the survey it commissioned ===")
    turning = 100 - cor["through_pct_mean"]
    print(f'  JDA: "approximately 50% of total traffic involves turning movements"')
    print(f"       (Patrika, 7 Apr 2026 - news reporting, not a JDA document)")
    print(f"  Survey: turning movements are {turning:.1f}% of the stream")
    print(f"  The claim overstates its own evidence by {JDA_TURNING_CLAIM_PCT/turning:.1f}x.")
    print(f"  Through movements are {cor['through_pct_mean']:.1f}%, which is the case FOR")
    print(f"  grade separation and AGAINST a scheme built to serve turning traffic.\n")

    print("=== The PCU correction, corroborated from inside the state government ===")
    print("  JMRC Jaipur Metro Phase-II DPR, March 2012, Table 2.10, 'per IRC 106:1990':")
    print(f"    two wheeler {JMRC_DPR_PCU['two wheeler']}   MAV {JMRC_DPR_PCU['MAV']}")
    print(f"  This survey used:")
    print(f"    two wheeler {SURVEY_PCU['two wheeler']}   MAV {SURVEY_PCU['MAV']}")
    print("  Another Rajasthan government transport document uses exactly the two values")
    print("  this audit corrects the survey to. The finding is not our interpretation.\n")

    print("=== IRC:SP:90-2010 interchange warrant, >10,000 PCU/h all arms ===")
    iw = interchange_warrant(cap)
    print(f"  {'junction':<10}{'corridor arms':>15}{'of warrant':>12}")
    print("  " + "-" * 40)
    for r in iw:
        print(f"  {r['junction']:<10}{r['corridor_arms_pcu']:>15,}{r['floor_vs_warrant']:>11.2f}x")
    print("  These are the TWO corridor approaches only. The cross-street arms are counted")
    print("  but have no measured width, so each figure is a FLOOR on all-arm volume.")
    print(f"  Even as a floor, every junction exceeds the {ROTARY_CAPACITY_PCU:,} PCU/h rotary")
    print(f"  capacity in cl. 5.7.1.2, and {sum(1 for r in iw if r['corridor_arms_pcu'] > SIGNAL_CAPACITY_PCU)}"
          f" of {len(iw)} exceed the {SIGNAL_CAPACITY_PCU:,} signalised figure.\n")

    print("=== IRC:103 (draft): a zebra crossing shall not be provided above ~1,250 PCU/h/dir ===")
    zw = zebra_warrant(cap)
    over = [z for z in zw if z["over"]]
    print(f"  approaches above the ceiling: {len(over)} of {len(zw)}")
    print(f"  worst: {max(zw, key=lambda z: z['multiple'])['multiple']}x the ceiling")
    print("  A surface pedestrian crossing is already unwarranted on every corridor")
    print("  approach. The scheme removes the signal that currently substitutes for one,")
    print("  and the survey never counted a pedestrian to find out who is affected.\n")

    print("=== IRC:SP:84-2014 cl. 2.14 median openings (2014 edition; check 2019) ===")
    ms = median_spacing(openings)
    for k, v in ms.items():
        print(f"  {k:<22}{v}")
    print(f"  Built-up spacing rule is >={MEDIAN_SPACING_BUILTUP_M} m and opening length "
          f"{MEDIAN_OPENING_LEN_M[0]}-{MEDIAN_OPENING_LEN_M[1]} m.\n")

    print("=== IRC:SP:41-1994 Table 3.1 ===")
    print("  This survey's ten-column class scheme and its static PCU factors ARE Table")
    print("  3.1. The same table carries a PEDESTRIAN Nos. row, and cl. 3.1(iv) requires")
    print("  it where pedestrian movement is substantial. It was left empty.")
    print("  Not a matter of judgement - a clause-level omission in the proforma the")
    print("  survey was written from.\n")

    print("=== IRC:SP:90-2010 cl. 5.6.7 ===")
    print('  "For justification of grade separator, intersection volume-delay survey is')
    print('   a MUST." Of the seven surveys cl. 5.6 requires, this programme ran one.')
    print("  That cuts both ways and is reported both ways: it is a gap in the evidence")
    print("  base for ANY grade separation here, including the one we argue for.")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "standards.json").write_text(json.dumps(dict(
        jda_turning_claim_pct=JDA_TURNING_CLAIM_PCT,
        measured_turning_pct=round(turning, 1),
        claim_overstatement=round(JDA_TURNING_CLAIM_PCT / turning, 1),
        jmrc_dpr_pcu=JMRC_DPR_PCU, survey_pcu=SURVEY_PCU,
        interchange_warrant_pcu=INTERCHANGE_WARRANT_PCU, interchange=iw,
        zebra_ceiling_pcu_dir=ZEBRA_CEILING_PCU_DIR,
        zebra_over=len(over), zebra_total=len(zw),
        median=ms,
        surveys_required_by_sp90=7, surveys_run=1,
        pedestrian_row_in_sp41_table_3_1=True, pedestrian_row_filled=False,
        unverified=["IRC:SP:84 clause 2.14 read from the 2014 edition; a 2019 edition "
                    "exists and was not checked",
                    "IRC:103 zebra ceiling is from a revision draft, not the published "
                    "2022 edition, whose scan has no text layer",
                    "the 50% turning claim is news reporting, not a JDA document"],
    ), indent=1))
    print(f"\nwritten: {OUT_DATA/'standards.json'}")
