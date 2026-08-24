"""
Tests for the functions that turn the survey into published numbers.

Before these, `approach_pcu`, `analyse`, `scenarios`, `uturn_verdict`,
`oversaturated_hours`, `through_vs_turning` and `corridor_order` had bodies no test ever
executed — while producing every v/c ratio, the U-turn verdict, the robustness grids and
the rupee figures on the dashboard and in every deliverable.

The fixtures in conftest.py make the expected answers computable on paper, so these are
assertions about arithmetic rather than smoke tests.
"""
import pytest

from src.analyse import composition, corridor_order, peak_hours, through_vs_turning, tmc_matrix
from src.capacity import approach_pcu, observed_vehicles
from src.economics import oversaturated_hours
from src.scheme_test import analyse as scheme_analyse
from src.sensitivity import elevated_verdict, uturn_verdict


# --- movement structure ------------------------------------------------------
def test_the_fixture_has_twelve_movements_per_junction(synth_bins):
    for code, g in synth_bins.groupby("junction"):
        assert len({(a, b) for a, b in zip(g.arm_from, g.arm_to)}) == 12, code


def test_no_movement_returns_to_its_own_arm(synth_bins):
    assert not (synth_bins.arm_from == synth_bins.arm_to).any()


# --- composition -------------------------------------------------------------
def test_composition_shares_sum_to_one(synth_bins, synth_day):
    c = composition(synth_bins, synth_day)
    for code, g in c.groupby("junction"):
        assert g.share.sum() == pytest.approx(1.0)


def test_composition_recovers_the_planted_mix(synth_bins, synth_day):
    """Two-wheelers are 50 of every 100 vehicles by construction."""
    c = composition(synth_bins, synth_day)
    tw = c[(c.junction == "TMC-01") & (c.veh_class == "TWO_W")].share.iloc[0]
    assert tw == pytest.approx(0.50, abs=1e-9)


# --- through vs turning ------------------------------------------------------
def test_through_share_is_one_third_when_movements_are_equal(synth_bins, synth_day):
    """
    Left, Straight and Right carry identical volume in the fixture, so the through share
    must be exactly a third. A model that mixed up the movement labels would not land here.
    """
    t = through_vs_turning(synth_bins, synth_day).set_index("junction")
    # through_pct is rounded to one decimal at source, so 33.3 is the right answer
    assert t.loc["TMC-01", "through_pct"] == pytest.approx(100 / 3, abs=0.05)


# --- peak hour ---------------------------------------------------------------
def test_a_flat_profile_still_yields_a_peak_hour(synth_bins, synth_day):
    ph = peak_hours(synth_bins, synth_day)
    assert len(ph) == 2


def test_peak_hour_finds_the_planted_peak(synth_peaked, synth_day):
    """SYN-01 carries triple volume 09:00-10:00; SYN-02 is flat."""
    ph = peak_hours(synth_peaked, synth_day).set_index("junction")
    assert ph.loc["TMC-01", "peak_start"].hour == 9


# --- PCU ---------------------------------------------------------------------
def test_approach_pcu_bands_are_ordered_and_cover_both_corridor_arms(synth_bins, synth_day):
    df = approach_pcu(synth_bins, synth_day)
    assert set(df.approach) == {"from Mansarover Metro", "from Sanganer Stadium"}
    assert len(df) == 4                       # 2 junctions x 2 corridor approaches
    for _, r in df.iterrows():
        assert r.pcu_lo <= r.pcu_pt <= r.pcu_hi


def test_approach_pcu_scales_with_demand(synth_bins, synth_peaked, synth_day):
    """Tripling the peak hour must raise the peak-hour PCU on that junction only."""
    flat = approach_pcu(synth_bins, synth_day).set_index(["junction", "approach"])
    peak = approach_pcu(synth_peaked, synth_day).set_index(["junction", "approach"])
    k1 = ("TMC-01", "from Mansarover Metro")
    k2 = ("TMC-02", "from Mansarover Metro")
    assert peak.loc[k1, "pcu_pt"] > flat.loc[k1, "pcu_pt"] * 2
    assert peak.loc[k2, "pcu_pt"] == pytest.approx(flat.loc[k2, "pcu_pt"])


def test_observed_vehicles_matches_the_planted_hourly_volume(synth_bins, synth_day):
    """
    Each approach is 3 movements x 4 bins x 100 veh = 1,200 vehicles in any hour.
    """
    v = observed_vehicles(synth_bins, synth_day)
    assert float(v["TMC-01"]) == pytest.approx(1200.0)


# --- TMC matrix --------------------------------------------------------------
def test_tmc_matrix_is_four_by_four_with_a_zero_diagonal(synth_bins, synth_day):
    veh, pcu = tmc_matrix(synth_bins, synth_day, "TMC-01")
    assert veh.shape == (4, 4) and pcu.shape == (4, 4)
    m = veh
    for i in range(4):
        assert m.iloc[i, i] == 0


def test_tmc_matrix_totals_match_the_daily_count(synth_bins, synth_day):
    """12 movements x 96 bins x 100 veh = 115,200 per junction."""
    veh, _pcu = tmc_matrix(synth_bins, synth_day, "TMC-01")
    assert veh.values.sum() == pytest.approx(115_200)


# --- scheme test -------------------------------------------------------------
def test_scheme_analyse_returns_a_row_per_corridor_approach(synth_bins, synth_day):
    res = scheme_analyse(synth_bins, synth_day)
    assert len(res) == 4
    for col in ("uturn_demand", "conflicting_flow", "vc_conservative"):
        assert col in res.columns


def test_a_heavier_conflicting_stream_never_improves_the_uturn(synth_bins, synth_peaked,
                                                               synth_day):
    flat = scheme_analyse(synth_bins, synth_day).set_index(["junction", "approach"])
    peak = scheme_analyse(synth_peaked, synth_day).set_index(["junction", "approach"])
    k = ("TMC-01", "Mansarover Metro")
    assert peak.loc[k, "conflicting_flow"] > flat.loc[k, "conflicting_flow"]
    assert peak.loc[k, "vc_conservative"] >= flat.loc[k, "vc_conservative"]


# --- sensitivity -------------------------------------------------------------
def test_uturn_verdict_runs_and_bounds_its_own_output(synth_bins, synth_day):
    fails, total = uturn_verdict(synth_bins, synth_day, "optimistic")
    assert 0 <= fails <= total and total > 0


def test_the_conservative_gap_is_never_kinder_than_the_optimistic_one(synth_bins, synth_day):
    opt, _ = uturn_verdict(synth_bins, synth_day, "optimistic")
    cons, _ = uturn_verdict(synth_bins, synth_day, "conservative")
    assert cons >= opt


def test_more_lane_capacity_never_relieves_fewer_approaches(synth_bins, synth_day):
    lean, tot = elevated_verdict(synth_bins, synth_day, 14.9, 1200, 2)
    rich, tot2 = elevated_verdict(synth_bins, synth_day, 14.9, 1800, 2)
    assert tot == tot2 and rich >= lean


def test_a_bigger_pcu_uplift_never_relieves_more_approaches(synth_bins, synth_day):
    small, _ = elevated_verdict(synth_bins, synth_day, 14.9, 1200, 2)
    large, _ = elevated_verdict(synth_bins, synth_day, 74.8, 1200, 2)
    assert large <= small


# --- economics ---------------------------------------------------------------
def test_oversaturated_hours_is_zero_when_capacity_exceeds_demand(synth_bins, synth_day):
    cap = {(j, a): 999_999 for j in ("TMC-01", "TMC-02")
           for a in ("from Mansarover Metro", "from Sanganer Stadium")}
    out = oversaturated_hours(synth_bins, synth_day, cap)
    assert out and all(v["hours_over"] == 0 for v in out.values())
    assert all(v["excess_pcu"] == 0 for v in out.values())


def test_a_flat_profile_over_capacity_is_over_for_the_whole_day(synth_bins, synth_day):
    """Every bin is identical, so if one hour is over capacity all 24 are."""
    cap = {(j, a): 1 for j in ("TMC-01", "TMC-02")
           for a in ("from Mansarover Metro", "from Sanganer Stadium")}
    out = oversaturated_hours(synth_bins, synth_day, cap)
    for v in out.values():
        assert v["hours_over"] > 20


def test_excess_rises_as_capacity_falls(synth_bins, synth_day):
    keys = [(j, a) for j in ("TMC-01",) for a in ("from Mansarover Metro",)]
    lo = oversaturated_hours(synth_bins, synth_day, {k: 500 for k in keys})
    hi = oversaturated_hours(synth_bins, synth_day, {k: 2000 for k in keys})
    assert lo[keys[0]]["excess_pcu"] > hi[keys[0]]["excess_pcu"]


# --- corridor ordering -------------------------------------------------------
def test_corridor_order_returns_a_complete_ordering(synth_bins, synth_day):
    best, cost, top, margin, links = corridor_order(synth_bins, synth_day)
    assert sorted(best) == ["TMC-01", "TMC-02"]
    assert len(links) == len(best) - 1


def test_corridor_order_margin_is_a_number_even_when_orderings_tie(synth_bins, synth_day):
    """
    Regression. Two orderings that fit the flows equally well made the runner-up cost
    zero, the margin nan, and a nan margin reads downstream as "inconclusive" rather
    than as a computation that failed.
    """
    import math
    _b, _c, _t, margin, _l = corridor_order(synth_bins, synth_day)
    assert margin is not None and not math.isnan(margin)


# --- audit gates must check what they claim to check -------------------------
def test_pcu_gate_tests_intervals_not_just_day_totals():
    """
    CLAUDE.md's gate is "implied factor per class constant across all 96 intervals". The
    check back-solved one ratio per workbook from the IN_1 day-total rows — twelve
    observations. A day total is a sum, so a factor that varied between intervals would
    still yield a single count-weighted ratio; twelve of those agreeing proves nothing
    about the intervals underneath.
    """
    import inspect
    from src import audit
    src = inspect.getsource(audit.check_pcu)
    assert "ROW_BINS" in src, "the PCU gate never iterates the 15-minute rows"
    assert "COL_PCU" in src, "the PCU gate never reads the per-interval stored PCU"
    assert "rows tested" in src


def test_peak_gate_reads_the_workbooks_own_rolling_hour_sheets():
    """
    The gate is "re-derived from 15-min bins matches the workbook's own rolling-hour
    sheets". ROW_HOURS was declared in tmc_parse.py and read by no module, so the section
    titled "re-derived vs the workbook's stated peaks" compared the re-derivation against
    nothing at all.
    """
    import inspect
    from src import audit
    src = inspect.getsource(audit.check_peak)
    assert "ROW_HOURS" in src, "the peak gate still never opens the rolling-hour rows"
    assert "rolling-hour" in src


# --- corridor ordering: the real case, not just the degenerate one ----------
def test_corridor_order_resolves_a_four_junction_chain():
    """
    The existing ordering tests use the two-junction fixture, where any algorithm returns
    the right answer because there is only one chain to find. The published corridor has
    six. This builds a four-junction chain with unambiguous continuity — southbound
    outflow at n feeds the Mansarover inflow at n+1 — and asserts the order comes back.
    """
    import pandas as pd
    from src.analyse import corridor_order, NORTH, SOUTH
    day = pd.Timestamp("2026-05-11").date()
    chain = ["TMC-01", "TMC-02", "TMC-03", "TMC-04"]
    # flow decays down the chain, so only one ordering fits the continuity
    flows = [4000, 3000, 2000, 1000]
    rows = []
    for code, f in zip(chain, flows):
        for arm, n in ((NORTH, f), (SOUTH, f)):
            for mvt in ("Straight", "Left", "Right"):
                rows.append(dict(junction=code, date=day, kind="movement",
                                 arm_from=arm, arm_to=SOUTH if arm == NORTH else NORTH,
                                 movement=mvt, veh_class="TWO_W",
                                 bin_start=pd.Timestamp("2026-05-11 09:00"),
                                 count=n if mvt == "Straight" else 0))
    best, cost, _top, margin, links = corridor_order(pd.DataFrame(rows), day)
    assert sorted(best) == sorted(chain), "not every junction was placed"
    assert len(links) == len(chain) - 1
    assert list(best) in (chain, chain[::-1]), (
        f"a monotonically decaying chain should order as {chain} or its reverse, got {best}")


def test_the_published_order_is_reported_as_inconclusive_where_it_is(published):
    """
    Continuity did not settle the real corridor — the margin between the best and
    runner-up orderings is about 1%, and chainage along the surveyed alignment resolved
    it instead. That must stay on the page. An order presented as derived-from-counts
    when the counts could not separate two candidates is the overclaim this audit exists
    to object to.
    """
    c = published("corridor")["corridor"] if "corridor" in published("corridor") \
        else published("corridor")
    assert c["order_conclusive"] is False, (
        "continuity is now reported as conclusive; if that is real the chainage "
        "tie-break should be retired, and if not the claim is overstated")
    assert c["order_margin_pct"] < 5, (
        f"margin of {c['order_margin_pct']}% is not the near-tie the text describes")
    assert len(c["order_candidates"]) > 1, "a tie needs its runner-up published"


def test_chainage_places_every_junction_and_labels_inferred_ones(published):
    """
    Chainage is what actually decided the published order, and nothing asserted it. It
    only counts as evidence for the three junctions matched by name — for the inferred
    ones it restates the position that was inferred, so the labels must survive.
    """
    from src.reports import chainage
    total, rows = chainage()
    assert total > 0 and len(rows) == 6
    ch = [r["chainage_m"] for r in rows]
    assert ch == sorted(ch), "chainage rows are not in order along the alignment"
    assert all(0 <= c <= total for c in ch), "a junction sits off the alignment"
    assert any(r["confidence"] == "inferred" for r in rows), (
        "every junction now reads as confirmed; three positions are still inferred "
        "pending the survey location schedule")
