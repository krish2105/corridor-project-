"""
Tests for masterdb.py — the six-junction master database.

The workbook is what a JDA engineer opens first, so the two things that must not be
wrong are the ones a reader cannot check by eye: whether the two survey days have been
silently added together, and whether the criticality ranking is a real ordering or an
artefact of the normalisation. Both are asserted here against inputs whose answers are
known by construction.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.masterdb import (_by_day, composition, cover, criticality,
                          criticality_sheet, hourly, hourly_extremes, inventory,
                          movements, peak_pcu, INDICATORS, PROVISIONAL)

DAY2 = pd.Timestamp("2026-05-12").date()


@pytest.fixture
def two_days(synth_bins):
    """
    Day one, plus a day two that copies it for every class except CAR_BUCKET.

    Built this way because it is what the real survey looks like: most class series
    reproduce day one to the vehicle and a few move, so a flag taken on the row total
    reads "different" while nine tenths of the row is a copy. Here the answer is known —
    every movement row should report exactly one of its classes as having changed.
    """
    d2 = synth_bins.copy()
    d2["date"] = DAY2
    d2["bin_start"] = d2.bin_start + pd.Timedelta(days=1)
    d2.loc[d2.veh_class == "CAR_BUCKET", "count"] += 1.0
    return pd.concat([synth_bins, d2], ignore_index=True)


def test_days_are_not_summed(two_days, synth_bins):
    """The two days stay apart. Adding them would double a day that was largely copied."""
    t = _by_day(two_days, ["junction", "arm_from", "movement", "arm_to"])
    assert {"Day 1 vehicles", "Day 2 vehicles"} <= set(t.columns)
    assert not any("both days" in c for c in t.columns)
    day1_total = synth_bins[synth_bins.kind == "movement"]["count"].sum()
    assert t["Day 1 vehicles"].sum() == day1_total


def test_class_identity_counted_not_taken_on_the_row_total(two_days):
    """
    The duplication flag is per class, because on the row total it disappears.

    Only CAR_BUCKET was changed, so each movement row is a copy in every class but one.
    A boolean on the row total would read False everywhere and say the second day was
    independently observed, which is the claim this workbook exists to contradict.
    """
    t = movements(two_days)
    counts = t["Class series identical to day 1"]
    n_same, n = zip(*[(int(a), int(b)) for a, b in
                      (s.split(" of ") for s in counts)])
    assert all(b - a == 1 for a, b in zip(n_same, n)), counts.value_counts().to_dict()
    assert all(a > 0 for a in n_same)


def test_composition_flags_identity_directly(two_days):
    """At class granularity the flag is the plain boolean, and only CAR_BUCKET moves."""
    t = composition(two_days)
    moved = t[~t["Day 2 identical to day 1"]]
    assert set(moved["Class code"]) == {"CAR_BUCKET"}


def test_composition_shows_the_corrected_label_and_the_issued_one(two_days):
    """
    A workbook that reproduces "Motar Cycle" reads as careless; one that silently fixes
    it cannot be traced to a source cell. The sheet has to carry both.
    """
    from src.spelling import fix as spell
    from src.tmc_parse import CLASS_LABELS
    t = composition(two_days)
    assert {"Survey column", "Survey column as issued", "Class code"} <= set(t.columns)
    row = t[t["Class code"] == "TWO_W"].iloc[0]
    assert row["Survey column as issued"] == CLASS_LABELS["TWO_W"] == "Motar Cycle, Scooter"
    assert row["Survey column"] == spell(CLASS_LABELS["TWO_W"]) == "Motor Cycle, Scooter"


def test_movement_arm_names_are_corrected(two_days):
    t = movements(two_days)
    arms = set(t["From arm"]) | set(t["To arm"])
    assert "Mansarovar Metro" in arms
    assert not any("Mansarover" in a for a in arms)


def test_shares_are_day_one_only_and_sum_to_100(two_days):
    """Shares are taken on the analysis day, not on a doubled total."""
    for f in (composition, movements):
        t = f(two_days)
        col = [c for c in t.columns if c.startswith("Share")][0]
        for _, g in t.groupby("Junction"):
            assert abs(g[col].sum() - 100.0) < 0.1


def test_hourly_keeps_the_date(two_days):
    h = hourly(two_days)
    assert set(h.Date) == {"2026-05-11", "2026-05-12"}
    assert len(h) == h.Junction.nunique() * 2 * 24


def test_hourly_extremes_bracket_the_hours(two_days):
    h = hourly(two_days)
    x = hourly_extremes(h)
    merged = h.merge(x, on=["Junction", "Date"])
    assert (merged["Busiest hour vehicles"] >= merged.Vehicles).all()
    assert (merged["Quietest hour vehicles"] <= merged.Vehicles).all()
    assert (x["Peak to trough ratio"] >= 1).all()


# --- criticality -------------------------------------------------------------

def _payload(daily, peak, vc, uturn, expo, through):
    """A corridor payload carrying only the fields criticality() reads."""
    codes = [f"TMC-0{i}" for i in range(1, 7)]
    return dict(
        junctions=[dict(code=c, daily_veh=daily[i], peak_veh=peak[i],
                        through_pct=through[i]) for i, c in enumerate(codes)],
        capacity=dict(junctions=[dict(junction=c, vc_pt=vc[i])
                                 for i, c in enumerate(codes)]),
        scheme=dict(uturns=[dict(junction=c, uturn_demand=uturn[i])
                            for i, c in enumerate(codes)]),
        safety=dict(junctions=[dict(junction=c, change_pct=expo[i])
                               for i, c in enumerate(codes)]))


def test_criticality_is_bounded_and_ordered():
    """Six indicators each normalised to [0,1], so the score cannot leave [0,6]."""
    rising = list(range(1, 7))
    d = _payload([x * 1000 for x in rising], [x * 100 for x in rising],
                 [x * 0.2 for x in rising], [x * 50 for x in rising],
                 [x * 2 for x in rising], [100 - x for x in rising])
    t = criticality(d)
    assert t.score.between(0, 6).all()
    assert t["rank"].tolist() == [1, 2, 3, 4, 5, 6]
    # every indicator rises with the index, so the last junction must rank first
    assert t.iloc[0].junction == "TMC-06"


def test_criticality_does_not_invent_an_order_from_identical_inputs():
    """
    A flat corridor must score flat.

    The normalisation divides by (max - min). On identical inputs that is zero, and the
    natural way to write it produces either a division by zero or - worse - a spurious
    ranking that reads as a finding.
    """
    flat = [5] * 6
    d = _payload(flat, flat, flat, flat, flat, flat)
    t = criticality(d)
    assert (t.score == 0).all()
    assert (t["rank"] == 1).all()


def test_criticality_publishes_its_components():
    """
    No weighting is applied, so the components must be visible.

    An unweighted sum is only defensible if a reader can apply their own weights, which
    means every normalised indicator has to be in the sheet, not just the total.
    """
    d = _payload(list(range(1, 7)), list(range(1, 7)), list(range(1, 7)),
                 list(range(1, 7)), list(range(1, 7)), list(range(1, 7)))
    t = criticality(d)
    norm = [f"n_{k}" for k in INDICATORS]
    assert len(norm) == 6 and set(norm) <= set(t.columns)
    for c in norm:
        assert t[c].between(0, 1).all()
    assert (t[norm].sum(axis=1).round(3) - t.score).abs().max() < 1e-9


# --- the measurement caveat --------------------------------------------------

def test_cover_states_the_measurement_status():
    """
    Every width in this workbook is CAD-derived, and the DWG carries no dimensions.

    The user's own decision was that a total station survey is required, so the cover
    sheet has to say so. A workbook whose widths look measured, when they are scaled off
    linework, is the kind of thing that ends up in a design.
    """
    d = _payload(*[[1] * 6] * 6)
    d["meta"] = dict(survey_dates=["2026-05-11", "2026-05-12"])
    d["audit"] = dict(day2=dict(identical=396, series=555),
                      arithmetic=dict(discrepancies=225))
    t = cover(d)
    text = " ".join(t.Detail.astype(str))
    assert "total station" in text.lower()
    assert PROVISIONAL in text
    for gap in ("U-turn", "rickshaw", "Pedestrian"):
        assert any(gap.lower() in s.lower() for s in t.Item.astype(str) + t.Detail.astype(str))


def test_the_workbook_sheet_is_the_same_table_under_readable_labels():
    """
    export.py publishes criticality() and the workbook publishes criticality_sheet().
    They must be one table, or the dashboard and the spreadsheet rank the corridor
    differently and a reviewer holding both has no way to tell which is right.
    """
    d = _payload(list(range(1, 7)), list(range(6, 0, -1)), [1, 3, 2, 6, 4, 5],
                 [9, 1, 4, 2, 8, 3], [2, 2, 9, 1, 5, 5], [50] * 6)
    machine, sheet = criticality(d), criticality_sheet(d)
    assert sheet["Criticality score"].tolist() == machine.score.tolist()
    assert sheet["Rank"].tolist() == machine["rank"].tolist()
    for key, label in INDICATORS.items():
        assert sheet[label].tolist() == machine[key].tolist()
        assert sheet[f"{label} (normalised)"].tolist() == machine[f"n_{key}"].tolist()
