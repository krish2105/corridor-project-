"""
annotate.py — choose frames worth labelling, and ingest the labels that come back.

THE BOTTLENECK IS HUMAN TIME, NOT COMPUTE
Stage-two fine-tuning needs roughly 500-800 annotated frames from the actual camera. At
a realistic 2-4 minutes per frame that is 20-50 hours of someone's life, so WHICH frames
get labelled matters more than how many.

Uniform sampling is the obvious approach and it is wasteful. Two hours of 4K at 30 fps is
216,000 frames; consecutive ones are nearly identical, so labelling both teaches the model
almost nothing new while costing the same. Sampling the quiet 03:00 stretch teaches it
about empty tarmac.

Selection here does three things instead:

  stratify   spread across the whole session, so dawn, peak and dusk lighting are all
             represented rather than one hour dominating
  de-duplicate  reject a frame too similar to one already chosen, measured on a
             downsampled grey histogram-of-differences
  prefer busy  more objects per frame means more labels per annotation-hour, and the
             classes that matter here - auto-rickshaw, e-rickshaw - only appear in traffic

INGESTION
Whatever tool is used, the output lands as YOLO txt. CVAT XML, Roboflow YOLO export and
Label Studio JSON are all read here so the choice of tool does not lock anything in.

E-RICKSHAW
This is the ONLY route to an e-rickshaw class. It postdates IDD, COCO never had it, and
the JDA survey has a column heading with no data under it. If it is not annotated here it
cannot be counted anywhere, and the honest response is to say so rather than emit a zero.
Labels are therefore validated against CLASSES_STAGE2, which carries E_RIK and CYCLE_RIK -
not the stage-one list, which deliberately does not.

Run:  uv run python src/annotate.py                     # self-test
      uv run python src/annotate.py --frames VIDEO.mov 600
      uv run python src/annotate.py --ingest cvat ANN.xml
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import PROCESSED
from src.train import CLASSES_STAGE2 as CLASSES

# Two frames closer than this on a 32x32 grey signature are treated as the same scene.
DUP_THRESHOLD = 0.045
TARGET_FRAMES = 600          # methodology says 500-800; the knee is around here
MIN_STRATA = 12              # never take everything from one stretch of the session


def signature(frame, size=32):
    import cv2
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    s = cv2.resize(g, (size, size)).astype(np.float32) / 255.0
    return (s - s.mean()) / (s.std() + 1e-6)


def too_similar(sig, chosen, thr=DUP_THRESHOLD):
    for c in chosen:
        if float(np.mean(np.abs(sig - c))) < thr:
            return True
    return False


def select_frames(video, out_dir, target=TARGET_FRAMES, strata=MIN_STRATA,
                  detector=None, device="mps"):
    """
    Pick `target` frames worth annotating and write them as JPEGs.

    detector: optional YOLO used only to rank frames by object count. Its labels are
    NOT saved - a model's guesses must never become training targets, which is how a
    model's own errors get baked in and then validated against themselves.
    """
    import cv2
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    per_stratum = max(1, target // strata)
    bounds = np.linspace(0, total, strata + 1).astype(int)
    chosen_sigs, written = [], 0
    manifest = []

    for s in range(strata):
        lo, hi = bounds[s], bounds[s + 1]
        # oversample the stratum, then keep the best of what survives de-duplication
        step = max(1, (hi - lo) // (per_stratum * 6))
        pool = []
        for f in range(lo, hi, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, frame = cap.read()
            if not ok:
                continue
            sig = signature(frame)
            if too_similar(sig, chosen_sigs):
                continue
            score = 0
            if detector is not None:
                r = detector.predict(frame, verbose=False, device=device, conf=0.25)[0]
                score = len(r.boxes)
            pool.append((score, f, frame, sig))
        pool.sort(key=lambda t: -t[0])
        for score, f, frame, sig in pool[:per_stratum]:
            if too_similar(sig, chosen_sigs):
                continue
            chosen_sigs.append(sig)
            name = f"f{f:07d}.jpg"
            cv2.imwrite(str(out / name), frame)
            manifest.append(dict(file=name, frame=f, stratum=s, objects=int(score)))
            written += 1
    cap.release()
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return written, manifest


# --- ingestion -------------------------------------------------------------
def _yolo_line(cls_idx, x0, y0, x1, y1, W, H):
    cx, cy = (x0 + x1) / 2 / W, (y0 + y1) / 2 / H
    return f"{cls_idx} {cx:.6f} {cy:.6f} {(x1-x0)/W:.6f} {(y1-y0)/H:.6f}"


def from_cvat(xml_path, out_dir, classes=CLASSES):
    """CVAT for images 1.1 XML -> YOLO txt. Unknown labels are dropped, not guessed."""
    root = ET.parse(xml_path).getroot()
    out = Path(out_dir); (out / "labels").mkdir(parents=True, exist_ok=True)
    n_box, dropped, unknown = 0, 0, set()
    for img in root.findall("image"):
        W, H = float(img.get("width")), float(img.get("height"))
        lines = []
        for b in img.findall("box"):
            label = (b.get("label") or "").strip()
            if label not in classes:
                dropped += 1; unknown.add(label); continue
            lines.append(_yolo_line(classes.index(label), float(b.get("xtl")),
                                    float(b.get("ytl")), float(b.get("xbr")),
                                    float(b.get("ybr")), W, H))
            n_box += 1
        stem = Path(img.get("name")).stem
        (out / "labels" / f"{stem}.txt").write_text("\n".join(lines))
    return dict(boxes=n_box, dropped=dropped, unknown_labels=sorted(unknown))


def from_labelstudio(json_path, out_dir, classes=CLASSES):
    """Label Studio JSON export (percent-based rectangles) -> YOLO txt."""
    data = json.loads(Path(json_path).read_text())
    out = Path(out_dir); (out / "labels").mkdir(parents=True, exist_ok=True)
    n_box, dropped, unknown = 0, 0, set()
    for task in data:
        anns = task.get("annotations") or []
        if not anns:
            continue
        stem = Path(task.get("data", {}).get("image", "unknown")).stem
        lines = []
        for r in anns[0].get("result", []):
            v = r.get("value", {})
            labels = v.get("rectanglelabels") or []
            if not labels or labels[0] not in classes:
                dropped += 1
                if labels:
                    unknown.add(labels[0])
                continue
            cx = (v["x"] + v["width"] / 2) / 100
            cy = (v["y"] + v["height"] / 2) / 100
            lines.append(f"{classes.index(labels[0])} {cx:.6f} {cy:.6f} "
                         f"{v['width']/100:.6f} {v['height']/100:.6f}")
            n_box += 1
        (out / "labels" / f"{stem}.txt").write_text("\n".join(lines))
    return dict(boxes=n_box, dropped=dropped, unknown_labels=sorted(unknown))


def from_roboflow(export_dir, out_dir, classes=CLASSES):
    """
    Roboflow YOLO export -> our class indices.

    Roboflow orders classes alphabetically by default, which will NOT match our fixed
    order. Remapping through data.yaml rather than copying the txt files is the whole
    point: copying them silently relabels every box.
    """
    import yaml
    src = Path(export_dir)
    cfg = yaml.safe_load((src / "data.yaml").read_text())
    theirs = cfg["names"] if isinstance(cfg["names"], list) else \
        [cfg["names"][k] for k in sorted(cfg["names"])]
    out = Path(out_dir); (out / "labels").mkdir(parents=True, exist_ok=True)
    remap, unknown = {}, set()
    for i, name in enumerate(theirs):
        if name in classes:
            remap[i] = classes.index(name)
        else:
            unknown.add(name)
    n_box, dropped = 0, 0
    for txt in src.rglob("labels/**/*.txt"):
        lines = []
        for ln in txt.read_text().splitlines():
            parts = ln.split()
            if len(parts) != 5:
                continue
            old = int(parts[0])
            if old not in remap:
                dropped += 1; continue
            lines.append(" ".join([str(remap[old])] + parts[1:]))
            n_box += 1
        (out / "labels" / txt.name).write_text("\n".join(lines))
    return dict(boxes=n_box, dropped=dropped, unknown_labels=sorted(unknown),
                remap=remap)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--frames":
        vid, n = a[1], int(a[2]) if len(a) > 2 else TARGET_FRAMES
        try:
            from ultralytics import YOLO
            det = YOLO("yolo11n.pt")
        except Exception:
            det = None
        w, man = select_frames(vid, PROCESSED / "annotate_frames", target=n, detector=det)
        print(f"selected {w} frames -> {PROCESSED / 'annotate_frames'}")
        print(f"  objects per frame, median: "
              f"{int(np.median([m['objects'] for m in man])) if man else 0}")
        print("  Label these in CVAT, Roboflow or Label Studio, then ingest with --ingest.")
        sys.exit(0)
    if a and a[0] == "--ingest":
        fmt, path = a[1], a[2]
        fn = dict(cvat=from_cvat, labelstudio=from_labelstudio, roboflow=from_roboflow)[fmt]
        res = fn(path, PROCESSED / "own_yolo")
        print(json.dumps(res, indent=1))
        sys.exit(0)

    print("SELF-TEST - no footage exists, so frame selection is exercised on a synthetic")
    print("clip and ingestion on synthetic exports in each supported format.\n")
    import tempfile
    import cv2
    ok = 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # a clip with three distinct scenes, each repeated - de-duplication must collapse them
        vid = td / "clip.mp4"
        vw = cv2.VideoWriter(str(vid), cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 240))
        rng = np.random.default_rng(3)
        scenes = [rng.integers(0, 90, (240, 320, 3), dtype=np.uint8) for _ in range(3)]
        for s in scenes:
            for _ in range(150):
                vw.write(np.clip(s + rng.integers(-2, 3, s.shape), 0, 255).astype(np.uint8))
        vw.release()

        n, man = select_frames(vid, td / "frames", target=24, strata=3)
        good = 0 < n <= 24
        ok += good
        print(f"  {'frame selection returns a bounded set':<46}"
              f"{f'{n} frames':>14}  {'PASS' if good else 'FAIL'}")

        strata_used = len({m["stratum"] for m in man})
        good = strata_used == 3
        ok += good
        print(f"  {'every stratum represented':<46}{f'{strata_used}/3':>14}  "
              f"{'PASS' if good else 'FAIL'}")

        good = n <= 12
        ok += good
        print(f"  {'near-duplicate scenes collapsed':<46}"
              f"{f'{n} from 450 frames':>14}  {'PASS' if good else 'FAIL'}")

        # CVAT
        xml = td / "cvat.xml"
        xml.write_text(
            '<annotations><image name="f0000001.jpg" width="320" height="240">'
            '<box label="AUTO" xtl="10" ytl="20" xbr="60" ybr="80"/>'
            '<box label="TWO_W" xtl="100" ytl="30" xbr="130" ybr="70"/>'
            '<box label="spaceship" xtl="0" ytl="0" xbr="5" ybr="5"/>'
            '</image></annotations>')
        r = from_cvat(xml, td / "cv")
        good = r["boxes"] == 2 and r["dropped"] == 1 and r["unknown_labels"] == ["spaceship"]
        ok += good
        detail = "{} kept, {} dropped".format(r["boxes"], r["dropped"])
        print(f"  {'CVAT ingest, unknown label dropped not guessed':<46}{detail:>14}  "
              f"{'PASS' if good else 'FAIL'}")

        # Label Studio
        ls = td / "ls.json"
        ls.write_text(json.dumps([{"data": {"image": "/x/f0000002.jpg"}, "annotations": [
            {"result": [{"value": {"x": 10, "y": 10, "width": 20, "height": 30,
                                   "rectanglelabels": ["AUTO"]}}]}]}]))
        r2 = from_labelstudio(ls, td / "ls")
        good = r2["boxes"] == 1
        ok += good
        detail = "{} box".format(r2["boxes"])
        print(f"  {'Label Studio ingest':<46}{detail:>14}  "
              f"{'PASS' if good else 'FAIL'}")

        # Roboflow, with a deliberately different class order
        import yaml as _y
        rf = td / "rf"; (rf / "labels").mkdir(parents=True)
        _y.safe_dump(dict(names=["AUTO", "CAR_BUCKET", "TWO_W"]),
                     open(rf / "data.yaml", "w"))
        (rf / "labels" / "a.txt").write_text("0 0.5 0.5 0.1 0.1\n2 0.2 0.2 0.1 0.1")
        r3 = from_roboflow(rf, td / "rfo")
        want = {0: CLASSES.index("AUTO"), 1: CLASSES.index("CAR_BUCKET"),
                2: CLASSES.index("TWO_W")}
        good = r3["remap"] == want and r3["boxes"] == 2
        ok += good
        print(f"  {'Roboflow class order remapped, not copied':<46}"
              f"{str(r3['remap']):>14}  {'PASS' if good else 'FAIL'}")

    print(f"\n  GATE - annotation pipeline verified: **{ok} of 6**")
    print("\n  Roboflow orders classes alphabetically. Copying its label files instead of")
    print("  remapping through data.yaml silently relabels every box - an auto-rickshaw")
    print("  becomes whatever happens to sit at that index in our list.")
