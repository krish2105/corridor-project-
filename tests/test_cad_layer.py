"""
Tests for the CAD readers, against a synthetic drawing with known geometry.

atlas.read_geometry, medians.median_runs/chainage and capacity's transect logic had
bodies no test executed, because they need a 198 MB drawing that is the client's and is
not in this repository. The fixture is a straight 500 m corridor: 14 m kerb to kerb, a
median with exactly one 20 m opening, two buildings. Every expected answer is known.
"""
import pytest

from src.atlas import LAYER_CAT, read_geometry
from src.medians import classify, openings


def test_the_reader_finds_every_planted_layer(synth_dxf):
    geo = read_geometry(synth_dxf)
    assert set(geo) >= {"alignment", "carriageway", "median", "structures"}


def test_layers_land_in_the_right_categories(synth_dxf):
    geo = read_geometry(synth_dxf)
    assert len(geo["carriageway"]) == 2          # one edge either side
    assert len(geo["median"]) == 2               # two runs, one opening between them
    assert len(geo["structures"]) == 2
    assert len(geo["alignment"]) == 1


def test_geometry_survives_the_stream_intact(synth_dxf):
    """A 500 m centreline must come back as a 500 m centreline."""
    geo = read_geometry(synth_dxf)
    _layer, _kind, pts = geo["alignment"][0]
    assert len(pts) == 2
    assert abs(pts[1][1] - pts[0][1]) == pytest.approx(500.0, abs=0.01)


def test_coordinates_stay_in_utm_43n(synth_dxf):
    """Jaipur is E~578000 N~2976000. Anything else means a projection went wrong."""
    geo = read_geometry(synth_dxf)
    for cat in geo.values():
        for _l, _k, pts in cat:
            for x, y in pts:
                assert 570_000 < x < 590_000, x
                assert 2_970_000 < y < 2_985_000, y


def test_an_unknown_layer_is_ignored_not_guessed(synth_dxf, tmp_path):
    extra = tmp_path / "extra.dxf"
    extra.write_text(synth_dxf.read_text().replace("BUILDING", "SOME UNMAPPED LAYER"))
    geo = read_geometry(extra)
    assert "structures" not in geo or len(geo["structures"]) == 0


def test_the_planted_median_opening_is_the_one_that_is_found(synth_dxf):
    """
    Runs at 0-240 and 260-500 leave exactly one 20 m gap. This is the erratum case:
    a max over all pairwise distances would report 500 m, the whole median.
    """
    geo = read_geometry(synth_dxf)
    runs = sorted((min(p[1] for p in pts), max(p[1] for p in pts))
                  for _l, _k, pts in geo["median"])
    gaps = openings(runs)
    assert len(gaps) == 1
    assert gaps[0][1] == pytest.approx(20.0, abs=0.01)
    assert classify(gaps[0][1]) in {"typical opening", "wide / junction mouth"}


def test_carriageway_width_is_recoverable_from_the_edges(synth_dxf):
    """Edges at -7 and +7 must give 14 m kerb to kerb, not 7 and not 28."""
    geo = read_geometry(synth_dxf)
    xs = [pts[0][0] for _l, _k, pts in geo["carriageway"]]
    assert max(xs) - min(xs) == pytest.approx(14.0, abs=0.01)


def test_every_mapped_layer_name_has_a_category():
    assert all(isinstance(v, str) and v for v in LAYER_CAT.values())


# --- median openings and the chainage convention ------------------------------

def test_openings_are_reported_at_their_centre_not_an_edge():
    """
    Which edge of a gap is its "start" depends on which end the corridor is chained from,
    so reporting the start moved every opening by its own width when the convention was
    reversed - up to 33 m here, and up to 47 m on the U-turn detours derived from them.
    Nothing caught it because nothing had ever run both ways.

    The centre is direction-independent, and it is where a vehicle turning through 180
    degrees actually is.
    """
    from src.medians import openings
    merged = [(0.0, 100.0), (130.0, 200.0), (260.0, 300.0)]
    got = openings(merged)
    assert got == [(115.0, 30.0), (230.0, 60.0)]


def test_opening_centres_mirror_when_the_corridor_is_chained_from_the_other_end():
    """
    The invariance the whole convention rests on: chainage direction decides which end is
    zero and nothing else. Reverse the runs, mirror the chainages, and the centres land on
    the same physical points.
    """
    from src.medians import openings
    total = 300.0
    fwd = [(0.0, 100.0), (130.0, 200.0), (260.0, 300.0)]
    rev = sorted((total - hi, total - lo) for lo, hi in fwd)
    a = sorted(total - c for c, _w in openings(fwd))
    b = sorted(c for c, _w in openings(rev))
    assert a == pytest.approx(b)
    # and the widths are unchanged either way
    assert sorted(w for _c, w in openings(fwd)) == sorted(w for _c, w in openings(rev))
