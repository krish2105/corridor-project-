"""
Tests for routes.py — the enumeration of every path through a signal-free junction.

This file exists because the same route was described in prose in two places and the two
descriptions disagreed. `analyse()` called a bay "northbound" meaning the direction its
traffic leaves in; `uturn_detour()` read the same word geographically. Both ran, both
looked reasonable, and every detour was measured to the opening on the wrong side.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.routes import (N, E, S, W, all_routes, bay_movements,
                        conflicting_direction, route, turn_of)


def test_left_is_the_next_arm_clockwise():
    """India drives on the left, so the left turn is the near-side one and crosses nothing."""
    assert turn_of(N, E) == "Left"
    assert turn_of(E, S) == "Left"
    assert turn_of(S, W) == "Left"
    assert turn_of(W, N) == "Left"


def test_right_crosses_the_opposing_stream():
    assert turn_of(N, W) == "Right"
    assert turn_of(S, E) == "Right"


def test_twelve_movements_and_no_uturn_among_them():
    rs = all_routes()
    assert len(rs) == 12
    assert not [r for r in rs if r["turn"] == "U-turn"]


def test_six_survive_and_six_are_rerouted():
    rs = all_routes()
    assert len([r for r in rs if r["permitted"] == "direct"]) == 6
    assert len([r for r in rs if r["permitted"] == "re-routed"]) == 6


def test_every_left_turn_and_the_corridor_through_are_untouched():
    """The scheme bans what crosses opposing traffic. These do not."""
    for f, t in ((N, E), (E, S), (S, W), (W, N), (N, S), (S, N)):
        assert route(f, t)["permitted"] == "direct", (f, t)


def test_a_corridor_right_turn_overshoots_and_uses_the_far_bay():
    """
    N->W keeps heading south past the exit it wants, turns at the bay SOUTH of the
    junction, and comes back northbound to take the left.
    """
    r = route(N, W)
    assert r["permitted"] == "re-routed"
    assert r["bay"] == "south"
    assert r["rejoins"] == "northbound"
    assert "overshooting" in r["legs"][0]


def test_a_cross_street_movement_can_only_leave_by_turning_left():
    """
    E->N wants north. Its only legal exit is a left turn, which puts it SOUTHbound, so it
    turns at the south bay and comes back through. Getting this backwards is the whole
    reason the file exists.
    """
    r = route(E, N)
    assert r["bay"] == "south"
    assert "southbound" in r["legs"][0]
    assert r["rejoins"] == "northbound"


def test_the_two_bays_partition_the_rerouted_movements():
    """A movement on neither bay is uncosted; one on both is double-counted."""
    south, north = bay_movements("south"), bay_movements("north")
    assert len(south) == len(north) == 3
    keys = [(r["from_arm"], r["to_arm"]) for r in south + north]
    assert len(set(keys)) == 6


def test_a_bay_crosses_the_stream_it_rejoins():
    """
    A driver leaving the SOUTH bay rejoins northbound, so the flow they must cross is the
    northbound through movement. Stating it the other way round still runs.
    """
    assert conflicting_direction("south") == "northbound"
    assert conflicting_direction("north") == "southbound"
    for r in bay_movements("south"):
        assert r["rejoins"] == "northbound"
    for r in bay_movements("north"):
        assert r["rejoins"] == "southbound"


def test_every_rerouted_movement_takes_four_legs():
    """One manoeuvre becomes four. That count is the finding, so it is asserted."""
    for r in all_routes():
        if r["permitted"] == "re-routed":
            assert len(r["legs"]) == 4, r


def test_a_rerouted_movement_ends_at_the_arm_it_wanted():
    """The re-route must actually deliver the driver where they were going."""
    for r in all_routes():
        if r["permitted"] == "re-routed":
            assert r["to_arm"] in r["legs"][-1], r
