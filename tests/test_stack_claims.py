"""
Tests that the stack we CLAIM is the stack we USE.

This exists because the capability statement — the document that tells a client what we
can do — named five technologies the project does not use, and one of them, ezdxf, had
been evaluated and deliberately REJECTED because the survey drawing is 198 MB and
ezdxf.readfile is not practical on it. The DXF is streamed by a parser written for this
project. The document said otherwise for weeks.

That is the same defect this engagement exists to find in someone else's work: a stated
figure that nobody checked against the thing it describes. It is worse here, because the
whole pitch is that we check.

So the check is automated. `pyproject.toml` is checked against the import graph, and
every generated document is checked against a list of libraries we do not use.
"""
import ast
import re
import sys
import tomllib
from pathlib import Path

import pytest

from src.config import ROOT

# Import name -> distribution name, where they differ.
ALIAS = {"cv2": "opencv-python", "yaml": "pyyaml", "PIL": "pillow"}

# Declared but never imported, legitimately: pandas loads these itself when asked for
# Parquet and for markdown tables. Removing them breaks to_parquet / to_markdown.
IMPLICIT = {"pyarrow", "tabulate"}

# Evaluated and not used. Naming any of these in a deliverable is a false claim.
# ezdxf: cannot practically open a 198 MB DXF; dxf_inventory streams group codes instead.
# sahi:  the slicing technique is implemented directly in detect.py, under our own tests.
# osmnx / geopandas / networkx / folium: never needed — the survey supplies movements and
#        the CAD supplies geometry.
NOT_USED = {"ezdxf", "sahi", "osmnx", "geopandas", "networkx", "folium"}

# What a client actually receives.
DELIVERABLES = [ROOT / "README.md",
                ROOT / "out" / "method_statement.md",
                ROOT / "out" / "capacity_report.md",
                ROOT / "out" / "validation_report.md",
                ROOT / "docs" / "data_dictionary.md",
                *sorted((ROOT / "out" / "service").glob("*.md"))]


def _imported():
    """Every third-party top-level package imported anywhere in src/ or tests/."""
    stdlib = set(sys.stdlib_module_names)
    found = set()
    for p in list((ROOT / "src").glob("*.py")) + list((ROOT / "tests").glob("*.py")):
        for n in ast.walk(ast.parse(p.read_text())):
            if isinstance(n, ast.Import):
                found |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                found.add(n.module.split(".")[0])
    # conftest is this repo's own fixture module, imported by name because pandas ships
    # a top-level `tests` package that shadows `tests.conftest`.
    local = {"src", "tests", "conftest"}
    return {ALIAS.get(m, m).lower() for m in found
            if m not in stdlib and m not in local}


def _declared():
    d = tomllib.loads((ROOT / "pyproject.toml").read_text())
    deps = list(d["project"]["dependencies"])
    deps += [x for grp in d.get("dependency-groups", {}).values() for x in grp]
    return {re.split(r"[>=<\[;]", x)[0].strip().lower() for x in deps}


def test_everything_imported_is_declared():
    """
    numpy, torch and pytest were all imported directly while arriving only as transitive
    dependencies of pandas, ultralytics and nothing at all. A clean install could break
    without a single line of our code changing.
    """
    missing = sorted(_imported() - _declared())
    assert missing == [], f"imported but not declared: {missing}"


def test_everything_declared_is_used():
    unused = sorted(_declared() - _imported() - IMPLICIT)
    assert unused == [], f"declared but never imported: {unused}"


def test_the_rejected_libraries_are_not_declared():
    assert _declared() & NOT_USED == set()


def test_the_rejected_libraries_are_not_imported():
    assert _imported() & NOT_USED == set()


@pytest.mark.parametrize("path", DELIVERABLES, ids=lambda p: p.name)
def test_no_deliverable_claims_a_library_we_do_not_use(path):
    """The capability statement claimed ezdxf, geopandas, networkx and SAHI."""
    if not path.exists():
        pytest.skip(f"{path.name} not generated")
    text = path.read_text().lower()
    named = sorted(lib for lib in NOT_USED if re.search(rf"\b{lib}\b", text))
    assert named == [], f"{path.name} names libraries the project does not use: {named}"


def test_claude_md_records_why_each_rejected_library_was_rejected():
    """
    CLAUDE.md may name them — it is the only place that should, and only to say they are
    not used and why, so nobody helpfully reintroduces one.
    """
    md = (ROOT / "CLAUDE.md").read_text()
    section = md[md.find("Deliberately NOT used"):]
    assert section, "CLAUDE.md has no 'Deliberately NOT used' section"
    for lib in NOT_USED:
        assert lib in section.lower(), f"{lib} not accounted for in CLAUDE.md"


def test_the_slicing_we_describe_is_the_slicing_we_implement():
    """We claim sliced inference. These are the functions that have to exist for it."""
    src = (ROOT / "src" / "detect.py").read_text()
    for fn in ("def slices(", "def merge(", "def iou("):
        assert fn in src, fn
