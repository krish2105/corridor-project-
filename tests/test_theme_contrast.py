"""
Contrast and touch-target tests for the design tokens.

These check the CSS directly rather than a rendered page, so they run in the suite
without a browser and cannot be skipped for convenience.

The defect they pin was real and shipped: --faint was #8B938E, which is 2.81:1 on the
paper ground where WCAG AA wants 4.5:1, and it was carrying 31 elements of small label
text on the live dashboard. A palette can look considered and still be unreadable, and
nothing in a screenshot review reliably catches a 2.8:1 ratio at 11px.
"""
import re
from pathlib import Path

import pytest

from src.config import ROOT

SURFACES = [ROOT / "web" / "app" / "globals.css",
            ROOT / "src" / "page_template.html",
            ROOT / "src" / "pitch_template.html"]
AA_NORMAL = 4.5
AA_LARGE = 3.0


def _lum(hex_colour):
    h = hex_colour.lstrip("#")
    vals = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4) for c in vals]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def tokens(path, block):
    """
    Pull the token values from one :root block.

    block 0 is the light palette on bare :root; 1 and 2 are the dark redefinitions under
    the media query and the [data-theme] stamp, which must agree with each other.
    """
    text = path.read_text()
    blocks = re.findall(r":root[^{]*\{([^}]*)\}", text)
    assert len(blocks) >= 3, f"{path.name}: expected 3 :root blocks, found {len(blocks)}"
    return dict(re.findall(r"--([\w-]+)\s*:\s*(#[0-9A-Fa-f]{6})", blocks[block]))


@pytest.mark.parametrize("path", SURFACES, ids=lambda p: p.name)
@pytest.mark.parametrize("block,theme", [(0, "light"), (1, "dark-media"), (2, "dark-stamp")])
def test_body_text_meets_aa_on_every_ground(path, block, theme):
    t = tokens(path, block)
    grounds = [t[g] for g in ("paper", "surface", "sunk") if g in t]
    for fg in ("ink", "muted", "faint"):
        if fg not in t:
            continue
        for bg in grounds:
            r = contrast(t[fg], bg)
            assert r >= AA_NORMAL, f"{path.name} {theme}: --{fg} on {bg} is {r:.2f}:1"


@pytest.mark.parametrize("path", SURFACES, ids=lambda p: p.name)
@pytest.mark.parametrize("block,theme", [(0, "light"), (1, "dark-media"), (2, "dark-stamp")])
def test_semantic_colours_meet_aa(path, block, theme):
    """Accent, risk and ok all carry text, so they are held to the same bar."""
    t = tokens(path, block)
    for fg in ("accent", "risk", "ok", "defect"):
        if fg not in t:
            continue
        for g in ("paper", "surface"):
            if g in t:
                r = contrast(t[fg], t[g])
                assert r >= AA_NORMAL, f"{path.name} {theme}: --{fg} on --{g} is {r:.2f}:1"


@pytest.mark.parametrize("path", SURFACES, ids=lambda p: p.name)
def test_the_two_dark_definitions_agree(path):
    """
    A dark palette split across a media query and a [data-theme] stamp must define the
    same values, or the toggle and the OS setting disagree on the same page.
    """
    assert tokens(path, 1) == tokens(path, 2), path.name


@pytest.mark.parametrize("path", SURFACES, ids=lambda p: p.name)
def test_hierarchy_survives_the_contrast_fix(path):
    """faint must stay lighter than muted, or the de-emphasis it exists for is gone."""
    for block in (0, 1):
        t = tokens(path, block)
        if "faint" in t and "muted" in t and "paper" in t:
            assert contrast(t["faint"], t["paper"]) <= contrast(t["muted"], t["paper"]), \
                f"{path.name} block {block}: faint is no lighter than muted"


@pytest.mark.parametrize("path", SURFACES, ids=lambda p: p.name)
def test_touch_targets_are_raised_on_coarse_pointers(path):
    """
    Apple HIG asks 44x44pt, Material 48x48dp. The desktop density here is deliberate, so
    the minimum is raised only under (pointer: coarse) — and that rule must not be nested
    inside another media query, which is how it was first written.
    """
    text = path.read_text()
    assert "pointer: coarse" in text, path.name
    m = re.search(r"@media\s*\(pointer:\s*coarse\)\s*\{", text)
    assert m, path.name
    before = text[:m.start()]
    assert before.count("{") - before.count("}") == 0, \
        f"{path.name}: the coarse-pointer rule is nested inside another block"
    rule = text[m.start():m.start() + 400]
    assert "44px" in rule, path.name


@pytest.mark.parametrize("path", SURFACES, ids=lambda p: p.name)
def test_reduced_motion_is_respected(path):
    assert "prefers-reduced-motion" in path.read_text(), path.name


@pytest.mark.parametrize("path", SURFACES, ids=lambda p: p.name)
def test_body_paints_its_own_background(path):
    """
    An artifact composites over a ground the viewer paints in its own theme. A transparent
    body silently borrows the host's, and the page renders one theme's text on the other
    theme's ground.
    """
    text = path.read_text()
    m = re.search(r"body\s*\{([^}]*)\}", text)
    assert m and "background" in m.group(1), path.name
