"""
Tests for the three learned applications: anomaly, cluster, forecast.

Each of these can fail silently in the same way - by producing a confident output from a
broken statistic - so the tests are written against inputs whose answer is known. The
regression tests matter most: two of the three detectors here shipped a defect on their
first run (a spike detector that measured the morning ramp, a digit score that gave every
junction the maximum because it scored significance instead of effect), and both are
pinned below.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.anomaly import (SPIKE_MIN_VEH, composition_shift, duplicate_day, flatline_run,
                         profile_spike, screen, terminal_digit)
from src.cluster import (SILHOUETTE_MIN, class_split, external_label_test, fit,
                         silhouette)
from src.forecast import approach_hours, evaluate, loo, mape, targets

DAY2 = pd.Timestamp("2026-05-12").date()


def _second_day(bins, jitter=None):
    """A second survey day: an exact copy unless `jitter` adds to it."""
    d2 = bins.copy()
    d2["date"] = DAY2
    d2["bin_start"] = d2.bin_start + pd.Timedelta(days=1)
    if jitter is not None:
        d2["count"] = d2["count"] + jitter(len(d2))
    return pd.concat([bins, d2], ignore_index=True)


# --- anomaly: duplicate day --------------------------------------------------

def test_duplicate_day_finds_a_wholesale_copy(synth_bins):
    t = duplicate_day(_second_day(synth_bins))
    assert len(t) > 0
    assert (t.share == 1.0).all()


def test_duplicate_day_clears_an_independent_second_day(synth_bins):
    rng = np.random.default_rng(0)
    t = duplicate_day(_second_day(synth_bins, lambda n: rng.integers(1, 20, n)))
    assert (t.share == 0.0).all()


def test_duplicate_day_is_silent_on_a_single_day(synth_bins):
    assert len(duplicate_day(synth_bins)) == 0


# --- anomaly: terminal digit -------------------------------------------------

def _counts_frame(values):
    n = len(values)
    return pd.DataFrame(dict(
        junction="TMC-01", kind="movement", sheet="V_1", veh_class="CAR_BUCKET",
        date=pd.Timestamp("2026-05-11").date(),
        bin_label=[f"b{i}" for i in range(n)], count=np.asarray(values, dtype=float)))


def test_terminal_digit_clears_an_unrounded_count():
    rng = np.random.default_rng(1)
    t = terminal_digit(_counts_frame(rng.integers(20, 400, 4000)))
    assert t.p.iloc[0] > 0.01
    assert abs(t.excess_0_5_pct.iloc[0]) < 3


def test_terminal_digit_catches_rounding_to_0_and_5():
    rng = np.random.default_rng(2)
    v = rng.integers(20, 400, 4000)
    v[:1500] = (v[:1500] // 5) * 5            # a tally sheet rounded by hand
    t = terminal_digit(_counts_frame(v))
    assert t.p.iloc[0] < 1e-6
    assert t.excess_0_5_pct.iloc[0] > 10


# --- anomaly: flatline -------------------------------------------------------

def _series_frame(values, veh_class="CAR_BUCKET"):
    n = len(values)
    start = pd.Timestamp("2026-05-11 08:00")
    return pd.DataFrame(dict(
        junction="TMC-01", kind="movement", sheet="V_1", veh_class=veh_class,
        date=start.date(),
        bin_start=[start + pd.Timedelta(minutes=15 * i) for i in range(n)],
        bin_label=[f"{i:04d}" for i in range(n)],
        arm_from="Mansarover Metro", arm_to="Patrika Gate", movement="Left",
        count=np.asarray(values, dtype=float), stored_pcu=0.0))


def test_flatline_reports_the_repeated_value_not_the_first():
    """
    Regression. The first version reported v[0] because `np.argmax(v == v)` is always 0,
    so every finding named the wrong number and a reviewer chasing it would find a
    perfectly ordinary count at the start of the day.
    """
    rng = np.random.default_rng(8)
    v = rng.integers(50, 150, 96).astype(float)
    v[0] = 999.0                              # a distinctive first bin
    v[40:50] = 77.0                           # the actual run
    t = flatline_run(_series_frame(v))
    assert len(t) == 1
    assert t.value.iloc[0] == 77.0
    assert t.run_bins.iloc[0] == 10


def test_flatline_is_silent_on_a_varying_series():
    rng = np.random.default_rng(9)
    assert flatline_run(_series_frame(rng.integers(50, 5000, 96).astype(float))).empty


# --- anomaly: profile spike --------------------------------------------------

def test_profile_spike_is_blind_to_a_straight_ramp():
    """
    Regression, and the reason the detector was rewritten.

    The first version took the residual from a centred rolling median, which lags a ramp,
    so the whole two-hour morning climb registered as anomalous: 110 bins per thousand.
    The second difference is exactly zero on any straight line, whatever its slope. The
    ramp carries noise here because a noiseless one has no scale to test against at all.
    """
    rng = np.random.default_rng(10)
    v = np.arange(96) * 20.0 + rng.normal(0, 3, 96)
    t = profile_spike(_series_frame(v))
    assert t.n_spikes.iloc[0] == 0


def test_profile_spike_finds_an_injected_spike():
    rng = np.random.default_rng(11)
    v = 200.0 + rng.normal(0, 5, 96)
    v[47] += 10 * SPIKE_MIN_VEH
    t = profile_spike(_series_frame(v))
    assert t.n_spikes.iloc[0] == 1


def test_profile_spike_ignores_a_statistically_large_but_tiny_departure():
    """A four-vehicle wobble in a slow class is not something to send a reviewer after."""
    v = np.tile([3.0, 4.0], 48)
    v[47] = 4.0 + 4                           # second difference of 5, well under the floor
    t = profile_spike(_series_frame(v))
    assert t.empty or t.n_spikes.iloc[0] == 0


# --- anomaly: composition ----------------------------------------------------

def test_composition_shift_catches_a_transposed_column(synth_bins):
    """
    A column swapped during data entry moves vehicles between classes without changing
    the interval total, so no conservation check can see it. The share vector can.
    """
    b = synth_bins.copy()
    j = b.junction.iloc[0]
    labels = sorted(b.bin_label.unique())[20:24]
    hit = (b.junction == j) & b.bin_label.isin(labels)
    a, c = b.veh_class == "CAR_BUCKET", b.veh_class == "TWO_W"
    ca = b.loc[hit & a, "count"].to_numpy()
    b.loc[hit & a, "count"] = b.loc[hit & c, "count"].to_numpy() * 40
    b.loc[hit & c, "count"] = ca
    t = composition_shift(b)
    assert len(t) == 1 and t.junction.iloc[0] == j


# --- anomaly: scoring --------------------------------------------------------

def test_scores_are_bounded_and_never_negative(synth_bins):
    """
    Regression. Scoring a junction whose 0s and 5s are UNDER-represented on the raw
    excess produced a negative contribution, which credited it for rounding less than
    nothing. Every detector must land in [0, 1] and the total in [0, 6].
    """
    _, sc = screen(_second_day(synth_bins), None)
    parts = [c for c in sc.columns if c.startswith("s_")]
    assert len(parts) == 6
    for c in parts:
        assert sc[c].between(0, 1).all(), (c, sc[c].tolist())
    assert sc.integrity_flag_score.between(0, 6).all()


def test_screen_survives_an_absent_mismatch_register(synth_bins):
    """The register is a separate artefact and may not be there. That is not a crash."""
    findings, sc = screen(synth_bins, None)
    assert (sc.s_arith == 0).all()
    assert findings["arithmetic"].empty


# --- cluster: silhouette -----------------------------------------------------

def _dist(x):
    from scipy.spatial.distance import squareform, pdist
    return squareform(pdist(x))


def test_silhouette_separates_two_tight_groups():
    x = np.array([[0, 0], [0, .01], [.01, 0], [10, 10], [10, 10.01], [10.01, 10]])
    s = silhouette(_dist(x), [1, 1, 1, 2, 2, 2])
    assert s > 0.9


def test_silhouette_reports_a_blob_as_a_blob():
    rng = np.random.default_rng(3)
    x = rng.normal(size=(40, 2))
    s = silhouette(_dist(x), rng.integers(1, 4, 40))
    assert s < SILHOUETTE_MIN


def test_silhouette_of_one_cluster_is_zero():
    assert silhouette(_dist(np.random.default_rng(4).normal(size=(6, 2))), [1] * 6) == 0.0


def test_fit_is_deterministic():
    """
    Ward linkage, not k-means, precisely so this holds: a typology that moves when it is
    re-run is not a finding.
    """
    rng = np.random.default_rng(5)
    p = pd.DataFrame(rng.normal(size=(24, 8)))
    a, b = fit(p), fit(p)
    assert list(a[0]) == list(b[0]) and a[1:] == b[1:]


# --- cluster: the held-out label ---------------------------------------------

def _indexed(x, arms):
    return pd.DataFrame(x, index=pd.MultiIndex.from_tuples(
        [(f"TMC-0{i % 6 + 1}", a) for i, a in enumerate(arms)],
        names=["junction", "arm_from"]))


def test_external_label_test_recovers_a_label_the_clusters_match():
    arms = ["Mansarover Metro"] * 6 + ["Cross"] * 6
    p = _indexed(np.zeros((12, 2)), arms)
    labels = np.array([1] * 6 + [2] * 6)
    purity, pval, _ = external_label_test(p, labels, np.random.default_rng(6))
    assert purity == 1.0 and pval < 0.05


def test_external_label_test_rejects_a_split_that_matches_nothing():
    arms = ["Mansarover Metro", "Cross"] * 6
    p = _indexed(np.zeros((12, 2)), arms)
    labels = np.array([1] * 6 + [2] * 6)      # cuts straight across the label
    purity, pval, null_mean = external_label_test(p, labels, np.random.default_rng(7))
    assert purity == pytest.approx(0.5)
    assert pval > 0.05


def test_class_split_reports_size_and_range_not_only_significance():
    arms = ["Mansarover Metro"] * 12 + ["Cross"] * 12
    comp = _indexed(np.zeros((24, 1)), arms)
    comp.columns = ["TWO_W"]
    comp["TWO_W"] = [0.40] * 12 + [0.60] * 12
    s = class_split(comp, "TWO_W")
    assert s["corridor_mean"] == 0.40 and s["cross_mean"] == 0.60
    assert s["min_share"] == 0.40 and s["max_share"] == 0.60
    assert s["p"] < 0.01


# --- forecast ----------------------------------------------------------------

def test_loo_never_uses_the_held_out_point():
    """
    The whole validity of the reported error rests on this. If the held-out approach
    contributes to its own factor, the MAPE is measuring the fit, not the prediction.
    """
    partial = pd.Series([10.0, 10.0, 10.0, 10.0])
    honest = pd.Series([20.0, 20.0, 20.0, 20.0])
    rogue = honest.copy()
    rogue.iloc[0] = 900.0                     # an approach unlike any other
    assert loo(partial, honest)[0] == loo(partial, rogue)[0]


def test_mape_is_zero_on_an_exact_prediction():
    a = np.array([1.0, 2.0, 3.0])
    assert mape(a, a) == 0.0


def test_a_corridor_of_identical_shapes_predicts_itself(synth_bins):
    """
    The fixture gives every approach the same flat profile at a different volume, which is
    exactly the case a ratio estimator should nail. If it cannot, the estimator is wrong.
    """
    h = approach_hours(synth_bins)
    h = h.mul(np.linspace(1, 4, len(h)), axis=0)   # same shape, different volumes
    res = evaluate(h, targets(h))
    assert (res.mape < 1e-6).all()


def test_every_window_is_compared_against_the_no_model_baseline(synth_bins):
    h = approach_hours(synth_bins)
    res = evaluate(h, targets(h))
    assert {"mape", "baseline_mape", "worst_approach_pct"} <= set(res.columns)
    assert res.baseline_mape.notna().all()
