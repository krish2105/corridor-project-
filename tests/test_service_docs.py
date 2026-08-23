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

# Every test here renders a deliverable, which needs out/data. See conftest.
from conftest import needs_generated_output

pytestmark = needs_generated_output()


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


# --- README ------------------------------------------------------------------
def test_readme_names_only_modules_that_exist():
    """The documented run order is the first thing anyone follows. It must work."""
    from src.config import ROOT
    from src.service_docs import PIPELINE_ORDER
    for module, _desc in PIPELINE_ORDER:
        assert (ROOT / "src" / f"{module}.py").exists(), module


def test_readme_run_order_respects_dependencies():
    """capacity feeds delay, delay feeds economics, and exports come after all of them."""
    from src.service_docs import PIPELINE_ORDER
    order = [m for m, _ in PIPELINE_ORDER]
    assert order.index("capacity") < order.index("delay")
    assert order.index("delay") < order.index("economics")
    assert order.index("economics") < order.index("export")
    assert order.index("export") < order.index("reports")
    assert order.index("reports") < order.index("service_docs")


def test_readme_carries_the_full_findings_table(c):
    """Regression: the README's table stopped at the audit, understating by five findings."""
    from src.service_docs import readme
    rm = readme(c)
    assert str(c["cap"]["design_life_first_failure_med"]) in rm
    assert str(c["dly"]["spillback_count"]) in rm
    assert str(c["eco"]["annual_cost_crore"][1]) in rm
    assert str(c["tests"]) in rm


def test_readme_on_disk_matches_what_the_generator_produces(c):
    """
    If these diverge, someone edited the output instead of the generator.

    Note the self-reference: the README states the test count, so ADDING a test makes
    this fail until `uv run python src/service_docs.py` is re-run. That is deliberate —
    it is the same relationship a lockfile has to a manifest, and it is what stops the
    figure going stale the way "26 tests" did. Regenerating is the fix, not an exemption.
    """
    from src.config import ROOT
    from src.service_docs import readme
    on_disk = (ROOT / "README.md").read_text()
    assert on_disk == readme(c)


def test_readme_states_the_errata_count_from_the_document_itself(c):
    from src.config import ROOT
    from src.service_docs import readme
    actual = (ROOT / "docs" / "jaipur_corridor_study.md").read_text().count("ERRATUM")
    assert f"correcting {actual} defects" in readme(c)


def test_superseded_docs_say_so_at_the_top():
    """
    docs/inputs_models_stack.md describes a six-arm roundabout, not this corridor.
    Anyone following its input list would collect the wrong things.
    """
    from src.config import ROOT
    doc = (ROOT / "docs" / "inputs_models_stack.md").read_text()
    assert "SUPERSEDED" in doc[:400]
    runbook = (ROOT / "docs" / "setup_runbook.md").read_text()
    i = runbook.find("# PROMPT ORDER")
    assert i > 0 and "SUPERSEDED" in runbook[i:i + 400]


def test_a_filtered_pytest_run_cannot_overwrite_the_published_test_count():
    """
    The collection hook writes out/data/testcount.json, which service_docs.py publishes as
    a headline figure. It used to write on EVERY run, so `pytest tests/test_x.py` recorded
    that file's handful of tests as the project's count and the next document build shipped
    it. CI runs a filtered step, so this had a scheduled cause. The hook must bail out on
    any filtered invocation.
    """
    import inspect
    import conftest
    src = inspect.getsource(conftest.pytest_collection_finish)
    for opt in ("keyword", "markexpr", "file_or_dir"):
        assert opt in src, f"the hook does not check for a {opt} filter"
    assert "return" in src.split("filtered")[-1][:200], (
        "the hook detects a filtered run but does not bail out of it")
