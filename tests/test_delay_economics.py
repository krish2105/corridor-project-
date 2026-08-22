"""
Tests for queue, delay, journey time, cost, and the Phase 6 driver.

The failure mode being guarded is a number that looks reasonable and is not. Two in
particular: a queue reported longer than the road can physically hold, which reads as a
measurement and is a model artefact; and an excess-arrivals figure multiplied by a
duration twice, which inflates every rupee downstream without looking wrong anywhere.
"""
import json

import pytest

from src.delay import (JAM_FOOTPRINT_M2, JAM_PACKING, T_HOURS, minutes_to_spillback,
                       queue_and_delay, queue_metres, spillback)
from src.economics import VOT_INR_PER_VEH_HR, WORKING_DAYS, annual_cost
from src.pipeline import STAGES, GateFailure


# --- the queueing model ------------------------------------------------------
def test_under_capacity_reports_no_deterministic_queue():
    r = queue_and_delay(1000, 2400)
    assert r["queue_pcu"] == 0 and not r["oversaturated"]


def test_at_capacity_is_not_treated_as_oversaturated():
    r = queue_and_delay(2400, 2400)
    assert not r["oversaturated"]


def test_queue_grows_at_exactly_the_excess():
    r = queue_and_delay(3400, 2400, t_hours=1.0)
    assert r["queue_pcu"] == pytest.approx(1000)


def test_delay_matches_the_closed_form():
    """0.5 * T * (1 - 1/X), in minutes. Pinned so a refactor cannot drift it."""
    r = queue_and_delay(4800, 2400, t_hours=1.0)
    assert r["mean_delay_min"] == pytest.approx(60 * 0.5 * 1.0 * (1 - 1 / 2.0))


def test_doubling_the_period_quadruples_total_delay():
    """Total delay goes as T squared; a linear result would mean the area is wrong."""
    a = queue_and_delay(3400, 2400, t_hours=1.0)["total_delay_pcu_hr"]
    b = queue_and_delay(3400, 2400, t_hours=2.0)["total_delay_pcu_hr"]
    assert b == pytest.approx(4 * a)


# --- storage and spillback ---------------------------------------------------
def test_two_wheelers_store_far_more_densely_than_cars():
    """The reason a 6.5 m-per-car conversion is wrong on this corridor."""
    assert JAM_FOOTPRINT_M2["TWO_W"] < JAM_FOOTPRINT_M2["CAR_BUCKET"] / 4


def test_queue_length_uses_the_measured_width():
    veh_a, m_a = queue_metres(1000, {"CAR_BUCKET": 1.0}, 1.0, 7.0)
    veh_b, m_b = queue_metres(1000, {"CAR_BUCKET": 1.0}, 1.0, 14.0)
    assert veh_a == veh_b
    assert m_a == pytest.approx(2 * m_b)


def test_a_queue_is_never_reported_longer_than_the_road_can_hold():
    """Regression guard on the whole point of the spillback cap."""
    shown, spills = spillback(3964, 539)
    assert spills and shown == 539


def test_no_upstream_junction_means_no_spillback_claim():
    shown, spills = spillback(3000, None)
    assert not spills and shown == 3000


def test_time_to_spillback_scales_with_available_storage():
    early = minutes_to_spillback(200, 2000)
    late = minutes_to_spillback(800, 2000)
    assert early is not None and late is not None and early < late


def test_no_spillback_time_when_the_queue_fits():
    assert minutes_to_spillback(2000, 500) is None


def test_jam_packing_is_conservative():
    """A higher packing figure shortens every queue, so this is the cautious end."""
    assert 0 < JAM_PACKING <= 1.0


# --- economics ---------------------------------------------------------------
def test_every_value_of_time_is_a_band_not_a_point():
    for cls, band in VOT_INR_PER_VEH_HR.items():
        assert len(band) == 2 and band[0] < band[1], cls


def test_working_days_is_a_band():
    assert len(WORKING_DAYS) == 2 and WORKING_DAYS[0] < WORKING_DAYS[1]


def test_cost_scales_linearly_with_delay_and_days():
    vot = {k: v[0] for k, v in VOT_INR_PER_VEH_HR.items()}
    comp = {"TWO_W": 0.5, "CAR_BUCKET": 0.5}
    a = annual_cost(1000, comp, 0.8, 300, vot)
    assert annual_cost(2000, comp, 0.8, 300, vot) == pytest.approx(2 * a)
    assert annual_cost(1000, comp, 0.8, 600, vot) == pytest.approx(2 * a)


def test_a_heavier_stream_costs_more_than_a_two_wheeler_stream():
    vot = {k: v[0] for k, v in VOT_INR_PER_VEH_HR.items()}
    light = annual_cost(1000, {"TWO_W": 1.0}, 0.8, 300, vot)
    heavy = annual_cost(1000, {"AUTO_TRK_BUS": 1.0}, 0.8, 300, vot)
    assert heavy > light


# --- the published outputs stay consistent with each other -------------------
def test_delay_and_economics_outputs_agree_on_the_approach_count():
    from src.config import OUT_DATA
    d = json.loads((OUT_DATA / "delay.json").read_text())
    e = json.loads((OUT_DATA / "economics.json").read_text())
    assert d["n_approaches"] == len(e["approaches"])


def test_spillback_count_is_consistent_with_the_per_approach_rows():
    from src.config import OUT_DATA
    d = json.loads((OUT_DATA / "delay.json").read_text())
    assert d["spillback_count"] == sum(1 for a in d["approaches"] if a["spillback"])


def test_reported_queue_never_exceeds_reported_storage_in_the_published_data():
    from src.config import OUT_DATA
    d = json.loads((OUT_DATA / "delay.json").read_text())
    for a in d["approaches"]:
        if a["storage_m"] and not a["spillback"]:
            assert a["queue_m"] <= a["storage_m"]


def test_economics_declares_the_value_of_time_as_a_policy_input():
    from src.config import OUT_DATA
    e = json.loads((OUT_DATA / "economics.json").read_text())
    assert "policy" in e["assumptions"]["vot_status"].lower()
    assert e["assumptions"]["excluded"]


# --- the pipeline driver -----------------------------------------------------
def test_validation_precedes_nothing_that_publishes():
    assert STAGES.index("validate") > STAGES.index("count")
    assert STAGES.index("homography") == 0


def test_gate_failure_is_its_own_exception():
    """So a caller can distinguish 'the gate said no' from 'the code broke'."""
    assert issubclass(GateFailure, Exception)
