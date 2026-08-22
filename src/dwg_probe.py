"""
dwg_probe.py — Phase 0 coordinate-system discovery for the JDA survey drawing.

Phase 0 of docs/jaipur_corridor_study.md calls this the single highest-risk unknown
in the project: every downstream metre depends on getting the CRS right. This runs
the magnitude test on the drawing's own header extents and reports the verdict.

Needs LibreDWG (`brew install libredwg`). LibreDWG recovers the header reliably but
not the entity sections of this file — for geometry, convert with ODA File Converter
to ASCII DXF and run the Phase 1.2 layer inventory instead.

Run:  uv run python src/dwg_probe.py
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import CRS_GEO, CRS_WORK, JAIPUR_UTM_ANCHOR, ROOT

DWG = ROOT / "00_source" / "dwg" / "mansrover  road final.dwg"
TO_WGS = Transformer.from_crs(CRS_WORK, CRS_GEO, always_xy=True)


def header_extents(dwg_path):
    """Convert to DXF and read $EXTMIN/$EXTMAX. Returns (xmin, ymin, xmax, ymax)."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "probe.dxf"
        subprocess.run(["dwg2dxf", "-o", str(out), str(dwg_path)],
                       capture_output=True, check=False)
        if not out.exists():
            raise RuntimeError("dwg2dxf produced nothing — is libredwg installed?")
        lines = out.read_text(errors="ignore").splitlines()

    def grab(var):
        i = lines.index(var)
        vals = {}
        for j in range(i + 1, min(i + 8, len(lines)), 2):
            vals[lines[j].strip()] = lines[j + 1].strip()
        return float(vals["10"]), float(vals["20"])

    xmin, ymin = grab("$EXTMIN")
    xmax, ymax = grab("$EXTMAX")
    return xmin, ymin, xmax, ymax


def classify(xmin, ymin):
    """Phase 0.1 magnitude heuristic."""
    if 60 < xmin < 100 and 5 < ymin < 40:
        return "EPSG:4326", "WGS84 geographic degrees"
    if 100_000 < xmin < 1_000_000 and 2_000_000 < ymin < 4_000_000:
        return "EPSG:32643", "UTM Zone 43N — the working CRS for this project"
    if xmin < 50_000:
        return None, "drawing-local / unreferenced — needs GCP fitting (Phase 0.3)"
    return None, "unrecognised, likely a local municipal grid — needs GCP fitting"


if __name__ == "__main__":
    if not DWG.exists():
        raise SystemExit(f"Not found: {DWG}")

    xmin, ymin, xmax, ymax = header_extents(DWG)
    epsg, verdict = classify(xmin, ymin)

    print(f"drawing   : {DWG.name}")
    print(f"X range   : {xmin:>14,.2f}  ->  {xmax:>14,.2f}   span {xmax-xmin:>9,.1f}")
    print(f"Y range   : {ymin:>14,.2f}  ->  {ymax:>14,.2f}   span {ymax-ymin:>9,.1f}")
    print(f"\nverdict   : {verdict}")

    if epsg != CRS_WORK:
        raise SystemExit(f"GATE FAILED — expected {CRS_WORK}, got {epsg or 'unreferenced'}")

    # Phase 0 insists on a plot-on-imagery check. The numeric half of that is
    # confirming the drawing lands near Jaipur rather than in the Arabian Sea.
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    ax, ay = JAIPUR_UTM_ANCHOR
    off = ((cx - ax) ** 2 + (cy - ay) ** 2) ** 0.5
    print(f"\ncentroid  : E {cx:,.1f}  N {cy:,.1f}")
    print(f"offset from the Jaipur anchor {JAIPUR_UTM_ANCHOR}: {off/1000:.2f} km")

    print("\ncorners in WGS84 (paste into Google Maps to confirm by eye):")
    for label, (x, y) in {"SW": (xmin, ymin), "NW": (xmin, ymax),
                          "NE": (xmax, ymax), "SE": (xmax, ymin),
                          "centre": (cx, cy)}.items():
        lon, lat = TO_WGS.transform(x, y)
        print(f"  {label:<7} {lat:.6f}, {lon:.6f}")

    ok = off < 15_000
    print(f"\nGATE — drawing within 15 km of Jaipur centre: {'PASS' if ok else 'FAIL'} "
          f"({off/1000:.2f} km)")
    print(f"GATE — CRS is {CRS_WORK}: PASS")
    print("\nGeometry is NOT extracted here. LibreDWG reads this file's header but not "
          "its entity sections;\nconvert with ODA File Converter (ASCII DXF, ACAD 2018) "
          "for the linework and layer table.")
