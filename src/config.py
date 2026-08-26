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
# The workbooks carry no georeference. These come from matching the survey's arm
# names against the junctions JDA names in its signal-free
# scheme (Bhrigu Path, Rajat Path, VT Road, Patel Marg, Vijay Path, B-2 Bypass),
# then locating each on the survey drawing's own alignment.
#
# Three arm names match exactly - Rajatpath (TMC-05), VT Road (TMC-04), Patel Marg
# Crossing (TMC-03) - and they fall in the same order JDA lists them, which is what
# fixes the sequence. Positions are the centroid of the traffic-signal cluster at
# each junction, all within 10 m of the alignment.
#
# CONFIDENCE is per junction and honest: the three name-matched ones are firm, the
# rest are placed by position in the sequence. The survey contractor's location
# schedule would settle it outright. Every downstream output carries this flag.
# EVERY POSITION HERE IS UNCONFIRMED, and the distinction this table used to draw was
# wrong in a way worth spelling out.
#
# Three rows were labelled "name match" and shown as confirmed on the map. What matched
# was the NAME: the survey's own arm label, say "Patel Marg Crossing", against a junction
# JDA names in its scheme. That tells us the junction exists. It says nothing about where
# it is. The position of all six came from picking one of 39 signal clusters out of the
# CAD, and JDA's reviewer says those picks sit on the wrong road.
#
# So "name match" was being presented as position confidence when it was only ever
# identity confidence. Two different claims, one label, and the map showed the stronger
# one. All six are now marked unconfirmed until JDA supplies the survey location
# schedule or their own pins.
#
# Nothing else in the pipeline depends on these coordinates. The counts, the movement
# matrices, the PCU correction and the U-turn analysis all come from the workbooks. What
# they do drive is chainage, and therefore corridor ordering and the detour distances,
# which is why those carry their own caveats.
JUNCTION_COORDS = {
    #          lat        lon        JDA name        cluster  confidence
    "TMC-01": (26.840536, 75.770289, "B-2 Bypass",   "C8",  "unconfirmed"),
    "TMC-02": (26.847800, 75.769429, "Vijay Path",   "C21", "unconfirmed"),
    "TMC-03": (26.852267, 75.767456, "Patel Marg",   "C26", "unconfirmed"),
    "TMC-04": (26.860842, 75.763579, "VT Road",      "C18", "unconfirmed"),
    "TMC-05": (26.864799, 75.758347, "Rajat Path",   "C22", "unconfirmed"),
    "TMC-06": (26.871403, 75.755127, "Bhrigu Path",  "C28", "unconfirmed"),
}
# The road is deliberately UNNAMED. Every one of the six junctions carries
# "Mansarover Metro" as its north arm and "Sanganer Stadium" as its south arm, so the
# corridor is defined by the survey itself. Which physical road that is was our
# inference and it was challenged, so the name is withdrawn until JDA confirms it.
# Nothing downstream depends on the name; the counts, the matrices and the movement
# analysis are unaffected.
CORRIDOR_ROAD = "the Mansarover Metro \u2013 Sanganer Stadium corridor"
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
