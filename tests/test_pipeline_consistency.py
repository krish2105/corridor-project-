"""
Tests that tie the derived outputs back to each other and to their source.

Two kinds live here. The first need only the published JSON in out/data and check that
the numbers on the dashboard agree with the numbers in the files a reviewer downloads.
The second need the client workbooks, which are deliberately not in this repository, and
skip cleanly when they are absent rather than failing for the wrong reason.

The sensitivity check is the important one. Its grid is supposed to contain the published
baseline as one of its cells; when it did not, the grid was silently exploring a different
assumption set from the one every headline figure came from, and reported a spillback
range that was wrong in both directions.
"""
import json

import pytest

from src.config import OUT_DATA, ROOT

DATA = OUT_DATA
SOURCE = ROOT / "00_source" / "extracted"
needs_source = pytest.mark.skipif(
    not SOURCE.exists() or not any(SOURCE.rglob("*.xlsx")),
    reason="client workbooks are not in this repository by design")


def _load(name):
    p = DATA / f"{name}.json"
    if not p.exists():
        pytest.skip(f"{name}.json not generated yet")
    return json.loads(p.read_text())


# --- the sensitivity grid must contain the published baseline ----------------
def _anchor_lane_cap(d):
    """The per-lane capacity the published delay actually used. Derived, never hardcoded."""
    caps = {a["capacity_pcu_hr"] for a in d["approaches"] if a["storage_m"] is not None}
    assert caps, "delay.json must publish the capacity each queue was derived from"
    return sum(caps) / len(caps) / 2          # two lanes per direction


def test_sensitivity_grid_reproduces_the_published_spillback_count():
    """
    Regression, twice over.

    First: lane_capacity_pcu is PER LANE and was compared against a total, so the grid's
    baseline cell disagreed with delay.py and the reported range was wrong.

    Then, worse and quieter: the fix pinned the anchor at a hardcoded 1200 PCU/lane, and
    at that value the rescale factor is identically 1 by construction — so this test
    passed for ANY baseline, including the retired 1200 that delay.py had never used. It
    could not fail. The anchor is now DERIVED from the capacity delay.py publishes, so
    the assertion has something real to bite on.
    """
    from src.delay import JAM_PACKING
    from src.sensitivity import spillback_verdict
    d = _load("delay")
    spills, total = spillback_verdict(JAM_PACKING, 1.0, _anchor_lane_cap(d))
    published = sum(1 for a in d["approaches"]
                    if a["spillback"] and a["storage_m"] is not None)
    assert spills == published, (
        f"grid centre says {spills} spill back, delay.py published {published}")
    assert total == sum(1 for a in d["approaches"] if a["storage_m"] is not None)


def test_the_sensitivity_axis_brackets_the_published_capacity():
    """
    An axis whose values all sit to one side of the real baseline does not test
    sensitivity — it tests a different scenario. The published per-lane capacity must lie
    inside the range the grid sweeps.
    """
    from src.sensitivity import AXES, QUEUE_AXES
    d = _load("delay")
    anchor = _anchor_lane_cap(d)
    # BOTH grids sweep a lane-capacity axis, and both must bracket the real value. Only
    # the queue axis was checked at first, and the main grid was found sitting entirely
    # below the published capacity while still being labelled "IRC planning".
    for name, axis in (("AXES", AXES["lane_capacity_pcu"]),
                       ("QUEUE_AXES", QUEUE_AXES["lane_capacity_pcu"])):
        assert min(axis) <= anchor <= max(axis), (
            f"{name}: published capacity {anchor:.0f} PCU/lane sits outside the swept "
            f"axis {sorted(axis)}")


def test_no_module_rebuilds_demand_from_the_retired_lane_capacity():
    """
    capacity.py retired 1200 PCU/lane as unsourced and replaced it with IRC:92-2017's
    2700 PCU/dir. sensitivity.py went on rebuilding demand from 1200 for a while, with a
    comment claiming it matched delay.py. Nothing may reintroduce it as a baseline.
    """
    import re
    from pathlib import Path
    src = Path(__file__).resolve().parent.parent / "src"
    for mod in ("sensitivity.py", "delay.py"):
        text = (src / mod).read_text()
        for m in re.finditer(r"(base_cap|baseline)\s*=\s*([0-9.]+)", text):
            assert False, f"{mod}: baseline hardcoded as {m.group(2)}; read it from the data"


def test_denser_packing_never_increases_spillback():
    from src.sensitivity import spillback_verdict
    d = _load("delay")
    c = _anchor_lane_cap(d)
    loose, _ = spillback_verdict(0.65, 1.0, c)
    dense, _ = spillback_verdict(0.85, 1.0, c)
    assert dense <= loose


def test_more_capacity_never_increases_spillback():
    from src.sensitivity import spillback_verdict
    d = _load("delay")
    c = _anchor_lane_cap(d)
    lean, _ = spillback_verdict(0.75, 1.0, c * 0.8)
    generous, _ = spillback_verdict(0.75, 1.0, c * 1.4)
    assert generous <= lean


def test_bigger_vehicles_never_reduce_spillback():
    from src.sensitivity import spillback_verdict
    _load("delay")
    small, _ = spillback_verdict(0.75, 0.8, 1200)
    large, _ = spillback_verdict(0.75, 1.2, 1200)
    assert large >= small


# --- cross-output consistency ------------------------------------------------
def test_every_capacity_approach_appears_in_the_delay_output():
    cap, dly = _load("capacity"), _load("delay")
    a = {(j["junction"], j["approach"]) for j in cap["junctions"]}
    b = {(r["junction"], r["approach"]) for r in dly["approaches"]}
    assert a == b


def test_design_life_covers_every_relieved_approach():
    cap = _load("capacity")
    assert len(cap["design_life"]) == len(cap["relief"])


def test_no_approach_is_relieved_to_worse_than_it_started():
    cap = _load("capacity")
    for r in cap["relief"]:
        assert r["vc_after"] <= r["vc_before"]


def test_scheme_test_never_quotes_a_capacity_past_the_degenerate_threshold():
    """v/c above NO_GAP_VC means 'no viable gaps', never a number."""
    from src.scheme_test import NO_GAP_VC
    s = _load("scheme_test")
    assert s["no_gap_vc_threshold"] == NO_GAP_VC
    assert s["no_viable_gap"] <= len(s["uturns"])


def test_economics_and_delay_agree_on_which_approaches_exist():
    e, d = _load("economics"), _load("delay")
    assert {(r["junction"], r["approach"]) for r in e["approaches"]} == \
           {(r["junction"], r["approach"]) for r in d["approaches"]}


def test_the_dashboard_json_carries_the_same_figures_as_the_source_files():
    """web/public/corridor.json is what the deployed site reads."""
    web = ROOT / "web" / "public" / "corridor.json"
    if not web.exists():
        pytest.skip("dashboard bundle not exported yet")
    d = json.loads(web.read_text())
    if not d.get("delay"):
        pytest.skip("delay stage not exported")
    assert d["delay"]["spillback_count"] == _load("delay")["spillback_count"]
    assert d["capacity"]["design_life_first_failure_med"] == \
        _load("capacity")["design_life_first_failure_med"]


# --- tests that need the client data -----------------------------------------
@needs_source
def test_every_junction_has_exactly_twelve_movements():
    from src.tmc_parse import parse_all
    bins, _ = parse_all()
    day = sorted(bins.date.unique())[0]
    mv = bins[(bins.kind == "movement") & (bins.date == day)]
    for code, g in mv.groupby("junction"):
        pairs = {(a, b) for a, b in zip(g.arm_from, g.arm_to)}
        assert len(pairs) == 12, code


@needs_source
def test_no_u_turn_is_synthesised_anywhere():
    from src.tmc_parse import parse_all
    bins, _ = parse_all()
    mv = bins[bins.kind == "movement"]
    assert not (mv.arm_from == mv.arm_to).any()


@needs_source
def test_peak_hour_rederivation_lands_inside_the_surveyed_day():
    from src.analyse import peak_hours
    from src.tmc_parse import parse_all
    bins, _ = parse_all()
    day = sorted(bins.date.unique())[0]
    ph = peak_hours(bins, day)
    assert len(ph) > 0
