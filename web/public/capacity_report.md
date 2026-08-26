# Capacity and design-year assessment
### the Mansarover Metro – Sanganer Stadium corridor, Jaipur — six surveyed junctions

**Base year** 2026  |  **Design horizon** 20 years to 2046  |  **Survey date** 2026-05-11
**Generated** 2026-08-26 from `out/data/capacity.json`. Every figure in this document is read from the pipeline output at generation time; none is transcribed.

---

## 1. Finding

**12 of 12 surveyed approaches already exceed their carrying capacity at the 2026 peak hour.** The worst, TMC-05 from Mansarover Metro, runs at a volume-to-capacity ratio of **2.29** — Level of Service **F**. This is a present-day measurement, not a projection.

The corridor carries **1.56x** the traffic that the planning-stage assumption implies, which is the gap this assessment exists to quantify.

## 2. Basis of assessment

| Parameter | Value | Source |
|---|---|---|
| Capacity, per direction | 2,700 PCU/hr at 7.5 m, scaled by measured width | IRC:92-2017 Table 6.3 / Indo-HCM Table 5.4, four-lane divided urban |
| Lane width | 3.5 m | IRC:86 urban arterial |
| Shy distance | 1.0 m | kerb and median clearance |
| Peak hour factor | applied | derived per approach from 15-minute bins |
| Growth | 4.0% / 6.0% / 8.0% | low / medium / high scenario |
| PCU | share-dependent, interpolated | IRC:106 |

**Carriageway widths are measured, not assumed.** They come from transects cut across the surveyed CAD alignment, taking the outermost kerb either side of the median. This matters: the alignment is offset from the median, so measuring to the nearest kerb returns the median offset rather than the carriageway.

| Junction | JDA name | Measured width | Transects | Lanes/dir | Capacity |
|---|---|---|---|---|---|
| TMC-01 | B-2 Bypass | 7.2 m | 5 | 2 | 2,592 PCU/hr |
| TMC-02 | Vijay Path | 7.1 m | 31 | 2 | 2,556 PCU/hr |
| TMC-03 | Patel Marg | 7.1 m | 30 | 2 | 2,556 PCU/hr |
| TMC-04 | VT Road | 7.2 m | 27 | 2 | 2,592 PCU/hr |
| TMC-05 | Rajat Path | 7.0 m | 30 | 2 | 2,520 PCU/hr |
| TMC-06 | Bhrigu Path | 7.0 m | 27 | 2 | 2,520 PCU/hr |

## 3. Demand against capacity, by approach

PCU is reported as a band, not a point. The survey's composite vehicle classes (car/taxi/tempo/auto/pickup in one column) cannot be resolved to a single IRC:106 factor, so a point estimate would be false precision. The low figure assumes the bucket behaves as cars; the high figure assumes the heavier mix.

| Junction | Approach | Peak | Capacity | PCU low | PCU high | v/c | LOS |
|---|---|---|---|---|---|---|---|
| TMC-01 | Mansarover Metro | 09:15 | 2,592 | 3,301 | 4,860 | 1.27–1.87 | F |
| TMC-01 | Sanganer Stadium | 08:30 | 2,592 | 3,938 | 5,704 | 1.52–2.20 | F |
| TMC-02 | Mansarover Metro | 09:15 | 2,556 | 3,115 | 4,830 | 1.22–1.89 | F |
| TMC-02 | Sanganer Stadium | 18:15 | 2,556 | 2,971 | 4,496 | 1.16–1.76 | F |
| TMC-03 | Mansarover Metro | 09:00 | 2,556 | 3,744 | 5,256 | 1.46–2.06 | F |
| TMC-03 | Sanganer Stadium | 18:30 | 2,556 | 3,735 | 5,315 | 1.46–2.08 | F |
| TMC-04 | Mansarover Metro | 09:15 | 2,592 | 3,502 | 5,029 | 1.35–1.94 | F |
| TMC-04 | Sanganer Stadium | 17:45 | 2,592 | 3,182 | 5,064 | 1.23–1.95 | F |
| TMC-05 | Mansarover Metro | 09:45 | 2,520 | 5,773 | 8,437 | 2.29–3.35 | F |
| TMC-05 | Sanganer Stadium | 09:15 | 2,520 | 4,070 | 6,183 | 1.62–2.45 | F |
| TMC-06 | Mansarover Metro | 09:15 | 2,520 | 3,788 | 5,436 | 1.50–2.16 | F |
| TMC-06 | Sanganer Stadium | 09:30 | 2,520 | 3,537 | 5,649 | 1.40–2.24 | F |

## 4. The published scheme does not resolve this

The scheme under construction — signal-free corridor, 7 U-turn bays — replaces signalised turning with U-turn bays. Tested by gap acceptance against the measured opposing flow, **12 of 12 approaches fail** under conservative critical-gap assumptions and **12 still fail** under optimistic ones.

On **12** approaches the opposing flow is heavy enough that gap acceptance degenerates entirely: there is no usable gap, and no capacity figure is quoted because none would be meaningful.

The mechanism is that removing a signalised right turn does not remove the demand — it converts it into a U-turn. Across the corridor that forces **14,908 additional U-turning vehicles per hour** onto bays sized for far less.

## 5. Grade separation returns the corridor to service

Removing the through movement from the at-grade surface — the elevated option — leaves only turning traffic at the junction. Applying the measured through percentage to each approach returns **all 12 approaches** to acceptable operation on opening. Section 6 tests how long that holds.

| Junction | Approach | Through % | Peak PCU | Residual | v/c before | v/c after | LOS after |
|---|---|---|---|---|---|---|---|
| TMC-01 | Mansarover Metro | 57.2% | 3,317 | 1,420 | 1.28 | 0.55 | C |
| TMC-01 | Sanganer Stadium | 57.2% | 3,963 | 1,696 | 1.53 | 0.65 | C |
| TMC-02 | Mansarover Metro | 68.3% | 3,126 | 991 | 1.22 | 0.39 | B |
| TMC-02 | Sanganer Stadium | 68.3% | 2,990 | 948 | 1.17 | 0.37 | B |
| TMC-03 | Mansarover Metro | 77.4% | 3,750 | 847 | 1.47 | 0.33 | B |
| TMC-03 | Sanganer Stadium | 77.4% | 3,757 | 849 | 1.47 | 0.33 | B |
| TMC-04 | Mansarover Metro | 67.9% | 3,510 | 1,127 | 1.35 | 0.43 | B |
| TMC-04 | Sanganer Stadium | 67.9% | 3,194 | 1,025 | 1.23 | 0.40 | B |
| TMC-05 | Mansarover Metro | 78.7% | 5,777 | 1,231 | 2.29 | 0.49 | C |
| TMC-05 | Sanganer Stadium | 78.7% | 4,086 | 870 | 1.62 | 0.35 | B |
| TMC-06 | Mansarover Metro | 72.9% | 3,797 | 1,029 | 1.51 | 0.41 | B |
| TMC-06 | Sanganer Stadium | 72.9% | 3,566 | 966 | 1.42 | 0.38 | B |

## 6. How long does that relief last?

Opening-year relief is not the same as a design life, and the difference is the whole point of a 20-year horizon. Applying compound growth to the residual turning demand gives the year each approach returns to capacity.

| Junction | Approach | v/c on opening | 4% | 6% | 8% |
|---|---|---|---|---|---|
| TMC-01 | Mansarover Metro | 0.55 | 2042 | 2037 | 2034 |
| TMC-01 | Sanganer Stadium | 0.65 | 2037 | 2034 | 2032 |
| TMC-02 | Mansarover Metro | 0.39 | 2051 | 2043 | 2039 |
| TMC-02 | Sanganer Stadium | 0.37 | 2052 | 2044 | 2039 |
| TMC-03 | Mansarover Metro | 0.33 | 2055 | 2046 | 2041 |
| TMC-03 | Sanganer Stadium | 0.33 | 2055 | 2046 | 2041 |
| TMC-04 | Mansarover Metro | 0.43 | 2048 | 2041 | 2037 |
| TMC-04 | Sanganer Stadium | 0.40 | 2050 | 2042 | 2038 |
| TMC-05 | Mansarover Metro | 0.49 | 2045 | 2039 | 2036 |
| TMC-05 | Sanganer Stadium | 0.35 | 2053 | 2045 | 2040 |
| TMC-06 | Mansarover Metro | 0.41 | 2049 | 2042 | 2038 |
| TMC-06 | Sanganer Stadium | 0.38 | 2051 | 2043 | 2039 |

**At the medium 6% growth rate, 0 of 12 approaches still hold at 2046.** The first returns to capacity in **2034** — 8 years after the base year — and the last in 2046.

This does not withdraw the recommendation; grade separation is still the only measure tested here that returns the corridor to service at all. It qualifies it. A structure sized on opening-year relief alone would be delivering a corridor that is over capacity again well inside its own design horizon, so the scheme needs a demand-side measure alongside it — public transport priority, parking control, or access management — not a structure on its own.

The growth rates are applied to a counted flow that is already capacity-constrained. A saturated approach cannot show suppressed or diverted trips, so these dates are the optimistic end: real demand recovery would bring them forward, not push them back.

## 7. Queue, delay, and what the congestion costs

A volume-to-capacity ratio is not something anyone can act on. Deterministic oversaturation queueing converts it into quantities that are: how many vehicles are queued, how far back they reach, and how long a trip takes. That model needs no signal timings, which matters because the survey records none anywhere in the twelve workbooks — an HCM control-delay model would require inventing its own inputs.

| Junction | Approach | Queue veh | Queue m | Storage m | Delay min | Blocks back |
|---|---|---|---|---|---|---|
| TMC-01 | Mansarover Metro | 831 | 860 | 1,884 | 6.6 | no |
| TMC-01 | Sanganer Stadium | 1,571 | 1,626 | n/a | 10.4 | leaves study area |
| TMC-02 | Mansarover Metro | 673 | 393 | 393 | 5.5 | TMC-03 at 37 min |
| TMC-02 | Sanganer Stadium | 513 | 488 | 1,884 | 4.4 | no |
| TMC-03 | Mansarover Metro | 1,495 | 1,333 | 2,332 | 9.6 | no |
| TMC-03 | Sanganer Stadium | 1,504 | 393 | 393 | 9.6 | TMC-02 at 18 min |
| TMC-04 | Mansarover Metro | 1,127 | 190 | 190 | 7.8 | TMC-05 at 11 min |
| TMC-04 | Sanganer Stadium | 739 | 659 | 2,332 | 5.7 | no |
| TMC-05 | Mansarover Metro | 4,119 | 539 | 539 | 16.9 | TMC-06 at 8 min |
| TMC-05 | Sanganer Stadium | 1,981 | 190 | 190 | 11.5 | TMC-04 at 6 min |
| TMC-06 | Mansarover Metro | 1,601 | 1,584 | n/a | 10.1 | leaves study area |
| TMC-06 | Sanganer Stadium | 1,311 | 539 | 539 | 8.8 | TMC-05 at 25 min |

**6 of 12 queues reach the junction behind them inside the peak hour.** No queue is reported longer than the road can physically hold: past the point where a queue blocks the junction upstream, the approaches stop being independent and the deterministic model has left the regime it is valid in. A metre figure beyond that would be a fiction dressed as a measurement.

Over the 5.34 km corridor a through trip takes **8.0 minutes** at free flow and **64.5 minutes** at the peak in the southbound direction — an effective **5.0 km/h**. Grade-separated through traffic does not enter the junctions and so returns to the free-flow figure, a saving of **56.5 minutes per trip**. The peak figure is a floor: it sums queues as though independent, and several are not.

Approaches are over capacity for a mean of **7.0 hours a day**, counted from the survey's own 96 intervals rather than assumed from a nominal peak period. That accumulates **28,262 vehicle-hours** of delay daily.

| Case | Annual cost of delay |
|---|---|
| Do nothing | Rs 135–320 crore |
| Grade separated | Rs 35–83 crore |
| **Annual benefit** | **Rs 100–237 crore** |

**These rupee figures are indicative and deliberately banded.** The delay is measured; the value of time is a policy input and not ours to set. Authorities appraise against their own approved rates, so quoting a single figure derived from a rate the authority has not adopted would present a policy choice as an engineering result. The method is the deliverable; substituting JDA's rates changes one table in `src/economics.py`.

Excluded entirely: vehicle operating cost, fuel, emissions, accident cost, reliability. Each is real and each would raise the figure, so what is quoted is a lower bound. Queue carry-over between consecutive oversaturated hours is also not modelled, for the same reason the queue lengths are capped, and that too makes this conservative.

## 8. Do these conclusions survive their own assumptions?

Both were re-run across **144 combinations** of PCU uplift, lane capacity, effective lane count, critical gap and growth rate.

- **U-turn scheme fails:** holds. Robust across the grid.
- **Grade separation relieves on opening:** all 12 approaches pass in **21 of 24** combinations.

No single assumption dominates the outcome — the swing across the grid is negligible, so naming a most-influential parameter would overstate what the analysis shows.

## 9. Limitations

- The survey covers **one day**, not the two the workbooks present. Day two is derived from day one; see the integrity audit report.
- Composite vehicle classes prevent a point PCU estimate. Bands are reported throughout and no band is collapsed to its midpoint.
- Critical gap values are from literature, not measured at this corridor. They are **not** conservative: an earlier version of this report said so, and it was withdrawn. They sit mid-pack against the four-lane median-opening studies that match this geometry, so measurement could move the finding either way. The same test is published across twelve bases so the reader can pick one.
- E-rickshaw has no IRC PCU factor and no column in the survey. It is excluded rather than assumed, and its absence understates demand by an unknown amount.
- Three of the six junction positions are inferred from the scheme description and are labelled as such. The survey location schedule would confirm them.
- **TMC-01 width is measured from 5 transects against a typical 30.** The surveyed drawing runs 6.52 km and TMC-01 sits 1 m from its end, so a width band around that junction falls largely outside the drawing. Its width figure rests on fewer measurements than the others and should be treated as the least certain of the six.

**Corridor order.** Chainage along the surveyed alignment places the junctions in the order TMC-06, TMC-05, TMC-04, TMC-03, TMC-02, TMC-01. For the 0 junctions matched by name this is independent geometric evidence, and the full sequence reproduces the order the scheme itself lists. For the inferred three it only restates the assumed position and confirms nothing.

This resolves a question the flow data could not. Deriving the order from corridor continuity - matching each junction's southbound outflow to the next junction's inflow - separated the leading candidates by too small a margin to call, and was reported as inconclusive. The surveyed geometry answers it directly.

## The critical gap, across every published basis

The critical gap is the single most attackable input in this report: it was chosen from the literature, not measured on this corridor. Rather than defend one value, the servability test is re-run on every basis reachable.

| Basis | t_c (s) | t_f (s) | Unservable | Geometric match |
|---|---:|---:|---:|---|
| Kerala median openings, traditional/Raff | 2.05 | 1.23 | 11 of 12 | median openings, but the paper states carriageway width only and never lane count - reading it as four-lane was our inference, not theirs |
| Kerala median openings, merging behaviour | 2.80 | 1.70 | 12 of 12 | median openings, lane count not stated in the paper |
| Khan 2022 thesis, four-lane median openings, modified Raff / binary logit | 3.36 | 2.04 | 12 of 12 | closest of all: four-lane divided median openings, and the only source with a MEASURED four-lane follow-up time (2.04 s, two-wheelers, Table 8.2) |
| Mohan & Chandra 2020, RT from minor, 4-lane divided | 3.50 | 2.10 | 12 of 12 | four-lane divided major, but a junction movement not a median opening |
| Datta & Bhuyan 2014, four-lane median openings, prob. equilibrium | 3.79 | 2.17 | 12 of 12 | closest by road type: median openings explicitly on four-lane divided |
| ours, optimistic | 3.87 | 2.00 | 12 of 12 | none stated |
| Khan 2022 thesis, four-lane median openings, occupancy time / SVM | 4.26 | 2.04 | 12 of 12 | closest of all: four-lane divided median openings, authors' preferred methods |
| Gupta et al. 2018, four-lane median openings, Varanasi | 4.45 | 2.50 | 12 of 12 | closest overall: four-lane divided median openings, carriageway 7.03-8.90 m per direction against this corridor's ~7 m |
| CSIR-CRRI NH-8 design recommendation | 4.50 | 2.70 | 12 of 12 | the only Indian DESIGN value for a median opening, but inter-urban NH not urban |
| ours, conservative | 5.03 | 3.00 | 12 of 12 | none stated |
| Datta & Bhuyan 2014, four-lane median openings, INAFOGA | 5.09 | 3.00 | 12 of 12 | closest by road type: median openings explicitly on four-lane divided |
| IRC:SP:41 Table III-2, RT from major, 4-lane, 48 kmph | 5.50 | 3.00 | 12 of 12 | four-lane, but HCM 1985 in metric with no Indian calibration |

The finding holds in **12 of 12** bases. Where it does not, that basis uses the traditional Raff method, which the authors who published it recommend against for mixed traffic. It is reported rather than omitted.

**The U-turn is modelled as a merge into the opposing stream, not a crossing of it.** A merge needs a smaller gap than a crossing does, so this choice sets the whole scale and is the load-bearing assumption behind every number above.

**Where ours sits.** our gap sits mid-pack in the Indian field evidence - above the Kerala openings, below Gupta, CSIR-CRRI and IRC:SP:41 - so the finding rests on neither the generous nor the punitive end

---

Prepared from the JDA classified turning-movement survey dated 2026-05-11. Method, standards and acceptance gates are set out in the accompanying method statement.