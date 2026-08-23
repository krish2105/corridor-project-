"""
Tests for the conflict analysis and the new exhibits.

The conflict construction is validated against a figure every text on four-leg
intersections reports: 32 points, 16 crossing, 8 merging, 8 diverging. That check earned
its place immediately — the first version counted every PAIR sharing an entry as a
diverging point and returned 40. A three-way split happens at two points, not three.
"""
import pytest

from src.exhibits import continuity, flow_raster, tornado, volume_flow
from src.safety import conflict_points, exposure, movements_of, scheme_conflicts


# --- the construction must reproduce the known answer ------------------------
def test_a_four_arm_junction_has_thirty_two_conflict_points():
    pts = conflict_points(movements_of(4))
    kinds = {k: sum(1 for p in pts if p["kind"] == k)
             for k in ("crossing", "merging", "diverging")}
    assert kinds == {"crossing": 16, "merging": 8, "diverging": 8}
    assert len(pts) == 32


def test_splits_are_counted_as_points_not_pairs():
    """
    Regression. Three movements leaving one arm separate at two points, not three.
    Counting pairs gave C(3,2)=3 per arm and a 40-point total.
    """
    pts = conflict_points(movements_of(4))
    div = [p for p in pts if p["kind"] == "diverging"]
    assert len(div) == 8                      # 2 splits x 4 arms
    per_arm = {}
    for p in div:
        per_arm[p["arm"]] = per_arm.get(p["arm"], 0) + 1
    assert set(per_arm.values()) == {2}


def test_removing_the_right_turn_removes_conflict_points():
    full = conflict_points(movements_of(4))
    kept = [m for m in movements_of(4) if (m[1] - m[0]) % 4 != 3]
    fewer = conflict_points(kept, 4)
    assert len(fewer) < len(full)


def test_exposure_weights_by_the_product_of_the_conflicting_flows():
    pts = conflict_points(movements_of(4))
    small = exposure(pts, {m: 10.0 for m in movements_of(4)})
    large = exposure(pts, {m: 20.0 for m in movements_of(4)})
    # doubling every flow quadruples a product-weighted exposure
    assert large["crossing"] == pytest.approx(4 * small["crossing"])


def test_no_flow_means_no_exposure():
    pts = conflict_points(movements_of(4))
    assert all(v == 0 for v in exposure(pts, {}).values())


def test_the_scheme_moves_right_turn_conflicts_to_the_uturn():
    flows = {m: 100.0 for m in movements_of(4)}
    s = scheme_conflicts(flows)
    assert len(s["uturn"]) == 4                       # one per approach
    assert all(p["where"] == "mid-block U-turn opening" for p in s["uturn"])
    assert s["uturn_exposure"]["crossing"] > 0
    assert s["total_exposure"]["crossing"] >= s["junction_exposure"]["crossing"]


# --- exhibits ----------------------------------------------------------------
def test_volume_flow_gives_twelve_movements_per_junction(synth_bins, synth_day):
    vf = volume_flow(synth_bins, synth_day)
    assert len(vf) == 2
    for j in vf:
        assert len(j["movements"]) == 12
        assert len(j["arms"]) == 4


def test_volume_flow_labels_turns_by_clockwise_offset(synth_bins, synth_day):
    """Left is the next arm clockwise, because India drives on the left."""
    j = volume_flow(synth_bins, synth_day)[0]
    for m in j["movements"]:
        off = (m["to_i"] - m["from_i"]) % 4
        assert m["turn"] == {1: "Left", 2: "Straight", 3: "Right"}[off]


def test_no_movement_is_labelled_a_uturn(synth_bins, synth_day):
    for j in volume_flow(synth_bins, synth_day):
        assert all(m["turn"] != "U-turn" for m in j["movements"])


def test_tornado_reports_both_directions(synth_bins, synth_day):
    """
    Two-wheelers are understated and the heavy buckets overstated. Reporting only the
    favourable half would repeat the error the survey made.
    """
    t = tornado(synth_bins, synth_day)
    assert t["base_pcu"] > 0
    tw = next(r for r in t["classes"] if r["veh_class"] == "TWO_W")
    assert tw["swing_low_pct"] > 0                      # 0.50 surveyed vs 0.75 IRC
    assert any(r["swing_high_pct"] < 0 for r in t["classes"])


def test_tornado_is_sorted_by_magnitude(synth_bins, synth_day):
    mags = [r["magnitude"] for r in tornado(synth_bins, synth_day)["classes"]]
    assert mags == sorted(mags, reverse=True)


def test_composite_classes_report_a_band_not_a_point(synth_bins, synth_day):
    t = tornado(synth_bins, synth_day)
    car = next(r for r in t["classes"] if r["veh_class"] == "CAR_BUCKET")
    assert not car["exact"]
    assert car["irc_low"] != car["irc_high"]


def test_continuity_publishes_the_residual(synth_bins, synth_day):
    c = continuity(synth_bins, synth_day, ["TMC-01", "TMC-02"])
    assert len(c) == 1
    assert "mean_residual_pct" in c[0] and "series" in c[0]
    assert len(c[0]["series"]) > 0


def test_flow_raster_covers_every_link_and_bin(synth_bins, synth_day):
    r = flow_raster(synth_bins, synth_day, ["TMC-01", "TMC-02"])
    assert {c["link"] for c in r} == {0, 1}
    assert len({c["t"] for c in r}) == 96
