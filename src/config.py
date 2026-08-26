"""
config.py — corridor and junction constants.

One corridor, six junctions. Everything that is a fact about the study site rather
than a fact about the code lives here.
"""
from pathlib import Path

# --- paths ------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "00_source" / "extracted"
OUT = ROOT / "out"
OUT_DATA = OUT / "data"
PROCESSED = ROOT / "data" / "processed"

# --- study site -------------------------------------------------------------
CORRIDOR_NAME = "Mansarover Metro — Sanganer Stadium"
CITY = "Jaipur"
CRS_WORK = "EPSG:32643"          # UTM Zone 43N, metres. All geometry lives here.
CRS_GEO = "EPSG:4326"            # ingest/display boundary only

# Jaipur sanity anchor: WGS84 26.9124N 75.7873E -> UTM43N E578000 N2976000
JAIPUR_UTM_ANCHOR = (578_000.0, 2_976_000.0)

# India drives on the left, so circulation and arm ordering are CLOCKWISE, and the
# LEFT turn is the near-side (non-conflicting) one. The RIGHT turn crosses opposing
# traffic and is the capacity-limiting movement.
DRIVES_ON = "left"
ARM_ORDER = "clockwise"

# --- survey -----------------------------------------------------------------
SURVEY_DATES = ("2026-05-11", "2026-05-12")   # Monday, Tuesday
SURVEY_DIRS = ("INT_11-05-2026", "INT_12-05-2026")
BIN_MINUTES = 15
BINS_PER_DAY = 96                # 24 h of 15-min bins, running 08:00 -> 08:00

# The six junctions, arms listed CLOCKWISE from north as the survey sheets order them.
# N and S arms are the corridor itself; E and W are the cross-streets.
JUNCTIONS = {
    "TMC-01": ("Mansarover Metro", "Patrika Gate", "Sanganer Stadium", "Sumer Nagar"),
    "TMC-02": ("Mansarover Metro", "Durgapur", "Sanganer Stadium", "Mohanpura"),
    "TMC-03": ("Mansarover Metro", "Patel Marg Crossing", "Sanganer Stadium", "Sumer Nagar"),
    "TMC-04": ("Mansarover Metro", "VT Road", "Sanganer Stadium", "Dholai"),
    "TMC-05": ("Mansarover Metro", "Rajatpath", "Sanganer Stadium", "Mangyawas"),
    "TMC-06": ("Mansarover Metro", "New Aatish Market", "Sanganer Stadium", "Mansarover"),
}

# --- junction coordinates ---------------------------------------------------
# Junction positions and the corridor centreline, both supplied by JDA as a KML.
#
# The earlier derivation is gone, not amended, because it was wrong at the root: we
# matched the survey's arm names against JDA's signal-free scheme names, then placed each
# junction at the nearest traffic-signal cluster in the CAD. That put six junctions on a
# parallel road, 269 to 950 m from where JDA's own points sit. Three were labelled
# "name match" and drawn as confirmed, which conflated identity with position - the
# survey's arm name told us a junction existed, never where it was.
#
# Checked on receipt, not taken on trust:
#   every point falls inside a sane Jaipur box
#   every point sits 2 to 10 m off JDA's own centreline, so they are on that road
#   ordering along that centreline matches the placemark numbering, so 1 = TMC-01
#   the CAD drawing covers the centreline, all 14 vertices inside its extent
# The JDA names carried NO trailing padding until it was added here to line the columns
# up, and that padding travelled all the way into the published JSON and the workbook as
# "B-2 Bypass ". Source-file cosmetics are not data. Aligned with the comment instead.
JUNCTION_COORDS = {
    #            lat          lon           JDA name        cluster  source
    "TMC-01": (26.8395707, 75.7678008, "B-2 Bypass",  "C8",  "JDA KML"),
    "TMC-02": (26.8460752, 75.7647913, "Vijay Path",  "C21", "JDA KML"),
    "TMC-03": (26.8504204, 75.7627824, "Patel Marg",  "C26", "JDA KML"),
    "TMC-04": (26.8564306, 75.7586546, "VT Road",     "C18", "JDA KML"),
    "TMC-05": (26.8630543, 75.7541118, "Rajat Path",  "C22", "JDA KML"),
    "TMC-06": (26.8767054, 75.7476133, "Bhrigu Path", "C28", "JDA KML"),
}

# JDA's centreline, straight from the KML. 4,625 m against the 6,517 m we had derived by
# taking the longest "alignment" line out of the CAD, which is the error this fixes.
# Chainage, corridor ordering and the U-turn detour distances are all measured along
# THIS, and the map draws it rather than joining our own pins.
#
# STORED NORTH TO SOUTH, WHICH IS HOW THE KML ORDERS IT, AND REVERSED BELOW.
# The KML runs from Bhrigu Path down to B-2 Bypass, so chainage taken straight off it
# started at TMC-06 and counted DOWN to 4,620 m at TMC-01 - the reverse of the survey's
# own junction numbering, and unreadable against any drawing that numbers the other way.
# The vertex list is kept in the order JDA supplied it, and the direction is applied in
# one place so the convention is a stated decision rather than a property of a file.
_KML_CENTRELINE_N_TO_S = [   # lon, lat
    (75.7475901, 26.8767279),
    (75.7476610, 26.8761611),
    (75.7489347, 26.8736845),
    (75.7510200, 26.8693287),
    (75.7536447, 26.8640933),
    (75.7544285, 26.8624599),
    (75.7559417, 26.8593660),
    (75.7565723, 26.8582708),
    (75.7585921, 26.8563545),
    (75.7610023, 26.8541978),
    (75.7628329, 26.8504361),
    (75.7648088, 26.8459617),
    (75.7662462, 26.8427872),
    (75.7677936, 26.8395192),
]

# Which end is chainage zero. South, so that chainage increases with the junction number:
# TMC-01 at the Sanganer Stadium end is 0 and TMC-06 at Mansarovar Metro is the far end.
# Distances BETWEEN points are unaffected either way, so every detour and every width is
# unchanged by this - only the station a feature is reported at moves.
#
# JDA has not stated its own convention. Reviewer question 2 asks for it; if they chain
# from the north this flips to "north" and nothing else changes.
CHAINAGE_FROM = "north"
CHAINAGE_ZERO_AT = "Mansarovar Metro end (J1 / survey sheet TMC-06)"
CORRIDOR_CENTRELINE = (list(reversed(_KML_CENTRELINE_N_TO_S))
                       if CHAINAGE_FROM == "south" else list(_KML_CENTRELINE_N_TO_S))

# The road name, restored and now SOURCED rather than inferred.
#
# We named it New Sanganer Road by inference, JDA's reviewer challenged it, and it was
# withdrawn. JDA then supplied a KML whose corridor LineString is itself named
# "NEW SANGANER ROAD", so the name comes from them. The withdrawal stands as a record of
# how it was arrived at the first time: by assumption, not by evidence.
CORRIDOR_ROAD = "New Sanganer Road"
CORRIDOR_ROAD_SOURCE = "named in JDA's supplied KML"

# JDA is converting this road to signal-free operation with 7 U-turns, which is
# almost certainly why the survey exists - and the survey counted no U-turns.
JDA_SCHEME = "signal-free corridor, 7 U-turn bays"

# --- scheme junction numbering ------------------------------------------------
# TWO NUMBERINGS, AND THE REASON THERE ARE TWO.
#
# The workbooks are named 01_TMC .. 06_TMC and their codes run SOUTH to north, so TMC-01
# is at Sanganer Stadium. A scheme drawing numbers junctions along the corridor from its
# start, and this corridor starts at Mansarovar Metro - so the scheme numbering runs the
# other way: J1 at Mansarovar Metro, J6 at Sanganer Stadium.
#
# JDA's reviewer reads the map, not the workbook index, so J-numbers are what is DISPLAYED
# everywhere. The TMC code is kept beside it on every table, popup and sheet, because it
# is the survey sheet a figure traces back to and renaming it would break that. Renumbering
# a client's own survey files is not something a consultant gets to do; cross-referencing
# them is standard practice.
#
# Derived from position, not typed. Sorting by latitude descending gives north to south on
# this corridor, and a test asserts that ordering agrees with chainage along JDA's
# centreline - so if a junction ever moves, the numbering follows rather than going stale.
SCHEME_NO = {code: i for i, code in enumerate(
    sorted(JUNCTION_COORDS, key=lambda c: -JUNCTION_COORDS[c][0]), start=1)}
SCHEME_LABEL = {code: f"J{n}" for code, n in SCHEME_NO.items()}
SURVEY_OF = {label: code for code, label in SCHEME_LABEL.items()}
NUMBERING_NOTE = ("J1 to J6 run north to south from Mansarovar Metro, which is how the "
                  "scheme reads on a drawing. The survey workbooks are numbered the other "
                  "way, TMC-01 at Sanganer Stadium, and that code is kept beside every "
                  "figure so it traces back to its source sheet.")

# The survey counts LEFT / STRAIGHT / RIGHT only. U-turns were never surveyed —
# that is a gap to report, not a zero to assume.
MOVEMENTS = ("Left", "Straight", "Right")
UTURNS_SURVEYED = False

if __name__ == "__main__":
    print(f"Corridor : {CORRIDOR_NAME}, {CITY}")
    print(f"Junctions: {len(JUNCTIONS)}  ({', '.join(JUNCTIONS)})")
    print(f"Movements: {len(JUNCTIONS) * 4 * len(MOVEMENTS)} total "
          f"({4 * len(MOVEMENTS)} per junction), U-turns surveyed: {UTURNS_SURVEYED}")
    print(f"Source   : {SOURCE}  exists={SOURCE.exists()}")
