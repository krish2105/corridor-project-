"""
Tests for uturn_framework.py — the U-turn decision ladder.

The framework's whole value is that it says which constraint binds and refuses to claim
anything about the ones below it. Both of those are easy to get subtly wrong, and both
were wrong on the first run, so both are pinned here.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.scheme_test import FOLLOW_UP_S, gap_capacity
from src.uturn_framework import (BLOCKED, CRITERIA, FAIL, NOT_REACHED, PASS, admits,
                                 assess, back_solve, bay_ceiling, live_alternatives)

T_F = FOLLOW_UP_S[0]


def _bay(demand, conflicting, junction="TMC-01", bay="northbound", t_c=3.9):
    return dict(junction=junction, bay=bay, jda_name="B-2 Bypass ", approach="Mansarover",
                uturn_demand=float(demand), conflicting_flow=float(conflicting),
                t_c_lo=t_c, t_c_hi=t_c + 1.2,
                vc_optimistic=demand / gap_capacity(conflicting, t_c, T_F),
                vc_conservative=demand / gap_capacity(conflicting, t_c + 1.2, T_F))


def _detour(junction="TMC-01", bay="northbound", chainage=800, one_way=700, m=1400):
    return dict(junction=junction, bay=bay, bay_chainage_m=chainage,
                junction_chainage_m=chainage - one_way, one_way_m=one_way,
                detour_m=m, veh_km_per_hour=100.0, bay_beyond_drawing=False)


# --- the ceiling of the instrument -------------------------------------------

def test_bay_ceiling_is_the_follow_up_headway():
    """With nothing to yield to, throughput is 3600 / t_f and nothing lifts it."""
    assert bay_ceiling(2.0) == 1800.0
    assert bay_ceiling(3.0) == 1200.0


def test_capacity_approaches_the_ceiling_as_conflict_vanishes():
    """The ceiling is not asserted - it is the limit of the capacity form itself."""
    assert gap_capacity(1.0, 3.9, T_F) == pytest.approx(bay_ceiling(T_F), rel=0.01)


def test_demand_above_the_ceiling_reports_no_reachable_conflicting_flow():
    """
    Regression. The bisection over conflicting flow walked down to its lower bound and
    reported "the opposing stream must fall 100%", which reads as an extreme version of a
    solvable problem. It is not one: a single opening cannot pass that demand at all.
    """
    s = back_solve(_bay(demand=bay_ceiling(T_F) + 500, conflicting=2500))
    assert s["above_bay_ceiling"] is True
    assert s["conflicting_needed"] is None
    assert s["conflicting_reduction_pct"] is None
    assert "no reduction" in s["note"].lower()


def test_a_solvable_bay_back_solves_to_a_flow_that_actually_serves_it():
    s = back_solve(_bay(demand=400, conflicting=2500))
    assert s["above_bay_ceiling"] is False
    assert gap_capacity(s["conflicting_needed"], 3.9, T_F) == pytest.approx(400, rel=0.02)


# --- the ladder --------------------------------------------------------------

def _assess_one(bay, detours=None, openings=(), lanes=None):
    return assess([bay], detours or [], list(openings), lanes or {"TMC-01": 3})[0]


def test_criteria_below_the_binding_one_are_not_reached_never_passed():
    """
    The point of an ordered ladder. Marking an untested criterion as a pass would tell a
    reader the geometry was checked and cleared, when it was never looked at.
    """
    r = _assess_one(_bay(demand=3000, conflicting=3000), [_detour()],
                    [dict(chainage_m=800, width_m=30.0)])
    assert r["binding_criterion"] == "gap capacity"
    below = CRITERIA[1:]
    assert all(r["checks"][c]["status"] == NOT_REACHED for c in below)
    assert not any(r["checks"][c]["status"] == PASS for c in below)


def test_blocked_criteria_below_the_binding_one_are_kept_but_kept_separate():
    """
    Regression. The not-reached pass overwrote the blocked flags, so the framework
    reported nothing left to measure while its own advice section listed two surveys.
    A criterion below the binding one is not blocking today's verdict, but it is exactly
    what needs data the moment the binding one is cleared.
    """
    r = _assess_one(_bay(demand=3000, conflicting=3000))     # no detour, no opening
    assert r["blocked_on"] == []
    assert set(r["blocked_if_binding_cleared"]) >= {"median width", "weaving", "detour burden"}
    assert r["verdict"] == "fails"


def test_a_bay_that_clears_the_gap_is_decided_by_the_next_criterion():
    r = _assess_one(_bay(demand=60, conflicting=1200), [_detour()],
                    [dict(chainage_m=800, width_m=8.0)])
    assert r["checks"]["gap capacity"]["status"] == PASS
    assert r["binding_criterion"] == "median width"


def test_an_undecidable_bay_names_what_blocks_it():
    """Never a silent gap: the verdict is undecided AND the missing measurement is named."""
    r = _assess_one(_bay(demand=60, conflicting=1200))
    assert r["verdict"] == "undecided"
    assert "median width" in r["blocked_on"]
    assert "total station" in r["checks"]["median width"]["detail"]


def test_a_distant_opening_is_not_treated_as_this_bay_s_opening():
    """A measured opening 400 m away tells you nothing about the width at the bay."""
    r = _assess_one(_bay(demand=60, conflicting=1200), [_detour(chainage=800)],
                    [dict(chainage_m=1200, width_m=30.0)])
    assert r["checks"]["median width"]["status"] == BLOCKED


# --- the design vehicle ------------------------------------------------------

def test_admits_returns_the_largest_vehicle_the_width_clears():
    assert admits(40.0)[0] == "articulated"
    assert admits(28.0)[0] == "bus_truck"
    assert admits(4.0)[0] is None


def test_admits_is_honest_about_sitting_inside_the_band():
    """The radii are a policy input carried as a band, so a width inside it says so."""
    veh, how = admits(27.5)
    assert veh == "bus_truck" and "band" in how


def test_admits_handles_an_unmeasured_width():
    assert admits(None) == (None, None)


# --- the alternatives ladder -------------------------------------------------

def test_geometric_fixes_are_dead_when_bays_sit_above_the_ceiling():
    """
    A wider median lowers the follow-up headway a little. It cannot answer a bay whose
    demand exceeds what any single opening passes, and saying otherwise would put a
    moderate-cost measure in front of a client it cannot help.
    """
    rows = assess([_bay(demand=bay_ceiling(T_F) + 900, conflicting=3000)], [], [],
                  {"TMC-01": 3})
    alts = {a["measure"]: a for a in live_alternatives(rows)}
    assert alts["widen the median, add an acceleration lane"]["live"] is False
    assert alts["relocate the bay"]["live"] is False
    assert alts["keep the signal"]["live"] is True


def test_grade_separation_is_not_claimed_to_make_an_over_ceiling_bay_work():
    rows = assess([_bay(demand=bay_ceiling(T_F) + 900, conflicting=3000)], [], [],
                  {"TMC-01": 3})
    g = next(a for a in live_alternatives(rows)
             if a["measure"].startswith("grade separate"))
    assert g["live"] is True
    assert "removing the NEED" in g["note"]


def test_signalising_is_live_only_while_some_bay_is_under_the_ceiling():
    over = assess([_bay(demand=bay_ceiling(T_F) + 900, conflicting=3000)], [], [],
                  {"TMC-01": 3})
    s = next(a for a in live_alternatives(over) if a["measure"].startswith("signalise"))
    assert s["live"] is False

    under = assess([_bay(demand=900, conflicting=3000)], [], [], {"TMC-01": 3})
    s2 = next(a for a in live_alternatives(under) if a["measure"].startswith("signalise"))
    assert s2["live"] is True


# --- weaving -----------------------------------------------------------------

def test_weaving_fails_when_the_bay_lands_on_top_of_the_junction():
    """
    TMC-04's northbound bay sits 4 m from its junction on the drawing. A vehicle
    re-entering there is changing lane inside the junction it is trying to reach.
    """
    r = _assess_one(_bay(demand=60, conflicting=1200),
                    [_detour(one_way=4, m=9)], [dict(chainage_m=800, width_m=30.0)],
                    lanes={"TMC-01": 3})
    assert r["checks"]["weaving"]["status"] == FAIL
    assert r["binding_criterion"] == "weaving"
