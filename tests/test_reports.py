"""
Tests for the generated deliverables.

The property under test is that a report cannot state something the pipeline does not.
Two failure modes are pinned: a figure typed by hand drifting from the analysis, and an
unmeasured quantity appearing as a number - a zero in an accuracy table reads as a
measurement, which is worse than an obviously empty cell.
"""
import json

import pytest

from src.reports import _status_line, capacity_report, method_statement, validation_report
from src.validate import GATES, validate, _synth

DATA_FILE = "validation.json"


@pytest.fixture
def no_validation(tmp_path, monkeypatch):
    """Force the pro-forma branch regardless of what is on disk."""
    import src.reports as R
    monkeypatch.setattr(R, "DATA", R.DATA)      # keep _load working for the real inputs
    monkeypatch.setattr(R, "_opt", lambda name: None)
    return None


@pytest.fixture
def with_validation(monkeypatch):
    res = validate(_synth(bias=0.02, noise=0.05), assignment_accuracy=0.97)
    res["unmapped_rate"] = 0.06
    import src.reports as R
    monkeypatch.setattr(R, "_opt", lambda name: res if name == "validation" else None)
    return res


# --- the pro forma must not look like a result -------------------------------
def test_proforma_declares_itself(no_validation):
    md, pending = validation_report()
    assert pending
    assert "PRO FORMA" in md


def test_proforma_shows_no_measurement_as_a_number(no_validation):
    """A zero here would read as 'the detector found nothing', not 'not yet run'."""
    md, _ = validation_report()
    body = md.split("## 3.")[1].split("## 8.")[0]
    assert "0.0%" not in body
    assert "0%" not in body.replace("100%", "").replace("90%", "").replace("95%", "") \
        .replace("10%", "").replace("20%", "").replace("15%", "")


def test_proforma_publishes_the_gates_before_any_data_exists(no_validation):
    md, _ = validation_report()
    for g in GATES.values():
        assert f"{g['target']:.0%}" in md
        assert f"{g['minimum']:.0%}" in md


def test_proforma_gives_no_verdict(no_validation):
    md, _ = validation_report()
    assert "No verdict" in md
    assert "accepted for reporting" not in md


def test_proforma_lists_detector_classes_not_pcu_buckets(no_validation):
    """Regression: the class table once listed HAND_CART and BULLOCK, which no
    detector emits - they are PCU and gap-acceptance buckets."""
    md, _ = validation_report()
    table = md.split("## 4.")[1].split("## 5.")[0]
    assert "TWO_W" in table and "E_RIK" in table
    assert "HAND_CART" not in table and "BULLOCK" not in table
    assert "PERSON" not in table          # counted, but never enters the TMC


# --- the measured branch -----------------------------------------------------
def test_measured_branch_renders_figures(with_validation):
    md, pending = validation_report()
    assert not pending
    assert "PRO FORMA" not in md
    assert f"{with_validation['total']['manual_total']:,}" in md


def test_failures_lead_the_status_line():
    v = dict(accepted=False, meets_target=False,
             failed_gates=["TOTAL"], marginal_gates=["TWO_W"])
    line = _status_line(v)
    assert line.index("Failed gates") < line.index("within tolerance")


def test_accepted_but_not_at_target_is_not_reported_as_a_clean_pass():
    v = dict(accepted=True, meets_target=False, failed_gates=[],
             marginal_gates=["ASSIGNMENT"])
    line = _status_line(v)
    assert "ACCEPTED" in line
    assert "All gates met at target" not in line


# --- the written reports are bound to the pipeline ---------------------------
def test_capacity_report_numbers_come_from_the_pipeline():
    import src.reports as R
    cap = capacity_report()
    c = R._load("capacity")
    for k, w in c["widths"].items():
        assert f"{w['width_m']} m" in cap


def test_reports_contain_no_placeholders():
    cap, meth = capacity_report(), method_statement()
    for doc in (cap, meth):
        assert "TODO" not in doc and "TBD" not in doc and "XXX" not in doc


def test_method_statement_states_where_it_stops_being_reliable():
    meth = method_statement()
    assert "stops being reliable" in meth
    assert "e-rickshaw" in meth.lower()


# --- design life -------------------------------------------------------------
def test_capacity_report_states_design_life_not_only_opening_year():
    """
    Regression: the report was titled 'capacity and design-year assessment', declared a
    20-year horizon, and contained no forecast at all — so the grade-separation section
    read as a clean win when 0 of 12 approaches actually survive to the horizon.
    """
    import src.reports as R
    cap = capacity_report()
    c = R._load("capacity")
    assert "How long does that relief last" in cap
    assert str(c["design_life_first_failure_med"]) in cap
    for d in c["design_life"]:
        assert str(d["fails_med"]) in cap


def test_opening_year_relief_is_labelled_as_such():
    cap = capacity_report()
    section = cap.split("## 5.")[1].split("## 6.")[0]
    assert "on opening" in section


# --- data dictionary ---------------------------------------------------------
def test_every_published_field_is_documented():
    """
    The dictionary's field list is read from the data, so this fails the moment a field
    is added to the pipeline without a description — which is the whole point of
    generating it rather than writing it.
    """
    from src.dictionary import build
    _md, _doc, undocumented, _unused = build()
    assert undocumented == [], f"undocumented fields: {undocumented}"


def test_dictionary_states_the_crs_and_explains_the_bands():
    from src.dictionary import build
    md, *_ = build()
    assert "EPSG:32643" in md
    assert "false precision" in md
    assert "policy" in md.lower()
