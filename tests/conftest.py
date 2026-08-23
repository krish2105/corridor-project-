"""
Synthetic survey fixtures.

WHY THESE EXIST
Coverage of the analysis layer was 23-46% and the uncovered part was the part that
matters: `approach_pcu`, `analyse`, `scenarios`, `uturn_verdict`, `oversaturated_hours`,
`through_vs_turning`, `corridor_order` — every function that turns the workbooks into a
published number. Their bodies were never executed by any test. A silent error in
`approach_pcu` would flow into both artifacts, the dashboard, the capacity report and the
commercial pack, and nothing would fail.

They were untested because they need the client's twelve workbooks and a 198 MB CAD
drawing, neither of which is in this repository by design. So the fixture builds a
corridor small enough to reason about by hand: two junctions, one day, four arms each,
twelve movements, ninety-six fifteen-minute bins, with counts chosen so the expected
answers can be worked out on paper and asserted exactly.

WHAT IS DELIBERATELY NOT SYNTHETIC
The class scheme, the arm ordering, the 08:00 day boundary and the bin structure are
copied from the real survey rather than invented, because a fixture that disagrees with
the source format tests the fixture instead of the code.
"""
import json
from datetime import date, datetime, timedelta

import pandas as pd
import pytest

DAY = date(2026, 5, 11)
START = datetime(2026, 5, 11, 8, 0)
N_BINS = 96                      # 24 h of 15-minute bins, 08:00 -> 08:00

# REAL junction codes with their REAL arm names, carrying SYNTHETIC counts.
#
# Not a stylistic choice. analyse.py and scheme_test.py resolve arm order by looking the
# junction code up in the module-level JUNCTIONS / JUNCTION_COORDS registries in
# config.py, so a junction that is not in those dicts raises KeyError before any
# arithmetic runs. Invented codes fail immediately.
#
# That coupling is exactly why this layer had no tests: the analysis functions cannot be
# exercised on data that does not describe this specific corridor. Taking the arms as a
# parameter would fix it properly and is recorded as a finding; using the real codes here
# buys the coverage now without refactoring the analysis right before a client sees it.
from src.config import JUNCTIONS

ARMS = {code: list(JUNCTIONS[code]) for code in ("TMC-01", "TMC-02")}
MOVES = ["Left", "Straight", "Right"]

# A flat stream: every bin identical, so peak-hour arithmetic has an exact answer and any
# drift shows up immediately. Composition is roughly the real one - two-wheelers about
# half the stream - because the PCU correction is share-dependent and a fixture with an
# unrealistic mix would exercise the wrong branch of factor_band().
PER_BIN = {"TWO_W": 50.0, "CAR_BUCKET": 40.0, "AUTO_TRK_BUS": 6.0,
           "AGRI_LCV": 2.0, "CYCLE": 2.0}


def _rows(junction, arms, per_bin, n_bins=N_BINS):
    out = []
    for entry in range(4):
        for offset, mv in enumerate(MOVES, start=1):
            exit_arm = arms[(entry + offset) % 4]
            sheet = f"V_{entry * 3 + offset}"
            for b in range(n_bins):
                t = START + timedelta(minutes=15 * b)
                for cls, n in per_bin.items():
                    out.append(dict(
                        junction=junction, date=DAY, sheet=sheet, kind="movement",
                        arm_from=arms[entry], arm_to=exit_arm, movement=mv,
                        bin_start=pd.Timestamp(t),
                        bin_label=f"{t:%H%M}-{(t + timedelta(minutes=15)):%H%M}",
                        veh_class=cls, count=float(n), stored_pcu=0.0))
    return out


@pytest.fixture(scope="session")
def synth_bins():
    """
    A two-junction corridor with a flat 24-hour profile.

    Exact by construction, per junction:
      each movement    = 96 bins x 100 veh = 9,600 veh/day
      each approach    = 3 movements       = 28,800 veh/day
      junction total   = 4 approaches      = 115,200 veh/day
      any hour         = 4 bins x 100      = 400 veh/movement-hour
    """
    rows = []
    for j, arms in ARMS.items():
        rows += _rows(j, arms, PER_BIN)
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def synth_day():
    return DAY


@pytest.fixture(scope="session")
def synth_peaked():
    """
    The same corridor with a real peak, so peak-hour selection has something to find.

    Bins 4-7 (09:00-10:00) carry triple volume on TMC-01 only. Peak hour must therefore
    resolve to 09:00 on TMC-01 and stay flat on TMC-02.
    """
    rows = []
    for j, arms in ARMS.items():
        base = _rows(j, arms, PER_BIN)
        if j == "TMC-01":
            for r in base:
                b = int((r["bin_start"] - pd.Timestamp(START)).total_seconds() // 900)
                if 4 <= b < 8:
                    r["count"] *= 3.0
        rows += base
    return pd.DataFrame(rows)


# --- synthetic CAD ----------------------------------------------------------
# atlas.py, medians.py and capacity.py stream the DXF as group-code pairs rather than
# loading a document, because the real drawing is 198 MB. That makes a fixture cheap:
# a valid DXF for these readers is just the pairs, in the right sections, on layer names
# the LAYER_CAT map recognises.
#
# Geometry is a straight 500 m corridor running north, with a carriageway edge either
# side 7 m from the centre, a median in the middle broken by one 20 m opening, and two
# buildings. Every answer is therefore known: width 14 m kerb to kerb, one opening, and
# an alignment 500 m long.

_UTM_E, _UTM_N = 578000.0, 2976000.0        # Jaipur, EPSG:32643


def _dxf_entity(layer, points, closed=False):
    out = ["0", "LWPOLYLINE", "8", layer, "90", str(len(points)),
           "70", "1" if closed else "0"]
    for x, y in points:
        out += ["10", f"{x:.3f}", "20", f"{y:.3f}"]
    return out


@pytest.fixture(scope="session")
def synth_dxf(tmp_path_factory):
    """A minimal DXF the streaming readers accept, with hand-known geometry."""
    n0, n1 = _UTM_N, _UTM_N + 500.0
    pairs = ["0", "SECTION", "2", "ENTITIES"]
    # corridor centreline
    pairs += _dxf_entity("kml road", [(_UTM_E, n0), (_UTM_E, n1)])
    # carriageway edges, 7 m either side -> 14 m kerb to kerb
    pairs += _dxf_entity("BT ROAD", [(_UTM_E - 7, n0), (_UTM_E - 7, n1)])
    pairs += _dxf_entity("BT ROAD", [(_UTM_E + 7, n0), (_UTM_E + 7, n1)])
    # median in two runs with a 20 m opening between 240 m and 260 m
    pairs += _dxf_entity("DIVIDER", [(_UTM_E, n0), (_UTM_E, n0 + 240)])
    pairs += _dxf_entity("DIVIDER", [(_UTM_E, n0 + 260), (_UTM_E, n1)])
    # two buildings clear of the carriageway
    pairs += _dxf_entity("BUILDING", [(_UTM_E + 20, n0 + 50), (_UTM_E + 30, n0 + 50),
                                      (_UTM_E + 30, n0 + 60), (_UTM_E + 20, n0 + 60)],
                         closed=True)
    pairs += _dxf_entity("BUILDING", [(_UTM_E - 30, n0 + 300), (_UTM_E - 20, n0 + 300),
                                      (_UTM_E - 20, n0 + 310), (_UTM_E - 30, n0 + 310)],
                         closed=True)
    pairs += ["0", "ENDSEC", "0", "EOF"]

    path = tmp_path_factory.mktemp("cad") / "synthetic.dxf"
    path.write_text("\n".join(pairs) + "\n")
    return path


def pytest_collection_finish(session):
    """
    Record how many tests were collected, so the builders do not have to shell out.

    build_pitch.py and service_docs.py previously ran `uv run pytest --collect-only` at
    BUILD time to learn their own test count. It worked, but a document build that spawns
    a test runner is slow, and it breaks anywhere pytest is not installed - which is any
    environment that only wants to render the deliverables.
    """
    from src.config import OUT_DATA
    try:
        OUT_DATA.mkdir(parents=True, exist_ok=True)
        (OUT_DATA / "testcount.json").write_text(json.dumps(
            {"collected": len(session.items)}))
    except Exception:
        pass          # recording the count must never fail a test run


def needs_generated_output():
    """
    Module-level skip for tests that render a deliverable.

    Rendering any document requires out/data, which is gitignored because every file in
    it derives from the client's workbooks and CAD. On a clean checkout - which is what
    CI runs - those files do not exist and reports._load() calls SystemExit. Sixteen
    tests failed that way on CI's very first run.
    """
    from src.config import OUT_DATA
    return pytest.mark.skipif(
        not (OUT_DATA / "corridor.json").exists(),
        reason="deliverables are generated from client data, absent on a clean checkout")


@pytest.fixture(scope="session")
def published():
    """
    Loader for generated datasets in out/data, or skip.

    Delivered as a fixture rather than an importable helper on purpose: pandas ships a
    top-level `tests` package, so `from tests.conftest import ...` resolves to
    site-packages instead of this file. Fixtures are injected by pytest and dodge the
    shadowing entirely.

    out/ is gitignored because everything in it derives from the client's workbooks and
    CAD, so on a clean checkout - which is exactly what CI runs - these files do not
    exist. A test that reads one without guarding fails for the wrong reason and turns
    CI red on its first run, which is what happened.
    """
    import json
    from src.config import OUT_DATA

    def _load(name):
        p = OUT_DATA / f"{name}.json"
        if not p.exists():
            pytest.skip(f"{name}.json is generated from client data, "
                        "absent on a clean checkout")
        return json.loads(p.read_text())
    return _load
