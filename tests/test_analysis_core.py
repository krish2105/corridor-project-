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


# --- capacity basis ----------------------------------------------------------
def test_capacity_comes_from_a_tabulated_code_value():
    """
    Regression. Capacity was 1200 PCU/lane/hr labelled "IRC:106 urban arterial capacity".
    IRC:106-1990 does not publish that figure; IRC:92-2017 Table 6.3 and Indo-HCM Table
    5.4 both give 2700 PCU/h per direction at 7.5 m. Worse than being unsourced, 1200 was
    LOWER than the code value, so it raised every v/c we publish — an error that
    flattered our own conclusion.
    """
    assert ASSUMPTIONS["base_capacity_pcu_per_dir"] == 2700
    assert ASSUMPTIONS["base_width_per_dir_m"] == 7.5
    assert "IRC:92-2017" in ASSUMPTIONS["capacity_source"]


def test_capacity_is_not_scaled_by_width_twice():
    """
    Deriving lanes from width and then also scaling a per-lane capacity by width counts
    the same adjustment twice. Capacity scales the per-DIRECTION figure only.
    """
    assert "capacity_pcu_per_lane_hr" not in ASSUMPTIONS


def test_a_narrower_carriageway_gets_less_capacity():
    base, bw = ASSUMPTIONS["base_capacity_pcu_per_dir"], ASSUMPTIONS["base_width_per_dir_m"]
    assert round(base * (7.0 / bw)) < round(base * (7.2 / bw)) < base


# --- critical gap, benchmarked ------------------------------------------------
def test_capacity_falls_as_the_critical_gap_rises():
    """The monotonicity the breakpoint bisection depends on."""
    from src.scheme_test import gap_capacity
    assert gap_capacity(2500, 5.5, 2.2) < gap_capacity(2500, 3.5, 2.2)


def test_the_breakpoint_gap_is_the_gap_that_exactly_serves_demand():
    from src.scheme_test import breakpoint_gap, gap_capacity
    demand, conflicting, tf = 400.0, 2800.0, 2.2
    t = breakpoint_gap(demand, conflicting, tf)
    assert gap_capacity(conflicting, t, tf) == pytest.approx(demand, rel=0.01)


def test_the_composition_weighted_gap_sits_below_the_irc_car_value():
    """
    The per-CLASS gaps are not all below the IRC passenger-car figure, and should not be:
    a truck needs a longer gap than a car. The property that matters is the
    composition-WEIGHTED gap, which sits below it because two-wheelers are half this
    stream and accept shorter gaps.

    That is arithmetic, not conservatism. An earlier version of this test read the gap
    between the two as proof the U-turn finding "cannot be attacked as too pessimistic",
    which compared a mixed-traffic weighted mean against a single-class car value and
    called the composition difference caution. Withdrawn — what the weighted gap must do
    is stay consistent with its own inputs, which is what is asserted here. Where our gap
    actually sits against matched evidence is the job of the twelve-basis spread.
    """
    from src.scheme_test import CRITICAL_GAP_S, IRC_SP41_APPLIED, weighted_gap
    share = {"TWO_W": 0.49, "CAR_BUCKET": 0.48, "AUTO_TRK_BUS": 0.03}
    assert weighted_gap(share, 0) < IRC_SP41_APPLIED          # optimistic
    assert weighted_gap(share, 1) < IRC_SP41_APPLIED          # conservative
    # heavier classes must still need longer gaps than a car
    assert CRITICAL_GAP_S["TWO_W"][0] < CRITICAL_GAP_S["CAR_BUCKET"][0]
    assert CRITICAL_GAP_S["AUTO_TRK_BUS"][1] > CRITICAL_GAP_S["CAR_BUCKET"][1]


def test_no_module_still_claims_our_gaps_are_the_generous_end():
    """
    The "our gaps are the generous end for the scheme" framing was withdrawn: it ran in
    our own favour and did not survive the four-lane median-opening evidence. It had
    already leaked into scheme_test.py, reports.py and service_docs.py once. This asserts
    it does not come back — in code or in anything those modules publish.
    """
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    banned = re.compile(r"generous end|biased high|cannot be attacked as too pessimistic"
                        r"|makes the U-turn finding conservative", re.I)
    for rel in ("src/scheme_test.py", "src/reports.py", "src/service_docs.py"):
        text = (root / rel).read_text()
        # the withdrawal itself may quote the phrase; only flag it outside that context
        for m in banned.finditer(text):
            line_start = text.rfind("\n", 0, m.start()) + 1
            window = text[max(0, m.start() - 700):m.end() + 200]
            # the phrase is allowed where it is being withdrawn, negated, or quoted as
            # the thing that was wrong — not where it is being asserted
            ok = r"withdraw|retract|earlier version|no longer|wrong|neither|not conservative|moved twice"
            assert re.search(ok, window, re.I), (
                f"{rel}:{text[:m.start()].count(chr(10)) + 1} still asserts the retracted "
                f"framing: {text[line_start:m.end() + 60]!r}"
            )


def test_the_irc_benchmark_records_its_adjustment():
    from src.scheme_test import IRC_SP41_CAR_GAP_S, IRC_SP41_LARGE_CITY_ADJ, IRC_SP41_APPLIED
    assert IRC_SP41_APPLIED == IRC_SP41_CAR_GAP_S + IRC_SP41_LARGE_CITY_ADJ
    assert IRC_SP41_LARGE_CITY_ADJ < 0


def test_gap_capacity_matches_the_hcm_formula_worked_by_hand():
    """
    Pins the model, not just its behaviour. c = q_c*exp(-q_c*t_c/3600)/(1-exp(-q_c*t_f/3600)).
    The implementation previously spelled the 3600 scaling three different ways in one
    expression, which reads like a unit bug; this is what proves it was not.
    """
    from src.scheme_test import gap_capacity
    for q, tc, tf in [(1000, 6.5, 3.5), (500, 4.1, 2.2), (2500, 5.5, 3.0), (3000, 4.0, 2.2)]:
        expected = q * math.exp(-q * tc / 3600) / (1 - math.exp(-q * tf / 3600))
        assert gap_capacity(q, tc, tf) == pytest.approx(expected, rel=1e-9)


def test_the_critical_gap_matters_far_more_than_the_follow_up_headway():
    """
    Which unmeasured input to prioritise measuring. At representative values a half-second
    on the critical gap moves capacity about five times as much as the same change to the
    follow-up headway.
    """
    from src.scheme_test import gap_capacity
    q, tc, tf = 2800, 3.5, 2.2
    base = gap_capacity(q, tc, tf)
    d_tc = abs(gap_capacity(q, tc + 0.5, tf) / base - 1)
    d_tf = abs(gap_capacity(q, tc, tf + 0.5) / base - 1)
    assert d_tc > 4 * d_tf


def test_two_wheeler_gap_sits_inside_the_four_lane_median_opening_evidence():
    """
    Two-wheelers are half this stream, so their critical gap is the most consequential
    number in the model. It used to be 2.8 s, anchored on Kumar & Sasikumar's Kerala
    median openings — but that paper states carriageway width and never states lane
    count, so treating it as four-lane was our inference, not theirs.

    The two studies that DO measure median openings on roads explicitly described as
    four-lane divided both put two-wheelers higher: Gupta et al. 2018 (Varanasi,
    7.03-8.90 m per direction) at 3.83 s, and Datta & Bhuyan 2014 (six openings,
    Odisha/Jharkhand) at 3.37 s by probability equilibrium and 4.78 s by INAFOGA.

    The value must sit inside that evidence. Below it we would be overstating bay
    capacity; above it we would be manufacturing our own conclusion.
    """
    from src.scheme_test import CRITICAL_GAP_S, INDO_HCM_BASE_GAP_S
    lo, hi = CRITICAL_GAP_S["TWO_W"]
    assert 3.37 <= lo <= 4.78, f"optimistic {lo} outside the four-lane evidence"
    assert 3.37 <= hi <= 4.78, f"conservative {hi} outside the four-lane evidence"
    assert lo == INDO_HCM_BASE_GAP_S["2w"], "optimistic should be the Indo-HCM base"
    assert lo < hi


def test_follow_up_headway_band_contains_every_measured_indian_value():
    """
    Our follow-up band was assumed before any measurement was found. Every Indian value
    that exists must fall inside it, or the band is not defensible: 2.50 s (Ramireddy
    et al. 2025, Siegloch), 2.17 s (Dash et al.), and 2.04 s — the only one measured on
    four-lane median openings specifically (Khan 2022 thesis Table 8.2).

    The optimistic end is pinned to that four-lane measurement rather than sitting above
    it. A shorter follow-up means MORE bay capacity, so this runs against our own
    conclusion, which is exactly why it is pinned there and not left at the old 2.2 s.
    """
    from src.scheme_test import (FOLLOW_UP_S, FOLLOW_UP_MEASURED_S,
                                 FOLLOW_UP_FOUR_LANE_MEASURED_S)
    lo, hi = FOLLOW_UP_S
    for m in FOLLOW_UP_MEASURED_S:
        assert lo <= m <= hi, f"measured {m}s falls outside the band {FOLLOW_UP_S}"
    assert lo <= FOLLOW_UP_FOUR_LANE_MEASURED_S, (
        "optimistic follow-up sits above the four-lane measurement, which would understate "
        "bay capacity on the geometry that actually matches this corridor")


def test_follow_up_departs_from_the_convention_toward_the_measurement():
    """
    tf = 0.6 x tc is a convention, not a code relation — Indo-HCM has no median-opening
    chapter to carry one, and Indian studies state the ratio as an assumption in so many
    words. Our optimistic follow-up no longer follows it: it is pinned to the 2.04 s
    measured on four-lane median openings, roughly 0.3 s below what the convention implies.

    Assert the departure is real and in the right direction. A measurement on the matching
    geometry should beat a rule of thumb, and a shorter follow-up gives MORE bay capacity,
    so this weakens our own conclusion rather than strengthening it.
    """
    from src.scheme_test import (FOLLOW_UP_S, FOLLOWUP_RATIO_CONVENTION, weighted_gap,
                                 FOLLOW_UP_FOUR_LANE_MEASURED_S)
    share = {"TWO_W": 0.49, "CAR_BUCKET": 0.48, "AUTO_TRK_BUS": 0.03}
    implied = FOLLOWUP_RATIO_CONVENTION * weighted_gap(share, 0)
    assert FOLLOW_UP_S[0] < implied, "we should sit below the convention, not on it"
    assert abs(FOLLOW_UP_S[0] - FOLLOW_UP_FOUR_LANE_MEASURED_S) <= 0.05, (
        "the optimistic follow-up should track the four-lane measurement")


def test_the_model_difference_from_indo_hcm_is_stated_not_hidden():
    """Indo-HCM adds geometric factors a and b we cannot apply; that is recorded."""
    from src.scheme_test import INDO_HCM_FORM_DIFFERS
    assert "a = 1" in INDO_HCM_FORM_DIFFERS and "b = 0" in INDO_HCM_FORM_DIFFERS


# --- the gap spread is the sensitivity argument; it must be testable ---------
def _fake_uturns(n=12, demand=300.0, conflicting=1800.0):
    return [dict(uturn_demand=demand, conflicting_flow=conflicting) for _ in range(n)]


def test_gap_spread_is_monotonic_in_the_critical_gap():
    """
    A longer critical gap means fewer acceptable gaps, so it can never make MORE
    approaches servable. If this ever inverts, the capacity formula is wrong and every
    number in the spread with it.

    Testable at all only because gap_evidence_spread() was lifted out of __main__ — the
    calculation whose entire purpose is to show how sensitive the finding is to an
    assumption could not itself be exercised while it sat inline in the driver.
    """
    from src.scheme_test import gap_evidence_spread
    rows = gap_evidence_spread(_fake_uturns(), 3.87, 5.03, 12)
    assert rows == sorted(rows, key=lambda r: r["t_c"]), "spread is not sorted by t_c"
    unserv = [r["unservable"] for r in rows]
    assert unserv == sorted(unserv), (
        f"a longer gap made more approaches servable: {unserv}")


def test_gap_spread_covers_every_declared_basis():
    from src.scheme_test import gap_evidence_spread, GAP_EVIDENCE
    rows = gap_evidence_spread(_fake_uturns(), 3.87, 5.03, 12)
    assert len(rows) == len(GAP_EVIDENCE)
    assert {r["label"] for r in rows} == {e[0] for e in GAP_EVIDENCE}
    for r in rows:
        assert r["source"] and r["geometric_match"], f"{r['label']} lacks provenance"
        assert 0 <= r["unservable"] <= r["of"]
        assert r["no_viable_gap"] <= r["unservable"], (
            "a movement past the degeneracy threshold must also count as unservable")


def test_our_own_values_appear_in_the_spread_and_are_not_the_extremes():
    """
    The spread exists to show our gap is not cherry-picked. If ours were the lowest or
    highest basis in it, publishing the spread would be decoration.
    """
    from src.scheme_test import gap_evidence_spread
    rows = gap_evidence_spread(_fake_uturns(), 3.87, 5.03, 12)
    labels = [r["label"] for r in rows]
    ours = [i for i, l in enumerate(labels) if l.startswith("ours,")]
    assert len(ours) == 2, "both of our values should be in the spread"
    assert min(ours) > 0, "our optimistic gap is the lowest basis published"
    assert max(ours) < len(rows) - 1, "our conservative gap is the highest basis published"
