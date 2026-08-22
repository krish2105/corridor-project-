"""
count.py — tracks to a classified turning movement count.

Zone-based, not line-based. A line crossing tells you a vehicle passed; it does not tell
you where the vehicle came from or where it went, and a turning movement needs both. A
track that enters through zone A and leaves through zone C is unambiguously movement A->C.

This corrects the erratum recorded against the methodology's own `build_zones`, which is
fatal as written: it builds the entry and exit zone of each leg with identical arguments,
producing the same polygon twice, and `assign_movement` then takes the FIRST zone that
contains the point. The exit zone is therefore never reached, `exits` is always empty,
every track resolves to None, and track resolution is 0% against a >90% gate.

Two cases have to be handled separately:

  divided leg   entry and exit are physically separated by the median, so the zones are
                offset to either side of the centreline and a track is assigned by which
                polygon it occupies.
  undivided leg both directions share one surface, so one polygon serves both and the
                movement is resolved by the ORDER the track passes through zones, plus
                the sign of travel along the leg axis.

Run:  uv run python src/count.py     # self-test against synthetic tracks
"""
import math
import sys
from collections import defaultdict
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Clear of the junction so queued vehicles do not oscillate in and out of the zone.
ZONE_OFFSET_M = 15.0
# Long enough that nothing can skip it between frames: at 60 km/h and 25 fps a vehicle
# moves 0.67 m per frame, so 15 m is ample.
ZONE_DEPTH_M = 15.0
MIN_DWELL_FRAMES = 3          # filters tracks that merely clip a zone corner
RESOLUTION_GATE = 0.90        # methodology acceptance gate


def leg_zone(centre, bearing_deg, offset=ZONE_OFFSET_M, depth=ZONE_DEPTH_M,
             half_width=5.0, lateral=0.0):
    """
    Rectangular zone across a leg, `offset` m from the junction, `depth` m long.

    `lateral` shifts the zone perpendicular to the leg. That is what separates the entry
    and exit zones of a divided carriageway; it is zero on an undivided leg.
    """
    th = math.radians(bearing_deg)
    ux, uy = math.sin(th), math.cos(th)         # along the leg, away from the junction
    px, py = uy, -ux                            # perpendicular
    a = (centre[0] + ux * offset, centre[1] + uy * offset)
    b = (centre[0] + ux * (offset + depth), centre[1] + uy * (offset + depth))
    poly = LineString([a, b]).buffer(half_width, cap_style=2)
    if lateral:
        poly = translate(poly, px * lateral, py * lateral)
    return poly


def build_zones(centre, legs):
    """
    One entry and one exit zone per leg.

    legs: {name: {"bearing": deg, "divided": bool, "width": m}}
    Returns {(role, leg_name): polygon}, role in {"entry", "exit"}.
    """
    zones = {}
    for name, cfg in legs.items():
        w = cfg.get("width", 10.0)
        half = w / 4.0 + 1.0 if cfg.get("divided") else w / 2.0 + 2.0
        if cfg.get("divided"):
            # opposite sides of the median. Entry is the near side to an arriving
            # vehicle; on a left-hand-drive network that is the left of the leg axis
            # looking outward from the junction.
            shift = w / 4.0
            zones[("entry", name)] = leg_zone(centre, cfg["bearing"], half_width=half,
                                              lateral=+shift)
            zones[("exit", name)] = leg_zone(centre, cfg["bearing"], half_width=half,
                                             lateral=-shift)
        else:
            shared = leg_zone(centre, cfg["bearing"], half_width=half)
            zones[("entry", name)] = shared
            zones[("exit", name)] = shared
    return zones


def _zones_containing(zones, pt):
    """ALL zones containing the point, not the first. Taking the first is the erratum."""
    p = Point(pt)
    return [k for k, poly in zones.items() if poly.contains(p)]


def assign_movement(track, zones, centre, min_dwell=MIN_DWELL_FRAMES):
    """
    track: [(frame, x, y), ...] in metres.
    Returns (from_leg, to_leg) or None.

    Resolution is by ORDER, not by zone identity: the leg whose zone the track occupied
    while moving TOWARD the junction is the entry, and the leg it occupied while moving
    AWAY is the exit. That works whether or not the legs are divided, and it is what the
    original could not do.
    """
    if len(track) < 2 * min_dwell:
        return None
    visits = []                     # (leg, mean radial velocity, dwell)
    current, run, r0 = None, 0, None
    for f, x, y in track:
        hits = _zones_containing(zones, (x, y))
        leg = hits[0][1] if hits else None
        r = math.dist((x, y), centre)
        if leg == current:
            run += 1
        else:
            if current is not None and run >= min_dwell:
                visits.append((current, r - r0, run))
            current, run, r0 = leg, 1, r
    if current is not None and run >= min_dwell:
        visits.append((current, math.dist(track[-1][1:], centre) - r0, run))

    approaching = [v for v in visits if v[0] and v[1] < 0]   # radius shrinking
    departing = [v for v in visits if v[0] and v[1] > 0]     # radius growing
    if not approaching or not departing:
        return None
    return approaching[0][0], departing[-1][0]


def aggregate(tracks, zones, centre, fps=25.0, bin_minutes=15):
    """
    tracks: {track_id: {"class": str, "pts": [(frame, x, y), ...]}}
    Returns (counts, stats). counts keyed by (bin, class, from_leg, to_leg).
    """
    counts = defaultdict(int)
    resolved = 0
    for _tid, t in tracks.items():
        od = assign_movement(t["pts"], zones, centre)
        if od is None:
            continue
        resolved += 1
        first = t["pts"][0][0]
        b = int(first / fps / 60 / bin_minutes)
        counts[(b, t["class"], od[0], od[1])] += 1
    total = len(tracks)
    # guard the division: an empty track set raised ZeroDivisionError in the original,
    # which is the one case where the diagnostic matters most
    rate = resolved / total if total else 0.0
    return counts, dict(tracks=total, resolved=resolved, resolution=rate,
                        passes_gate=rate >= RESOLUTION_GATE)


# --- synthetic tracks, to prove the assignment before any footage exists ----
def synthesise_tracks(legs, centre, per_movement=12, divided=True, noise_m=0.4, seed=5):
    """Drive vehicles through known movements and return tracks plus the truth."""
    import random
    rng = random.Random(seed)
    names = list(legs)
    tracks, truth = {}, {}
    tid = 0
    for a in names:
        for b in names:
            if a == b:
                continue
            for _ in range(per_movement):
                pts = []
                tha = math.radians(legs[a]["bearing"])
                thb = math.radians(legs[b]["bearing"])
                w = legs[a].get("width", 10.0)
                lat_in = +w / 4.0 if divided else 0.0
                lat_out = -w / 4.0 if divided else 0.0
                f = 0
                # inbound along leg a, radius shrinking
                for d in range(45, 4, -1):
                    x = centre[0] + math.sin(tha) * d + math.cos(tha) * lat_in
                    y = centre[1] + math.cos(tha) * d - math.sin(tha) * lat_in
                    pts.append((f, x + rng.gauss(0, noise_m), y + rng.gauss(0, noise_m)))
                    f += 1
                # outbound along leg b, radius growing
                for d in range(4, 46):
                    x = centre[0] + math.sin(thb) * d + math.cos(thb) * lat_out
                    y = centre[1] + math.cos(thb) * d - math.sin(thb) * lat_out
                    pts.append((f, x + rng.gauss(0, noise_m), y + rng.gauss(0, noise_m)))
                    f += 1
                tracks[tid] = dict(**{"class": "CAR_BUCKET"}, pts=pts)
                truth[tid] = (a, b)
                tid += 1
    return tracks, truth


if __name__ == "__main__":
    print("SELF-TEST - no footage exists, so zone assignment is checked against synthetic")
    print("tracks driven through KNOWN movements.\n")
    centre = (575330.0, 2971680.0)
    legs4 = {"N": dict(bearing=0, divided=True, width=14.0),
             "E": dict(bearing=90, divided=True, width=14.0),
             "S": dict(bearing=180, divided=True, width=14.0),
             "W": dict(bearing=270, divided=True, width=14.0)}

    print(f"  {'case':<26}{'tracks':>8}{'resolved':>10}{'correct':>9}{'gate >90%':>11}")
    print("  " + "-" * 64)
    ok = 0
    cases = [("4-arm divided", legs4, True, 0.4),
             ("4-arm divided, noisy", legs4, True, 1.2),
             ("4-arm undivided", legs4, False, 0.4),
             ("skewed legs", {"N": dict(bearing=10, divided=True, width=14.0),
                              "E": dict(bearing=75, divided=True, width=14.0),
                              "S": dict(bearing=195, divided=True, width=14.0),
                              "W": dict(bearing=280, divided=True, width=14.0)}, True, 0.6)]
    for label, legs, div, noise in cases:
        # copy, do not mutate: the shared legs4 dict is reused across cases and
        # rewriting `divided` in place made the final check report on the wrong config
        legs = {k: {**v, "divided": div} for k, v in legs.items()}
        zones = build_zones(centre, legs)
        tracks, truth = synthesise_tracks(legs, centre, divided=div, noise_m=noise)
        good = 0
        res = 0
        for tid, t in tracks.items():
            od = assign_movement(t["pts"], zones, centre)
            if od is None:
                continue
            res += 1
            if od == truth[tid]:
                good += 1
        rate = res / len(tracks)
        acc = good / res if res else 0
        passed = rate >= RESOLUTION_GATE and acc >= 0.95
        ok += passed
        print(f"  {label:<26}{len(tracks):>8}{rate:>9.0%}{acc:>9.0%}"
              f"{'PASS' if passed else 'FAIL':>11}")

    print(f"\n  GATE - resolution >{RESOLUTION_GATE:.0%} and assignment accuracy >95%: "
          f"**{ok} of {len(cases)}**")

    print(f"\n  The erratum, checked directly:")
    for div in (True, False):
        lg = {k: {**v, "divided": div} for k, v in legs4.items()}
        z = build_zones(centre, lg)
        same = z[("entry", "N")].equals(z[("exit", "N")])
        expect = "correct - one surface serves both" if div is False else \
                 "correct - separated across the median"
        print(f"    divided={str(div):<5} entry polygon == exit polygon: {str(same):<5}  {expect}")
    print("    The methodology's version returns True in BOTH cases. On a divided leg that")
    print("    is the fatal one: the exit zone is unreachable, so every track resolves to")
    print("    None and resolution is 0% against a >90% gate.")
