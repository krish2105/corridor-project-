"""
Tests for the survey pipeline. The domain rules that are easy to get silently
wrong get the most attention: clockwise turn mapping under left-hand traffic,
the 08:00 day boundary, and share-dependent PCU interpolation.
"""
from datetime import date, datetime

import pytest

from src.config import JUNCTIONS, MOVEMENTS
from src.pcu import EXACT, IRC106, factor_band, irc_factor
from src.tmc_parse import bin_datetime, movement_for

ARMS = JUNCTIONS["TMC-01"]      # Mansarover Metro, Patrika Gate, Sanganer Stadium, Sumer Nagar

# The mapping stated by the workbooks' own Flow Table sheet. Ground truth.
FLOW_TABLE = {
    1:  ("Mansarover Metro", "Patrika Gate"),
    2:  ("Mansarover Metro", "Sanganer Stadium"),
    3:  ("Mansarover Metro", "Sumer Nagar"),
    4:  ("Patrika Gate", "Sanganer Stadium"),
    5:  ("Patrika Gate", "Sumer Nagar"),
    6:  ("Patrika Gate", "Mansarover Metro"),
    7:  ("Sanganer Stadium", "Sumer Nagar"),
    8:  ("Sanganer Stadium", "Mansarover Metro"),
    9:  ("Sanganer Stadium", "Patrika Gate"),
    10: ("Sumer Nagar", "Mansarover Metro"),
    11: ("Sumer Nagar", "Patrika Gate"),
    12: ("Sumer Nagar", "Sanganer Stadium"),
}


@pytest.mark.parametrize("idx,expected", FLOW_TABLE.items())
def test_movement_matches_workbook_flow_table(idx, expected):
    frm, to, _ = movement_for(idx, ARMS)
    assert (frm, to) == expected


def test_left_turn_is_next_arm_clockwise():
    """India drives on the left, so LEFT is the near-side turn onto the next arm clockwise."""
    for entry in range(4):
        v = entry * 3 + 1
        frm, to, mv = movement_for(v, ARMS)
        assert mv == "Left"
        assert frm == ARMS[entry]
        assert to == ARMS[(entry + 1) % 4]


def test_straight_is_the_opposite_arm():
    for entry in range(4):
        frm, to, mv = movement_for(entry * 3 + 2, ARMS)
        assert mv == "Straight"
        assert to == ARMS[(entry + 2) % 4]


def test_right_turn_crosses_opposing_traffic():
    """The RIGHT turn is the far-side, capacity-limiting movement in India."""
    for entry in range(4):
        frm, to, mv = movement_for(entry * 3 + 3, ARMS)
        assert mv == "Right"
        assert to == ARMS[(entry + 3) % 4]


def test_every_movement_enumerated_once_and_no_uturns():
    seen = {movement_for(i, ARMS)[:2] for i in range(1, 13)}
    assert len(seen) == 12
    assert all(f != t for f, t in seen), "a U-turn was enumerated; the survey has none"
    assert len(MOVEMENTS) == 3


# --- the 08:00 survey-day boundary -----------------------------------------
def test_bin_datetime_same_day_after_0800():
    assert bin_datetime("0800-0815", date(2026, 5, 11)) == datetime(2026, 5, 11, 8, 0)
    assert bin_datetime("2345-2400", date(2026, 5, 11)) == datetime(2026, 5, 11, 23, 45)


def test_bin_datetime_rolls_to_next_day_before_0800():
    """The survey day runs 08:00 to 08:00, so 00:15 belongs to the following date."""
    assert bin_datetime("0015-0030", date(2026, 5, 11)) == datetime(2026, 5, 12, 0, 15)
    assert bin_datetime("0745-0800", date(2026, 5, 11)) == datetime(2026, 5, 12, 7, 45)


def test_bins_span_exactly_24_hours():
    d = date(2026, 5, 11)
    first = bin_datetime("0800-0815", d)
    last = bin_datetime("0745-0800", d)
    assert (last - first).total_seconds() == 23.75 * 3600


# --- IRC:106 share-dependent PCU -------------------------------------------
def test_pcu_uses_low_value_below_5_percent():
    assert irc_factor("2W", 0.02) == 0.50
    assert irc_factor("2W", 0.05) == 0.50


def test_pcu_uses_high_value_at_or_above_10_percent():
    assert irc_factor("2W", 0.10) == 0.75
    assert irc_factor("2W", 0.47) == 0.75


def test_pcu_interpolates_linearly_between_5_and_10_percent():
    assert irc_factor("2W", 0.075) == pytest.approx(0.625)
    assert irc_factor("BUS", 0.075) == pytest.approx(2.95)


def test_two_wheeler_at_observed_corridor_share_is_not_the_surveyed_value():
    """The audit's central claim: 2W sits far above 10% share, so 0.75 applies, not 0.50."""
    assert irc_factor("2W", 0.49) == 0.75
    assert irc_factor("2W", 0.49) != 0.50


def test_composite_columns_refuse_to_give_a_point_estimate():
    lo, pt, hi = factor_band("CAR_BUCKET", 0.54)
    assert pt is None, "a composite column must not produce a point estimate"
    assert lo < hi


def test_exact_columns_give_a_point_estimate():
    for code in EXACT:
        lo, pt, hi = factor_band(code, 0.20)
        assert pt is not None and lo == pt == hi


def test_irc_table_is_monotonic():
    for cls, (lo, hi) in IRC106.items():
        assert lo <= hi, f"{cls}: the >=10% factor must not be lower than the <=5% factor"


# --- critical gap measurement ---------------------------------------------
def test_critical_gap_recovers_planted_value():
    """
    The estimator is only trustworthy on real footage if it can recover a value we
    planted in synthetic data. This is the gate the field measurement depends on.
    """
    from src.critical_gap import derive_gaps, measure, synthesise
    events, true_tc = synthesise(n_drivers=200, true_tc_mean=4.2,
                                 conflict_flow_vph=1800, seed=42)
    res = measure(derive_gaps(events), "test")
    assert res["reportable"], res.get("reason")
    assert abs(res["mle_mean"] - true_tc) < 0.5


def test_critical_gap_refuses_small_samples():
    """A handful of drivers gives a confident-looking wrong answer. It must refuse."""
    from src.critical_gap import derive_gaps, measure, synthesise
    events, _ = synthesise(n_drivers=8, seed=5)
    res = measure(derive_gaps(events), "tiny")
    assert res["reportable"] is False


def test_head_of_queue_drivers_never_reject_a_longer_gap():
    """
    For a driver at the head of the queue, a rejected gap must be shorter than the one
    accepted - otherwise they would have taken it. Queued followers are exempt: gaps
    consumed by the queue ahead were never theirs to take, which is exactly why the
    estimator uses head-of-queue drivers only.
    """
    from src.critical_gap import derive_gaps, synthesise
    events, _ = synthesise(n_drivers=150, seed=9)
    heads = [d for d in derive_gaps(events) if d["head_of_queue"]]
    assert heads, "no head-of-queue drivers resolved"
    for d in heads:
        if d["rejected"]:
            assert max(d["rejected"]) <= d["accepted"] + 1e-6


def test_follow_up_is_plausible():
    from src.critical_gap import follow_up, synthesise
    events, _ = synthesise(n_drivers=200, seed=13)
    fu = follow_up(events)
    assert fu is None or 0.5 < fu < 8.0


# --- Phase 6 pipeline ------------------------------------------------------
def test_homography_recovers_planted_transform():
    """The fit must recover a homography we planted, inside the 0.5 m acceptance gate."""
    from src.homography import RMSE_GATE_M, _plant_and_recover, fit
    px, world, origin, _ = _plant_and_recover(seed=21, noise_px=1.0, n=8)
    _H, _o, st = fit(px, world, origin=origin)
    assert st["rmse_m"] < RMSE_GATE_M
    assert st["passes_gate"]


def test_homography_rejects_too_few_gcps():
    import pytest as _pt
    from src.homography import fit
    with _pt.raises(ValueError):
        fit([[0, 0], [1, 0], [0, 1]], [[0, 0], [1, 0], [0, 1]])


def test_footpoint_is_bottom_centre():
    """A box centroid sits at half vehicle height and displaces a bus metres further."""
    from src.homography import footpoint
    assert footpoint((10, 20, 30, 60)) == (20.0, 60)


def test_divided_leg_entry_and_exit_zones_differ():
    """
    The methodology's build_zones returns the same polygon for both, which makes the
    exit zone unreachable and drives track resolution to zero.
    """
    from src.count import build_zones
    legs = {"N": dict(bearing=0, divided=True, width=14.0)}
    z = build_zones((0.0, 0.0), legs)
    assert not z[("entry", "N")].equals(z[("exit", "N")])


def test_undivided_leg_shares_one_zone():
    from src.count import build_zones
    legs = {"N": dict(bearing=0, divided=False, width=10.0)}
    z = build_zones((0.0, 0.0), legs)
    assert z[("entry", "N")].equals(z[("exit", "N")])


def test_track_assignment_recovers_known_movements():
    from src.count import RESOLUTION_GATE, assign_movement, build_zones, synthesise_tracks
    legs = {n: dict(bearing=b, divided=True, width=14.0)
            for n, b in (("N", 0), ("E", 90), ("S", 180), ("W", 270))}
    centre = (0.0, 0.0)
    zones = build_zones(centre, legs)
    tracks, truth = synthesise_tracks(legs, centre, per_movement=6, seed=3)
    res = [(assign_movement(t["pts"], zones, centre), truth[i]) for i, t in tracks.items()]
    got = [r for r in res if r[0] is not None]
    assert len(got) / len(res) >= RESOLUTION_GATE
    assert sum(1 for a, b in got if a == b) / len(got) >= 0.95


def test_aggregate_survives_empty_track_set():
    """The original raised ZeroDivisionError exactly when the diagnostic mattered most."""
    from src.count import aggregate, build_zones
    legs = {"N": dict(bearing=0, divided=True, width=14.0)}
    _c, st = aggregate({}, build_zones((0, 0), legs), (0, 0))
    assert st["tracks"] == 0 and st["resolution"] == 0.0


def test_validation_catches_planted_bias():
    from src.validate import _synth, validate
    assert validate(_synth(bias=0.00, noise=0.03, seed=3))["total"]["verdict"] == "PASS"
    assert validate(_synth(bias=0.20, noise=0.04, seed=4))["total"]["verdict"] == "FAIL"


def test_validation_mape_ignores_zero_manual_intervals():
    """Percentage error is undefined at zero; including it destroys rare-class stats."""
    from src.validate import mape
    val, n = mape([0, 0, 10], [5, 3, 11])
    assert n == 1 and abs(val - 0.1) < 1e-9


# --- detection stage -------------------------------------------------------
def test_slices_cover_the_whole_frame():
    """A gap in tile coverage is a blind spot that silently loses vehicles."""
    from src.detect import coverage, slices
    for w, h in ((1920, 1080), (3840, 2160), (1280, 720), (640, 640)):
        assert coverage(w, h, slices(w, h)) == 1.0


def test_slice_overlap_exceeds_a_two_wheeler():
    """Overlap must exceed the largest object or a vehicle on a seam is counted twice."""
    from src.detect import OVERLAP, SLICE
    assert SLICE * OVERLAP >= 100      # px, comfortably more than a 2W at 8-12 m


def test_merge_removes_cross_tile_duplicates():
    from src.detect import merge
    a = dict(bbox=(100, 100, 160, 140), conf=0.9, cls="CAR_BUCKET")
    dup = dict(bbox=(104, 102, 164, 142), conf=0.8, cls="CAR_BUCKET")
    far = dict(bbox=(600, 600, 660, 640), conf=0.7, cls="CAR_BUCKET")
    assert len(merge([a, dup, far])) == 2


def test_merge_keeps_different_classes_at_the_same_place():
    """A 2W beside a car must not be collapsed into one detection."""
    from src.detect import merge
    a = dict(bbox=(100, 100, 160, 140), conf=0.9, cls="CAR_BUCKET")
    b = dict(bbox=(102, 101, 162, 141), conf=0.8, cls="TWO_W")
    assert len(merge([a, b])) == 2


def test_auto_rickshaw_is_not_silently_mapped_to_car():
    """
    COCO has no auto-rickshaw. Folding it into `car` would reproduce exactly the
    composite-class failure the audit criticises in the survey.
    """
    from src.detect import COCO_TO_IRC, UNMAPPABLE
    assert "AUTO" not in COCO_TO_IRC.values()
    assert "E_RIK" not in COCO_TO_IRC.values()
    assert "AUTO" in UNMAPPABLE and "E_RIK" in UNMAPPABLE


def test_unmapped_coco_labels_are_flagged_not_guessed():
    from src.detect import COCO_TO_IRC
    assert COCO_TO_IRC.get("train", "UNMAPPED") == "UNMAPPED"


# --- the parse gate must be able to report a number other than zero ----------
def test_the_silently_absorbed_gate_is_not_a_hardcoded_zero():
    """
    The gate printed a literal 0, so it could not fail — while the code above it was
    quietly dropping stored totals that could not be read at all, which is precisely a
    silently-absorbed discrepancy. Two such cells exist in the real workbooks.
    """
    import re
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / "src" / "tmc_parse.py").read_text()
    assert not re.search(r'silently absorbed discrepancies:\s*0\s', src), (
        "the gate still prints a literal 0")
    assert "unreadable" in src, "unreadable stored totals are not registered"


def test_an_unreadable_stored_total_is_registered_not_skipped():
    """
    `stored is None` used to fall through with no register row, making an unreadable cell
    indistinguishable from one that agreed.
    """
    import inspect
    from src import tmc_parse
    src = inspect.getsource(tmc_parse.parse_workbook)
    assert "if stored is None:" in src, "the None branch is gone"
    none_branch = src.split("if stored is None:")[1][:400]
    assert "mismatches.append" in none_branch, (
        "an unreadable stored total still does not reach the register")
