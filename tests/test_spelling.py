"""
Tests for spelling.py.

The register is one of the few places where getting it slightly wrong is invisible: a
correction that quietly rewrites a figure, or one that erases the provenance it exists to
preserve, produces a document that looks better and is worth less.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.spelling import (ALLOW, CORRECTIONS, as_received_of, fix, known, unconfirmed)


def test_source_labels_are_not_rewritten():
    """
    The whole design. config and tmc_parse mirror what the workbooks say, and the audit's
    turn-mapping check is validated against the sheets' own headers. Correcting at source
    would break traceability from any figure back to a source cell.
    """
    from src.config import JUNCTIONS
    from src.tmc_parse import CLASS_LABELS
    assert CLASS_LABELS["TWO_W"] == "Motar Cycle, Scooter"
    assert CLASS_LABELS["BULLOCK"] == "Bullock Corts"
    assert JUNCTIONS["TMC-01"][0] == "Mansarover Metro"


def test_corrections_apply():
    assert fix("Motar Cycle, Scooter") == "Motor Cycle, Scooter"
    assert fix("Bullock Corts") == "Bullock Carts"
    assert fix("Mansarover Metro") == "Mansarovar Metro"
    assert fix("Rajatpath") == "Rajat Path"


def test_the_longer_place_rule_wins_over_the_shorter():
    """
    Regression by construction. `Mansarover` is a prefix of `Mansarover Metro`, so
    applying the short rule first yields `Mansarovar Metro` by luck here - but the
    ordering is what makes it luck-free, and a future pair may not be so forgiving.
    """
    assert fix("Mansarover Metro") == "Mansarovar Metro"
    assert fix("Mansarover") == "Mansarovar"


def test_fix_is_idempotent():
    for c in CORRECTIONS:
        assert fix(fix(c["as_received"])) == fix(c["as_received"])


def test_fix_leaves_non_strings_alone():
    assert fix(None) is None
    assert fix(12) == 12


def test_confirmed_corrections_never_touch_a_digit():
    """A change that alters a number has altered content, not spelling."""
    import re
    for c in CORRECTIONS:
        if c["confirmed"]:
            assert (re.findall(r"\d", c["as_received"])
                    == re.findall(r"\d", c["corrected"])), c["as_received"]


def test_the_inferred_ones_are_the_ones_that_change_a_word():
    unc = unconfirmed()
    assert len(unc) == 2
    for c in unc:
        assert c["kind"] == "inferred"
        assert "Table 3.1" in c["note"]


def test_provenance_is_recoverable():
    for c in CORRECTIONS:
        assert as_received_of(c["corrected"]) == c["as_received"]
    assert as_received_of("Sanganer Stadium") == "Sanganer Stadium"


def test_publishing_boundary_corrects_but_keeps_the_evidence():
    """
    `label` and `label_as_received` sit two lines apart in the same dict. A recursive
    correction that does not skip the provenance key erases exactly the field that proves
    the correction was needed.
    """
    from src.export import spell_payload
    out = spell_payload({"label": "Motar Cycle, Scooter",
                         "label_as_received": "Motar Cycle, Scooter",
                         "as_received": "Bullock Corts",
                         "nested": [{"arms": ["Mansarover Metro"]}]})
    assert out["label"] == "Motor Cycle, Scooter"
    assert out["label_as_received"] == "Motar Cycle, Scooter"
    assert out["as_received"] == "Bullock Corts"
    assert out["nested"][0]["arms"] == ["Mansarovar Metro"]


# --- the prose check ---------------------------------------------------------

@pytest.fixture(scope="module")
def words():
    from src.spelling import _dictionary
    w = _dictionary()
    if w is None:
        pytest.skip("no system word list at /usr/share/dict/words")
    return w


def test_known_accepts_inflections_the_base_word_list_omits(words):
    """
    macOS ships web2, which carries base forms only. Checked raw it reported 784 ordinary
    words as misspellings - a gate nobody would read, and therefore no gate.
    """
    for w in ("accepting", "aligned", "applies", "accumulated", "carrying", "stopped"):
        assert known(w, words), w


def test_known_accepts_contractions_and_possessives(words):
    for w in ("don't", "you've", "aren't", "JDA's", "corridor's"):
        assert known(w, words), w


def test_known_accepts_hyphenated_compounds_of_known_parts(words):
    assert known("peak-hour", words)
    assert known("left-hand", words)


def test_known_still_rejects_the_errors_this_module_exists_for(words):
    """
    The gate is generous about inflections and must not be generous about these. If a
    stem rule ever accepts them the check has stopped working.
    """
    for w in ("mansarover", "trailor", "corts", "motar", "servability"):
        assert w not in words, w
        stripped = ALLOW - {"mansarover", "trailor", "corts", "motar", "rajatpath"}
        import src.spelling as sp
        real, sp.ALLOW = sp.ALLOW, stripped
        try:
            assert not sp.known(w, words), w
        finally:
            sp.ALLOW = real
