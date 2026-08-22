"""
homography.py — image pixels to UTM 43N metres.

The bridge between video and the survey drawing. Because both ends live in EPSG:32643,
counting zones can be generated from the CAD geometry rather than hand-drawn on a frame.

Two things here correct errata recorded against the methodology's own version:

  float64, with a local origin. The original held UTM coordinates in float32. At a
  northing near 2,976,040 that quantises to roughly 0.25 m before any real error is
  measured, against a 0.5 m acceptance gate - half the budget spent on storage format.
  Subtracting a junction-local origin keeps the numbers small and the precision intact.

  Plain least-squares, not a robust estimator. An earlier erratum in the methodology
  recommended LMEDS. Measurement says that is wrong at this sample size: across 40 random
  draws per cell, with 5-8 hand-picked GCPs LMEDS is 3-10x worse in median RMSE and
  reaches 2.0 m at p90 against 0.08 m for least-squares. LMEDS minimises the median
  residual over minimal subsets, and with so few points it can settle on a degenerate
  four-point fit that is perfect locally and badly wrong elsewhere. Robust estimators
  need redundancy; hand-picked control does not supply it. Use LMEDS or RANSAC only for
  large automatically-matched point sets where genuine outliers exist.

GROUND CONTROL POINTS
No field survey is needed. The JDA drawing carries 1,906 surveyed point features -
manholes, light bases, transformer plinths, gas markers - and every junction has 11 to
17 of them within 60 m. `candidates()` lists them for a junction; photograph the ones
visible from the camera and pair each with its pixel coordinate.

Run:  uv run python src/homography.py            # self-test
      uv run python src/homography.py TMC-04     # list GCP candidates at a junction
"""
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import CRS_GEO, CRS_WORK, JUNCTION_COORDS, OUT_DATA, ROOT

# Point layers that are sharp, permanent and identifiable in a video frame.
GCP_LAYERS = {
    "MAIN HOLE": "manhole cover",
    "GAS STONE": "gas marker stone",
    "BORING-": "borehole cover",
    "TRANSFORMER": "transformer plinth",
    "HI MAX LIGHT": "high-mast light base",
    "ELECTRIC PANEL BOARD": "panel board",
    "TELEPHONE TOWER": "tower base",
}
RMSE_GATE_M = 0.5      # methodology acceptance gate near the junction centre
MIN_GCPS = 4           # a homography needs 4; 6-8 lets you compute residuals and drop one


def candidates(junction, radius_m=60.0):
    """Surveyed point features near a junction, nearest first. Coordinates in UTM 43N."""
    from pyproj import Transformer
    from src.atlas import read_geometry
    dxf = next((ROOT / "00_source" / "dxf").glob("*.dxf"), None)
    if dxf is None:
        raise SystemExit("No DXF in 00_source/dxf/ - convert the DWG first.")
    to_utm = Transformer.from_crs(CRS_GEO, CRS_WORK, always_xy=True)
    lat, lon = JUNCTION_COORDS[junction][0], JUNCTION_COORDS[junction][1]
    jx, jy = to_utm.transform(lon, lat)

    geom = read_geometry(dxf)
    out = []
    for _cat, items in geom.items():
        for layer, kind, vs in items:
            if kind == "point" and layer in GCP_LAYERS:
                x, y = vs[0]
                d = math.dist((x, y), (jx, jy))
                if d <= radius_m:
                    out.append(dict(kind=GCP_LAYERS[layer], layer=layer,
                                    easting=round(x, 2), northing=round(y, 2),
                                    dist_m=round(d, 1)))
    return sorted(out, key=lambda r: r["dist_m"])


def fit(img_pts, world_pts, origin=None):
    """
    Fit pixels -> UTM metres.

    img_pts   (N,2) pixel coordinates
    world_pts (N,2) UTM 43N eastings/northings
    returns   (H, origin, stats)

    World coordinates are shifted by `origin` before fitting and must be shifted back
    after. This is what keeps float64 precision meaningful at UTM magnitudes.
    """
    img = np.asarray(img_pts, dtype=np.float64).reshape(-1, 2)
    wld = np.asarray(world_pts, dtype=np.float64).reshape(-1, 2)
    if len(img) != len(wld):
        raise ValueError("img_pts and world_pts must be the same length")
    if len(img) < MIN_GCPS:
        raise ValueError(f"{len(img)} GCPs supplied, need at least {MIN_GCPS}")

    if origin is None:
        origin = wld.mean(axis=0)
    origin = np.asarray(origin, dtype=np.float64)
    local = wld - origin

    # method=0 is plain least-squares over all points. See the module docstring: robust
    # estimators are worse here, not better, because there is no outlier population and
    # too little redundancy for them to work with.
    H, mask = cv2.findHomography(img, local, 0)
    if H is None:
        raise RuntimeError("Homography fit failed - check the GCP pairing order")

    proj = cv2.perspectiveTransform(img.reshape(-1, 1, 2), H).reshape(-1, 2)
    resid = np.linalg.norm(proj - local, axis=1)
    stats = dict(
        n=len(img),
        rmse_m=float(np.sqrt((resid ** 2).mean())),
        max_residual_m=float(resid.max()),
        residuals_m=[round(float(r), 3) for r in resid],
        inliers=int(mask.sum()) if mask is not None else len(img),
        passes_gate=bool(np.sqrt((resid ** 2).mean()) < RMSE_GATE_M),
    )
    return H, origin, stats


def to_world(H, origin, pts):
    """Pixels -> UTM 43N metres. pts (N,2)."""
    p = np.asarray(pts, dtype=np.float64).reshape(-1, 1, 2)
    local = cv2.perspectiveTransform(p, H).reshape(-1, 2)
    return local + np.asarray(origin, dtype=np.float64)


def footpoint(bbox):
    """
    Bottom-centre of a bounding box.

    A homography is only valid for points ON the ground plane. A box centroid sits at
    roughly half vehicle height, so projecting it displaces a bus several metres further
    than a motorcycle. The footpoint is where the vehicle meets the road.
    """
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, y2)


def _plant_and_recover(seed=0, noise_px=0.0, n=8):
    """Generate a known homography, project GCPs through it, and try to recover it."""
    rng = np.random.default_rng(seed)
    origin = np.array([575330.0, 2971680.0])          # near TMC-04 in UTM 43N
    # a plausible oblique camera view of a ~60 m square of ground
    src = np.array([[0, 0], [1920, 0], [1920, 1080], [0, 1080]], dtype=np.float64)
    dst = np.array([[-30, 34], [28, 30], [22, -18], [-24, -14]], dtype=np.float64)
    H_true = cv2.getPerspectiveTransform(src.astype(np.float32), dst.astype(np.float32))

    px = np.column_stack([rng.uniform(120, 1800, n), rng.uniform(120, 960, n)])
    local = cv2.perspectiveTransform(px.reshape(-1, 1, 2), H_true).reshape(-1, 2)
    world = local + origin
    if noise_px:
        px = px + rng.normal(0, noise_px, px.shape)
    return px, world, origin, H_true


if __name__ == "__main__":
    if len(sys.argv) > 1:
        j = sys.argv[1].upper()
        if j not in JUNCTION_COORDS:
            raise SystemExit(f"Unknown junction {j}. One of: {', '.join(JUNCTION_COORDS)}")
        cands = candidates(j)
        print(f"Surveyed GCP candidates within 60 m of {j} ({JUNCTION_COORDS[j][2]})\n")
        print(f"  {'dist':>6}  {'feature':<22}{'easting':>12}{'northing':>14}")
        print("  " + "-" * 56)
        for c in cands:
            print(f"  {c['dist_m']:>5.1f}m  {c['kind']:<22}{c['easting']:>12,.2f}"
                  f"{c['northing']:>14,.2f}")
        print(f"\n  {len(cands)} candidates. Photograph 6 that are visible from the camera,")
        print("  spread across the frame - corners and centre, not clustered. Clustered")
        print("  points give a fit that is excellent locally and wildly wrong at the edges.")
        OUT_DATA.mkdir(parents=True, exist_ok=True)
        p = OUT_DATA / f"gcp_candidates_{j}.json"
        p.write_text(json.dumps(dict(junction=j, radius_m=60, candidates=cands), indent=1))
        print(f"\n  written: {p}")
        sys.exit(0)

    print("SELF-TEST - no footage exists, so the fit is checked by planting a known")
    print("homography, projecting ground control through it, and recovering it.\n")
    print(f"  {'GCPs':>5}{'pixel noise':>13}{'RMSE m':>10}{'max resid':>11}"
          f"{'gate <0.5m':>12}")
    print("  " + "-" * 51)
    ok = 0
    cases = [(8, 0.0), (8, 0.5), (6, 1.0), (12, 2.0), (6, 3.0)]
    for n, noise in cases:
        px, world, origin, _ = _plant_and_recover(seed=n * 7 + int(noise * 10),
                                                  noise_px=noise, n=n)
        _H, _o, st = fit(px, world, origin=origin)
        good = st["passes_gate"]
        ok += good
        print(f"  {n:>5}{noise:>12.1f}px{st['rmse_m']:>10.3f}{st['max_residual_m']:>11.3f}"
              f"{'PASS' if good else 'FAIL':>12}")
    print(f"\n  GATE - homography recovered within {RMSE_GATE_M} m RMSE: "
          f"**{ok} of {len(cases)}**")

    # the erratum, demonstrated rather than asserted
    px, world, origin, _ = _plant_and_recover(seed=3, noise_px=0.0, n=8)
    H64, o64, s64 = fit(px, world, origin=origin)
    w32 = np.asarray(world, dtype=np.float32).astype(np.float64)   # round-trip via float32
    H32, o32, s32 = fit(px, w32, origin=None)
    print(f"\n  The float32 erratum, measured:")
    print(f"    float64 with a local origin : RMSE {s64['rmse_m']:.4f} m")
    print(f"    world coords through float32: RMSE {s32['rmse_m']:.4f} m")
    print(f"    quantisation cost           : {abs(s32['rmse_m']-s64['rmse_m']):.4f} m "
          f"of a {RMSE_GATE_M} m budget")
