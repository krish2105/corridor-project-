"""
Tests for the dashboard components, read as source.

The defect pinned here is one that no unit test of the data layer could ever catch and
that a screenshot would not reveal either: the junction picker could display one
junction's label above another junction's numbers.

JunctionExplorer wrapped its panel in `AnimatePresence mode="wait"`, which holds the
outgoing panel mounted until its exit animation reports completion. That completion runs
on requestAnimationFrame, which is paused entirely in a hidden tab and throttled on some
devices. Measured: zero rAF frames in 10.2 seconds with the tab hidden, during which
aria-pressed read TMC-02 while the movement table still listed TMC-01's arms.

On a page whose entire value is that its numbers can be trusted, a state where the label
and the data disagree is the worst failure available.
"""
import re
from pathlib import Path

import pytest

from src.config import ROOT

COMPONENTS = ROOT / "web" / "components"
EXPLORER = COMPONENTS / "JunctionExplorer.tsx"


def _code_only(path):
    """
    Strip JSX and block comments before matching.

    The first version of these tests matched the words inside the very comment that
    explains why the pattern was removed, and failed on a file that was correct.
    """
    src = path.read_text()
    src = re.sub(r"\{/\*.*?\*/\}", "", src, flags=re.S)   # JSX comment blocks
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)         # plain block comments
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)          # line comments
    return src



def test_the_junction_panel_does_not_wait_on_an_animation_to_swap():
    src = _code_only(EXPLORER)
    assert 'mode="wait"' not in src
    assert "AnimatePresence" not in src


def test_the_panel_is_keyed_on_the_selected_junction():
    """Keying on `code` is what makes the swap happen with React state, synchronously."""
    src = _code_only(EXPLORER)
    assert re.search(r"key=\{code\}", src)


def test_the_panel_reads_its_data_from_the_selected_code():
    src = _code_only(EXPLORER)
    assert re.search(r"junctions\.find\(\s*\(?x\)?\s*=>\s*x\.code === code\s*\)", src)


def test_the_reason_is_recorded_where_someone_would_re_add_it():
    """A comment, so the next person does not helpfully restore the crossfade."""
    src = EXPLORER.read_text()
    assert "requestAnimationFrame" in src
    assert "hidden tab" in src


def test_no_component_reintroduces_a_blocking_exit_animation():
    offenders = [p.name for p in COMPONENTS.glob("*.tsx")
                 if 'mode="wait"' in _code_only(p)]
    assert offenders == []


@pytest.mark.parametrize("path", sorted(COMPONENTS.glob("*.tsx")), ids=lambda p: p.name)
def test_client_components_declare_use_client(path):
    """A hook in a server component fails at build, but only if the directive is right."""
    src = path.read_text()
    if re.search(r"\buse(State|Effect|Ref|Memo|ReducedMotion)\b", src):
        assert src.lstrip().startswith('"use client"'), path.name


@pytest.mark.parametrize("path", sorted(COMPONENTS.glob("*.tsx")), ids=lambda p: p.name)
def test_toggles_expose_their_state_to_assistive_tech(path):
    """A button that toggles must say so; aria-pressed is how a screen reader reads it."""
    src = path.read_text()
    if "onClick" in src and ("setCode" in src or "toggle" in src.lower()):
        assert "aria-pressed" in src or "aria-label" in src, path.name
