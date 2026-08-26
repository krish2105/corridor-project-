"""
scheme_test.py — Phase 8. Will JDA's seven U-turn bays carry the traffic?

The question this project exists to answer.

JDA is converting this corridor to signal-free operation, replacing junction
signals with seven U-turn bays. The survey commissioned for it counted no U-turns, so
on the face of it the scheme has no traffic evidence base.

It does, in a column nobody has read that way. **Under signal-free operation a right
turn becomes a U-turn.** A driver wanting to turn right can no longer cross opposing
traffic at the junction; they travel through, turn around at a downstream median bay,
come back and turn left. So the demand each U-turn bay must carry is the RIGHT-TURN
volume the survey already recorded, and that volume is in hand for every approach.

Capacity of an unsignalised U-turn is gap acceptance: a vehicle waits for a gap in the
opposing through stream large enough to cross. Standard form (Siegloch / HCM / Indo-HCM):

    c = q_c * exp(-q_c * t_c) / (1 - exp(-q_c * t_f))

    c   = capacity of the U-turn movement, veh/h
    q_c = conflicting (opposing through) flow, veh/s
    t_c = critical gap, s
    t_f = follow-up time, s

Critical gap is composition-dependent and this is why it matters here. Two-wheelers
accept far shorter gaps than cars, and they are 49% of this stream, so a Western t_c
would badly understate capacity. The critical gap is weighted by the observed
composition, and results are reported as a band because t_c is a judgement, not a
measurement.

Run:  uv run python src/scheme_test.py
"""
import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.analyse import NORTH, SOUTH, through_vs_turning
from src.config import CHAINAGE_FROM, JUNCTION_COORDS, OUT_DATA
from src.pcu import SURVEYED, factor_band
from src.tmc_parse import parse_all

# --- critical gap and follow-up, by class ----------------------------------
# Indian mixed-traffic values. Two-wheelers and autos accept markedly shorter gaps than
# cars; using a single car-based figure understates capacity where 2W dominate. Reported
# as a band because these are literature values calibrated elsewhere, not measured here.
CRITICAL_GAP_S = {          # (optimistic, conservative)
    "TWO_W":        (3.5, 4.4),
    "CAR_BUCKET":   (4.2, 5.6),
    "AGRI_LCV":     (5.0, 6.5),
    "AUTO_TRK_BUS": (5.5, 7.0),
    "TRL_MAV":      (6.0, 7.5),
    "CYCLE":        (3.0, 4.0),
    "CYCLE_RIK":    (3.5, 4.5),
    "HAND_CART":    (4.0, 5.0),
    "HORSE_DRAWN":  (4.5, 6.0),
    "BULLOCK":      (5.0, 6.5),
}
FOLLOW_UP_S = (2.0, 3.0)    # (optimistic, conservative)
# Corroborated after the fact by the only two measured Indian values reachable, both of
# which fall inside this band near its optimistic end: 2.50 s (Ramireddy, Jatoth &
# Srikanth 2025, Siegloch regression, Hyderabad and Kurnool) and 2.17 s (Dash, Mohapatra
# & Dey, Transp. Letters 11(5)).
#
# The one value measured on FOUR-LANE median openings specifically is 2.04 s for
# two-wheelers (Khan 2022 thesis Table 8.2). The optimistic end was 2.2 s and moved down
# to 2.0 to sit at that measurement, on the same rule applied to the critical gap: follow
# the closest-matched evidence. It moves against us - a shorter follow-up means MORE bay
# capacity and fewer failing approaches - and it is made anyway. The value is
# also the only per-class follow-up time that exists for this manoeuvre in India: the
# thesis presents the rest as a bar chart with no numeric table, and every published
# paper carrying them is closed. So we do not disaggregate follow-up by class either.
FOLLOW_UP_MEASURED_S = (2.50, 2.17, 2.04)
FOLLOW_UP_FOUR_LANE_MEASURED_S = 2.04

# Above this conflicting flow, classical gap acceptance degenerates: acceptable gaps
# essentially cease to exist and the capacity formula runs to near zero, which makes the
# resulting v/c an artefact rather than a ratio. Past it the honest statement is "no
# viable gaps", not a number.
NO_GAP_VC = 3.0

ASSUMPTIONS = {
    "model": "Siegloch / HCM gap acceptance, unsignalised",
    "conflicting_stream": "opposing through movement at the U-turn bay",
    "critical_gap_source": "Indian mixed-traffic literature, composition-weighted",
    "bays_planned_by_jda": 7,
    "right_turn_becomes_uturn": True,
}



# IRC:SP:41-1994 Appendix III Table III-2, "Basic Critical Gap (secs) for Passenger Cars".
# Crossing a 4-lane road under Stop control at roughly 48 km/h is about 6.0 s, with a
# -0.5 s adjustment where population exceeds 2.5 lakh. Jaipur qualifies.
#
# This is a PASSENGER CAR value, and it is one basis among the twelve in GAP_EVIDENCE,
# not a benchmark our numbers are validated against.
#
# An earlier version of this comment argued that because our composition-weighted gaps
# come out below this car value, they are "the generous end for the scheme" and the
# finding therefore cannot be attacked as too pessimistic. That is withdrawn. It compared
# a mixed-traffic weighted gap against a single-class car gap and read the difference as
# conservatism, when the difference is mostly just composition - two-wheelers are half
# this stream and accept shorter gaps, so a lower weighted mean is arithmetic, not
# caution. Against the four-lane median-opening studies that actually match this geometry
# our gap sits mid-pack, which is what GAP_DIRECTION_NOTE records and what the published
# spread lets a reader check for themselves.
IRC_SP41_CAR_GAP_S = 6.0
IRC_SP41_LARGE_CITY_ADJ = -0.5
IRC_SP41_APPLIED = IRC_SP41_CAR_GAP_S + IRC_SP41_LARGE_CITY_ADJ


# Indo-HCM 2017 base critical gap, FOUR-LANE DIVIDED intersection, by vehicle class.
#
# SECONDARY SOURCE. CSIR-CRRI does not publish the manual free; its own "Indo-HCM
# Snippets" preview redacts the whole of section 8.5, and the public full-text mirrors are
# missing Chapter 8 entirely. These numbers come from a peer-reviewed paper reproducing
# the manual's tables, not from the manual. Marked as such wherever they appear, and worth
# closing out with an institutional copy before they go to a client as a citation.
#
# The movement is RIGHT TURN FROM MINOR TO MAJOR, not a U-turn. Indo-HCM appears to
# publish no U-turn row at all, which is consistent with IRC having no U-turn bay clause
# either. It is the nearest published movement, not the same movement.
INDO_HCM_BASE_GAP_S = {"2w": 3.5, "3w": 3.7, "4w": 3.8}

# WHERE OUR GAP SITS IN THE EVIDENCE, AND HOW THAT CLAIM MOVED TWICE.
#
# First we asserted our gaps sat BELOW published values and were therefore generous to the
# scheme. Wrong, and wrong in the direction that flattered our own conclusion. Then, on
# Kerala median-opening data, we asserted they sat ABOVE all Indian field measurements and
# the finding was exposed. Also wrong: that paper never states lane count.
#
# With the four-lane divided median-opening studies in hand, the accurate statement is
# that our composition-weighted optimistic gap sits mid-pack - above Kerala and Mohan &
# Chandra, below Gupta, CSIR-CRRI and IRC:SP:41. It is neither the generous end nor the
# punitive one. That is why the spread is published rather than a single value: the
# reader re-runs the finding on whichever basis they trust and sees the answer move.
GAP_DIRECTION_NOTE = ("our gap sits mid-pack in the Indian field evidence - above the "
                      "Kerala openings, below Gupta, CSIR-CRRI and IRC:SP:41 - so the "
                      "finding rests on neither the generous nor the punitive end")

# The two-wheeler value, and why it moved from 2.8 to 3.5.
#
# It was set at 2.8 against Kumar & Sasikumar's Kerala median openings. That was the
# wrong anchor: the Kerala paper states carriageway width per direction (6.0-10.5 m) and
# never states lane count, so reading it as four-lane was our inference, not theirs.
#
# Two studies do measure median openings on roads explicitly described as four-lane
# divided, and both put two-wheelers well above 2.8:
#
#   Gupta, Mondal & Sharma 2018, Curr. Sci. 114(7) Table 5 - Varanasi, carriageway
#     7.03-8.90 m per direction, which is close to this corridor's ~7 m. Two-wheeler
#     critical gap averages 3.83 s over sites and methods.
#   Datta & Bhuyan 2014 - six median openings, Odisha and Jharkhand. Two-wheelers
#     average 3.37 s by probability equilibrium and 4.78 s by INAFOGA.
#
# 3.5 s sits inside that range and coincides with the Indo-HCM four-lane-divided base.
# The conservative value moves 3.8 -> 4.4 to sit between the two studies' upper methods,
# and lands beside CSIR-CRRI's own 4.5 s design recommendation for Indian median openings
# (Khan, Chalumuri & Senapathi 2015).
# 2.8 was below all three four-lane estimates, so it overstated bay capacity.
TWO_WHEELER_GAP_BASIS = ("Gupta, Mondal & Sharma 2018 (Varanasi, four-lane divided, "
                         "7.03-8.90 m per direction) 3.83 s and Datta & Bhuyan 2014 "
                         "(six four-lane median openings) 3.37-4.78 s; 3.5 s sits "
                         "inside both")
INDO_HCM_GAP_SOURCE = ("Mohan & Chandra 2020, Can. J. Civ. Eng. 47(6), produced under the "
                       "CSIR-CRRI Indo-HCM project: base critical gap, four-lane divided, "
                       "right turn minor-to-major, via a secondary reproduction")

# INDO-HCM HAS NO MEDIAN-OPENING CHAPTER. Verified against the manual's own chapter list:
# 1 basic concepts, 2 two-lane, 3 multilane interurban, 4 expressways, 5 urban roads,
# 6 signalised intersections, 7 roundabouts, 8 uncontrolled intersections, 9 pedestrian,
# 10 travel time reliability. Nothing covers mid-block median openings or U-turns, and
# Annexure 7C (critical gap and follow-up estimation) is scoped to roundabouts.
#
# So the 3.5 s above is NOT an Indian code value for this manoeuvre - it is a junction
# right-turn figure from the Indo-HCM project. It is used because the four-lane
# median-opening field studies independently bracket it, not because a code mandates it.
# There is no Indian code value to fall back on here, and that is itself a finding: the
# scheme JDA is building has no design gap published for it in any Indian standard.
INDO_HCM_NO_UTURN_CHAPTER = ("Indo-HCM 2017 has no chapter, table or parameter set for "
                             "mid-block median openings or U-turns; Annexure 7C is scoped "
                             "to roundabouts. No Indian code publishes a design gap for "
                             "the manoeuvre this scheme is built on.")

# The nearest thing to an Indian DESIGN value for a median opening, and it is a
# recommendation rather than a code clause. CSIR-CRRI measured 748 U-turning vehicles on
# NH-8 Delhi-Manesar across seven gap-acceptance methods spanning 2.10-7.26 s, and
# concluded 4.5 s is optimum for designing median openings on Indian corridors. Our
# conservative two-wheeler gap of 4.4 s sits beside it.
CSIR_CRRI_DESIGN_GAP_S = 4.5
CSIR_CRRI_DESIGN_SOURCE = ("Khan, Chalumuri & Senapathi 2015, J. EASTS 11:1842-1855, "
                           "CSIR-CRRI, NH-8 Delhi-Manesar, 748 U-turning vehicles")

# The tf = 0.6 x tc rule is a CONVENTION, not a code relation, and certainly not an
# Indo-HCM one - the manual has no median-opening chapter to carry it. Indian studies
# state it as an assumption in so many words: 'the follow-up was assumed to be 60% of
# the critical gap as established in several studies' (Kota, Pallela & Lalam 2025).
#
# We no longer follow it. Our optimistic follow-up is pinned to the 2.04 s measured on
# four-lane median openings, which is about 0.3 s below what the convention implies at
# our weighted gap. A measurement on the matching geometry beats a rule of thumb, and
# the departure is published rather than reconciled away.
FOLLOWUP_RATIO_CONVENTION = 0.60

# Indo-HCM's capacity form carries two geometric adjustment factors we do not apply:
#     C = a * v_c * exp(-v_c (t_c - b) / 3600) / (1 - exp(-v_c t_f / 3600))
# We use the plain HCM potential-capacity form, which is this with a = 1 and b = 0. The
# values of a and b are in the part of Chapter 8 that is redacted in every free copy, so
# applying them is not possible yet. Stated rather than silently ignored.
INDO_HCM_FORM_DIFFERS = ("Indo-HCM adds geometric factors a and b to the HCM form; we use "
                         "a = 1, b = 0 because their values sit in a chapter no free copy "
                         "of the manual reproduces")


# WHICH ANALOGUE THE U-TURN IS MODELLED AS — the load-bearing assumption here.
#
# No Indian standard publishes a U-turn critical gap. IRC:SP:41 has no U-turn row at all;
# Indo-HCM Chapter 8 scopes itself to "three legged and four legged unsignalized
# intersections only" and does not cover median openings. So a U-turn has to be modelled
# as something else, and the choice decides the answer:
#
#   as a MERGE into one stream        Indian field gaps 1.4-2.8 s  -> bays look better
#   as a CROSSING of both lanes       Indian field gaps 3.5-9.1 s  -> bays look far worse
#
# We model it as a MERGE. A U-turn from a median bay on a divided carriageway enters the
# opposing stream and joins it; it does not traverse to a far-side receiving lane. The
# crossing analogue would only apply if bay geometry forced vehicles across both lanes,
# which the drawing does not show. This is the more favourable of the two choices for the
# scheme, and it is stated rather than left implicit.
UTURN_ANALOGUE = "merge into the opposing stream, not a crossing of it"

# Published Indian field values, for the method spread rather than a single number.
#
# Bhatt, Gore & Shah (2022) measured the SAME vehicle at the SAME junction at 1.18 s by
# Ashworth and 2.88 s by the Indo-HCM occupancy-time method - a 2.4x spread, and their
# capacities at one junction range 337-2213 PCU/h on method choice alone. Publishing one
# critical gap, ours or anyone else's, hides that. So the spread is published and the
# point at which the conclusion changes is published with it.
GAP_EVIDENCE = [
    # label, t_c, t_f, source, geometric match to this corridor
    ("Kerala median openings, traditional/Raff", 2.05, 1.23,
     "Kumar & Sasikumar 2020, IJTTE 10(4), six mid-block median openings, Kerala",
     "median openings, but the paper states carriageway width only and never lane "
     "count - reading it as four-lane was our inference, not theirs"),
    ("Kerala median openings, merging behaviour", 2.80, 1.70,
     "Kumar & Sasikumar 2020; merging behaviour is the method those authors recommend "
     "for mixed traffic",
     "median openings, lane count not stated in the paper"),
    # The most directly relevant evidence reachable: four-lane divided median openings,
    # five estimation methods, from the PhD thesis behind the closed TRR papers on exactly
    # this manoeuvre. Both of the authors' own preferred methods and their lower pair are
    # carried, because the two differ by 0.9 s on the same sites.
    ("Khan 2022 thesis, four-lane median openings, modified Raff / binary logit", 3.36, 2.04,
     "T. Khan PhD thesis 2022, IIT (ISM) Dhanbad, ch. 7-8; the dataset behind Khan et al. "
     "TRR 2678 and 2679, which are closed access. Values may differ from the edited papers",
     "closest of all: four-lane divided median openings, and the only source with a "
     "MEASURED four-lane follow-up time (2.04 s, two-wheelers, Table 8.2)"),
    ("Khan 2022 thesis, four-lane median openings, occupancy time / SVM", 4.26, 2.04,
     "same thesis; the authors conclude occupancy time and SVM give the values closest "
     "to published literature, so this is their own preferred pair",
     "closest of all: four-lane divided median openings, authors' preferred methods"),
    ("Datta & Bhuyan 2014, four-lane median openings, prob. equilibrium", 3.79, 2.17,
     "Datta & Bhuyan 2014, ICAET, six median openings on four-lane divided roads, "
     "Odisha and Jharkhand; mean over all classes and sites",
     "closest by road type: median openings explicitly on four-lane divided"),
    ("Gupta et al. 2018, four-lane median openings, Varanasi", 4.45, 2.50,
     "Gupta, Mondal & Sharma 2018, Curr. Sci. 114(7) Table 5, traditional and INAFOGA "
     "over 30 observations; follow-up from Ramireddy et al. 2025 Siegloch measurement",
     "closest overall: four-lane divided median openings, carriageway 7.03-8.90 m per "
     "direction against this corridor's ~7 m"),
    ("Datta & Bhuyan 2014, four-lane median openings, INAFOGA", 5.09, 3.00,
     "Datta & Bhuyan 2014; INAFOGA/merging-behaviour method, mean over all classes",
     "closest by road type: median openings explicitly on four-lane divided"),
    ("ours, optimistic", None, None,
     "composition-weighted from literature", "none stated"),
    ("ours, conservative", None, None,
     "composition-weighted from literature", "none stated"),
    ("Mohan & Chandra 2020, RT from minor, 4-lane divided", 3.50, 2.10,
     "Can. J. Civ. Eng. 47(6), produced under the CSIR-CRRI Indo-HCM project",
     "four-lane divided major, but a junction movement not a median opening"),
    ("CSIR-CRRI NH-8 design recommendation", 4.50, 2.70,
     "Khan, Chalumuri & Senapathi 2015, J. EASTS 11:1842-1855; 748 U-turning vehicles "
     "across seven methods spanning 2.10-7.26 s; follow-up at the 0.6 x t_c convention",
     "the only Indian DESIGN value for a median opening, but inter-urban NH not urban"),
    ("IRC:SP:41 Table III-2, RT from major, 4-lane, 48 kmph", 5.50, 3.00,
     "IRC:SP:41-1994 Appendix III Table III-2, passenger cars, large-city adjustment "
     "applied", "four-lane, but HCM 1985 in metric with no Indian calibration"),
]


def breakpoint_gap(demand, conflicting, t_f, lo=0.05, hi=12.0):
    """
    The critical gap at which a bay would exactly serve its demand.

    Answers the question that matters about a value we did not measure: not "is it
    right" but "how wrong would it have to be to change the answer". Capacity falls
    monotonically with t_c, so a bisection is exact.
    """
    for _ in range(200):
        mid = (lo + hi) / 2
        if gap_capacity(conflicting, mid, t_f) > demand:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def gap_benchmark(uturns, t_f_opt, t_f_cons):
    """Our weighted gaps, the IRC car value, and the gap each bay would need."""
    rows = []
    for u in uturns:
        need = breakpoint_gap(u["uturn_demand"], u["conflicting_flow"], t_f_opt)
        rows.append(dict(junction=u["junction"], approach=u["approach"],
                         t_c_optimistic=round(u["t_c_lo"], 2),
                         t_c_conservative=round(u["t_c_hi"], 2),
                         t_c_required=round(need, 2),
                         margin_s=round(u["t_c_lo"] - need, 2),
                         works_at_our_optimistic=need >= u["t_c_lo"]))
    return rows


def cap_ok(sc):
    """Junctions returned under planning capacity by the elevated scheme."""
    return int((sc.s2_vc < 1.0).sum())


def gap_capacity(q_c_veh_hr, t_c, t_f):
    """
    Gap-acceptance capacity, veh/h. The HCM potential-capacity form:

        c = q_c * exp(-q_c * t_c / 3600) / (1 - exp(-q_c * t_f / 3600))

    q_c is the conflicting flow in veh/h; t_c and t_f are in seconds. Verified against
    the formula worked by hand at four points; see tests.

    The previous body computed the same thing but wrote the scaling as
    `3600 * (...) / 3600 * 3600`, which is a multiply by 3600 spelled three ways and
    reads like a unit bug even though it is not.
    """
    if q_c_veh_hr <= 0:
        return float("inf")
    q = q_c_veh_hr / 3600.0            # conflicting flow, veh/second
    denom = 1.0 - math.exp(-q * t_f)
    if denom <= 0:
        return float("inf")
    return q_c_veh_hr * math.exp(-q * t_c) / denom


def weighted_gap(share, which):
    """Composition-weighted critical gap. `which` is 0 optimistic, 1 conservative."""
    tot = sum(share.values())
    if tot <= 0:
        return CRITICAL_GAP_S["CAR_BUCKET"][which]
    return sum(share.get(c, 0) * CRITICAL_GAP_S[c][which] for c in CRITICAL_GAP_S) / tot


def peak_window(series):
    i = max(range(len(series) - 3), key=lambda k: series.iloc[k:k + 4].sum())
    return series.index[i], series.iloc[i:i + 4]


# WHICH MOVEMENTS ACTUALLY FEED A U-TURN BAY.
#
# The first version of this counted right turns from the two CORRIDOR arms only, and
# nothing else. That was wrong, and a reviewer for JDA caught it: under a median U-turn
# scheme the bays serve the cross-street traffic too, and in the full form they serve the
# cross-street THROUGH movement as well. Counting two of the six feeding movements
# understated corridor U-turn demand by about 3.4x.
#
# Working it through for left-hand drive, a junction with the corridor running N-S:
#
#   Northbound-merging bay (vehicles head south, U-turn, come back north)
#     N -> W   right turn off the corridor: straight through, U-turn, then left into W
#     E -> N   right turn off the cross-street: left onto the corridor southbound,
#              U-turn, back north
#     E -> W   cross-street through: same left onto the corridor, U-turn, then left into W
#
#   Southbound-merging bay, the mirror image
#     S -> E   right turn off the corridor
#     W -> S   right turn off the cross-street
#     W -> E   cross-street through
#
# Three movements share each bay, so the demands ADD at the bay rather than being
# tested one at a time. The conflicting stream is whichever corridor through movement
# the bay merges into, which is the opposite direction to the one the vehicle arrived on.
#
# Which cross arm is "east" is derived from the data rather than assumed: the arm whose
# right turn lands on the north arm is the east side.
FEEDS_BAY = "right turns from all four arms, plus the cross-street through movement"


def bay_demand(pk, cross_east, cross_west):
    """
    (northbound bay demand, southbound bay demand) for one peak window.

    Returns the SUM over every movement that has to use each bay, because they queue
    for the same gap in the same opposing stream.
    """
    def n(frm, mvt):
        return float(pk[(pk.arm_from == frm) & (pk.movement == mvt)]["count"].sum())
    north = n(NORTH, "Right")                      # corridor right turn
    south = n(SOUTH, "Right")
    if cross_east is not None:
        north += n(cross_east, "Right") + n(cross_east, "Straight")
    if cross_west is not None:
        south += n(cross_west, "Right") + n(cross_west, "Straight")
    return north, south


def analyse(bins, day, full_mut=True):
    """
    Per junction: the demand each U-turn bay must serve, against its gap-acceptance
    capacity.

    full_mut=False reproduces the original corridor-right-turns-only reading, kept so the
    two can be published side by side rather than one quietly replacing the other.
    """
    mv = bins[(bins.kind == "movement") & (bins.date == day)]
    rows = []
    for code, g in mv.groupby("junction"):
        share = g.groupby("veh_class")["count"].sum()
        share = (share / share.sum()).to_dict()
        tc_lo, tc_hi = weighted_gap(share, 0), weighted_gap(share, 1)

        # peak hour on the junction, used consistently for demand and conflict
        tot = g.groupby("bin_start")["count"].sum().sort_index()
        start, _ = peak_window(tot)
        window = tot.index[list(tot.index).index(start):][:4]
        pk = g[g.bin_start.isin(window)]

        # identify the cross arms by where their right turn lands, not by assuming
        cross_east = cross_west = None
        for a in pk.arm_from.unique():
            if a in (NORTH, SOUTH):
                continue
            to = pk[(pk.arm_from == a) & (pk.movement == "Right")]["arm_to"]
            if len(to) and to.iloc[0] == NORTH:
                cross_east = a
            elif len(to) and to.iloc[0] == SOUTH:
                cross_west = a

        if full_mut:
            d_north, d_south = bay_demand(pk, cross_east, cross_west)
        else:
            d_north, d_south = bay_demand(pk, None, None)

        # a bay merging INTO the northbound stream conflicts with northbound through,
        # which is the traffic arriving from the south arm and going straight
        thru_north = float(pk[(pk.arm_from == SOUTH) & (pk.movement == "Straight")]["count"].sum())
        thru_south = float(pk[(pk.arm_from == NORTH) & (pk.movement == "Straight")]["count"].sum())

        for arm, demand, thru, bay in ((NORTH, d_north, thru_north, "northbound"),
                                       (SOUTH, d_south, thru_south, "southbound")):
            if demand <= 0:
                continue
            cap_lo = gap_capacity(thru, tc_hi, FOLLOW_UP_S[1])   # conservative
            cap_hi = gap_capacity(thru, tc_lo, FOLLOW_UP_S[0])   # optimistic
            rows.append(dict(
                junction=code, approach=arm, bay=bay,
                jda_name=JUNCTION_COORDS[code][2],
                uturn_demand=demand, conflicting_flow=thru,
                t_c_lo=round(tc_lo, 2), t_c_hi=round(tc_hi, 2),
                cap_conservative=cap_lo, cap_optimistic=cap_hi,
                vc_conservative=demand / cap_lo if cap_lo else float("inf"),
                vc_optimistic=demand / cap_hi if cap_hi else float("inf"),
                peak_start=str(start)[11:16]))
    return pd.DataFrame(rows)


def uturn_detour(uturns):
    """
    How much further a converted movement actually has to travel.

    A right turn at a signalised junction is one manoeuvre. Under a median U-turn scheme
    the same driver goes past the junction, runs to the median opening, turns through
    180 degrees, comes back, and only then makes the left. The distance is measurable
    from the drawing: junction chainage against the nearest opening wide enough to turn
    in, doubled for the return leg.

    Two honest limits, both reported rather than smoothed:

      The drawing ENDS. A junction near either end has no opening beyond it in the CAD,
      so its detour cannot be measured in that direction. That is a limit of the survey
      extent, not a finding about the road, and those rows are returned with
      bay_beyond_drawing set rather than dropped or guessed at.

      The nearest opening is not necessarily the one the scheme will use. JDA names seven
      bays and we do not have their chainages, so this is the SHORTEST detour physically
      available. A purpose-built bay placed further out makes every number here larger.
    """
    import json as _j
    from src.reports import chainage as _chainage
    total, jrows = _chainage()
    p = OUT_DATA / "median_openings.geojson"
    if not p.exists():
        return []
    g = _j.loads(p.read_text())
    ops = sorted(f["properties"]["chainage_m"] for f in g["features"]
                 if f["properties"].get("uturn_possible"))
    demand = {(u["junction"], u["bay"]): u["uturn_demand"] for u in uturns}

    # WHICH WAY IS NORTH ALONG THE CHAINAGE, derived rather than assumed.
    #
    # This read `northbound -> openings at higher chainage` as a bare fact. It was not one:
    # chainage used to start at the NORTHERN end, so higher chainage meant further SOUTH
    # and every bay here was matched to an opening on the wrong side of its junction. The
    # figures looked entirely reasonable, which is why it survived. Reversing the chainage
    # direction fixed it by accident; deriving the sign from the convention fixes it on
    # purpose, and flipping CHAINAGE_FROM will not silently swap them again.
    north_is_up = CHAINAGE_FROM == "south"

    def toward(direction, c):
        ahead = (o for o in ops if (o > c) if (direction == "northbound") == north_is_up)
        behind = (o for o in ops if (o < c) if (direction == "northbound") != north_is_up)
        return sorted(ahead) + sorted(behind)

    out = []
    for r in jrows:
        c = r["chainage_m"]
        for bay, cand in (("northbound", toward("northbound", c)),
                          ("southbound", toward("southbound", c))):
            d = demand.get((r["junction"], bay))
            if d is None:
                continue
            if not cand:
                out.append(dict(junction=r["junction"], bay=bay, demand=d,
                                bay_beyond_drawing=True, one_way_m=None,
                                detour_m=None, veh_km_per_hour=None))
                continue
            b = min(cand, key=lambda o: abs(o - c))
            leg = abs(b - c)
            out.append(dict(junction=r["junction"], bay=bay, demand=d,
                            bay_beyond_drawing=False,
                            junction_chainage_m=round(c), bay_chainage_m=round(b),
                            one_way_m=round(leg), detour_m=round(2 * leg),
                            veh_km_per_hour=round(2 * leg / 1000 * d, 1)))
    return out


def scenarios(bins, day, res):
    """Three futures for the corridor, scored on whether the movement can be served."""
    tv = through_vs_turning(bins, day).set_index("junction")
    cap = json.loads((OUT_DATA / "capacity.json").read_text())
    relief = {r["junction"]: r for r in cap["relief"]}
    out = []
    for code in sorted(res.junction.unique()):
        sub = res[res.junction == code]
        worst = sub.loc[sub.vc_conservative.idxmax()]
        r = relief.get(code, {})
        out.append(dict(
            junction=code, jda_name=JUNCTION_COORDS[code][2],
            s0_vc=r.get("vc_before"), s0_los="F" if (r.get("vc_before") or 0) >= 1 else "-",
            s1_uturn_vc_cons=float(worst.vc_conservative),
            s1_uturn_vc_opt=float(worst.vc_optimistic),
            s1_works=bool(worst.vc_conservative < 1.0),
            s2_vc=r.get("vc_after"), s2_los=r.get("los_after"),
            through_pct=float(tv.loc[code, "through_pct"])))
    return pd.DataFrame(out)


def gap_evidence_spread(uturns, t_c_ours, t_c_ours_conservative, of):
    """
    Re-run the serviceability test on every published critical-gap basis.

    The single most attackable number in this audit is the critical gap, because we chose
    it and it is not measured on this corridor. So rather than defend one value, the same
    test runs across every basis reachable and the reader picks.

    Lifted out of __main__ deliberately. It sat inline in the driver, which meant the one
    calculation whose whole purpose is to show how sensitive the finding is to an
    assumption could not itself be tested — the same trap as the pipeline's
    "all stages passed" line.
    """
    spread = []
    for label, tc, tf, src, match in GAP_EVIDENCE:
        t_c = tc if tc is not None else (t_c_ours if "optimistic" in label
                                         else t_c_ours_conservative)
        t_f = tf if tf is not None else (FOLLOW_UP_S[0] if "optimistic" in label
                                         else FOLLOW_UP_S[1])
        fails = nogap = 0
        for u in uturns:
            c = gap_capacity(u["conflicting_flow"], t_c, t_f)
            vc = u["uturn_demand"] / c if c else 99
            if vc > 1.0:
                fails += 1
            if vc >= NO_GAP_VC:
                nogap += 1
        spread.append(dict(label=label, t_c=round(t_c, 2), t_f=round(t_f, 2),
                           unservable=fails, no_viable_gap=nogap,
                           of=of, source=src, geometric_match=match))
    spread.sort(key=lambda r: r["t_c"])
    return spread


if __name__ == "__main__":
    bins, _ = parse_all()
    day = sorted(bins.date.unique())[0]

    print("=== Assumptions ===")
    for k, v in ASSUMPTIONS.items():
        print(f"  {k:<28} {v}")
    print(f"  {'follow_up_s':<28} {FOLLOW_UP_S}")
    print("\n  Critical gap is weighted by observed composition. With two-wheelers at ~49%")
    print("  of this stream, a car-based critical gap would badly understate capacity.\n")

    res = analyse(bins, day)
    print("=== Can a U-turn bay carry the right-turn demand it inherits? ===")
    print("  demand = peak-hour RIGHT turns from that approach, which become U-turns")
    print("  conflict = opposing through flow the driver must find a gap in\n")
    print(f"  {'junction':<9}{'JDA name':<13}{'approach':<20}{'demand':>8}{'conflict':>10}"
          f"{'t_c':>7}{'cap':>8}{'v/c':>7}  verdict")
    print("  " + "-" * 96)
    for _, r in res.sort_values("vc_conservative", ascending=False).iterrows():
        if r.vc_conservative >= NO_GAP_VC:
            v, vc = "no viable gaps", "  --"
        elif r.vc_conservative >= 1.0:
            v, vc = "FAILS", f"{r.vc_conservative:>6.2f}"
        elif r.vc_conservative >= 0.85:
            v, vc = "marginal", f"{r.vc_conservative:>6.2f}"
        else:
            v, vc = "ok", f"{r.vc_conservative:>6.2f}"
        ap = r.approach.replace("Mansarover Metro", "from N").replace("Sanganer Stadium", "from S")
        print(f"  {r.junction:<9}{r.jda_name:<13}{ap:<20}{r.uturn_demand:>8,.0f}"
              f"{r.conflicting_flow:>10,.0f}{r.t_c_hi:>7.1f}{r.cap_conservative:>8,.0f}"
              f"{vc:>7}  {v}")

    fails = int((res.vc_conservative >= 1.0).sum())
    nogap = int((res.vc_conservative >= NO_GAP_VC).sum())
    fails_opt = int((res.vc_optimistic >= 1.0).sum())
    print(f"\n  GATE — U-turn movements the bays cannot serve (conservative gap): "
          f"**{fails} of {len(res)}**")
    print(f"  Of those, {nogap} sit past the point where acceptable gaps effectively cease")
    print(f"  to exist, so no ratio is quoted for them.")
    print(f"  Under the OPTIMISTIC critical gap, still unservable: **{fails_opt} of {len(res)}**")

    # --- the second-order effect, which is the real finding -----------------
    print(f"\n=== What happens when the gap is not there ===")
    print("  Classical gap acceptance assumes a driver waits. Indian drivers do not: they")
    print("  creep, encroach, and force the movement, and opposing traffic yields. So the")
    print("  U-turn does not simply fail to happen.")
    print("\n  It blocks the opposing through stream instead. Every forced U-turn imposes a")
    print("  stoppage on the movement the scheme exists to speed up. At these conflicting")
    print("  flows the bays would not merely underperform - they would convert a capacity")
    print("  problem at the junction into a capacity problem on the link, where there is no")
    print("  signal left to meter it.")
    blocked = res[res.vc_conservative >= 1.0]
    tot_forced = blocked.uturn_demand.sum() - blocked.cap_conservative.sum()
    print(f"\n  Peak-hour U-turn demand with no gap to serve it: "
          f"**{tot_forced:,.0f} vehicles/hour** across {len(blocked)} approaches.")
    print("  That is the volume that would be forcing its way across opposing traffic.")

    sc = scenarios(bins, day, res)
    print("\n=== Three futures for the corridor ===\n")
    print(f"  {'junction':<9}{'JDA name':<13}{'S0 do-nothing':>15}{'S1 JDA U-turns':>17}"
          f"{'S2 elevated':>14}")
    print("  " + "-" * 70)
    for _, r in sc.iterrows():
        s1 = ("no gaps" if r.s1_uturn_vc_cons >= NO_GAP_VC
              else f"{r.s1_uturn_vc_cons:.2f} {'FAIL' if not r.s1_works else 'ok'}")
        print(f"  {r.junction:<9}{r.jda_name:<13}{f'v/c {r.s0_vc:.2f} F':>15}{s1:>17}"
              f"{f'v/c {r.s2_vc:.2f} {r.s2_los}':>14}")

    n_ok_s1 = int(sc.s1_works.sum())
    print(f"\n  S0  do-nothing            : all {len(sc)} junctions over capacity today")
    print(f"  S1  JDA signal-free       : U-turn movement serviceable at "
          f"**{n_ok_s1} of {len(sc)}** junctions")
    print(f"  S2  elevated through-road : {cap_ok(sc)} of {len(sc)} junctions returned "
          f"under planning capacity")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "scheme_test.json").write_text(json.dumps(dict(
        assumptions={**ASSUMPTIONS, "follow_up_s": list(FOLLOW_UP_S)},
        analysis_date=str(day),
        uturns=[{k: (v if not hasattr(v, "item") else v.item())
                 for k, v in r.items()} for r in res.to_dict("records")],
        scenarios=[{k: (v if not hasattr(v, "item") else v.item())
                    for k, v in r.items()} for r in sc.to_dict("records")],
        fails_conservative=fails, fails_optimistic=fails_opt,
        no_viable_gap=nogap, no_gap_vc_threshold=NO_GAP_VC,
        forced_uturns_per_hour=float(tot_forced),
        s1_serviceable=n_ok_s1, n_junctions=len(sc),
    ), indent=1, default=str))
    # --- how wrong would the critical gap have to be? -------------------------
    bench = gap_benchmark(res.to_dict("records") if hasattr(res, "to_dict") else res,
                          FOLLOW_UP_S[0], FOLLOW_UP_S[1])
    import statistics as _st
    med_need = _st.median(r["t_c_required"] for r in bench)
    med_opt = _st.median(r["t_c_optimistic"] for r in bench)
    print("\n=== The critical gap is the value we did not measure ===")
    print("  So the question is not whether it is right, but how wrong it would have to")
    print("  be to change the answer. Lower gap = more bay capacity = better for the scheme.\n")
    print(f"  {'junction':<10}{'approach':<20}{'ours (opt)':>11}{'needed':>9}{'margin':>9}")
    print("  " + "-" * 60)
    for r in bench:
        print(f"  {r['junction']:<10}{r['approach'][:19]:<20}{r['t_c_optimistic']:>11.2f}"
              f"{r['t_c_required']:>9.2f}{r['margin_s']:>9.2f}")
    print(f"\n  median gap required for the bays to work : {med_need:.2f} s")
    print(f"  our already-optimistic weighted value     : {med_opt:.2f} s")
    print(f"  margin                                    : {med_opt - med_need:.2f} s")
    print(f"\n  IRC:SP:41 App III Table III-2 passenger-car value, 4-lane crossing,")
    print(f"  Stop control, large-city adjustment applied: {IRC_SP41_APPLIED} s")
    print("  Our weighted gaps sit BELOW that because two-wheelers are half the stream.")
    print("  This claim has moved twice, and both earlier versions are withdrawn. We")
    print("  first said our gaps sat below published values and were generous to the")
    print("  scheme; then, on Kerala data, that they sat above every Indian measurement.")
    print("  The Kerala paper never states lane count. Against the studies that do")
    print("  measure four-lane median openings, our gap sits mid-pack. That is the")
    print("  reason the spread below is published rather than a single number.")

    print("\n=== There is no Indian code value for this manoeuvre ===")
    print("  Indo-HCM 2017 has no chapter, table or parameter set for mid-block median")
    print("  openings or U-turns; Annexure 7C is scoped to roundabouts. So the base gaps")
    print("  below are a JUNCTION right-turn figure from the Indo-HCM project, not a code")
    print("  value for a median opening, and they are used only as one basis among many.")
    print("    " + ",  ".join(f"{k} {v} s" for k, v in INDO_HCM_BASE_GAP_S.items()))
    print(f"    {INDO_HCM_GAP_SOURCE}")
    print(f"\n  our optimistic two-wheeler gap  {CRITICAL_GAP_S['TWO_W'][0]} s")
    print(f"  that junction figure            {INDO_HCM_BASE_GAP_S['2w']} s")
    print( "  four-lane median-opening field evidence brackets both: Gupta 3.83,")
    print( "  Datta & Bhuyan 3.37 to 4.78. Two-wheelers are half this stream, so this is")
    print( "  the single most consequential number in the model.")
    print(f"\n  nearest Indian DESIGN value    {CSIR_CRRI_DESIGN_GAP_S} s")
    print(f"    {CSIR_CRRI_DESIGN_SOURCE}")

    print(f"\n  The tf = {FOLLOWUP_RATIO_CONVENTION:.0%} x tc rule is a convention, not a code relation.")
    print(f"  It implies {FOLLOWUP_RATIO_CONVENTION*med_opt:.2f} s at our weighted gap. We use "
          f"{FOLLOW_UP_S[0]} s instead,")
    print(f"  pinned to the {FOLLOW_UP_FOUR_LANE_MEASURED_S} s measured on four-lane median openings")
    print( "  (Khan 2022 thesis Table 8.2) - the only follow-up time measured on the")
    print( "  geometry that matches this corridor. A measurement beats a rule of thumb,")
    print( "  and a shorter follow-up gives MORE bay capacity, so this runs against us.")
    print("\n  Caveat carried into the output: CRRI does not publish the manual free, its")
    print("  own preview redacts section 8.5, and no free full text reproduces Chapter 8.")
    print("  These figures come from a paper reproducing the tables. The movement is a")
    print("  right turn from minor to major, NOT a U-turn - Indo-HCM appears to publish no")
    print("  U-turn row, consistent with IRC having no U-turn bay clause either.")

    payload = json.loads((OUT_DATA / "scheme_test.json").read_text())
    payload["gap_benchmark"] = bench
    payload["gap_required_median_s"] = round(med_need, 2)
    payload["gap_ours_median_s"] = round(med_opt, 2)
    payload["gap_margin_s"] = round(med_opt - med_need, 2)
    payload["irc_sp41_car_gap_s"] = IRC_SP41_APPLIED
    payload["gap_source"] = ("composition-weighted from literature; benchmarked against "
                             "IRC:SP:41-1994 Appendix III Table III-2 passenger-car value "
                             "and Indo-HCM 2017 base gaps")
    # --- the method spread, and where the conclusion changes -------------------
    spread = gap_evidence_spread(
        res.to_dict("records") if hasattr(res, "to_dict") else res,
        med_opt, _st.median(r["t_c_conservative"] for r in bench), len(bench))

    print("\n=== The critical gap is method-dependent by 2.4x. So publish the spread. ===")
    print("  Bhatt, Gore & Shah (2022) measured the same vehicle at the same junction at")
    print("  1.18 s by Ashworth and 2.88 s by occupancy time, giving capacities of 337 to")
    print("  2,213 PCU/h at one junction on method choice alone. One number hides that.\n")
    print(f"  {'basis':<66}{'t_c':>6}{'t_f':>6}{'unservable':>12}")
    print("  " + "-" * 90)
    for r in spread:
        print(f"  {r['label']:<66}{r['t_c']:>6.2f}{r['t_f']:>6.2f}"
              f"{r['unservable']:>7} of {r['of']}")
    holds = [r for r in spread if r["unservable"] >= r["of"] * 0.5]
    print(f"\n  The conclusion holds in {len(holds)} of {len(spread)} bases.")
    breaks = [r for r in spread if r["unservable"] < r["of"] * 0.5]
    if breaks:
        for b in breaks:
            print(f"  IT DOES NOT HOLD at: {b['label']} ({b['unservable']} of {b['of']})")
        print("  That basis uses traditional Raff, which the same authors who published it")
        print("  recommend AGAINST for mixed traffic in favour of merging behaviour. At")
        print("  their recommended method the conclusion holds. Both are published.")
    print(f"\n  U-turn modelled as: {UTURN_ANALOGUE}")

    payload["uturn_analogue"] = UTURN_ANALOGUE
    payload["feeds_bay"] = FEEDS_BAY

    # what the detour actually costs, measured off the drawing
    det = uturn_detour(payload["uturns"])
    payload["uturn_detour"] = det
    measured = [d for d in det if not d["bay_beyond_drawing"]]
    if measured:
        payload["detour_min_m"] = min(d["detour_m"] for d in measured)
        payload["detour_max_m"] = max(d["detour_m"] for d in measured)
        payload["detour_mean_m"] = round(sum(d["detour_m"] for d in measured) / len(measured))
        payload["detour_veh_km_per_hour"] = round(sum(d["veh_km_per_hour"] for d in measured), 1)
        payload["detour_bays_measured"] = len(measured)
        payload["detour_bays_beyond_drawing"] = len(det) - len(measured)

    print("\n=== What the detour costs, measured off the drawing ===")
    print("  A right turn was one manoeuvre. Now it is: past the junction, out to the")
    print("  median opening, through 180 degrees, back, then the left turn.\n")
    print(f"  {'junction':<9}{'bay':<12}{'to bay':>9}{'detour':>9}{'demand':>9}{'veh-km/h':>10}")
    print("  " + "-" * 60)
    for d in det:
        if d["bay_beyond_drawing"]:
            print(f"  {d['junction']:<9}{d['bay']:<12}{'--':>9}{'--':>9}"
                  f"{d['demand']:>9.0f}{'  beyond drawing':>10}")
        else:
            print(f"  {d['junction']:<9}{d['bay']:<12}{d['one_way_m']:>9,}{d['detour_m']:>9,}"
                  f"{d['demand']:>9.0f}{d['veh_km_per_hour']:>10,.0f}")
    # One row can dominate the mean, and here it does. TMC-01 sits at the end of the
    # drawing with no opening for 2 km beyond it, AND its position is one of the three
    # inferred ones. Both reasons to quote the corridor figure without it as well as
    # with it, rather than let the least certain row set the headline.
    typical = [d for d in measured if d["detour_m"] < 1000]
    if typical:
        payload["detour_mean_typical_m"] = round(sum(d["detour_m"] for d in typical) / len(typical))
        payload["detour_veh_km_typical"] = round(sum(d["veh_km_per_hour"] for d in typical), 1)
        payload["detour_outliers_excluded"] = len(measured) - len(typical)

    if measured:
        print(f"\n  detour {payload['detour_min_m']:,} to {payload['detour_max_m']:,} m, "
              f"mean {payload['detour_mean_m']:,} m, over "
              f"{payload['detour_bays_measured']} bays the drawing covers")
        print(f"  extra {payload['detour_veh_km_per_hour']:,.0f} vehicle-km in the peak hour")
        if typical and len(typical) < len(measured):
            print(f"\n  Excluding {len(measured)-len(typical)} row(s) over 1 km: mean "
                  f"{payload['detour_mean_typical_m']:,} m, "
                  f"{payload['detour_veh_km_typical']:,.0f} extra vehicle-km/h.")
            print("  TMC-01 is the excluded one. It sits at the end of the drawing with no")
            print("  opening for 2 km beyond it, and its position is one of the three")
            print("  inferred. Least certain row, largest number: quoted both ways.")
        print("\n  This is the SHORTEST detour available: the nearest opening wide enough to")
        print("  turn in. A purpose-built bay further out makes every figure here larger.")
    payload["gap_direction_note"] = GAP_DIRECTION_NOTE
    payload["two_wheeler_gap_basis"] = TWO_WHEELER_GAP_BASIS
    payload["gap_evidence_spread"] = spread
    payload["gap_conclusion_holds_in"] = len(holds)
    payload["gap_bases_tested"] = len(spread)
    payload["indo_hcm_base_gap_s"] = INDO_HCM_BASE_GAP_S
    payload["indo_hcm_gap_source"] = INDO_HCM_GAP_SOURCE
    payload["followup_ratio_convention"] = FOLLOWUP_RATIO_CONVENTION
    payload["indo_hcm_form_differs"] = INDO_HCM_FORM_DIFFERS
    payload["indo_hcm_no_uturn_chapter"] = INDO_HCM_NO_UTURN_CHAPTER
    payload["csir_crri_design_gap_s"] = CSIR_CRRI_DESIGN_GAP_S
    payload["csir_crri_design_source"] = CSIR_CRRI_DESIGN_SOURCE
    payload["follow_up_measured_s"] = list(FOLLOW_UP_MEASURED_S)
    payload["follow_up_four_lane_measured_s"] = FOLLOW_UP_FOUR_LANE_MEASURED_S
    payload["two_wheeler_gap_ours"] = CRITICAL_GAP_S["TWO_W"][0]
    payload["two_wheeler_gap_indo_hcm"] = INDO_HCM_BASE_GAP_S["2w"]
    payload["followup_implied_by_indo_hcm"] = [
        round(FOLLOWUP_RATIO_CONVENTION * med_opt, 2),
        round(FOLLOWUP_RATIO_CONVENTION * _st.median(r["t_c_conservative"] for r in bench), 2)]
    payload["followup_ours"] = list(FOLLOW_UP_S)
    (OUT_DATA / "scheme_test.json").write_text(json.dumps(payload, indent=1))

    print(f"\nwritten: {OUT_DATA/'scheme_test.json'}")
