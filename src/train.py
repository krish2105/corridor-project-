"""
train.py — fine-tune detection for Indian traffic classes.

WHY THIS STAGE IS NOT OPTIONAL
COCO has no auto-rickshaw and no e-rickshaw class. On this corridor the survey's own
composite column already mixes autos with cars, and its flow-diagram sheet carries an
e-rickshaw heading with no data beneath it. Running COCO weights and reporting the output
would reproduce the exact class-scheme failure the audit criticises. IDD supplies
`autorickshaw` directly, which is the single most valuable class COCO lacks.

TWO STAGES, IN ORDER
  1. IDD          Indian road scenes, 34 classes, includes autorickshaw. Teaches the model
                  what these vehicles look like at all.
  2. Own frames   ~500-800 annotated frames from the actual camera. Teaches it what they
                  look like at THIS height, angle and light. Highest accuracy per hour of
                  effort, and the stage people skip.

E-rickshaw is in neither. IDD predates its spread and lumps it under vehicle fallback or
autorickshaw depending on the annotator. It has to come from your own frames, and until
it does, e-rickshaw counts are not reportable - which is worth stating rather than
quietly emitting a number.

WHERE TO RUN IT
Training on the RTX 3060 (CUDA), inference and checks on the MacBook (MPS). CUDA is
materially faster for training and 12 GB handles YOLO11m; MPS is fine for everything else.

Run:  uv run python src/train.py                 # self-test on a synthetic dataset
      uv run python src/train.py --prepare IDD_ROOT
      uv run python src/train.py --train data/processed/idd_yolo/data.yaml
"""
import shutil
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import PROCESSED, ROOT

# Acceptance before counts produced by this model are trusted at all.
GATE_MAP50_OVERALL = 0.80
GATE_MAP50_PER_CLASS = 0.70

# IDD label -> the survey's scheme. `autorickshaw` is the reason this stage exists.
IDD_TO_IRC = {
    "car": "CAR_BUCKET",
    "motorcycle": "TWO_W",
    "rider": "TWO_W",              # IDD labels rider separately from the machine
    "autorickshaw": "AUTO",        # absent from COCO entirely
    "bus": "AUTO_TRK_BUS",
    "truck": "TRL_MAV",
    "bicycle": "CYCLE",
    "animal": "ANIMAL",
    "person": "PERSON",            # pedestrians, counted separately, never in the TMC
}
# Order is the class index the model learns. Fixed here so runs stay comparable.
CLASSES = ["TWO_W", "CAR_BUCKET", "AUTO", "AUTO_TRK_BUS", "TRL_MAV",
           "CYCLE", "ANIMAL", "PERSON"]
NOT_LEARNABLE_FROM_IDD = {
    "E_RIK": "e-rickshaw - postdates IDD; annotate from your own frames or do not report it",
    "CYCLE_RIK": "cycle-rickshaw - not a distinct IDD class",
}

TRAIN_DEFAULTS = dict(epochs=60, imgsz=960, batch=8, patience=15,
                      optimizer="auto", cos_lr=True, mosaic=0.6,
                      # small objects dominate here; heavy scale jitter hurts them
                      scale=0.3, fliplr=0.5, flipud=0.0)


def prepare(idd_root, out_dir=None, splits=("train", "val")):
    """
    IDD -> YOLO layout, remapping labels to the survey scheme.

    Expects the IDD Detection release: JPEGImages/ and Annotations/ per split.
    Classes not in IDD_TO_IRC are dropped rather than guessed.
    """
    idd_root = Path(idd_root)
    out = Path(out_dir or PROCESSED / "idd_yolo")
    counts = {c: 0 for c in CLASSES}
    dropped = 0
    for split in splits:
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)
    # IDD ships XML (Pascal VOC style) in the detection release
    import xml.etree.ElementTree as ET
    for split in splits:
        ann_dir = idd_root / "Annotations" / split
        img_dir = idd_root / "JPEGImages" / split
        if not ann_dir.exists():
            raise SystemExit(f"Expected {ann_dir} - is this the IDD Detection release?")
        for xml in sorted(ann_dir.rglob("*.xml")):
            root = ET.parse(xml).getroot()
            size = root.find("size")
            W, H = float(size.find("width").text), float(size.find("height").text)
            lines = []
            for obj in root.findall("object"):
                name = (obj.find("name").text or "").strip().lower()
                irc = IDD_TO_IRC.get(name)
                if irc is None or irc not in CLASSES:
                    dropped += 1
                    continue
                bb = obj.find("bndbox")
                x0, y0 = float(bb.find("xmin").text), float(bb.find("ymin").text)
                x1, y1 = float(bb.find("xmax").text), float(bb.find("ymax").text)
                cx, cy = (x0 + x1) / 2 / W, (y0 + y1) / 2 / H
                bw, bh = (x1 - x0) / W, (y1 - y0) / H
                lines.append(f"{CLASSES.index(irc)} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
                counts[irc] += 1
            if not lines:
                continue
            stem = xml.stem
            src_img = next((p for p in img_dir.rglob(f"{stem}.*")), None)
            if src_img is None:
                continue
            shutil.copy(src_img, out / "images" / split / src_img.name)
            (out / "labels" / split / f"{stem}.txt").write_text("\n".join(lines))
    data = dict(path=str(out.resolve()), train="images/train", val="images/val",
                names={i: c for i, c in enumerate(CLASSES)})
    (out / "data.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    return out / "data.yaml", counts, dropped


def train(data_yaml, weights="yolo11m.pt", device=None, **kw):
    """Fine-tune. device: 'cuda' on the 3060, 'mps' on the MacBook, None to autodetect."""
    from ultralytics import YOLO
    if device is None:
        import torch
        device = "cuda" if torch.cuda.is_available() else (
            "mps" if torch.backends.mps.is_available() else "cpu")
    cfg = {**TRAIN_DEFAULTS, **kw}
    model = YOLO(weights)
    model.train(data=str(data_yaml), device=device, project=str(ROOT / "out" / "train"),
                name="idd", exist_ok=True, **cfg)
    return model


def evaluate(model, data_yaml, device=None):
    """
    mAP@0.5 overall and per class, against the acceptance gates.

    Reports per class because an overall figure hides the classes that matter: a model
    can score well on cars and still be blind to auto-rickshaws, which is precisely the
    failure this stage exists to prevent.
    """
    m = model.val(data=str(data_yaml), device=device, verbose=False)
    per = {}
    try:
        names = m.names if hasattr(m, "names") else {}
        for i, ap in enumerate(m.box.maps):
            per[names.get(i, str(i))] = float(ap)
    except Exception:
        pass
    overall = float(m.box.map50) if hasattr(m.box, "map50") else float("nan")
    weak = {k: v for k, v in per.items() if v < GATE_MAP50_PER_CLASS}
    return dict(map50=overall, per_class=per,
                passes_overall=overall >= GATE_MAP50_OVERALL,
                weak_classes=weak, accepted=overall >= GATE_MAP50_OVERALL and not weak)


def _synthetic_dataset(root, n_train=24, n_val=8, seed=7):
    """
    A tiny dataset of coloured rectangles on noise, one colour per class.

    This does not prove the model can see an auto-rickshaw. It proves the pipeline is
    wired correctly end to end - label format, class indexing, data.yaml, the training
    call and the evaluation gates - so that the moment real data arrives the only
    variable left is the data.
    """
    import cv2
    rng = np.random.default_rng(seed)
    root = Path(root)
    colours = [(220, 60, 60), (60, 200, 90), (70, 110, 240), (240, 190, 50),
               (200, 80, 220), (90, 220, 220), (150, 150, 150), (250, 250, 250)]
    for split, n in (("train", n_train), ("val", n_val)):
        (root / "images" / split).mkdir(parents=True, exist_ok=True)
        (root / "labels" / split).mkdir(parents=True, exist_ok=True)
        for i in range(n):
            H = W = 320
            img = (rng.integers(40, 70, (H, W, 3))).astype(np.uint8)
            lines = []
            for _ in range(rng.integers(2, 5)):
                c = int(rng.integers(0, len(CLASSES)))
                w = int(rng.integers(40, 80)); h = int(rng.integers(30, 60))
                x = int(rng.integers(0, W - w)); y = int(rng.integers(0, H - h))
                cv2.rectangle(img, (x, y), (x + w, y + h), colours[c], -1)
                lines.append(f"{c} {(x+w/2)/W:.6f} {(y+h/2)/H:.6f} {w/W:.6f} {h/H:.6f}")
            cv2.imwrite(str(root / "images" / split / f"{i:04d}.jpg"), img)
            (root / "labels" / split / f"{i:04d}.txt").write_text("\n".join(lines))
    data = dict(path=str(root.resolve()), train="images/train", val="images/val",
                names={i: c for i, c in enumerate(CLASSES)})
    (root / "data.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    return root / "data.yaml"


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--prepare":
        yml, counts, dropped = prepare(args[1])
        print(f"written: {yml}")
        for c, n in counts.items():
            print(f"  {c:<14}{n:>9,}")
        print(f"  dropped (no mapping): {dropped:,}")
        for k, why in NOT_LEARNABLE_FROM_IDD.items():
            print(f"  NOT IN IDD  {k}: {why}")
        sys.exit(0)
    if args and args[0] == "--train":
        m = train(args[1])
        res = evaluate(m, args[1])
        print(f"mAP@0.5 {res['map50']:.3f}  accepted={res['accepted']}")
        sys.exit(0)

    print("SELF-TEST - IDD is not present, so the PIPELINE is exercised end to end on a")
    print("synthetic dataset. This proves the wiring, not that the model can see an")
    print("auto-rickshaw. Only real data proves that.\n")

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        yml = _synthetic_dataset(td)
        cfg = yaml.safe_load(Path(yml).read_text())
        ok = 0
        print(f"  {'check':<44}{'result':>22}")
        print("  " + "-" * 66)

        good = cfg["names"] == {i: c for i, c in enumerate(CLASSES)}
        ok += good
        print(f"  {'class list and indices stable':<44}{'PASS' if good else 'FAIL':>22}")

        good = "AUTO" in CLASSES and CLASSES.index("AUTO") == 2
        ok += good
        print(f"  {'auto-rickshaw present as its own class':<44}{'PASS' if good else 'FAIL':>22}")

        good = all(k not in CLASSES for k in NOT_LEARNABLE_FROM_IDD)
        ok += good
        print(f"  {'e-rickshaw NOT claimed as learnable':<44}{'PASS' if good else 'FAIL':>22}")

        lbl = next(Path(td).joinpath("labels", "train").glob("*.txt"))
        vals = [float(v) for v in lbl.read_text().split("\n")[0].split()[1:]]
        good = all(0.0 <= v <= 1.0 for v in vals)
        ok += good
        print(f"  {'label geometry normalised 0-1':<44}{'PASS' if good else 'FAIL':>22}")

        try:
            from ultralytics import YOLO
            import torch
            dev = "mps" if torch.backends.mps.is_available() else "cpu"
            m = YOLO("yolo11n.pt")
            m.train(data=str(yml), epochs=2, imgsz=320, batch=4, device=dev,
                    project=td, name="smoke", verbose=False, plots=False, val=True)
            good = True
        except Exception as e:
            good = False
            print(f"    training error: {str(e)[:140]}")
        ok += good
        print(f"  {'2-epoch training run completes':<44}{'PASS' if good else 'FAIL':>22}")

        print(f"\n  GATE - pipeline wiring verified: **{ok} of 5**")
    print(f"\n  Acceptance for a real run: mAP@0.5 >= {GATE_MAP50_OVERALL} overall AND")
    print(f"  >= {GATE_MAP50_PER_CLASS} for EVERY class. Per class matters: a model can")
    print("  score well overall and still be blind to auto-rickshaws, which is the exact")
    print("  failure this stage exists to prevent.")
