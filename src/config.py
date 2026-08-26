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
JUNCTION_COORDS = {
    #          lat          lon          JDA name       cluster  source
    "TMC-01": (26.8395707, 75.7678008, "B-2 Bypass ", "C8 ", "JDA KML"),
    "TMC-02": (26.8460752, 75.7647913, "Vijay Path ", "C21", "JDA KML"),
    "TMC-03": (26.8504204, 75.7627824, "Patel Marg ", "C26", "JDA KML"),
    "TMC-04": (26.8564306, 75.7586546, "VT Road    ", "C18", "JDA KML"),
    "TMC-05": (26.8630543, 75.7541118, "Rajat Path ", "C22", "JDA KML"),
    "TMC-06": (26.8767054, 75.7476133, "Bhrigu Path", "C28", "JDA KML"),
}

# JDA's centreline, straight from the KML. 4,625 m against the 6,517 m we had derived by
# taking the longest "alignment" line out of the CAD, which is the error this fixes.
# Chainage, corridor ordering and the U-turn detour distances are all measured along
# THIS, and the map draws it rather than joining our own pins.
CORRIDOR_CENTRELINE = [   # lon, lat
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
