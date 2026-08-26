"""
sync_web.py — put the generated outputs where the dashboard reads them.

WHY THIS EXISTS. The copy from out/ to web/public/ was done by hand, and twice that
broke the site. The second time took it down completely: export.py RESHAPES
constraint_profile.json for the browser, thinning it to (ch, score, hard) so the page does
not ship the full atlas, and a manual `cp` of the raw file put `chainage_m` back. The
component reads `r.ch`, got undefined, and Recharts died on `e.toFixed is not a function`
with nothing on screen but a client-side exception.

So: export.py owns everything it reshapes, this script copies only what is copied
verbatim, and it refuses to touch the reshaped files at all.

Run:  uv run python src/sync_web.py
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import OUT, OUT_DATA, ROOT

WEB = ROOT / "web" / "public"

# export.py writes these itself, in a different shape from out/data. Copying the raw
# version over them is what broke the dashboard, so this script will not do it.
RESHAPED = {"constraint_profile.json", "junction_candidates.geojson", "atlas.geojson",
            "basemap.geojson", "centreline.geojson", "corridor.json",
            "profiles_series.json", "exhibits_series.json"}

# written by the test run, not the pipeline; export publishes it
SKIP = {"testcount.json"}

DOCS = ["audit_report.md", "capacity_report.md", "method_statement.md",
        "validation_report.md"]


def sync():
    if not OUT_DATA.exists():
        raise SystemExit("out/data does not exist. Run the pipeline first.")
    copied, skipped, missing = [], [], []

    for src in sorted(OUT_DATA.glob("*.json")):
        if src.name in RESHAPED or src.name in SKIP:
            skipped.append(src.name)
            continue
        if (WEB / src.name).exists():
            shutil.copy(src, WEB / src.name)
            copied.append(src.name)

    for src in sorted(OUT_DATA.glob("*.geojson")):
        if src.name in RESHAPED:
            skipped.append(src.name)
            continue
        if (WEB / src.name).exists():
            shutil.copy(src, WEB / src.name)
            copied.append(src.name)

    for name in DOCS + ["data_dictionary.md"]:
        src = (ROOT / "docs" / name) if name == "data_dictionary.md" else (OUT / name)
        if src.exists():
            shutil.copy(src, WEB / name)
            copied.append(name)
        else:
            missing.append(name)

    print(f"copied  : {len(copied)}")
    for n in copied:
        print(f"          {n}")
    print(f"\nnot touched, export.py owns their shape: {len(skipped)}")
    for n in sorted(set(skipped)):
        print(f"          {n}")
    if missing:
        print(f"\nMISSING, generate them first: {', '.join(missing)}")

    # the check that would have caught the outage
    bad = []
    p = WEB / "constraint_profile.json"
    if p.exists():
        rows = json.loads(p.read_text())
        if rows and "ch" not in rows[0]:
            bad.append("constraint_profile.json is in the raw shape; run src/export.py")
    print()
    if bad:
        for b in bad:
            print(f"  BROKEN: {b}")
        raise SystemExit(1)
    print("  web/public is in the shape the dashboard expects")
    return len(copied)


if __name__ == "__main__":
    sync()
