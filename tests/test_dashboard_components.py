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
    """
    A button that toggles must say so, or a screen reader announces "button" and nothing
    about its state.

    Three attributes are correct here, for different controls, and the right one depends
    on what the button does: aria-pressed for a toggle button that stays in, aria-expanded
    for a disclosure that reveals a panel, aria-label where the control has no text.
    Accepting only the first would have pushed a disclosure into announcing itself as a
    pressed toggle, which is worse for a screen reader than the narrower test looked.
    """
    src = path.read_text()
    if "onClick" in src and ("setCode" in src or "toggle" in src.lower()):
        assert any(a in src for a in ("aria-pressed", "aria-expanded", "aria-label")), (
            f"{path.name}: a toggling button exposes no state to assistive tech")


# --- basemap -----------------------------------------------------------------
def test_the_map_has_no_third_party_tile_source():
    """
    Regression. The map pulled raster tiles from tile.openstreetmap.org, which breaches
    the OSM Tile Usage Policy for a commercial deliverable and could be rate-limited or
    blocked without warning while a client is looking at it.
    """
    src = _code_only(COMPONENTS / "CorridorMap.tsx")
    assert "openstreetmap.org" not in src
    assert "tile." not in src


def test_the_basemap_is_the_survey_drawing():
    src = _code_only(COMPONENTS / "CorridorMap.tsx")
    assert "basemap.geojson" in src
    for layer in ("base-structures", "base-carriageway", "base-median"):
        assert layer in src, layer


def test_basemap_colours_come_from_theme_tokens_not_literals():
    """A literal here is a light-theme colour that survives into dark mode."""
    src = _code_only(COMPONENTS / "CorridorMap.tsx")
    for tok in ("--sunk", "--rule-hard", "--rule"):
        assert tok in src, tok


def test_the_map_repaints_when_the_theme_changes():
    """
    Regression. Paint colours resolve from CSS custom properties once, at construction,
    so without an observer a switch to dark left the map a bright grey rectangle on a
    near-black page. The initial call matters too: the ground layer is created in the
    constructor, so a first load in dark mode was wrong without it.
    """
    src = _code_only(COMPONENTS / "CorridorMap.tsx")
    assert "MutationObserver" in src
    assert "data-theme" in src
    assert "prefers-color-scheme" in src
    assert src.count("repaint()") >= 1


def test_the_theme_listener_is_removed_with_the_same_reference():
    """Passing a fresh arrow to removeEventListener removes nothing and leaks per mount."""
    src = _code_only(COMPONENTS / "CorridorMap.tsx")
    assert 'mq.addEventListener("change", repaint)' in src
    assert 'mq.removeEventListener("change", repaint)' in src
    assert "themeWatch.disconnect()" in src


# --- volume flow diagram -----------------------------------------------------
def test_a_through_movement_is_never_called_a_turn():
    """
    Regression. The group label read "straight turns", which is not a thing. A through
    movement does not turn, and that phrase is the kind an engineer stops reading after.
    """
    src = _code_only(COMPONENTS / "VolumeFlow.tsx")
    assert "straight turns" not in src.lower()
    assert "through movements" in src


def test_isolation_is_driven_by_click_not_hover_alone():
    """
    There is no hover on a phone, and a phone in a meeting is the whole reason this is a
    link rather than a PDF. Hover stays as a desktop preview; click is what has to work.
    """
    src = _code_only(COMPONENTS / "VolumeFlow.tsx")
    assert "onClick" in src
    assert "setPinned" in src
    assert "pinned ?? hover" in src


def test_movements_enter_and_leave_on_the_left():
    """
    India drives on the left. Entering and leaving on opposite sides of the centreline is
    what makes a left turn hug the kerb and a right turn cross the junction — drawn from
    the centreline, the diagram stops showing which movement crosses opposing traffic.
    """
    src = _code_only(COMPONENTS / "VolumeFlow.tsx")
    assert "entering ? 1 : -1" in src


def test_the_uncounted_uturn_is_shown_as_a_hole():
    src = _code_only(COMPONENTS / "VolumeFlow.tsx")
    assert "strokeDasharray" in src
    assert "U?" in src
