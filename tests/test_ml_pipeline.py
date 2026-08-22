"""
Tests for the detection training chain.

The property under test throughout is that a mistake here produces a WRONG NUMBER rather
than an error: a leaked train/val split inflates mAP past its own gate, and a copied
Roboflow label file relabels every box while remaining perfectly valid YOLO. Both fail
silently in production, so both are pinned here.
"""
import json

import pytest

from src.annotate import from_cvat, from_labelstudio, from_roboflow, too_similar, signature
from src.finetune import BUFFER_FRAMES, _frame_index, split_by_block
from src.train import CLASSES, CLASSES_STAGE2, IDD_TO_IRC, NOT_LEARNABLE_FROM_IDD

import numpy as np


# --- the split must not leak -------------------------------------------------
FRAMES = [f"f{i:07d}.jpg" for i in range(0, 6000, 20)]


def test_split_is_disjoint():
    tr, va, _ = split_by_block(FRAMES)
    assert set(tr) & set(va) == set()
    assert tr and va


def test_no_train_frame_inside_the_temporal_buffer():
    """The whole reason the split is by block: adjacent frames are the same scene."""
    tr, va, _ = split_by_block(FRAMES)
    nearest = min(abs(_frame_index(t) - _frame_index(v)) for t in tr for v in va)
    assert nearest >= BUFFER_FRAMES


def test_a_random_split_would_leak():
    """Guards the claim itself - if this ever passes, the buffer is pointless."""
    import random
    rnd = FRAMES[:]
    random.Random(1).shuffle(rnd)
    tr, va = rnd[:225], rnd[225:]
    nearest = min(abs(_frame_index(t) - _frame_index(v)) for t in tr for v in va)
    assert nearest < BUFFER_FRAMES


def test_val_fraction_stays_sane():
    tr, va, _ = split_by_block(FRAMES)
    assert 0.15 <= len(va) / (len(tr) + len(va)) <= 0.40


def test_split_handles_degenerate_input():
    assert split_by_block([]) == ([], [], [])
    tr, va, _ = split_by_block(["f0000001.jpg", "f0009999.jpg"])
    assert len(tr) + len(va) == 2


# --- ingestion must never guess a class -------------------------------------
def test_cvat_drops_unknown_labels_rather_than_guessing(tmp_path):
    xml = tmp_path / "a.xml"
    xml.write_text(
        '<annotations><image name="f1.jpg" width="100" height="100">'
        '<box label="AUTO" xtl="10" ytl="10" xbr="30" ybr="30"/>'
        '<box label="hovercraft" xtl="0" ytl="0" xbr="5" ybr="5"/>'
        '</image></annotations>')
    r = from_cvat(xml, tmp_path / "o")
    assert r["boxes"] == 1
    assert r["unknown_labels"] == ["hovercraft"]


def test_cvat_writes_normalised_yolo(tmp_path):
    xml = tmp_path / "a.xml"
    xml.write_text(
        '<annotations><image name="f1.jpg" width="200" height="100">'
        '<box label="AUTO" xtl="50" ytl="20" xbr="150" ybr="60"/>'
        '</image></annotations>')
    from_cvat(xml, tmp_path / "o")
    cls, cx, cy, w, h = (tmp_path / "o" / "labels" / "f1.txt").read_text().split()
    assert int(cls) == CLASSES.index("AUTO")
    assert float(cx) == pytest.approx(0.5) and float(cy) == pytest.approx(0.4)
    assert float(w) == pytest.approx(0.5) and float(h) == pytest.approx(0.4)


def test_roboflow_remaps_indices_instead_of_copying(tmp_path):
    """
    Roboflow orders classes alphabetically. With this class list the mapping is a
    REVERSAL, so copying the label files would relabel every box - the exact failure
    this remap exists to prevent.
    """
    import yaml
    src = tmp_path / "rf"
    (src / "labels").mkdir(parents=True)
    yaml.safe_dump(dict(names=["AUTO", "CAR_BUCKET", "TWO_W"]),
                   open(src / "data.yaml", "w"))
    (src / "labels" / "a.txt").write_text("0 0.5 0.5 0.1 0.1\n2 0.2 0.2 0.1 0.1")
    r = from_roboflow(src, tmp_path / "o")
    assert r["remap"] == {0: CLASSES.index("AUTO"), 1: CLASSES.index("CAR_BUCKET"),
                          2: CLASSES.index("TWO_W")}
    assert r["remap"] != {0: 0, 1: 1, 2: 2}          # a copy would have been wrong
    assert r["boxes"] == 2


def test_labelstudio_percentages_become_fractions(tmp_path):
    js = tmp_path / "ls.json"
    js.write_text(json.dumps([{"data": {"image": "/x/f2.jpg"}, "annotations": [
        {"result": [{"value": {"x": 10, "y": 20, "width": 30, "height": 40,
                               "rectanglelabels": ["AUTO"]}}]}]}]))
    from_labelstudio(js, tmp_path / "o")
    cls, cx, cy, w, h = (tmp_path / "o" / "labels" / "f2.txt").read_text().split()
    assert float(cx) == pytest.approx(0.25) and float(w) == pytest.approx(0.30)


# --- frame selection ---------------------------------------------------------
def test_identical_frames_are_treated_as_duplicates():
    rng = np.random.default_rng(0)
    a = rng.integers(0, 255, (64, 64, 3), dtype=np.uint8)
    s1 = signature(a)
    assert too_similar(s1, [s1])


def test_distinct_frames_are_not_duplicates():
    rng = np.random.default_rng(0)
    s1 = signature(rng.integers(0, 255, (64, 64, 3), dtype=np.uint8))
    s2 = signature(rng.integers(0, 255, (64, 64, 3), dtype=np.uint8))
    assert not too_similar(s1, [s2])


# --- class model -------------------------------------------------------------
def test_idd_maps_only_to_declared_classes():
    assert set(IDD_TO_IRC.values()) <= set(CLASSES)


def test_autorickshaw_is_learnable_from_idd():
    """The class COCO cannot see at all, and the single biggest reason to use IDD."""
    assert "autorickshaw" in IDD_TO_IRC


def test_classes_idd_cannot_teach_are_named_not_silently_missing():
    """Stage one deliberately excludes them; they must still be declared, with a reason."""
    assert NOT_LEARNABLE_FROM_IDD
    assert all(c not in CLASSES for c in NOT_LEARNABLE_FROM_IDD)
    assert all(reason for reason in NOT_LEARNABLE_FROM_IDD.values())


def test_stage_two_can_learn_what_idd_could_not():
    assert set(CLASSES) < set(CLASSES_STAGE2)
    assert set(NOT_LEARNABLE_FROM_IDD) <= set(CLASSES_STAGE2)


def test_annotation_accepts_the_classes_only_annotation_can_teach(tmp_path):
    """
    Regression: annotation once validated against the stage-one class list, so an
    annotator's E_RIK boxes were dropped as an unknown label - silently discarding the
    single class that self-annotation exists to capture.
    """
    xml = tmp_path / "a.xml"
    xml.write_text(
        '<annotations><image name="f1.jpg" width="100" height="100">'
        '<box label="E_RIK" xtl="10" ytl="10" xbr="30" ybr="30"/>'
        '<box label="CYCLE_RIK" xtl="40" ytl="10" xbr="60" ybr="30"/>'
        '</image></annotations>')
    r = from_cvat(xml, tmp_path / "o")
    assert r["boxes"] == 2
    assert r["dropped"] == 0
