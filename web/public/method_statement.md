# Method statement
### the Mansarover Metro – Sanganer Stadium corridor corridor assessment, Jaipur

**Generated** 2026-08-26. Figures are read from pipeline output at generation time.

---

## 1. Purpose and scope

To establish, from the authority's own classified turning-movement survey, what the the Mansarover Metro – Sanganer Stadium corridor corridor carries at present, whether the published scheme (signal-free corridor, 7 U-turn bays) resolves the demand, and what does.

Scope is the **6 surveyed junctions** over **4.71 km** of alignment. Each is a four-arm junction with twelve movements. No U-turn is counted anywhere in the source survey.

## 2. Standards applied

| Standard | Applied to |
|---|---|
| Indo-HCM 2017 | capacity, level of service, gap acceptance |
| IRC:106 | share-dependent passenger car unit factors |
| IRC:SP:41 | at-grade intersection geometry |
| IRC:92 | grade-separated intersection assessment |
| IRC:SP:19 | survey and investigation procedure |
| IRC:86 | urban arterial cross-section |
| EPSG:32643 | all spatial work, UTM zone 43N, metres |

**India drives on the left.** The right turn crosses opposing traffic and is the capacity-limiting movement throughout. This was verified against the direction headings of every movement sheet in the source workbooks rather than assumed.

## 3. Method, stage by stage

Each stage carries a numeric acceptance gate. A failed gate is reported, not worked around.

| Stage | Method | Acceptance gate |
|---|---|---|
| Survey ingest | Parse all workbooks to tidy 15-minute bins. Every stored total is recomputed from components and disagreements are registered, never silently corrected. | zero silently absorbed discrepancies |
| Integrity audit | Seven independent checks: arithmetic, conservation, approach reconciliation, PCU back-solve, peak-hour rederivation, timing against IRC:SP:19, inter-day independence. | each check reports pass/fail |
| PCU correction | IRC:106 factors interpolated on each class's share of the stream. Composite classes report a band, not a point. | no composite bucket collapsed to a point estimate |
| Georeference | Survey CAD parsed and projected to EPSG:32643. | RMSE < 3 m |
| Constraint atlas | All constraint layers extracted from the CAD; pier siting profiled at 25 m stations against an 8 m footprint. | hard constraints flagged, not scored away |
| Capacity | Widths measured on transects across the alignment; demand from corrected PCU at the derived peak. | measured widths, not assumed |
| Scheme test | Gap acceptance against measured opposing flow, both optimistic and conservative critical gaps. | v/c above 3.0 reported as 'no viable gaps', not as a number |
| Design life | Compound growth applied to the residual turning demand after grade separation, to find the year each approach returns to capacity. | relief reported for the horizon, not the opening year |
| Queue and delay | Deterministic oversaturation queueing. No signal model is used because the survey records no signal timings. Queue converted to a length by vehicle footprint against the measured carriageway width. | no queue reported longer than the road can physically hold |
| Economics | Delay valued at an occupancy-weighted value of time, over the oversaturated hours counted from the survey's own intervals. | every figure banded; value of time declared a policy input |
| Annotation (pending footage) | Frames selected by temporal stratification and de-duplication, labelled in CVAT, Roboflow or Label Studio. | unknown labels dropped, never guessed |
| Detection stage 2 (pending footage) | Fine-tune on frames from the study camera, starting from the IDD weights at a tenth of the learning rate. | train/val split by contiguous time block, never at random |
| Sensitivity | Every conclusion re-run across the full assumption grid. | 144 combinations |
| Detection (pending footage) | YOLO fine-tuned on IDD then on annotated frames from the study camera. Sliced inference over overlapping tiles for small two-wheelers; ByteTrack association; homography to ground plane by footpoint. | mAP@0.5 >= 0.80 overall, >= 0.70 per class |
| Count validation (pending footage) | Automated counts against manual counts from the same footage. | MAPE < 10% total, < 15% per major class |

## 4. Data provenance

| Input | Source | Status |
|---|---|---|
| Classified turning-movement survey | JDA, via appointed contractor | received, audited |
| Corridor CAD drawing | JDA | received, parsed |
| Junction positions | three matched by name to the scheme, three inferred | labelled as such throughout |
| Study footage | to be recorded at the study junction | outstanding |
| Critical gap | literature, Raff-derived | to be measured from footage |

**Client source data is not redistributed.** The survey workbooks and the CAD drawing are the authority's to share. Everything derived from them is published in open formats and is downloadable from the dashboard.

## 5. Quality assurance

- No stored total is trusted. Every one is recomputed and disagreements are registered with file, sheet and row.
- No figure appears in a report that is not read from pipeline output at generation time. Reports cannot drift from the analysis.
- Every module is independently runnable and prints its own verification metric. Silent success is not treated as success.
- Conclusions are re-run across the full assumption grid before publication.
- Findings that did not survive checking were withdrawn rather than softened. The audit report records them.

## 6. Where this stops being reliable

- **One day of data.** The workbooks present two; the second is derived from the first. Weekday-to-weekend variation is unmeasured.
- **Survey timing.** The count was taken in May, outside the IRC:SP:19 recommended window, on a day the project's own methodology excludes.
- **Composite classes.** Auto-rickshaw is pooled with cars and pickups in the source. This cannot be undone by analysis; it needs re-survey or video.
- **No e-rickshaw column.** Excluded rather than assumed. Demand is understated by an unknown amount.
- **Critical gap is not local.** Literature values are used and flagged. The direction of the bias makes the U-turn conclusion conservative.
- **Detection accuracy is unverified** until footage exists. The pipeline and its gates are built and tested; the accuracy figure is not yet measurable.

## 7. Deliverables

| Ref | Deliverable | Format |
|---|---|---|
| D1 | Integrity audit report | Markdown |
| D2 | Corrected dataset | Parquet + JSON |
| D3 | Contractor query letter | Markdown |
| D4 | Corridor Constraint Atlas | A3 PDF |
| D5 | Median opening schedule | GeoJSON |
| D6 | Capacity and design-year assessment | Markdown |
| D7 | Interactive dashboard | Web link |
| D8 | Count validation report | Markdown, pro forma until footage |
| D9 | Method statement | this document |

---

All spatial data is EPSG:32643. All analysis code is public and every derived dataset is downloadable from the dashboard.