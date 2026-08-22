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
