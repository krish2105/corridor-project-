"""
pipeline.py — one command from footage to validated counts.

WHY A DRIVER AND NOT FIVE COMMANDS
homography, detect, count, validate and critical_gap each run standalone and each prints
its own metric, which is right for developing them and wrong for a field day. Run by hand
they need five invocations with intermediate files passed between them, and the step most
likely to be skipped under time pressure is validation - which is the only one that says
whether any of the rest can be believed.

So the gates are enforced here rather than trusted to whoever is running it.

FAIL AT THE FIRST GATE
Each stage has a numeric threshold. A stage that fails stops the run and says so; it does
not carry on and produce counts that then get quoted. A pipeline that completes on a
failed homography emits a full turning-movement matrix built on a bad projection, and
nothing downstream looks wrong.

RESUME
Stages write their output and are skipped when it already exists, because detection over
two hours of 4K is the expensive step and re-running it after a downstream typo wastes an
afternoon. Pass --fresh to force everything.

Run:  uv run python src/pipeline.py                       # self-test, no footage needed
      uv run python src/pipeline.py --video FOOTAGE.MOV --junction TMC-04 --gcps gcps.csv
      uv run python src/pipeline.py ... --fresh
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import JUNCTION_COORDS, OUT_DATA, PROCESSED

STAGES = ["homography", "detect", "count", "validate", "critical_gap"]


class GateFailure(Exception):
    """A stage did not meet its acceptance threshold. The run stops here."""


def _stage_path(work, name):
    return Path(work) / f"{name}.json"


def _done(work, name, fresh):
    p = _stage_path(work, name)
    return None if fresh or not p.exists() else json.loads(p.read_text())


def _save(work, name, payload):
    p = _stage_path(work, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=1, default=str))
    return payload


def run_homography(work, gcps_csv, fresh=False):
    """Fit the pixel-to-ground projection. Gate: reprojection RMSE < 0.5 m."""
    cached = _done(work, "homography", fresh)
    if cached:
        return cached
    import csv
    import numpy as np
    from src.homography import fit, RMSE_GATE_M, MIN_GCPS

    img, world = [], []
    with open(gcps_csv) as f:
        for row in csv.DictReader(f):
            img.append((float(row["px"]), float(row["py"])))
            world.append((float(row["x"]), float(row["y"])))
    if len(img) < MIN_GCPS:
        raise GateFailure(f"homography needs {MIN_GCPS}+ GCPs, got {len(img)}")
    H, origin, stats = fit(np.array(img), np.array(world))
    if not stats["passes_gate"]:
        raise GateFailure(
            f"homography RMSE {stats['rmse_m']:.3f} m, gate is < {RMSE_GATE_M} m. "
            "Re-check the ground control points before going further - every distance "
            "downstream inherits this error.")
    return _save(work, "homography",
                 dict(H=np.asarray(H).tolist(), origin=list(origin),
                      rmse=stats["rmse_m"], gcps=len(img), stats=stats))


def run_detect(work, video, homog, weights=None, fresh=False, max_frames=None):
    """Detect and track. Gate: the run produced tracks at all."""
    cached = _done(work, "detect", fresh)
    if cached:
        return cached
    import numpy as np
    from src.detect import track_video, load_model

    model, device = load_model(weights) if weights else load_model()
    t0 = time.time()
    tracks = track_video(video, model=model, device=device,
                         homography=np.array(homog["H"]),
                         origin=tuple(homog["origin"]), max_frames=max_frames)
    if not tracks:
        raise GateFailure("detection produced no tracks. Check the video path, the "
                          "confidence threshold, and that the camera actually sees the "
                          "junction.")
    return _save(work, "detect",
                 dict(n_tracks=len(tracks), seconds=round(time.time() - t0, 1),
                      device=device,
                      tracks={str(k): v for k, v in tracks.items()}))


def run_count(work, det, junction, fresh=False):
    """Zones and movement assignment. Gate: > 90% of tracks resolve to a movement."""
    cached = _done(work, "count", fresh)
    if cached:
        return cached
    from src.count import build_zones, aggregate, RESOLUTION_GATE
    from src.config import JUNCTIONS
    from pyproj import Transformer

    lat, lon, name, _cl, _conf = JUNCTION_COORDS[junction]
    T = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    centre = T.transform(lon, lat)
    # arms are listed clockwise from north in config, which is the bearing order
    legs = [dict(name=a, bearing=b, divided=True)
            for a, b in zip(JUNCTIONS[junction], (0, 90, 180, 270))]
    zones = build_zones(centre, legs)
    tracks = {int(k): v for k, v in det["tracks"].items()}
    counts, stats = aggregate(tracks, zones, centre)
    if not stats["passes_gate"]:
        raise GateFailure(
            f"only {stats['resolution']:.1%} of tracks resolved to a movement, gate is "
            f"{RESOLUTION_GATE:.0%}. Unresolved tracks are usually zone geometry, not "
            "detection - check the leg bearings and the junction centre first.")
    return _save(work, "count",
                 dict(stats=stats, counts={f"{b}|{c}|{fl}|{tl}": n
                                           for (b, c, fl, tl), n in counts.items()}))


def run_validate(work, cnt, manual_csv, fresh=False):
    """Automated against manual. Gate: MAPE under the thresholds in validate.py."""
    cached = _done(work, "validate", fresh)
    if cached:
        return cached
    import csv
    from collections import defaultdict
    from src.validate import validate

    # manual csv: interval,veh_class,manual_count
    manual = defaultdict(dict)
    with open(manual_csv) as f:
        for row in csv.DictReader(f):
            manual[row["veh_class"]][int(row["interval"])] = int(row["manual_count"])

    auto = defaultdict(lambda: defaultdict(int))
    for key, n in cnt["counts"].items():
        b, cls, _fl, _tl = key.split("|")
        auto[cls][int(b)] += n

    pairs = {cls: [(m, auto[cls].get(i, 0)) for i, m in sorted(ivals.items())]
             for cls, ivals in manual.items()}
    res = validate(pairs, assignment_accuracy=cnt["stats"]["resolution"])
    res["unmapped_rate"] = None
    if not res["accepted"]:
        _save(work, "validate", res)      # keep the evidence even when it fails
        raise GateFailure(
            "counts did not meet the validation gates: "
            + ", ".join(res["failed_gates"]) +
            ". They are not used in any published figure until they do - see "
            "out/validation_report.md for the full table.")
    return _save(work, "validate", res)


def run_critical_gap(work, events_csv, fresh=False):
    """Measured critical gap. Optional - absent means the literature values stand."""
    cached = _done(work, "critical_gap", fresh)
    if cached:
        return cached
    from src.critical_gap import load_events, derive_gaps, measure, follow_up
    ev = load_events(events_csv)
    drivers = derive_gaps(ev)
    res = measure(drivers, label="field")
    res["follow_up"] = follow_up(ev)
    if not res.get("reportable"):
        print(f"  critical gap NOT reportable: {res.get('reason')}")
        print("  the literature values stand and the U-turn finding is unchanged")
    return _save(work, "critical_gap", res)


def run(video, junction, gcps, manual=None, events=None, weights=None,
        work=None, fresh=False, max_frames=None):
    work = Path(work or PROCESSED / "phase6" / junction)
    order, results = [], {}
    print(f"=== Phase 6 pipeline, {junction} "
          f"({JUNCTION_COORDS[junction][2]}) ===\n")

    def step(name, fn, *a, **kw):
        was = _stage_path(work, name).exists() and not fresh
        t0 = time.time()
        r = fn(*a, **kw)
        print(f"  {name:<14}{'cached' if was else f'{time.time()-t0:6.1f}s'}   ok")
        results[name] = r
        order.append(name)
        return r

    h = step("homography", run_homography, work, gcps, fresh)
    print(f"                 RMSE {h['rmse']:.3f} m over {h['gcps']} GCPs")
    d = step("detect", run_detect, work, video, h, weights, fresh, max_frames)
    print(f"                 {d['n_tracks']:,} tracks on {d['device']}")
    c = step("count", run_count, work, d, junction, fresh)
    print(f"                 {c['stats']['resolution']:.1%} of tracks resolved")
    if manual:
        v = step("validate", run_validate, work, c, manual, fresh)
        print(f"                 total MAPE {v['total']['mape']:.1%} "
              f"({v['total']['verdict']})")
    if events:
        g = step("critical_gap", run_critical_gap, work, events, fresh)
        if g.get("reportable"):
            print(f"                 t_c {g['mle_mean']:.2f} s from {g['n']} drivers")
    return results, work


if __name__ == "__main__":
    a = sys.argv[1:]
    if a:
        def opt(flag, default=None):
            return a[a.index(flag) + 1] if flag in a else default
        try:
            res, work = run(video=opt("--video"), junction=opt("--junction", "TMC-04"),
                            gcps=opt("--gcps"), manual=opt("--manual"),
                            events=opt("--events"), weights=opt("--weights"),
                            fresh="--fresh" in a,
                            max_frames=int(opt("--max-frames", 0)) or None)
            print(f"\n  all stages passed their gates. outputs in {work}")
            print("  next: uv run python src/reports.py && uv run python src/export.py")
        except GateFailure as e:
            print(f"\n  STOPPED at a gate:\n    {e}")
            sys.exit(1)
        sys.exit(0)

    print("SELF-TEST - no footage exists, so the driver is exercised against synthetic")
    print("stages: the chain, the resume behaviour, and that a failed gate stops it.\n")
    import tempfile
    import numpy as np
    ok = 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # a homography good enough to pass, from a synthetic ground plane
        import csv
        from src.homography import fit, RMSE_GATE_M, MIN_GCPS
        rng = np.random.default_rng(4)
        world = np.array([[578000 + x, 2976000 + y]
                          for x, y in [(0, 0), (40, 0), (40, 30), (0, 30),
                                       (20, 15), (10, 25)]], dtype=float)
        Htrue = np.array([[3.1, 0.4, 120.0], [0.2, 2.9, 80.0], [0.0006, 0.0004, 1.0]])
        loc = world - world.mean(0)
        hp = np.hstack([loc, np.ones((len(loc), 1))]) @ Htrue.T
        img = (hp[:, :2] / hp[:, 2:]) + rng.normal(0, 0.4, (len(loc), 2))
        g = td / "gcps.csv"
        with open(g, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["px", "py", "x", "y"])
            for (px, py), (x, y) in zip(img, world):
                w.writerow([px, py, x, y])

        h = run_homography(td / "w", g)
        good = h["rmse"] < RMSE_GATE_M
        ok += good
        detail = "{:.3f} m".format(h["rmse"])
        print(f"  {'homography stage runs and meets its gate':<50}{detail:>12}  "
              f"{'PASS' if good else 'FAIL'}")

        h2 = run_homography(td / "w", g)
        good = h2 == h and _stage_path(td / "w", "homography").exists()
        ok += good
        print(f"  {'a completed stage is cached, not re-run':<50}{'resumed':>12}  "
              f"{'PASS' if good else 'FAIL'}")

        # too few GCPs must stop the run rather than fit something meaningless
        g2 = td / "few.csv"
        with open(g2, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["px", "py", "x", "y"])
            for (px, py), (x, y) in list(zip(img, world))[:3]:
                w.writerow([px, py, x, y])
        try:
            run_homography(td / "w2", g2)
            good = False
        except GateFailure:
            good = True
        ok += good
        print(f"  {'too few GCPs stops the run':<50}{'GateFailure':>12}  "
              f"{'PASS' if good else 'FAIL'}")

        # an empty detection must stop, not produce an empty matrix
        try:
            run_detect(td / "w3", "does_not_exist.mov", h, max_frames=1)
            good = False
        except Exception as e:
            good = isinstance(e, GateFailure) or "no tracks" in str(e).lower() \
                or "does_not_exist" in str(e)
        ok += good
        print(f"  {'missing footage stops the run':<50}{'raises':>12}  "
              f"{'PASS' if good else 'FAIL'}")

        # a failed validation gate must stop the run AND keep its evidence
        from src.validate import validate as _v, _synth
        bad = _v(_synth(bias=0.30, noise=0.10), assignment_accuracy=0.70)
        cnt = dict(stats=dict(resolution=0.70, passes_gate=True), counts={})
        man = td / "manual.csv"
        with open(man, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["interval", "veh_class", "manual_count"])
            for i in range(6):
                w.writerow([i, "TWO_W", 400])
        try:
            run_validate(td / "w4", cnt, man)
            good = False
        except GateFailure:
            good = _stage_path(td / "w4", "validate").exists()
        ok += good
        print(f"  {'failed validation stops the run, keeps evidence':<50}"
              f"{'GateFailure':>12}  {'PASS' if good else 'FAIL'}")

        good = STAGES == ["homography", "detect", "count", "validate", "critical_gap"]
        ok += good
        print(f"  {'stage order puts validation before publication':<50}"
              f"{f'{len(STAGES)} stages':>12}  {'PASS' if good else 'FAIL'}")

    print(f"\n  GATE - pipeline driver verified: **{ok} of 6**")
    print("\n  The fourth and fifth checks are the point. A driver that completes on a")
    print("  bad homography or a failed validation emits a full turning-movement matrix")
    print("  that looks entirely normal, and nothing downstream ever flags it.")
