"""
Tests for the modules that produce the headline findings.

These were the least-tested modules in the project and they carry the most weight:
capacity.py gives every v/c ratio, scheme_test.py gives the U-turn verdict,
sensitivity.py gives the robustness claim behind both. A silent error in any of them
changes a published conclusion without breaking anything.

The specific defects pinned here are ones that were actually made and corrected during
the work, because a bug that happened once is the best evidence of what this code gets
wrong: halving an already-halved carriageway width, quoting a gap-acceptance capacity
after the model has degenerated, and comparing a per-lane capacity against a total.
"""
import math

import pytest

from src.capacity import ASSUMPTIONS, LOS_BANDS, failure_year, lanes_from_width, los
from src.medians import classify, openings
from src.scheme_test import (CRITICAL_GAP_S, FOLLOW_UP_S, NO_GAP_VC, gap_capacity,
                             weighted_gap)


# --- level of service --------------------------------------------------------
@pytest.mark.parametrize("vc,grade", [
    (0.10, "A"), (0.30, "A"), (0.31, "B"), (0.45, "B"),
    (0.46, "C"), (0.70, "C"), (0.71, "D"), (0.85, "D"),
    (0.86, "E"), (1.00, "E"), (1.01, "F"), (2.41, "F"),
])
def test_los_bands(vc, grade):
    """
    Draft IRC:106 (2022) Table 9, multilane divided urban road.

    These were 0.40/0.60/0.75/0.90 and labelled "Indo-HCM / IRC" until a search of
    IRC:106-1990, draft IRC:106 (2022), IRC:92, IRC:SP:41, IRC:SP:90 and Indo-HCM
    chapters 2, 3, 5 and 6 found no Indian standard publishing that set. The old bands
    reported v/c 0.86-0.90 as D when it is E.
    """
    assert los(vc) == grade


def test_the_los_bands_name_their_source():
    from src.capacity import LOS_SOURCE
    assert "IRC:106" in LOS_SOURCE and "draft" in LOS_SOURCE.lower()


def test_a_v_c_letter_is_labelled_a_midblock_measure():
    """Indo-HCM grades junctions on control delay, which this survey cannot support."""
    from src.capacity import LOS_CAVEAT
    assert "midblock" in LOS_CAVEAT and "control delay" in LOS_CAVEAT


def test_los_bands_are_monotonic():
    limits = [l for l, _ in LOS_BANDS]
    assert limits == sorted(limits)


# --- lane count --------------------------------------------------------------
def test_lanes_from_width_does_not_halve_an_already_halved_width():
    """
    Regression. measure_widths returns ONE carriageway. Halving again reports a
    four-lane arterial as one lane per direction and quadruples every v/c downstream.
    """
    assert lanes_from_width(7.2) == 2
    assert lanes_from_width(10.5) == 3
    assert lanes_from_width(14.0) == 4


def test_lanes_from_width_applies_shy_distance():
    w = 7.2
    expected = max(1, round((w - ASSUMPTIONS["shy_distance_m"]) / ASSUMPTIONS["lane_width_m"]))
    assert lanes_from_width(w) == expected


def test_a_carriageway_never_reports_zero_lanes():
    assert lanes_from_width(2.0) == 1


def test_missing_width_returns_none_not_a_guess():
    assert lanes_from_width(0) is None
    assert lanes_from_width(None) is None


# --- design life -------------------------------------------------------------
def test_already_over_capacity_fails_in_the_base_year():
    assert failure_year(1.38, 6.0) == ASSUMPTIONS["base_year"]


def test_failure_year_moves_earlier_as_growth_rises():
    assert failure_year(0.5, 8.0) < failure_year(0.5, 4.0)


def test_failure_year_matches_the_compound_growth_closed_form():
    vc, g = 0.59, 6.0
    n = math.log(1 / vc) / math.log(1 + g / 100)
    assert failure_year(vc, g) == ASSUMPTIONS["base_year"] + math.ceil(n)


def test_lower_opening_vc_buys_more_years():
    assert failure_year(0.35, 6.0) > failure_year(0.71, 6.0)


# --- gap acceptance ----------------------------------------------------------
def test_no_conflicting_flow_means_unlimited_capacity():
    assert gap_capacity(0, 4.2, 2.6) == float("inf")


def test_capacity_falls_as_conflicting_flow_rises():
    a = gap_capacity(600, 4.2, 2.6)
    b = gap_capacity(2400, 4.2, 2.6)
    assert b < a


def test_a_longer_critical_gap_lowers_capacity():
    assert gap_capacity(1800, 6.0, 2.6) < gap_capacity(1800, 3.5, 2.6)


def test_a_longer_follow_up_lowers_capacity():
    assert gap_capacity(1800, 4.2, 3.0) < gap_capacity(1800, 4.2, 2.2)


def test_the_no_viable_gap_threshold_exists_and_is_above_one():
    """
    Past this the model degenerates and a v/c number would be meaningless. An earlier
    version reported 147.87 as though it were a measurement.
    """
    assert NO_GAP_VC > 1.0


# --- composition-weighted critical gap ---------------------------------------
def test_every_class_has_an_optimistic_and_conservative_gap():
    for cls, band in CRITICAL_GAP_S.items():
        assert len(band) == 2 and band[0] < band[1], cls


def test_follow_up_is_a_band_too():
    assert FOLLOW_UP_S[0] < FOLLOW_UP_S[1]


def test_a_two_wheeler_stream_accepts_shorter_gaps_than_a_truck_stream():
    tw = weighted_gap({"TWO_W": 1.0}, 0)
    trk = weighted_gap({"AUTO_TRK_BUS": 1.0}, 0)
    assert tw < trk


def test_conservative_gap_always_exceeds_optimistic():
    share = {"TWO_W": 0.47, "CAR_BUCKET": 0.50, "AUTO_TRK_BUS": 0.03}
    assert weighted_gap(share, 1) > weighted_gap(share, 0)


def test_empty_composition_falls_back_rather_than_dividing_by_zero():
    assert weighted_gap({}, 0) == CRITICAL_GAP_S["CAR_BUCKET"][0]


def test_weighted_gap_normalises_unnormalised_shares():
    a = weighted_gap({"TWO_W": 1.0, "CAR_BUCKET": 1.0}, 0)
    b = weighted_gap({"TWO_W": 50.0, "CAR_BUCKET": 50.0}, 0)
    assert a == pytest.approx(b)


# --- median openings ---------------------------------------------------------
def test_openings_measures_gaps_between_adjacent_runs():
    """
    The erratum: taking a max over all pairwise distances returns the span of the whole
    median, not an opening. Runs at 0-10, 25-40, 60-70 have 15 m and 20 m openings.
    """
    got = openings([(0, 10), (25, 40), (60, 70)])
    assert [round(w) for _s, w in got] == [15, 20]


def test_a_single_median_run_has_no_openings():
    assert openings([(0, 100)]) == []


def test_classify_orders_the_bands_by_width():
    grades = [classify(w) for w in (1.0, 6.0, 12.0, 40.0)]
    assert grades[0] == "too narrow"
    assert len(set(grades)) == 4          # each width lands in a different band


def test_a_junction_mouth_is_not_reported_as_a_u_turn_opening():
    """A 40 m gap is where a side road meets the corridor, not a U-turn bay."""
    assert classify(40.0) == "wide / junction mouth"
