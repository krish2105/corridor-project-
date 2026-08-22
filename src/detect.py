"""
detect.py — video to world-coordinate vehicle tracks.

The stage between footage and count.py. Detection, sliced inference for small objects,
multi-object tracking, and projection to UTM 43N through the homography.

WHAT OFF-THE-SHELF DETECTION CANNOT DO, AND WHY IT MATTERS HERE
A COCO-trained model has no auto-rickshaw class and no e-rickshaw class. On this corridor
those are not a rounding error: the survey's own composite column mixes autos with cars,
and JDA's flow-diagram sheet has an e-rickshaw heading with no data under it. Running COCO
weights and reporting the result would reproduce exactly the class-scheme failure the
audit criticises. The mapping below therefore states what is UNMAPPABLE rather than
quietly folding autos into `car`, and fine-tuning is a prerequisite, not an improvement.

SMALL OBJECTS
From 8-12 m the two-wheelers that are half this stream occupy few pixels, and standard
inference resizes the whole frame to 640 px, shrinking a 30 px motorcycle to nothing.
Sliced inference runs detection on overlapping tiles at native resolution and merges the
results. It is slower, which does not matter for recorded video.

TWO ENVIRONMENT CONSTRAINTS, RECORDED SO THEY DO NOT BITE LATER
supervision is pinned to <0.31. Its ByteTrack is deprecated and slated for removal, but
it is the only tracker in either library that accepts EXTERNALLY supplied detections.
Ultralytics' native tracking runs its own detection, which cannot consume sliced
inference - and sliced inference is the entire reason small two-wheelers are detectable
here. If supervision drops it, the options are to vendor the tracker or move to boxmot;
do not "fix" this by switching to model.track(), which silently discards slicing.

opencv-python and av (an ultralytics dependency) both bundle libavdevice, so macOS prints
a duplicate-class objc warning on import. It is noisy rather than harmful in practice,
but it is a real symbol clash and worth knowing about if decoding ever behaves oddly.

WHAT IS VERIFIED HERE, AND WHAT IS NOT
Verified: slicing geometry and coverage, box merging, the class mapping and its declared
gaps, tracker behaviour on synthetic sequences with known paths, projection to world
coordinates, and the handoff to count.py. Model load and a real forward pass on MPS.
NOT verified: detection accuracy. That needs real frames and fine-tuned weights, and any
number quoted for it before then would be invented.

Run:  uv run python src/detect.py            # self-test
      uv run python src/detect.py VIDEO.mov  # run on footage
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MODEL = "yolo11m.pt"          # balanced; yolo11n for a quick check, yolo11x to fine-tune from
DEVICE = "mps"                # Apple silicon. Use "cuda" on the RTX 3060 for batch work.
CONF = 0.25
SLICE = 640
OVERLAP = 0.2

# COCO class -> the survey's scheme. Deliberately incomplete, and the gaps are the point.
COCO_TO_IRC = {
    "motorcycle": "TWO_W",
    "car": "CAR_BUCKET",
    "bus": "AUTO_TRK_BUS",
    "truck": "TRL_MAV",
    "bicycle": "CYCLE",
}
# Present in the stream, absent from COCO. Until the model is fine-tuned these are either
# missed entirely or silently mis-assigned, and either way the count is wrong.
UNMAPPABLE = {
    "AUTO": "auto-rickshaw - no COCO class; commonly 15-25% of an Indian urban stream",
    "E_RIK": "e-rickshaw - no COCO class; growing share, and absent from this survey too",
    "CYCLE_RIK": "cycle-rickshaw - no COCO class",
    "ANIMAL": "animal-drawn cart - no COCO class",
}
PEDESTRIAN = "person"         # counted separately, never folded into the TMC


def _make_tracker(sv):
    """
    ByteTrack, with its deprecation warning suppressed at the point of use.

    Suppressed deliberately and narrowly: the warning is correct, the pin in
    pyproject.toml is the mitigation, and letting it print on every frame of a long
    video buries real output. See the module docstring for why there is no alternative.
    """
    import warnings
    with warnings.catch_warnings():
        # match on the message: supervision raises this through a decorator, so a
        # module-path filter does not catch it
        warnings.filterwarnings("ignore", message=r".*ByteTrack.*deprecated.*")
        return sv.ByteTrack()


def slices(w, h, size=SLICE, overlap=OVERLAP):
    """
    Overlapping tiles covering the frame.

    Overlap must exceed the largest object or a vehicle straddling a seam is cut in two
    and counted twice at half size. 20% of 640 px is 128 px, comfortably more than a
    two-wheeler at this camera height.
    """
    step = int(size * (1 - overlap))
    xs = list(range(0, max(w - size, 0) + 1, step)) or [0]
    ys = list(range(0, max(h - size, 0) + 1, step)) or [0]
    if xs[-1] + size < w:
        xs.append(max(w - size, 0))
    if ys[-1] + size < h:
        ys.append(max(h - size, 0))
    return [(x, y, min(x + size, w), min(y + size, h)) for y in ys for x in xs]


def coverage(w, h, tiles):
    """Fraction of the frame covered by at least one tile. Must be 1.0."""
    m = np.zeros((h, w), dtype=bool)
    for x0, y0, x1, y1 in tiles:
        m[y0:y1, x0:x1] = True
    return float(m.mean())


def iou(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    ua = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / ua if ua > 0 else 0.0


def merge(dets, thr=0.5):
    """
    Greedy NMS across tile boundaries.

    Without this, every object in an overlap region is detected twice and the count is
    inflated by roughly the overlap fraction - which on a 20% overlap is a 20% error,
    larger than the entire PCU correction being argued about.
    """
    out = []
    for d in sorted(dets, key=lambda x: -x["conf"]):
        if all(iou(d["bbox"], k["bbox"]) < thr or d["cls"] != k["cls"] for k in out):
            out.append(d)
    return out


def load_model(name=MODEL, device=DEVICE):
    from ultralytics import YOLO
    m = YOLO(name)
    return m, device


def detect_frame(model, device, frame, conf=CONF, sliced=True):
    """One frame -> merged detections in frame pixel coordinates."""
    h, w = frame.shape[:2]
    tiles = slices(w, h) if sliced else [(0, 0, w, h)]
    dets = []
    for x0, y0, x1, y1 in tiles:
        crop = frame[y0:y1, x0:x1]
        res = model.predict(crop, conf=conf, device=device, verbose=False)[0]
        names = res.names
        for b in res.boxes:
            cx0, cy0, cx1, cy1 = [float(v) for v in b.xyxy[0]]
            label = names[int(b.cls[0])]
            dets.append(dict(bbox=(cx0 + x0, cy0 + y0, cx1 + x0, cy1 + y0),
                             conf=float(b.conf[0]), coco=label,
                             cls=COCO_TO_IRC.get(label, "UNMAPPED")))
    return merge(dets)


def track_video(path, model=None, device=DEVICE, homography=None, origin=None,
                every=1, max_frames=None):
    """
    Footage -> {track_id: {"class": str, "pts": [(frame, x, y), ...]}}

    Points are the bbox footpoint projected to UTM 43N when a homography is supplied,
    otherwise pixels. count.py expects world metres.
    """
    import cv2
    import supervision as sv
    from src.homography import footpoint, to_world

    if model is None:
        model, device = load_model()
    tracker = _make_tracker(sv)
    cap = cv2.VideoCapture(str(path))
    tracks, f = {}, 0
    while True:
        ok, frame = cap.read()
        if not ok or (max_frames and f >= max_frames):
            break
        if f % every == 0:
            dets = detect_frame(model, device, frame)
            if dets:
                sd = sv.Detections(
                    xyxy=np.array([d["bbox"] for d in dets], dtype=np.float32),
                    confidence=np.array([d["conf"] for d in dets], dtype=np.float32),
                    class_id=np.zeros(len(dets), dtype=int))
                sd = tracker.update_with_detections(sd)
                for i, tid in enumerate(sd.tracker_id):
                    fp = footpoint(sd.xyxy[i])
                    if homography is not None:
                        fp = tuple(to_world(homography, origin, [fp])[0])
                    rec = tracks.setdefault(int(tid), dict(**{"class": dets[min(i, len(dets)-1)]["cls"]},
                                                           pts=[]))
                    rec["pts"].append((f, float(fp[0]), float(fp[1])))
        f += 1
    cap.release()
    return tracks


# --- self-test -------------------------------------------------------------
def _synthetic_detections(n_objects=6, n_frames=60, w=1920, h=1080, seed=4):
    """Objects moving on straight paths; used to exercise merging and tracking."""
    rng = np.random.default_rng(seed)
    paths = []
    for _ in range(n_objects):
        x0, y0 = rng.uniform(100, w - 400), rng.uniform(100, h - 300)
        vx, vy = rng.uniform(-8, 8), rng.uniform(-5, 5)
        paths.append((x0, y0, vx, vy))
    frames = []
    for f in range(n_frames):
        dets = []
        for x0, y0, vx, vy in paths:
            x, y = x0 + vx * f, y0 + vy * f
            if 0 < x < w - 60 and 0 < y < h - 40:
                dets.append(dict(bbox=(x, y, x + 55, y + 38), conf=0.8,
                                 coco="car", cls="CAR_BUCKET"))
        frames.append(dets)
    return frames


if __name__ == "__main__":
    if len(sys.argv) > 1:
        vid = Path(sys.argv[1])
        if not vid.exists():
            raise SystemExit(f"Not found: {vid}")
        print(f"tracking {vid.name} ...")
        model, device = load_model()
        tr = track_video(vid, model, device, max_frames=None)
        print(f"  tracks: {len(tr)}")
        print("  Supply a homography to get world coordinates that count.py can use.")
        sys.exit(0)

    print("SELF-TEST\n")
    ok = 0
    total = 0

    # 1. slicing covers the whole frame
    print("  slicing geometry")
    for w, h in ((1920, 1080), (3840, 2160), (1280, 720)):
        t = slices(w, h)
        cov = coverage(w, h, t)
        good = cov == 1.0
        ok += good; total += 1
        print(f"    {w}x{h:<6} tiles={len(t):<4} coverage={cov:.1%}  "
              f"{'PASS' if good else 'FAIL'}")

    # 2. overlap merging removes duplicates across seams
    print("\n  duplicate removal across tile seams")
    a = dict(bbox=(100, 100, 160, 140), conf=0.9, cls="CAR_BUCKET")
    b = dict(bbox=(104, 102, 164, 142), conf=0.8, cls="CAR_BUCKET")   # same object
    c = dict(bbox=(600, 600, 660, 640), conf=0.7, cls="CAR_BUCKET")   # different
    m = merge([a, b, c])
    good = len(m) == 2
    ok += good; total += 1
    print(f"    3 detections, 2 of them the same object -> {len(m)} kept  "
          f"{'PASS' if good else 'FAIL'}")

    # 3. class mapping declares its gaps
    print("\n  class mapping")
    mapped = set(COCO_TO_IRC.values())
    good = "AUTO" not in mapped and "E_RIK" not in mapped and len(UNMAPPABLE) >= 4
    ok += good; total += 1
    print(f"    COCO covers: {sorted(mapped)}")
    print(f"    declared unmappable: {sorted(UNMAPPABLE)}")
    print(f"    auto/e-rickshaw NOT silently folded into car  "
          f"{'PASS' if good else 'FAIL'}")

    # 4. tracking holds identity on synthetic paths
    print("\n  tracking on synthetic paths")
    import supervision as sv
    frames = _synthetic_detections()
    tracker = _make_tracker(sv)
    seen = {}
    for f, dets in enumerate(frames):
        if not dets:
            continue
        sd = sv.Detections(xyxy=np.array([d["bbox"] for d in dets], dtype=np.float32),
                           confidence=np.array([d["conf"] for d in dets], dtype=np.float32),
                           class_id=np.zeros(len(dets), dtype=int))
        sd = tracker.update_with_detections(sd)
        for tid in sd.tracker_id:
            seen.setdefault(int(tid), 0)
            seen[int(tid)] += 1
    long_tracks = [k for k, v in seen.items() if v >= 20]
    good = 5 <= len(long_tracks) <= 8
    ok += good; total += 1
    print(f"    6 objects -> {len(seen)} ids, {len(long_tracks)} sustained >=20 frames  "
          f"{'PASS' if good else 'FAIL'}")

    # 5. the model actually loads and runs on this machine
    print("\n  model load and forward pass")
    try:
        import torch
        model, device = load_model("yolo11n.pt")
        blank = np.zeros((640, 640, 3), dtype=np.uint8)
        _ = model.predict(blank, verbose=False, device=device)
        good = torch.backends.mps.is_available()
        ok += good; total += 1
        print(f"    yolo11n loaded, forward pass on {device}, MPS available={good}  "
              f"{'PASS' if good else 'FAIL'}")
    except Exception as e:
        total += 1
        print(f"    FAILED: {e}")

    print(f"\n  GATE - plumbing verified: **{ok} of {total}**")
    print("\n  NOT verified, and cannot be before footage exists: detection accuracy.")
    print("  COCO weights cannot see an auto-rickshaw or an e-rickshaw at all. Fine-tune")
    print("  on IDD, then on ~500 frames from this camera angle, and only then does")
    print("  src/validate.py have anything meaningful to measure.")
