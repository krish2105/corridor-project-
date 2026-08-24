"""
Standards warrants and the whole-day profiles.

Both modules sat at 0% coverage: nothing imported them at all. They are not incidental —
standards.py is what puts the corridor against the codes it is built under, and
profiles.py produces the LOS grid whose whole argument is that the peak-hour convention
understates the problem. Neither had a single test.
"""
import pytest


# --- standards: the warrants ------------------------------------------------
def _cap(rows):
    return {"junctions": [dict(junction=j, approach=a, pcu_pt=p) for j, a, p in rows]}


def test_interchange_warrant_sums_both_corridor_arms_per_junction():
    from src.standards import interchange_warrant, INTERCHANGE_WARRANT_PCU
    out = interchange_warrant(_cap([("TMC-01", "N", 4000), ("TMC-01", "S", 3000),
                                    ("TMC-02", "N", 1000), ("TMC-02", "S", 500)]))
    by = {r["junction"]: r for r in out}
    assert by["TMC-01"]["corridor_arms_pcu"] == 7000
    assert by["TMC-02"]["corridor_arms_pcu"] == 1500
    assert by["TMC-01"]["floor_vs_warrant"] == round(7000 / INTERCHANGE_WARRANT_PCU, 2)


def test_the_interchange_figure_is_a_floor_not_a_total():
    """
    The survey measures the two corridor approaches; the cross-street arms are real
    traffic with no measured width. Reporting the corridor sum as the all-arm total would
    overstate how close each junction sits to the warrant, so the field is named
    floor_vs_warrant and must stay a lower bound.
    """
    from src.standards import interchange_warrant
    out = interchange_warrant(_cap([("TMC-01", "N", 4000), ("TMC-01", "S", 3000)]))
    assert "floor_vs_warrant" in out[0]
    assert "total_vs_warrant" not in out[0]


def test_zebra_warrant_flags_only_approaches_over_the_ceiling():
    from src.standards import zebra_warrant, ZEBRA_CEILING_PCU_DIR
    out = zebra_warrant(_cap([("TMC-01", "N", ZEBRA_CEILING_PCU_DIR + 1),
                              ("TMC-01", "S", ZEBRA_CEILING_PCU_DIR - 1),
                              ("TMC-02", "N", ZEBRA_CEILING_PCU_DIR)]))
    assert [r["over"] for r in out] == [True, False, False], "boundary is exclusive"
    assert out[0]["multiple"] >= 1.0


def test_median_spacing_counts_gaps_below_the_built_up_minimum():
    from src.standards import median_spacing, MEDIAN_SPACING_BUILTUP_M
    openings = [{"chainage_m": 0, "width_m": 19},
                {"chainage_m": 300, "width_m": 25},      # 300 m gap: too close
                {"chainage_m": 1200, "width_m": 18}]     # 900 m gap: fine
    r = median_spacing(openings)
    assert r["openings"] == 3 and r["gaps"] == 2
    assert r["closer_than_500m"] == 1
    assert r["closest_m"] == 300 < MEDIAN_SPACING_BUILTUP_M
    assert r["within_18_20m"] == 2, "18 and 19 are in range, 25 is not"


def test_median_spacing_survives_openings_with_no_chainage_or_width():
    """Real linework has gaps; the function must not divide by zero or raise."""
    from src.standards import median_spacing
    r = median_spacing([{"chainage_m": None, "width_m": None}])
    assert r["gaps"] == 0 and r["closest_m"] is None and r["median_gap_m"] is None


def test_the_survey_pcu_is_recorded_as_lower_than_the_states_own_dpr():
    """
    The audit's corroboration from inside the state government: JMRC's own Phase-II DPR
    carries 2W at 0.75 while this survey used 0.50. If those two ever agreed, the finding
    would evaporate and this constant pair would be the place it happened silently.
    """
    from src.standards import JMRC_DPR_PCU, SURVEY_PCU
    assert SURVEY_PCU["two wheeler"] < JMRC_DPR_PCU["two wheeler"]
    assert SURVEY_PCU["MAV"] > JMRC_DPR_PCU["MAV"], (
        "the MAV correction runs the other way and must keep doing so")


# --- profiles: the cumulative arrival/departure curves -----------------------
def test_cumulative_queue_forms_when_arrivals_exceed_capacity(synth_bins):
    """
    The defect this replaces: per-bin arrivals were compared against an HOURLY capacity,
    so everything got through and the module reported no queue at all on an approach
    running at v/c 2.41. Capacity must be converted to the bin.
    """
    from src.profiles import cumulative
    day = sorted(synth_bins.date.unique())[0]
    j = sorted(synth_bins.junction.unique())[0]
    arm = sorted(synth_bins[synth_bins.junction == j].arm_from.unique())[0]
    starved = cumulative(synth_bins, day, j, arm, capacity=1.0)
    assert starved is not None
    assert max(starved["queue"]) > 0, "no queue formed at a capacity of 1 PCU/hr"
    assert (starved["arrivals"] >= starved["departures"]).all(), (
        "departures exceeded arrivals — vehicles left before they arrived")


def test_cumulative_queue_clears_when_capacity_is_ample(synth_bins):
    from src.profiles import cumulative
    day = sorted(synth_bins.date.unique())[0]
    j = sorted(synth_bins.junction.unique())[0]
    arm = sorted(synth_bins[synth_bins.junction == j].arm_from.unique())[0]
    free = cumulative(synth_bins, day, j, arm, capacity=1_000_000)
    assert max(free["queue"]) == 0


def test_the_departure_band_brackets_the_central_line(synth_bins):
    """
    Arrivals are measured; departures are assumed. That assumption is drawn as a band so
    a reader can argue with it. If the band ever collapsed onto the central line the
    figure would look like a measurement.
    """
    from src.profiles import cumulative
    day = sorted(synth_bins.date.unique())[0]
    j = sorted(synth_bins.junction.unique())[0]
    arm = sorted(synth_bins[synth_bins.junction == j].arm_from.unique())[0]
    c = cumulative(synth_bins, day, j, arm, capacity=50.0)
    assert (c["dep_low"] <= c["departures"]).all()
    assert (c["departures"] <= c["dep_high"]).all()
    assert c["dep_high"].iloc[-1] > c["dep_low"].iloc[-1], "the band has no width"
    # a faster discharge must give the SHORTER queue
    assert (c["queue_low"] <= c["queue_high"]).all()


def test_hourly_pcu_returns_none_for_an_arm_with_no_movements(synth_bins):
    from src.profiles import hourly_pcu
    day = sorted(synth_bins.date.unique())[0]
    j = sorted(synth_bins.junction.unique())[0]
    assert hourly_pcu(synth_bins, day, j, "an arm that does not exist") is None
