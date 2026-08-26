# Count validation report
### the Mansarover Metro – Sanganer Stadium corridor corridor — automated counts against manual counts

**Generated** 2026-08-26. Structure and gates are final; measurements are outstanding.

**STATUS: PRO FORMA.** No footage has been processed, so no accuracy has been measured. The gates below are already fixed in code and are published here ahead of the measurement; they are not adjustable once a result exists.

Throughout this document **— means not yet measured**. No unmeasured quantity is shown as a number, because a zero in an accuracy table reads as a measurement.

---

## 1. What is being validated

Whether counts produced by detection and tracking can be trusted in place of a human counting the same footage. This is the only claim in the project that cannot be checked from the authority's data alone, so it is checked against a count made by hand.

The manual count is made from **the same footage**, not a separate roadside count. A roadside count would differ for reasons that have nothing to do with detection accuracy - different observer, different moment, different weather - and would confound the thing being measured with everything else.

## 2. Acceptance gates

Fixed in `src/validate.py` before any footage existed. Two thresholds per metric: a **target** the method should reach, and a **minimum** below which the result is not usable. A result between the two is reported as marginal, never rounded up to a pass.

| Metric | Target | Minimum | Direction |
|---|---|---|---|
| Total count MAPE | 5% | 10% | lower is better |
| Major class MAPE (AUTO_TRK_BUS, CAR_BUCKET, TWO_W) | 10% | 15% | lower is better |
| Minor class MAPE | 10% | 20% | lower is better |
| Movement assignment accuracy | 95% | 90% | higher is better |

Minor classes carry a looser minimum because their counts are small: a handful of buses in a 15-minute interval makes percentage error volatile for reasons that are arithmetic rather than a failure of detection.

## 3. Total accuracy

| Manual | Automated | MAPE | Intervals | Verdict |
|---|---|---|---|---|
| — | — | — | — | — |

## 4. Accuracy by vehicle class

| Class | Band | Manual | Automated | MAPE | Verdict |
|---|---|---|---|---|---|
| TWO_W | major | — | — | — | — |
| CAR_BUCKET | major | — | — | — | — |
| AUTO | minor | — | — | — | — |
| AUTO_TRK_BUS | major | — | — | — | — |
| TRL_MAV | minor | — | — | — | — |
| CYCLE | minor | — | — | — | — |
| ANIMAL | minor | — | — | — | — |
| E_RIK | minor | — | — | — | — |
| CYCLE_RIK | minor | — | — | — | — |

## 5. Movement assignment

A vehicle counted correctly but assigned to the wrong turning movement corrupts the matrix while leaving the total intact, so it is measured separately from count accuracy rather than folded into it.

| Metric | Result | Gate | Verdict |
|---|---|---|---|
| Tracks resolved to a movement | — | 90% minimum | — |

## 6. What the detector could not classify

The unmapped-detection rate is reported as a number rather than assumed to be zero. It is the direct measure of the gap this project has flagged from the start: the survey pools auto-rickshaw with cars, and has no e-rickshaw column at all. If a material share of detections cannot be classified, the counts inherit that limitation and the report says so.

| Diagnostic | Result |
|---|---|
| Detections not mapped to an IRC class | — |
| Tracks discarded before movement assignment | — |

## 7. Critical gap, measured against literature

The U-turn conclusion currently rests on critical-gap values from literature, not from this corridor. Footage replaces them with measured values from at least 25 head-of-queue drivers, estimated two ways - Raff and Troutbeck maximum likelihood - so the two can be compared rather than one trusted alone.

| Quantity | Literature (opt / cons) | Measured | Effect |
|---|---|---|---|
| Critical gap, two-wheeler | 3.5 / 4.4 s | — | 49% of the stream - dominates the weighted gap |
| Critical gap, car bucket | 4.2 / 5.6 s | — | sets U-turn bay capacity |
| Follow-up headway | 2.0 / 3.0 s | — | sets saturation discharge |
| Raff vs MLE disagreement | — | — | large disagreement withdraws the estimate |

The literature values are not measured at this corridor, and they are not conservative either — an earlier version of this report claimed they were, on the grounds that they were Raff-derived and so biased high. That was withdrawn. They are composition-weighted from field studies and sit mid-pack against the four-lane median-opening evidence, so measurement could move the finding in either direction. The finding as it stands is that 12 of 12 approaches fail; measurement is capable of changing that number and this report will state the revised figure whichever way it moves.

## 8. Verdict

No verdict. Nothing has been measured, and an accuracy figure will not appear in this document until footage has been processed through the pipeline.

## 9. Limitations that remain regardless of the result

- Validation covers the junction that was filmed. It does not transfer to the other five without either footage or a stated assumption.
- Manual counts are themselves fallible. Two independent passes over the same interval bound that error; a single pass does not.
- E-rickshaw accuracy depends entirely on self-annotated frames, since no public dataset carries the class. If those frames are not annotated, e-rickshaw is reported as absent rather than as zero.
- Night-time and adverse-weather accuracy is not established by daytime footage and is not claimed.

---

Method, standards and the full gate list are set out in the accompanying method statement. Gates are defined in `src/validate.py`.