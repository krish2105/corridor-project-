# Audit backlog

From the completeness audit (54 findings raised, 28 verified before the run was stopped).
**The verified batch came back 4-real out of 28, so treat every unverified item below as a
lead, not a fact. Reproduce it before fixing it.** Two findings were already refuted:
`useGridCursor.ts` is committed, and the README test count already matched — those
auditors read a working tree from before the last commit.

Status as of commit `9ded4e6`: 332 tests pass, dashboard builds clean, deployed.

---

## Done (commit 9ded4e6)

| # | Was wrong | Fixed by |
|---|---|---|
| 1 | `scheme_test.py:99` asserted "our gaps are the generous end" — contradicting its own withdrawal 30 lines below | rewrote to the correction; a mixed-traffic weighted mean sits below a single-class car value by arithmetic, not caution |
| 2 | Same retracted claim in 4 sites across `reports.py` / `service_docs.py`, shipping into client documents | rewrote all four |
| 3 | Same retracted claim live on the dashboard, `Standards.tsx:135` | replaced with the withdrawal |
| 4 | A test *pinned* the retracted framing | rewrote it; added a regression guard that fails if the framing reappears outside a withdrawal — it caught two of the sites above on first run |
| 5 | `sensitivity.py` rebuilt demand from a hardcoded 1200 PCU/lane, commented as matching `delay.py`. It didn't — `delay.py` uses ~2,592 PCU/dir from `capacity.json`, and 1200 is the figure `capacity.py` documents as retired | `delay.py` now publishes its divisor; `sensitivity.py` reads it; both axes re-centred on IRC:92-2017. Centre reproduces the published 6-of-10 exactly |
| 6 | The test guarding that could never fail — at 1200 the rescale factor is identically 1 by construction | anchored to published capacity; added axis-brackets and no-hardcoded-baseline tests |
| 7 | `tmc_parse.py` printed 24 movements/junction against a spec requiring 12 — divisor omitted the second survey day, nothing compared it to 12 | counts arm×turn pairs per junction-day; states pass/fail; passes at 12 |
| 8 | `sensitivity.py` claimed "144 combinations, each conclusion evaluated across all" directly above a line saying one assumption bore on conclusion 1 | states each conclusion's real grid: 2 / 24 / 27. `growth_pct` kept — the scenario tool does sweep it |
| 9 | CI dependency audit suffixed `\|\| true` — could print vulnerabilities and pass | removed |
| 10 | `conftest` wrote `testcount.json` on *every* pytest run, so any filtered run recorded its handful as the project count. CI runs a filtered step | hook bails on filtered runs; regression test added |
| 11 | CLAUDE.md: "Bullock Corts — zero counts in this survey". There are 142 (TMC-03/04/05) | corrected |
| 12 | 2W share published as 47% (`CLAUDE.md`, `delay.py`) and 49% (`scheme_test.py`). Parsed value is 49.11% | unified to 49% |
| 13 | Dashboard: "the argument is about five pinch points" above data giving 15 (182 stations, 167 clear) | derived from data, not asserted |
| 14 | `.src` used on 4 provenance blocks, styled by nothing — source notes read as body prose | given a rule |
| 15 | Scenario tool's gap control offered "optimistic"/"conservative" without saying what seconds they meant | reads "optimistic · 3.87s", wired from the published spread |

---

## To build / fix next — ordered by consequence

### ~~Tier 1 — gates that report something other than what they check~~ — DONE (commit below)
These are the project's own acceptance criteria. A gate that passes without checking is
worse than no gate, because it reads as verified.

- ~~**`pipeline.py`** prints "all stages passed their gates" after skipping the Counts MAPE
  gate.~~ FIXED. `summarise()` extracted from `__main__` so it is testable; names every
  gate that did not run and refuses the word "all"; forbids quoting an accuracy figure
  when validate was skipped.
- ~~**`delay.py`** — uncapped queue lengths published.~~ FIXED, and it was real:
  `spillback()` computed the cap and the caller discarded it, publishing a 3,823 m queue
  on a 539 m link. 6 of 10 approaches breached. Now publishes the capped `queue_m`, plus
  `queue_unconstrained_m` and `queue_model_in_regime` so the magnitude is not hidden.
- ~~**`audit.py`** — PCU-evidence gate checked 12 day-totals, not 96 intervals.~~ FIXED.
  Now applies the static factors to every class count on all **25,344** 15-minute rows
  across every sheet of all 12 workbooks and compares against each row's own stored PCU.
  0 failures — the static-PCU claim is true and is now proven to the standard the gate
  asks for.
- ~~**`audit.py`** — peak-hour gate never read the rolling-hour sheets.~~ FIXED, and it
  was real: `ROW_HOURS` was declared in `tmc_parse.py` and read by no module. Now compares
  against the workbooks' own 93 rolling-hour windows: **12 of 12 agree to within 1
  vehicle.**
- ~~**`tmc_parse.py`** — "0 silently absorbed" hardcoded; unreadable totals skipped.~~
  FIXED, both real. An unreadable stored total fell through with no register row; there
  are **2** such cells (`Total Slow`). Register 223 → 225, and the gate now reports a
  computed count instead of a literal.

### ~~Tier 2 — published claims that may not match the data~~ — DONE (commit 4816b22)
- ~~**`pitch_template.html`** — "a ₹50-crore programme", unbanded and unsourced.~~ FIXED,
  real. Our own invention, in a deliverable arguing that unsourced figures should not be
  trusted. Replaced with the banded ₹135–320 crore/yr we actually hold; withdrawal stated
  in the text. A test now rejects any rupee figure that is neither banded nor cited.
- ~~**`reports.py`** — gate table omitted the two-wheeler critical gap.~~ FIXED, real. 2W
  is 49% of the stream so the weighted gap moves with it, and 2.8 → 3.5 s was the change.
  The omitted row was the consequential one.
- ~~**`page.tsx`** — the grid maximum labelled as the central-assumption value.~~ FIXED,
  real, and it ran in our favour: 8 approaches quoted where the central cell gives 6.
  `queue_spillback_central` now published, asserting the packing axis centre really is
  `delay.py`'s `JAM_PACKING`; reproduces delay.py at 6 of 10. Both figures now shown.
- ~~**`service_docs.py`** — `PIPELINE_ORDER` gave a clean run four 404 download links.~~
  FIXED, real. The dependency is genuinely circular — `reports.py` loads `corridor.json`
  which only `export` writes, and `export` publishes the markdown `reports` produces — so
  both export passes are now named. Eight missing modules added. A pre-existing test
  asserted the broken half. `export` now warns instead of skipping in silence. All four
  links verified 200 live.

### ~~Tier 3 — coverage the deliverable claims but doesn't have~~ — DONE
- ~~46 of ~330 tests skip on a clean checkout.~~ FIXED — it was 56. No synthetic fixture
  needed: 11 of 14 `out/data` files are already committed under `web/public` for the
  dashboard build, so the loaders fall back there. Clean checkout went 290 pass / 53 skip
  / 7 fail → **341 pass / 18 skip / 0 fail**. New `test_web_public_matches_out_data` guard
  stops the two copies drifting.
- ~~`standards.py` and `profiles.py` at 0% coverage.~~ FIXED — 35% and 44%, testing the
  warrants and the cumulative-queue band rather than chasing the number. `audit.py` (7%)
  and `export.py` (0%) remain: both are IO-shaped over client workbooks and would need a
  synthetic workbook fixture to exercise meaningfully. **Still open.**
- ~~The 12-basis gap spread has no test.~~ FIXED — extracted as `gap_evidence_spread()`.
  Tests assert it is monotonic in the critical gap, covers every declared basis with
  provenance, and that our own two values are neither the lowest nor highest basis (else
  publishing the spread would be decoration).
- ~~Corridor ordering only exercised in the degenerate two-junction case.~~ FIXED — a
  four-junction chain with unambiguous continuity now exercises it, plus assertions that
  the published order is still reported as inconclusive (1.2% margin) and that chainage
  places all six junctions with the three inferred ones still labelled.
- ~~`testcount.json` written at collection, so a red suite still published a count.~~
  FIXED — moved to `pytest_sessionfinish` behind `exitstatus == 0`, and published to
  `web/public` so a clean checkout renders the same README.
- ~~`corridor.json` cast to `Corridor` without validation.~~ FIXED — `load()` checks the
  twelve required sections and fails the build naming what is missing and how to fix it,
  instead of surfacing as "Cannot read properties of undefined". Verified by removing a
  section.
- ~~Coverage can't be measured in CI.~~ FIXED — `pytest-cov` declared and carved out of
  the declared-but-unused check, since a pytest plugin is loaded by entry point and
  imported by nothing. Overall coverage now measurable: **34%**.

### Tier 4 — dashboard polish
- **`GapEvidence` and `Rail` animate under `prefers-reduced-motion`** — the CSS escape
  hatch can't reach Motion. Gate them behind `useReducedMotion()`.
- **LOS heatmap** — check white-on-light contrast at LOS B in dark theme, and whether the
  severity ramp inverts at F.
- **`Standards.tsx`** colours the aggregate gap margin green while the per-row renderer
  colours the same quantity red.
- **`safety.caveat`** is published but never reaches the reader.
- **Scenario tool lane-count buttons** are 35px under `(pointer: coarse)`.
- **Indo-HCM corroboration fields** (`indo_hcm_no_uturn_chapter`, `csir_crri_design_gap_s`,
  `follow_up_measured_s`) are published but absent from `types.ts` and every component.
- **The static HTML report and D6 carry none of the 12-basis spread** the Next.js
  dashboard publishes. Same finding, two surfaces.
- **Data dictionary** still lists 22 described-but-absent fields (incl. `gap_evidence_spread`)
  because the checker only walks top-level keys and these are nested. Make it recurse.

### Tier 5 — housekeeping
- **CLAUDE.md Layout** omits six modules that exist and names a `data/gcps/` that doesn't.
- **`phase6_field_plan.md`** is hand-written, referenced by nothing, published nowhere, and
  asks the enumerator to photograph two GCP types `homography.py` can't resolve.
- **`pytest-cov`** — lead claims it's declared but never imported, failing the stack-claims
  gate. **Verify this one carefully**: the auditor may have added it themselves mid-run.

---

## Blocked on you — nothing to build until these land

- **TMC-04 footage**, 7 GCP stills, ~500 annotated frames, IDD dataset download → unblocks
  the whole CV chain and turns D8 from pro forma into a measured validation.
- **Survey location schedule** → 3 of 6 junction positions are currently inferred and
  labelled as such on every map and table.
- **Contractor query letter** (`out/contractor_queries.md`, gitignored) — needs a recipient
  and four fields filled, then you send it. It's currently listed as "Delivered" in the
  register, which it isn't.
- **The empanelled principal** — the implementation plan cross-references someone "named in
  the commercial pack"; the commercial pack names nobody.
- **The BRTS demolition finding** (April 2025, this corridor) — researched, not built in.
  Whether it belongs in the deliverable is your call.
