"""
routes.py — every path a vehicle can take through a signal-free junction, enumerated.

WHY THIS EXISTS
The scheme test had the right demand on the wrong bay. `analyse()` used "northbound bay"
to mean the bay serving traffic that LEAVES northbound - which sits south of the junction,
because the driver has to overshoot before turning round. `uturn_detour()` read the same
word geographically and looked for an opening NORTH of the junction. Both were internally
consistent, the numbers looked reasonable, and every detour was measured to the opening on
the wrong side of the road.

That is what happens when a route is described in prose in one function and re-derived from
the prose in another. So the routes are enumerated once, here, as data: which of the twelve
movements survive the scheme, which are re-routed, what the re-routed ones actually do leg
by leg, and which side of the junction each U-turn bay is on. Everything downstream reads
this rather than re-deriving it.

THE GEOMETRY, STATED ONCE
Arms run clockwise from north: N=0, E=1, S=2, W=3. India drives on the LEFT, so a left turn
is the next arm CLOCKWISE from the approach and crosses nothing. The corridor is N-S; E and
W are the cross streets.

Under a full median U-turn scheme the junction permits left-in, left-out, and the corridor
through movement. Nothing crosses the opposing stream at the junction. Six of the twelve
movements survive untouched. The other six are re-routed through a median opening:

  N->W  corridor right   overshoot south, turn at the SOUTH bay, return north, turn left
  S->E  corridor right   overshoot north, turn at the NORTH bay, return south, turn left
  E->N  cross right      left onto southbound, turn at the SOUTH bay, straight on north
  W->S  cross right      left onto northbound, turn at the NORTH bay, straight on south
  E->W  cross through    left onto southbound, turn at the SOUTH bay, return, turn left
  W->E  cross through    left onto northbound, turn at the NORTH bay, return, turn left

So the SOUTH bay carries N->W, E->N and E->W, and every one of them rejoins the corridor
NORTHBOUND - which is why the flow it has to cross is the northbound through movement. The
NORTH bay is the mirror. Bays are named by the side of the junction they sit on, because
that is the unambiguous fact; the direction a driver leaves in is recorded separately.

Run:  uv run python src/routes.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import OUT_DATA

N, E, S, W = 0, 1, 2, 3
ARM_NAME = {N: "north", E: "east", S: "south", W: "west"}

# Which arms are the corridor. Everything else about the scheme follows from this.
CORRIDOR_ARMS = (N, S)


def turn_of(frm, to):
    """LEFT / THROUGH / RIGHT / U-TURN from the arm indices, under left-hand traffic."""
    off = (to - frm) % 4
    return {0: "U-turn", 1: "Left", 2: "Straight", 3: "Right"}[off]


def route(frm, to):
    """
    What a vehicle making this movement actually does once the signals are gone.

    Returns the movement, whether it survives, the bay side it needs, the direction it
    rejoins the corridor in, and the legs in order. Derived from the arm indices - there
    is no per-junction special case, because there is no per-junction geometry: all six
    are four-arm crossings of one corridor.
    """
    turn = turn_of(frm, to)
    base = dict(from_arm=ARM_NAME[frm], to_arm=ARM_NAME[to], turn=turn)

    if turn == "U-turn":
        return dict(base, permitted="not surveyed", bay=None, rejoins=None,
                    legs=["no U-turn was counted anywhere in this survey"])

    # Left turns are the near-side manoeuvre and cross nothing, so they are unaffected.
    if turn == "Left":
        return dict(base, permitted="direct", bay=None, rejoins=None,
                    legs=[f"left out of the {ARM_NAME[frm]} arm into the "
                          f"{ARM_NAME[to]} arm"])

    # The corridor through movement is the thing the scheme exists to speed up.
    if turn == "Straight" and frm in CORRIDOR_ARMS:
        return dict(base, permitted="direct", bay=None, rejoins=None,
                    legs=[f"straight through, {ARM_NAME[frm]} to {ARM_NAME[to]}"])

    # Everything left over crosses the opposing stream at the junction, so the scheme
    # bans it and sends the driver to a median opening instead.
    #
    # Which opening depends on the direction the driver is travelling when they leave the
    # junction, and that is NOT the direction they wanted to go:
    #   a corridor right turn overshoots, so it keeps its own heading
    #   a cross-street movement can only turn LEFT out of its arm, so it takes whatever
    #   heading that left turn gives it
    if frm in CORRIDOR_ARMS:                       # corridor right turn: N->W or S->E
        heading = S if frm == N else N             # keeps going the way it was going
        first = (f"straight through the junction, overshooting the {ARM_NAME[to]} arm "
                 f"it wants")
    else:                                          # cross street: right turn or through
        heading = (frm + 1) % 4                    # its only legal exit is a left turn
        first = (f"left out of the {ARM_NAME[frm]} arm onto the corridor, "
                 f"{ARM_NAME[heading]}bound")

    # The bay sits DOWNSTREAM of the junction in the direction of travel, and the driver
    # leaves it heading back the other way.
    bay_side = ARM_NAME[heading]
    rejoins = ARM_NAME[N if heading == S else S] + "bound"

    legs = [first,
            f"U-turn at the median opening {bay_side} of the junction",
            f"back {rejoins} to the junction"]
    # Having turned round, either they carry straight on through, or they take the left
    # that is now available to them.
    if to in CORRIDOR_ARMS:
        legs.append(f"straight through, exiting the {ARM_NAME[to]} arm")
    else:
        legs.append(f"left into the {ARM_NAME[to]} arm")

    return dict(base, permitted="re-routed", bay=bay_side, rejoins=rejoins, legs=legs)


def all_routes():
    """All twelve surveyed movements, in survey order."""
    return [route(f, t) for f in (N, E, S, W) for t in (N, E, S, W) if f != t]


def bay_movements(side):
    """Which movements a bay on this side of the junction has to serve."""
    return [r for r in all_routes() if r["bay"] == side]


def conflicting_direction(side):
    """
    The through movement a bay's traffic has to cross.

    A driver leaving the SOUTH bay is rejoining northbound, so what they must cross is the
    northbound through stream. Derived rather than stated, because getting this backwards
    is invisible: the arithmetic still runs and the answer is merely wrong.
    """
    return "northbound" if side == "south" else "southbound"


def _main():
    rs = all_routes()
    direct = [r for r in rs if r["permitted"] == "direct"]
    rerouted = [r for r in rs if r["permitted"] == "re-routed"]

    print("=== Every movement through a signal-free junction ===")
    print("  Four arms clockwise from north, India drives on the LEFT, corridor is N-S.")
    print(f"  {len(rs)} movements surveyed. {len(direct)} survive the scheme, "
          f"{len(rerouted)} are re-routed.\n")

    print(f"  {'movement':<16}{'turn':<10}{'under the scheme':<14}{'bay':<8}rejoins")
    print("  " + "-" * 68)
    for r in rs:
        print(f"  {r['from_arm']+' -> '+r['to_arm']:<16}{r['turn']:<10}"
              f"{r['permitted']:<14}{str(r['bay'] or '-'):<8}{r['rejoins'] or '-'}")

    print("\n=== What a re-routed driver actually does ===")
    for r in rerouted:
        print(f"\n  {r['from_arm']} -> {r['to_arm']}  ({r['turn'].lower()} turn, "
              f"{r['bay']} bay)")
        for i, leg in enumerate(r["legs"], 1):
            print(f"    {i}. {leg}")

    print("\n=== Which bay carries what ===")
    for side in ("south", "north"):
        mv = bay_movements(side)
        print(f"\n  The {side.upper()} bay serves {len(mv)} movements, and every one of "
              f"them rejoins {conflicting_direction(side)}:")
        for r in mv:
            print(f"    {r['from_arm']} -> {r['to_arm']:<6} ({r['turn'].lower()})")
        print(f"    so the flow it must cross is the {conflicting_direction(side)} "
              f"through movement.")

    # GATE - the two bays must partition the re-routed movements exactly. A movement on
    # neither bay is one nobody has costed; a movement on both is double-counted.
    south, north = bay_movements("south"), bay_movements("north")
    covered = len(south) + len(north)
    print(f"\n  GATE - re-routed movements assigned to exactly one bay: "
          f"**{covered} of {len(rerouted)}**")
    if covered != len(rerouted) or len(south) != len(north):
        raise SystemExit("bay assignment does not partition the re-routed movements")

    print("\n  The naming matters and it is the reason this file exists. A bay SOUTH of")
    print("  the junction serves traffic that leaves NORTHBOUND. Calling it the")
    print("  'northbound bay' is defensible and it is also how the detour search ended")
    print("  up looking for an opening on the wrong side of the road.")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "routes.json").write_text(json.dumps(dict(
        geometry="four arms clockwise from north; left-hand traffic; corridor is N-S",
        scheme="full median U-turn: left-in, left-out, corridor through only",
        movements=rs,
        n_direct=len(direct), n_rerouted=len(rerouted),
        bays={side: dict(side=side,
                         rejoins=conflicting_direction(side),
                         serves=[f"{r['from_arm']} -> {r['to_arm']}"
                                 for r in bay_movements(side)])
              for side in ("south", "north")},
        naming_note=("a bay is named by the side of the junction it sits on. The driver "
                     "leaves it travelling the other way, which is why the flow it "
                     "crosses is the opposite through movement"),
    ), indent=1))
    print(f"\nwritten: {OUT_DATA/'routes.json'}")


if __name__ == "__main__":
    _main()
