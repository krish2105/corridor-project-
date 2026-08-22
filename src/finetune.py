"""
finetune.py — stage two: adapt the IDD-trained model to THIS camera at THIS junction.

WHY A SECOND STAGE AT ALL
Stage one (train.py) teaches the model what an Indian road looks like from IDD's
dashcam viewpoint. Our camera is nothing like a dashcam: it is elevated, static, looking
down a corridor, and every vehicle is small and foreshortened. A model that scores well
on IDD can still miss half the two-wheelers here. Stage two is what closes that, and per
the methodology it is the highest value per hour spent of anything in the project.

THE ERROR THAT MAKES THE NUMBERS LIE
Frames from one continuous video are not independent samples. Frame 1000 and frame 1003
are the same scene with the vehicles moved a few pixels. Split those at random into train
and val and the model has effectively seen every validation image during training - val
mAP then measures memorisation, and it will read HIGH. That is the worst kind of error
here, because the gate is a mAP threshold: a leaked split sails through a gate that exists
precisely to stop an inadequate model being trusted.

So the split is by contiguous BLOCK, never at random, and a buffer of frames either side
of each boundary is discarded so no training frame is temporally adjacent to a validation
one. It costs a little data. It buys a val number that means something.

  |<-- train -->|xx buffer xx|<-- val -->|xx buffer xx|<-- train -->|

LEARNING RATE
Stage two runs at a tenth of stage one's rate. The model already knows what a vehicle is;
it is being asked to adjust to a viewpoint, not to relearn the class. A full-rate run on
a few hundred frames overwrites the IDD knowledge with whatever this camera happened to
see - catastrophic forgetting, and the rare classes go first.

Run:  uv run python src/finetune.py                                    # self-test
      uv run python src/finetune.py --prepare data/processed/annotate_frames
      uv run python src/finetune.py --run data/processed/own_yolo/data.yaml STAGE1.pt
"""
import json
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import PROCESSED, ROOT
from src.train import (CLASSES_STAGE2 as CLASSES, GATE_MAP50_OVERALL,
                       GATE_MAP50_PER_CLASS, evaluate)

VAL_FRACTION = 0.25
N_BLOCKS = 8              # more blocks = val covers more of the session, less contiguous
BUFFER_FRAMES = 90        # 3 s at 30 fps; a vehicle clears the frame in well under this
LR_STAGE2 = 0.001         # a tenth of the ultralytics default, see module docstring


def _frame_index(name):
    """f0001234.jpg -> 1234. Selection wrote this name; anything else sorts as 0."""
    stem = Path(name).stem
    digits = "".join(c for c in stem if c.isdigit())
    return int(digits) if digits else 0


def split_by_block(frames, n_blocks=N_BLOCKS, val_fraction=VAL_FRACTION,
                   buffer_frames=BUFFER_FRAMES):
    """
    Split frame names into (train, val, discarded) with a temporal buffer between them.

    Returns whole contiguous blocks to val, then drops any frame within buffer_frames of
    the opposite set. The discard count is returned rather than hidden - if it is large
    the frame selection was too clustered and that is worth knowing.
    """
    ordered = sorted(frames, key=_frame_index)
    if not ordered:
        return [], [], []
    n_blocks = max(2, min(n_blocks, len(ordered)))
    bounds = [round(i * len(ordered) / n_blocks) for i in range(n_blocks + 1)]
    blocks = [ordered[bounds[i]:bounds[i + 1]] for i in range(n_blocks)]

    # take val blocks spread through the session, not the tail - the tail is one
    # lighting condition and would make val unrepresentative in a different way
    n_val = max(1, round(n_blocks * val_fraction))
    step = max(1, n_blocks // n_val)
    val_idx = set(range(0, n_blocks, step))
    while len(val_idx) > n_val:
        val_idx.discard(max(val_idx))

    val = [f for i in val_idx for f in blocks[i]]
    train = [f for i in range(n_blocks) if i not in val_idx for f in blocks[i]]

    val_pos = [_frame_index(f) for f in val]
    keep_train, discarded = [], []
    for f in train:
        p = _frame_index(f)
        if any(abs(p - v) < buffer_frames for v in val_pos):
            discarded.append(f)
        else:
            keep_train.append(f)
    return keep_train, val, discarded


def prepare_own(frames_dir, labels_dir=None, out_dir=None, **kw):
    """
    Build a YOLO dataset from self-annotated frames of our own footage.

    frames_dir: JPEGs written by annotate.select_frames
    labels_dir: YOLO txt from annotate.from_cvat / from_roboflow / from_labelstudio
    """
    frames_dir = Path(frames_dir)
    labels_dir = Path(labels_dir) if labels_dir else PROCESSED / "own_yolo" / "labels"
    out = Path(out_dir or PROCESSED / "own_dataset")

    images = [p.name for p in sorted(frames_dir.glob("*.jpg"))]
    # a frame with no label file was never annotated; training on it teaches the model
    # that a road full of vehicles contains nothing at all
    labelled = [n for n in images if (labels_dir / f"{Path(n).stem}.txt").exists()]
    unlabelled = len(images) - len(labelled)

    train, val, discarded = split_by_block(labelled, **kw)

    for split, names in (("train", train), ("val", val)):
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)
        for n in names:
            shutil.copy(frames_dir / n, out / "images" / split / n)
            shutil.copy(labels_dir / f"{Path(n).stem}.txt",
                        out / "labels" / split / f"{Path(n).stem}.txt")

    data = dict(path=str(out.resolve()), train="images/train", val="images/val",
                names={i: c for i, c in enumerate(CLASSES)})
    (out / "data.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    report = dict(frames=len(images), labelled=len(labelled), unlabelled=unlabelled,
                  train=len(train), val=len(val), buffer_discarded=len(discarded))
    (out / "split_report.json").write_text(json.dumps(report, indent=1))
    return out / "data.yaml", report


def finetune(data_yaml, stage1_weights, epochs=60, imgsz=1280, device=None, **kw):
    """
    Stage two. Starts from stage-one weights, low LR, high imgsz.

    imgsz is 1280 rather than 640 because the whole problem with this camera is that
    two-wheelers are small. Halving the input resolution halves them again.
    """
    from ultralytics import YOLO
    if device is None:
        import torch
        device = "cuda" if torch.cuda.is_available() else \
            ("mps" if torch.backends.mps.is_available() else "cpu")
    model = YOLO(str(stage1_weights))
    model.train(data=str(data_yaml), epochs=epochs, imgsz=imgsz, device=device,
                lr0=LR_STAGE2, project=str(ROOT / "out" / "train"), name="stage2",
                exist_ok=True, **kw)
    return model, device


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--prepare":
        yml, rep = prepare_own(a[1], a[2] if len(a) > 2 else None)
        print(json.dumps(rep, indent=1)); print(yml); sys.exit(0)
    if a and a[0] == "--run":
        m, dev = finetune(a[1], a[2])
        res = evaluate(m, a[1], device=dev)
        print(json.dumps(res, indent=1)); sys.exit(0)

    print("SELF-TEST - no footage exists, so the split logic is checked against a")
    print("synthetic frame sequence and a real 2-epoch stage-2 run is executed.\n")
    import tempfile
    ok = 0

    names = [f"f{i:07d}.jpg" for i in range(0, 6000, 20)]   # 300 frames, 20 apart
    tr, va, disc = split_by_block(names)

    good = set(tr) & set(va) == set()
    ok += good
    print(f"  {'train and val are disjoint':<52}{f'{len(tr)}/{len(va)}':>13}  "
          f"{'PASS' if good else 'FAIL'}")

    tp = [_frame_index(f) for f in tr]; vp = [_frame_index(f) for f in va]
    nearest = min(abs(t - v) for t in tp for v in vp)
    good = nearest >= BUFFER_FRAMES
    ok += good
    print(f"  {'no train frame within the temporal buffer':<52}"
          f"{f'{nearest} >= {BUFFER_FRAMES}':>13}  {'PASS' if good else 'FAIL'}")

    # the whole point: a random split would NOT satisfy the buffer, and this proves it
    import random
    rnd = names[:]; random.Random(1).shuffle(rnd)
    rtr, rva = rnd[:225], rnd[225:]
    rnear = min(abs(_frame_index(t) - _frame_index(v)) for t in rtr for v in rva)
    good = rnear < BUFFER_FRAMES
    ok += good
    print(f"  {'a random split leaks, as claimed':<52}"
          f"{f'{rnear} < {BUFFER_FRAMES}':>13}  {'PASS' if good else 'FAIL'}")

    frac = len(va) / (len(tr) + len(va))
    good = 0.15 <= frac <= 0.40
    ok += good
    print(f"  {'val fraction stays in a sane band':<52}{f'{frac:.0%}':>13}  "
          f"{'PASS' if good else 'FAIL'}")

    good = len(disc) > 0
    ok += good
    print(f"  {'buffer discards are reported, not hidden':<52}"
          f"{f'{len(disc)} frames':>13}  {'PASS' if good else 'FAIL'}")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        fr = td / "frames"; lb = td / "labels"
        fr.mkdir(); lb.mkdir()
        import numpy as np, cv2
        rng = np.random.default_rng(11)
        for i in range(0, 3200, 100):                      # 32 frames
            img = rng.integers(40, 120, (256, 256, 3), dtype=np.uint8)
            cv2.rectangle(img, (90, 90), (150, 160), (230, 230, 230), -1)
            cv2.imwrite(str(fr / f"f{i:07d}.jpg"), img)
            (lb / f"f{i:07d}.txt").write_text("0 0.469 0.488 0.234 0.273")
        (fr / "f9999999.jpg").write_bytes((fr / "f0000000.jpg").read_bytes())  # unlabelled

        yml, rep = prepare_own(fr, lb, td / "ds", n_blocks=4, buffer_frames=50)
        good = rep["unlabelled"] == 1 and rep["train"] > 0 and rep["val"] > 0
        ok += good
        detail = "{} dropped".format(rep["unlabelled"])
        print(f"  {'unlabelled frames excluded from training':<52}{detail:>13}  "
              f"{'PASS' if good else 'FAIL'}")

        try:
            from ultralytics import YOLO
            import torch
            dev = "mps" if torch.backends.mps.is_available() else "cpu"
            m = YOLO("yolo11n.pt")
            m.train(data=str(yml), epochs=2, imgsz=256, batch=4, device=dev,
                    lr0=LR_STAGE2, project=str(td / "runs"), name="s2",
                    verbose=False, plots=False, val=True)
            res = evaluate(m, yml, device=dev)
            good = "map50" in res
            ok += good
            detail = "mAP50 {:.3f}".format(res["map50"])
            print(f"  {'real 2-epoch stage-2 run completes':<52}{detail:>13}  "
                  f"{'PASS' if good else 'FAIL'}")
        except Exception as e:
            print(f"  {'real 2-epoch stage-2 run completes':<52}{'ERROR':>13}  FAIL")
            print(f"      {type(e).__name__}: {str(e)[:90]}")

    print(f"\n  GATE - stage-two pipeline verified: **{ok} of 7**")
    print(f"  Gates carried from stage one: mAP50 >= {GATE_MAP50_OVERALL} overall, "
          f">= {GATE_MAP50_PER_CLASS} per class.")
    print("\n  The third check is the one that matters. A random split puts frames")
    print("  milliseconds apart on both sides, so val mAP measures memorisation and")
    print("  reads high - sailing through the very gate meant to catch a weak model.")
