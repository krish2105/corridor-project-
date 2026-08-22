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
# names against the junctions JDA names on New Sanganer Road in its signal-free
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
JUNCTION_COORDS = {
    #          lat        lon        JDA name        cluster  confidence
    "TMC-01": (26.840536, 75.770289, "B-2 Bypass",   "C8",  "inferred"),
    "TMC-02": (26.847800, 75.769429, "Vijay Path",   "C21", "inferred"),
    "TMC-03": (26.852267, 75.767456, "Patel Marg",   "C26", "name match"),
    "TMC-04": (26.860842, 75.763579, "VT Road",      "C18", "name match"),
    "TMC-05": (26.864799, 75.758347, "Rajat Path",   "C22", "name match"),
    "TMC-06": (26.871403, 75.755127, "Bhrigu Path",  "C28", "inferred"),
}
CORRIDOR_ROAD = "New Sanganer Road"
# JDA is converting this road to signal-free operation with 7 U-turns, which is
# almost certainly why the survey exists - and the survey counted no U-turns.
JDA_SCHEME = "signal-free New Sanganer Road, 7 U-turns"

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
