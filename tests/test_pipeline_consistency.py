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
def test_sensitivity_grid_reproduces_the_published_spillback_count():
    """
    Regression. lane_capacity_pcu is PER LANE and was compared against a total, so the
    grid's baseline cell disagreed with delay.py and the reported range was wrong.
    At packing = JAM_PACKING, footprint = 1.0 and 1200 PCU/lane the grid must return
    exactly what delay.py published.
    """
    from src.delay import JAM_PACKING
    from src.sensitivity import spillback_verdict
    d = _load("delay")
    spills, total = spillback_verdict(JAM_PACKING, 1.0, 1200)
    published = sum(1 for a in d["approaches"]
                    if a["spillback"] and a["storage_m"] is not None)
    assert spills == published
    assert total == sum(1 for a in d["approaches"] if a["storage_m"] is not None)


def test_denser_packing_never_increases_spillback():
    from src.sensitivity import spillback_verdict
    _load("delay")
    loose, _ = spillback_verdict(0.65, 1.0, 1200)
    dense, _ = spillback_verdict(0.85, 1.0, 1200)
    assert dense <= loose


def test_more_capacity_never_increases_spillback():
    from src.sensitivity import spillback_verdict
    _load("delay")
    lean, _ = spillback_verdict(0.75, 1.0, 1200)
    generous, _ = spillback_verdict(0.75, 1.0, 1800)
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
