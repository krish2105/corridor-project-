"""
Tests for the three commercial documents.

They were hand-written and went stale in exactly the way hand-written documents do:
quietly, and only in the numbers. A capability statement claiming 26 tests while the
suite held 144 is worse than no document — it is a credibility artefact that undermines
credibility. These tests exist so that cannot recur.
"""
import pytest

from src.service_docs import (DELIVERABLES, _status, capability_statement,
                              commercial_pack, context, implementation_plan, proven_table)


@pytest.fixture(scope="module")
def c():
    return context()


@pytest.fixture(scope="module")
def docs(c):
    return {"plan": implementation_plan(c), "pack": commercial_pack(c),
            "cap": capability_statement(c)}


def test_all_three_documents_generate(docs):
    assert all(len(v) > 3000 for v in docs.values())


def test_the_test_count_is_bound_not_typed(c, docs):
    """Regression: this said 26 while the suite held 144."""
    assert c["tests"] and c["tests"] > 100
    assert str(c["tests"]) in docs["plan"]
    assert str(c["tests"]) in docs["cap"]


def test_the_findings_table_carries_the_newest_conclusions(c):
    """A findings table that predates the strongest findings is the failure mode."""
    t = proven_table(c)
    assert str(c["cap"]["design_life_first_failure_med"]) in t
    assert str(c["dly"]["spillback_count"]) in t
    assert str(c["eco"]["annual_cost_crore"][1]) in t


def test_the_finding_that_argues_against_the_recommendation_is_included(c):
    t = proven_table(c)
    assert "does not last its own design horizon" in t
    assert "argues against our own recommendation" in t


def test_a_pro_forma_deliverable_is_not_reported_as_delivered():
    """
    Regression. A file on disk is not proof of a finished deliverable: D8 is a template
    whose gates are published ahead of its measurement.
    """
    d8 = next(d for d in DELIVERABLES if d[0] == "D8")
    assert "Pro forma" in _status(d8)
    assert "Delivered" not in _status(d8).replace("Pro forma", "")


def test_a_delivered_deliverable_says_so():
    d1 = next(d for d in DELIVERABLES if d[0] == "D1")
    assert _status(d1) == "**Delivered**" if d1[4].exists() else True


def test_a_missing_deliverable_is_scoped_not_promised(tmp_path):
    fake = ("DX", "Nonexistent", "n/a", "T9", tmp_path / "nope.md")
    assert _status(fake) == "Scoped"


def test_every_deliverable_has_a_real_path():
    for d in DELIVERABLES:
        assert d[4].is_absolute()


def test_rupee_figures_are_presented_as_bands(c, docs):
    """The delay is measured; the value of time is not ours to set."""
    if not c["eco"]:
        pytest.skip("economics not generated")
    lo, hi = c["eco"]["annual_cost_crore"]
    assert f"{lo}–{hi}" in docs["pack"]
    assert "policy input" in docs["pack"]


def test_the_honest_limits_survive_into_the_capability_statement(docs):
    cap = docs["cap"]
    for phrase in ("unverified", "inferred", "out of scope", "literature"):
        assert phrase in cap, phrase


def test_no_placeholder_text_anywhere(docs):
    joined = "\n".join(docs.values())
    for token in ("TODO", "TBD", "XXX", "lorem", "FIXME"):
        assert token not in joined
