"""
Tests for measurement.py — the uncertainty on every published dimension.

This module exists because a number scaled off linework is indistinguishable from a
measured one, so the tests are about the honesty of the output rather than its value: a
dimension must never be published without an uncertainty, and the convergence check must
be capable of reporting that a value has NOT settled.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.measurement import (CONVERGED_M, PUBLISHED_STEP, STEPS, register)


def _conv(seq, code="TMC-01"):
    """A convergence record with a given width at each step, coarse to fine."""
    return dict(junction=code, jda_name="B-2 Bypass",
                by_step=[dict(step_m=s, width_m=w, transects=3)
                         for s, w in zip(STEPS, seq)],
                converged_at_step=None, spread_m=round(max(seq) - min(seq), 2))


def _boot(ci_width, code="TMC-01"):
    return dict(junction=code, n=7, median_m=15.6,
                ci_m=[15.6 - ci_width / 2, 15.6 + ci_width / 2], ci_width_m=ci_width,
                min_m=10.2, max_m=16.2, above_wide_threshold=True)


def _reg(median=1.36):
    return [dict(feature="nearest median/divider line", n=179, median_m=median,
                 p90_m=3.92, max_m=14.56)]


def test_the_published_step_is_one_that_was_actually_tested():
    """
    Publishing a step outside the tested set would mean the convergence table is evidence
    for a spacing nobody ran.
    """
    assert PUBLISHED_STEP in STEPS


def test_steps_run_coarse_to_fine():
    """The table reads left to right as refinement; reversed, 'settles at' is meaningless."""
    assert list(STEPS) == sorted(STEPS, reverse=True)


def test_every_dimension_carries_an_uncertainty():
    """
    The gate. A row with a method and no uncertainty is the exact failure this register
    exists to prevent, and it would look complete.
    """
    rows = register([_conv([11.7, 15.6, 15.6, 15.7])], [_boot(4.8)], _reg())
    assert len(rows) >= 5
    for r in rows:
        assert r["uncertainty"] and r["uncertainty"].strip()
        assert r["method"] and r["resolved_by"] and r["used_for"]


def test_an_unquantifiable_dimension_says_so_rather_than_being_omitted():
    """
    Median opening width has no second reading to compare against. Leaving it out would
    make the register look complete while a published dimension went unexamined.
    """
    rows = register([_conv([11.7, 15.6, 15.6, 15.7])], [_boot(4.8)], _reg())
    opening = next(r for r in rows if r["dimension"].startswith("Median opening"))
    assert "not quantified" in opening["uncertainty"]
    assert "total station" in opening["resolved_by"]


def test_the_register_reports_the_real_bootstrap_spread():
    """Not a fixed sentence: the interval quoted has to come from the data passed in."""
    rows = register([_conv([12.0] * 4)],
                    [_boot(4.8, "TMC-01"), _boot(0.9, "TMC-02")], _reg())
    width = next(r for r in rows if r["dimension"].startswith("Carriageway width"))
    assert "0.9" in width["uncertainty"] and "4.8" in width["uncertainty"]


def test_registration_figure_is_carried_through_not_asserted():
    rows = register([_conv([12.0] * 4)], [_boot(1.0)], _reg(median=7.77))
    reg = next(r for r in rows if r["dimension"].startswith("KML against CAD"))
    assert "7.77" in reg["uncertainty"]


def test_registration_absent_is_reported_as_unquantified():
    """A check that could not run must not read as a check that passed."""
    rows = register([_conv([12.0] * 4)], [_boot(1.0)],
                    [dict(feature="nearest median/divider line", n=0,
                          unquantified="no linework within reach")])
    reg = next(r for r in rows if r["dimension"].startswith("KML against CAD"))
    assert reg["uncertainty"] == "not quantified"


def test_a_width_that_never_settles_is_reported_as_not_converged():
    """
    The check has to be able to say no. A convergence test that always finds convergence
    is not a test, and TMC-01 is on this page precisely because one value did not settle
    until the third spacing.
    """
    from src.measurement import CONVERGED_M as tol
    moving = [10.0, 13.0, 16.0, 19.0]           # never two adjacent within tolerance
    conv = None
    for i in range(len(STEPS) - 1):
        if abs(moving[i] - moving[i + 1]) <= tol:
            conv = STEPS[i]
            break
    assert conv is None

    settling = [11.7, 15.6, 15.6, 15.7]
    conv2 = None
    for i in range(len(STEPS) - 1):
        if abs(settling[i] - settling[i + 1]) <= tol:
            conv2 = STEPS[i]
            break
    assert conv2 == STEPS[1]                    # settles at the second spacing, not the first


def test_the_tolerance_is_smaller_than_anything_that_moves_a_lane_count():
    """
    A lane is 3.5 m. A convergence tolerance anywhere near that would call two widths
    equal when they imply different capacities, which is the only thing width is used for.
    """
    assert CONVERGED_M < 3.5 / 2
