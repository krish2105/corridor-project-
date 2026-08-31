"""
spelling.py — corrected labels for everything a reviewer reads, without losing the source.

THE PROBLEM THIS SOLVES, AND THE ONE IT REFUSES TO CREATE
The issued workbooks misspell their own column headings: `Motar Cycle`, `Bullock Corts`,
`Truck Trailor`. The place names carry a different problem - the survey writes `Mansarover`
where the Jaipur locality and its metro station are `Mansarovar`. Handing a client a
workbook that reproduces all of it looks careless, and it is the first thing a reviewer
sees.

The obvious fix is to correct the strings at source. That would be wrong. `config.JUNCTIONS`
and `tmc_parse.CLASS_LABELS` mirror what the twelve workbooks actually say, and the audit's
turn-mapping check is validated against the `Direction From/To` header those sheets carry.
Rewriting them silently breaks the one property this whole pipeline is built on: that any
figure can be traced back to a source cell.

So the source stays exactly as issued, correction happens at DISPLAY, and both spellings
are published side by side. A reviewer gets a clean document and can still see precisely
what was changed and why.

WHAT IS NOT CORRECTED
Two column headings look like they are missing a word rather than a letter -
`Three Wheeler (Auto) Axle Truck, Buses` against IRC:SP:41 Table 3.1's
`Three Wheeler (Auto), 3 Axle Truck, Buses`. A missing `3` changes what was counted, not
how it was spelled. Those carry `confirmed=False`, are rendered with the correction marked
as inferred, and appear on the reviewer question sheet instead of being quietly applied.

Run:  uv run python src/spelling.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import CORRIDOR_NAME, JUNCTIONS, JUNCTION_COORDS, OUT_DATA, ROOT

# Longest first at application time, so `Mansarover Metro` is matched before `Mansarover`
# and the shorter rule cannot corrupt what the longer one already fixed.
CORRECTIONS = [
    # --- survey column headings, plain typing errors -------------------------
    dict(as_received="Motar Cycle, Scooter",
         corrected="Motor Cycle, Scooter",
         kind="typo", confirmed=True,
         note="Motar -> Motor."),
    dict(as_received="Tractor Trailor, Truck Trailor Units (3 Axle & MAV)",
         corrected="Tractor Trailer, Truck Trailer Units (3 Axle & MAV)",
         kind="typo", confirmed=True,
         note="Trailor -> Trailer, twice."),
    dict(as_received="Bullock Corts",
         corrected="Bullock Carts",
         kind="typo", confirmed=True,
         note="Corts -> Carts."),
    dict(as_received="Car, Taxi, Tempo, Auto Rickshaw & Pick up",
         corrected="Car, Taxi, Tempo, Auto Rickshaw & Pickup",
         kind="style", confirmed=True,
         note="Pick up -> Pickup, as one noun."),

    # --- headings where a WORD looks missing, not a letter -------------------
    # Applied but flagged. IRC:SP:41 Table 3.1 is the proforma this scheme is copied from
    # and its rows carry the comma and the 3; the issued sheets do not. If that is a
    # typing error these are the standard rows. If it is not, the column counted something
    # we cannot name, which is a data question rather than a spelling one - so it is on
    # the reviewer question sheet and the correction is rendered as inferred.
    dict(as_received="Three Wheeler (Auto) Axle Truck, Buses",
         corrected="Three Wheeler (Auto), 3 Axle Truck, Buses",
         kind="inferred", confirmed=False,
         note="Comma and the 3 restored from IRC:SP:41 Table 3.1. NOT confirmed by JDA: "
              "a missing 3 changes what was counted, not how it was spelled."),
    dict(as_received="Agriculture Tractor, LCV Mini Bus",
         corrected="Agricultural Tractor, LCV, Mini Bus",
         kind="inferred", confirmed=False,
         note="Agriculture -> Agricultural, and a comma restored from IRC:SP:41 "
              "Table 3.1. The comma is NOT confirmed by JDA."),

    # --- place names ---------------------------------------------------------
    dict(as_received="Mansarover Metro",
         corrected="Mansarovar Metro",
         kind="place", confirmed=True,
         note="The Jaipur locality and its Pink Line metro station are Mansarovar. The "
              "survey writes Mansarover throughout."),
    dict(as_received="Mansarover",
         corrected="Mansarovar",
         kind="place", confirmed=True,
         note="As above, where the arm is the locality rather than the station."),
    dict(as_received="Rajatpath",
         corrected="Rajat Path",
         kind="place", confirmed=True,
         note="Two words in JDA's own scheme documents, which name the junction "
              "Rajat Path. The survey closes it up."),
]

_ORDERED = sorted(CORRECTIONS, key=lambda c: -len(c["as_received"]))


def fix(s):
    """Corrected text. Idempotent: running it on its own output changes nothing."""
    if not isinstance(s, str):
        return s
    for c in _ORDERED:
        s = s.replace(c["as_received"], c["corrected"])
    return s


def as_received_of(corrected):
    """The source spelling for a corrected label, or the label itself if untouched."""
    for c in _ORDERED:
        if c["corrected"] == corrected:
            return c["as_received"]
    return corrected


def unconfirmed():
    """Corrections that change a word rather than a letter. These need JDA to confirm."""
    return [c for c in CORRECTIONS if not c["confirmed"]]


# --- the prose check ---------------------------------------------------------
#
# Separate from the register above, which is about the CLIENT'S spelling. This is about
# ours: a generated report full of our own typos is no better than one full of theirs.
# Every word in the published documents is checked against the system word list, and
# anything unknown must be on the allowlist below or the gate fails.
#
# The allowlist is deliberately explicit rather than a pattern. A rule like "ignore
# capitalised words" would hide a misspelled place name, which is exactly the class of
# error that started this module.
ALLOW = {
    # place and scheme names
    "jaipur", "jda", "mansarovar", "mansarover", "sanganer", "rajat", "rajatpath",
    "patrika", "sumer", "durgapur", "mohanpura", "dholai", "mangyawas", "aatish",
    "bhrigu", "patel", "marg", "vt", "tmc", "corridorwide", "sanganer's",
    # places and bodies named in the precedent review
    "bengaluru", "chennai", "ahmedabad", "trivandrum", "koramangala", "agara", "sirsi",
    "iskcon", "kd", "sg", "bda", "dda", "uttipec", "uttipec's", "indot", "txdot",
    "deccan", "deshgujarat", "mdpi", "arxiv", "asce", "skywalk", "mut", "mutis",
    "mappls", "wikipedia", "vatika", "vihar", "aatish",
    "offside", "criticised", "rationalised", "summarise", "sustainability", "ft",
    "civ", "eng",
    # standards, codes and bodies
    "irc", "sp", "indo", "hcm", "csir", "crri", "easts", "epsg", "utm", "wgs", "kml",
    "dwg", "dxf", "cad", "geojson", "json", "parquet", "md", "html", "pdf", "xlsx",
    "annexure", "proforma",
    # traffic engineering
    "pcu", "pcus", "veh", "phf", "los", "uturn", "uturns", "signalised", "unsignalised",
    "carriageway", "carriageways", "kerb", "kerbs", "chainage", "chainages", "transect",
    "transects", "median", "medians", "spillback", "oversaturated", "saturation",
    "throughput", "sublane", "weaving", "deceleration", "decelerating", "gap",
    "midblock", "mid-block",
    "geometrics", "grade", "separation", "flyover", "rickshaw", "rickshaws", "tempo",
    "lcv", "mav", "axle", "bullock", "scooter", "pickup", "wheeler", "trailer",
    "vph", "kmh", "km", "hr", "nos", "crore", "lakh", "arterial", "roundabout",
    "roundabouts", "intersections", "movementwise", "turnings",
    # method and statistics
    "bootstrap", "resample", "resamples", "resampling", "silhouette", "mann", "whitney",
    "bonferroni", "iglewicz", "hoaglin", "mad", "mape", "chi", "quantile", "quantiles",
    "percentile", "percentiles", "normalised", "normalise", "unweighted", "typology",
    "detrend", "detrended", "harders", "ward", "linkage", "dendrogram", "poisson",
    "heteroscedastic", "leave", "loo", "holdout", "kml's", "logit", "mle", "svm",
    "ransac", "lmeds", "helmert", "rmse", "geh", "exceedance", "cagr", "quantisation",
    "quantised", "reprojection", "benchmark", "benchmarked", "baseline", "midpoint",
    "flatline", "footpoint", "sse", "tc", "tf", "vc", "cl", "med", "pct", "pt", "tw",
    "trl", "trk", "agri", "cls", "uin", "tps", "rars", "dof",
    # British and Commonwealth spellings, which this project uses throughout
    "centre", "centres", "centreline", "behaviour", "coloured", "favour", "favourable",
    "manoeuvre", "manoeuvres", "metre", "metres", "kilometre", "kilometres",
    "millimetres", "sub-metre", "vehicle-kilometres", "optimisation", "optimise",
    "memorise", "minimises", "realise", "stabilisation", "stabilises", "synchronised",
    "programme", "channeliser", "channelisers", "kerbside", "neighbours", "signage",
    "serviceability", "auditable", "switchable", "downloadable", "uncalibrated",
    "underperform", "hardcoded", "rewritten", "held", "held-out", "bottom-centre",
    "east-ish", "west-ish", "no-op", "pre-computed", "pre-monsoon", "multi-axle",
    "multi-junction", "screenlines", "sightlines", "rooftop", "rooftops", "handheld",
    "sortable",
    # place names, people and organisations cited in the reports
    "rajasthan", "varanasi", "hyderabad", "kerala", "kalianpur", "giriraj", "mahima",
    "mataram", "vande", "nagar", "bangladeshi", "lankan", "diwali", "holi", "teej",
    "gangaur", "makar", "sankranti", "gupta", "chandra", "mohan", "datta", "bhuyan",
    "mathur", "troutbeck", "bhuvan", "isro", "dgca", "nhai", "pwd", "govt", "nh", "rd",
    "iia", "iii", "iv", "et",
    # tools, formats and vendors named in the method and setup documents
    "google", "openstreetmap", "osm", "opendesign", "autocad", "acad", "qgis", "postgis",
    "sqlite", "supabase", "iphone", "netconvert", "deepsort", "yolov", "inafoga",
    "iiit", "graphml", "lwpolyline", "orthophoto", "polyline", "polylines",
    "georeference", "georeferenced", "georeferencing", "classify", "classifying",
    "finalising", "docstring", "tracebacks", "screenshots", "checklist", "database",
    "dataset", "datasets", "metadata", "endpoint", "filenames", "lockfiles", "backend",
    "auth", "api", "app", "url", "xml", "csv", "jpeg", "hevc", "bbox", "crs", "gnss",
    "gpu", "gl", "fps", "gb", "kb", "mb", "px", "pixel", "pixels", "dir", "debug",
    "debugging", "download", "numeric", "repo", "xhigh", "vs", "com", "af", "atc",
    "autofocus", "autorickshaw", "airspace", "anytime", "offline", "okay", "laptop",
    "box", "feet", "mini", "coordinate", "coordinates", "eis", "cv", "wb", "rs",
    "kmph", "lmv", "gsdp", "rt", "sw", "nw", "nnw", "pc", "pm", "forma",
    # software and file words that appear in generated docs
    "py", "js", "tsx", "ts", "css", "npm", "uv", "pytest", "numpy", "pandas", "scipy",
    "shapely", "pyproj", "openpyxl", "pyarrow", "tabulate", "matplotlib", "reportlab",
    "opencv", "ultralytics", "torch", "supervision", "pyyaml", "yolo", "bytetrack",
    "homography", "mps", "cuda", "rtx", "macbook", "nextjs", "maplibre", "recharts",
    "vercel", "runbook", "workflows", "config", "src", "geopandas", "osmnx", "networkx",
    "folium", "ezdxf", "sahi", "idd", "gcp", "gcps", "cvat", "roboflow",
}

# Our documents quote the survey's own labels, so the misspellings we are reporting turn
# up in our prose by design. Allowing them by construction from the register keeps that
# from being a hand-maintained list that drifts out of step with it.
ALLOW |= {w.lower() for c in CORRECTIONS
          for w in re.findall(r"[A-Za-z]+", c["as_received"])}

WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")


def _dictionary():
    p = Path("/usr/share/dict/words")
    if not p.exists():
        return None
    return {w.strip().lower() for w in p.read_text(errors="ignore").splitlines()}


# The macOS word list is web2: it carries base forms only, no inflections. Checking words
# against it raw reports `accepting`, `aligned` and `applies` as misspellings - 784 of
# them on the first run, which is a check nobody would read. So a word is known if any
# plausible stem of it is known.
#
# Deliberately generous. A spell gate that cries wolf gets switched off, and the errors
# this is for - Mansarover, Trailor, Corts - are not near-misses of real words; they
# survive every stem rule below.
_SUFFIXES = [
    ("ies", ["y", "ie"]), ("ied", ["y"]), ("ier", ["y"]), ("iest", ["y"]),
    ("ing", ["", "e"]), ("ed", ["", "e"]), ("es", [""]), ("s", [""]),
    ("ly", ["", "le"]), ("ness", [""]), ("ment", [""]), ("er", ["", "e"]),
    ("est", ["", "e"]), ("tion", ["te", "t"]), ("al", ["", "e"]),
]


def known(word, words):
    """Is this a real word, allowing for inflections the base word list omits?"""
    lo = word.lower().strip("'’-")
    if not lo:
        return True
    if lo in ALLOW or lo in words:
        return True
    # hyphenated compounds: known when every part is
    if "-" in lo:
        return all(known(p, words) for p in lo.split("-") if p)
    # contractions and possessives: check the stem, and only for real English endings.
    # Listing "aren't", "you've" and the rest by hand would be fifteen allowlist entries
    # that say nothing about the corridor.
    for tail in ("n't", "'s", "'ve", "'ll", "'re", "'d", "'m",
                 "\u2019t", "\u2019s", "\u2019ve", "\u2019ll", "\u2019re", "\u2019d",
                 "\u2019m"):
        if lo.endswith(tail) and len(lo) > len(tail):
            return known(lo[: -len(tail)], words)
    for suf, stems in _SUFFIXES:
        if lo.endswith(suf) and len(lo) > len(suf) + 1:
            base = lo[: -len(suf)]
            for s in stems:
                if base + s in words or base + s in ALLOW:
                    return True
            # doubled final consonant: stopped -> stop, running -> run
            if len(base) > 2 and base[-1] == base[-2] and base[:-1] in words:
                return True
    return False


def prose_files():
    """What a reviewer actually reads: the generated documents, not the source code."""
    out = []
    for pat in ("*.md",):
        out += sorted((ROOT / "out").glob(pat))
        out += sorted((ROOT / "docs").glob(pat))
    return [p for p in out if p.name != "audit_backlog.md"]


def unknown_words(paths, words):
    """{word: [files]} for every word not in the dictionary and not allowlisted."""
    found = {}
    for p in paths:
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        # strip fenced code, inline code and link targets - none of it is prose
        text = re.sub(r"```.*?```", " ", text, flags=re.S)
        text = re.sub(r"`[^`]*`", " ", text)
        text = re.sub(r"\]\([^)]*\)", " ", text)
        for w in WORD.findall(text):
            if known(w, words):
                continue
            found.setdefault(w.lower().strip("'’-"), set()).add(p.name)
    return {k: sorted(v) for k, v in sorted(found.items())}


def sources():
    """Every label the corrections are supposed to apply to, straight from the source."""
    from src.tmc_parse import CLASS_LABELS
    labels = list(CLASS_LABELS.values())
    arms = [a for arms in JUNCTIONS.values() for a in arms]
    jda = [v[2].strip() for v in JUNCTION_COORDS.values()]
    return labels + arms + jda + [CORRIDOR_NAME]


def _main():
    src = sources()
    blob = " || ".join(src)

    print("=== Spelling register ===")
    print("  Source labels are left exactly as issued. Correction happens at display,")
    print("  and both spellings are published so any figure stays traceable.\n")
    print(f"  {'as issued':<52}{'corrected':<50}{'kind':<10}ok")
    print("  " + "-" * 118)
    for c in CORRECTIONS:
        print(f"  {c['as_received']:<52}{c['corrected']:<50}{c['kind']:<10}"
              f"{'yes' if c['confirmed'] else 'ASK JDA'}")

    # GATE 1 - no phantom corrections. A rule for a string the data does not contain is
    # either a typo in this file or a label that has since changed, and both are silent.
    phantom = [c["as_received"] for c in CORRECTIONS if c["as_received"] not in blob]
    print(f"\n  GATE - corrections that match a real source label: "
          f"**{len(CORRECTIONS) - len(phantom)} of {len(CORRECTIONS)}**")
    if phantom:
        raise SystemExit(f"correction matches nothing in the source data: {phantom}")

    # GATE 2 - idempotent. If applying twice differs from applying once, one rule is
    # rewriting another's output and the register cannot be reasoned about.
    once = [fix(s) for s in src]
    twice = [fix(s) for s in once]
    print(f"  GATE - idempotent (fix(fix(x)) == fix(x)): "
          f"**{'PASS' if once == twice else 'FAIL'}**")
    if once != twice:
        raise SystemExit("corrections are not idempotent; one rule rewrites another")

    # GATE 3 - a CONFIRMED correction is text only. A spelling pass that changes a digit
    # has changed content, not spelling.
    #
    # Scoped to confirmed corrections, and the scoping is the finding rather than a
    # loophole. Run against everything, this gate fails on `Three Wheeler (Auto) Axle
    # Truck, Buses` because restoring the `3` from IRC:SP:41 Table 3.1 adds a digit - and
    # that is precisely why that entry is marked inferred and sits on the reviewer sheet.
    # The gate correctly refuses to let it pass as a spelling fix.
    digits = re.compile(r"\d")
    confirmed_only = [c for c in _ORDERED if c["confirmed"]]

    def fix_confirmed(s):
        for c in confirmed_only:
            s = s.replace(c["as_received"], c["corrected"])
        return s

    moved = [(a, fix_confirmed(a)) for a in src
             if digits.findall(a) != digits.findall(fix_confirmed(a))]
    print(f"  GATE - no CONFIRMED correction alters a digit: "
          f"**{'PASS' if not moved else 'FAIL'}**")
    if moved:
        raise SystemExit(f"a confirmed spelling correction changed a number: {moved}")
    adds_digit = [c["as_received"] for c in CORRECTIONS
                  if not c["confirmed"]
                  and digits.findall(c["as_received"]) != digits.findall(c["corrected"])]
    if adds_digit:
        print(f"  {len(adds_digit)} inferred correction(s) DO change a digit, which is "
              f"why they are inferred:")
        for s in adds_digit:
            print(f"    {s}")

    unc = unconfirmed()
    if unc:
        print(f"\n  {len(unc)} correction(s) change a WORD, not a letter, and are marked")
        print("  inferred rather than applied silently. They are on the reviewer sheet:")
        for c in unc:
            print(f"    {c['as_received']}")
            print(f"      -> {c['corrected']}")

    # --- our own prose ------------------------------------------------------
    words = _dictionary()
    print("\n=== Our own prose ===")
    files = prose_files()
    if words is None:
        print("  No system word list at /usr/share/dict/words; prose check skipped.")
        unknown = {}
    else:
        unknown = unknown_words(files, words)
        print(f"  {len(files)} generated documents checked against "
              f"{len(words):,} dictionary words.")
        if unknown:
            print(f"\n  {len(unknown)} word(s) not in the dictionary and not allowlisted:")
            for w, where in list(unknown.items())[:40]:
                print(f"    {w:<28}{', '.join(where)}")
        print(f"\n  GATE - unrecognised words in the published documents: "
              f"**{len(unknown)}**")

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    (OUT_DATA / "spelling.json").write_text(json.dumps(dict(
        policy=("source labels are left exactly as issued; correction happens at display "
                "and both spellings are published, so every figure stays traceable to a "
                "source cell"),
        corrections=CORRECTIONS,
        n_corrections=len(CORRECTIONS),
        n_unconfirmed=len(unc),
        unconfirmed_note=("these change a word rather than a letter, so they are rendered "
                          "as inferred and appear on the reviewer question sheet"),
        prose_documents_checked=len(files),
        prose_unrecognised=unknown,
    ), indent=1))
    print(f"\nwritten: {OUT_DATA/'spelling.json'}")
    if unknown:
        raise SystemExit(f"unrecognised words in published documents: {sorted(unknown)}")


if __name__ == "__main__":
    _main()
