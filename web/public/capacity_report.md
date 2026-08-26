# Capacity and design-year assessment
### New Sanganer Road, Jaipur — six surveyed junctions

**Base year** 2026  |  **Design horizon** 20 years to 2046  |  **Survey date** 2026-05-11
**Generated** 2026-08-26 from `out/data/capacity.json`. Every figure in this document is read from the pipeline output at generation time; none is transcribed.

---

## 1. Finding

**0 of 12 surveyed approaches already exceed their carrying capacity at the 2026 peak hour.** The worst, TMC-05 from Mansarover Metro, runs at a volume-to-capacity ratio of **0.88** — Level of Service **E**. This is a present-day measurement, not a projection.

The corridor carries **0.70x** the traffic that the planning-stage assumption implies, which is the gap this assessment exists to quantify.

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
| TMC-01 | B-2 Bypass | 15.6 m | 7 | 4 | 5,616 PCU/hr |
| TMC-02 | Vijay Path | 12.5 m | 9 | 3 | 4,500 PCU/hr |
| TMC-03 | Patel Marg | 13.0 m | 4 | 3 | 4,680 PCU/hr |
| TMC-04 | VT Road | 17.6 m | 13 | 5 | 6,336 PCU/hr |
| TMC-05 | Rajat Path | 18.2 m | 32 | 5 | 6,552 PCU/hr |
| TMC-06 | Bhrigu Path | 19.4 m | 9 | 5 | 6,984 PCU/hr |

## 3. Demand against capacity, by approach

PCU is reported as a band, not a point. The survey's composite vehicle classes (car/taxi/tempo/auto/pickup in one column) cannot be resolved to a single IRC:106 factor, so a point estimate would be false precision. The low figure assumes the bucket behaves as cars; the high figure assumes the heavier mix.

| Junction | Approach | Peak | Capacity | PCU low | PCU high | v/c | LOS |
|---|---|---|---|---|---|---|---|
| TMC-01 | Mansarover Metro | 09:15 | 5,616 | 3,301 | 4,860 | 0.59–0.87 | C |
| TMC-01 | Sanganer Stadium | 08:30 | 5,616 | 3,938 | 5,704 | 0.70–1.02 | D |
| TMC-02 | Mansarover Metro | 09:15 | 4,500 | 3,115 | 4,830 | 0.69–1.07 | C |
| TMC-02 | Sanganer Stadium | 18:15 | 4,500 | 2,971 | 4,496 | 0.66–1.00 | C |
| TMC-03 | Mansarover Metro | 09:00 | 4,680 | 3,744 | 5,256 | 0.80–1.12 | D |
| TMC-03 | Sanganer Stadium | 18:30 | 4,680 | 3,735 | 5,315 | 0.80–1.14 | D |
| TMC-04 | Mansarover Metro | 09:15 | 6,336 | 3,502 | 5,029 | 0.55–0.79 | C |
| TMC-04 | Sanganer Stadium | 17:45 | 6,336 | 3,182 | 5,064 | 0.50–0.80 | C |
| TMC-05 | Mansarover Metro | 09:45 | 6,552 | 5,773 | 8,437 | 0.88–1.29 | E |
| TMC-05 | Sanganer Stadium | 09:15 | 6,552 | 4,070 | 6,183 | 0.62–0.94 | C |
| TMC-06 | Mansarover Metro | 09:15 | 6,984 | 3,788 | 5,436 | 0.54–0.78 | C |
| TMC-06 | Sanganer Stadium | 09:30 | 6,984 | 3,537 | 5,649 | 0.51–0.81 | C |

## 4. The published scheme does not resolve this

The scheme under construction — signal-free corridor, 7 U-turn bays — replaces signalised turning with U-turn bays. Tested by gap acceptance against the measured opposing flow, **12 of 12 approaches fail** under conservative critical-gap assumptions and **12 still fail** under optimistic ones.

On **12** approaches the opposing flow is heavy enough that gap acceptance degenerates entirely: there is no usable gap, and no capacity figure is quoted because none would be meaningful.

The mechanism is that removing a signalised right turn does not remove the demand — it converts it into a U-turn. Across the corridor that forces **14,908 additional U-turning vehicles per hour** onto bays sized for far less.

## 5. Grade separation returns the corridor to service

Removing the through movement from the at-grade surface — the elevated option — leaves only turning traffic at the junction. Applying the measured through percentage to each approach returns **all 12 approaches** to acceptable operation on opening. Section 6 tests how long that holds.

| Junction | Approach | Through % | Peak PCU | Residual | v/c before | v/c after | LOS after |
|---|---|---|---|---|---|---|---|
| TMC-01 | Mansarover Metro | 57.2% | 3,317 | 1,420 | 0.59 | 0.25 | A |
| TMC-01 | Sanganer Stadium | 57.2% | 3,963 | 1,696 | 0.71 | 0.30 | B |
| TMC-02 | Mansarover Metro | 68.3% | 3,126 | 991 | 0.69 | 0.22 | A |
| TMC-02 | Sanganer Stadium | 68.3% | 2,990 | 948 | 0.66 | 0.21 | A |
| TMC-03 | Mansarover Metro | 77.4% | 3,750 | 847 | 0.80 | 0.18 | A |
| TMC-03 | Sanganer Stadium | 77.4% | 3,757 | 849 | 0.80 | 0.18 | A |
| TMC-04 | Mansarover Metro | 67.9% | 3,510 | 1,127 | 0.55 | 0.18 | A |
| TMC-04 | Sanganer Stadium | 67.9% | 3,194 | 1,025 | 0.50 | 0.16 | A |
| TMC-05 | Mansarover Metro | 78.7% | 5,777 | 1,231 | 0.88 | 0.19 | A |
| TMC-05 | Sanganer Stadium | 78.7% | 4,086 | 870 | 0.62 | 0.13 | A |
| TMC-06 | Mansarover Metro | 72.9% | 3,797 | 1,029 | 0.54 | 0.15 | A |
| TMC-06 | Sanganer Stadium | 72.9% | 3,566 | 966 | 0.51 | 0.14 | A |

## 6. How long does that relief last?

Opening-year relief is not the same as a design life, and the difference is the whole point of a 20-year horizon. Applying compound growth to the residual turning demand gives the year each approach returns to capacity.

| Junction | Approach | v/c on opening | 4% | 6% | 8% |
|---|---|---|---|---|---|
| TMC-01 | Mansarover Metro | 0.25 | 2062 | 2050 | 2045 |
| TMC-01 | Sanganer Stadium | 0.30 | 2057 | 2047 | 2042 |
| TMC-02 | Mansarover Metro | 0.22 | 2065 | 2052 | 2046 |
| TMC-02 | Sanganer Stadium | 0.21 | 2066 | 2053 | 2047 |
| TMC-03 | Mansarover Metro | 0.18 | 2070 | 2056 | 2049 |
| TMC-03 | Sanganer Stadium | 0.18 | 2070 | 2056 | 2049 |
| TMC-04 | Mansarover Metro | 0.18 | 2070 | 2056 | 2049 |
| TMC-04 | Sanganer Stadium | 0.16 | 2073 | 2058 | 2050 |
| TMC-05 | Mansarover Metro | 0.19 | 2069 | 2055 | 2048 |
| TMC-05 | Sanganer Stadium | 0.13 | 2079 | 2062 | 2053 |
| TMC-06 | Mansarover Metro | 0.15 | 2075 | 2059 | 2051 |
| TMC-06 | Sanganer Stadium | 0.14 | 2077 | 2060 | 2052 |

**At the medium 6% growth rate, 12 of 12 approaches still hold at 2046.** The first returns to capacity in **2047** — 21 years after the base year — and the last in 2062.

This does not withdraw the recommendation; grade separation is still the only measure tested here that returns the corridor to service at all. It qualifies it. A structure sized on opening-year relief alone would be delivering a corridor that is over capacity again well inside its own design horizon, so the scheme needs a demand-side measure alongside it — public transport priority, parking control, or access management — not a structure on its own.

The growth rates are applied to a counted flow that is already capacity-constrained. A saturated approach cannot show suppressed or diverted trips, so these dates are the optimistic end: real demand recovery would bring them forward, not push them back.

## 7. Queue, delay, and what the congestion costs

A volume-to-capacity ratio is not something anyone can act on. Deterministic oversaturation queueing converts it into quantities that are: how many vehicles are queued, how far back they reach, and how long a trip takes. That model needs no signal timings, which matters because the survey records none anywhere in the twelve workbooks — an HCM control-delay model would require inventing its own inputs.

| Junction | Approach | Queue veh | Queue m | Storage m | Delay min | Blocks back |
|---|---|---|---|---|---|---|
| TMC-01 | Mansarover Metro | 0 | 0 | 780 | 0.0 | no |
| TMC-01 | Sanganer Stadium | 0 | 0 | n/a | 0.0 | leaves study area |
| TMC-02 | Mansarover Metro | 0 | 0 | 521 | 0.0 | no |
| TMC-02 | Sanganer Stadium | 0 | 0 | 780 | 0.0 | no |
| TMC-03 | Mansarover Metro | 0 | 0 | 794 | 0.0 | no |
| TMC-03 | Sanganer Stadium | 0 | 0 | 521 | 0.0 | no |
| TMC-04 | Mansarover Metro | 0 | 0 | 874 | 0.0 | no |
| TMC-04 | Sanganer Stadium | 0 | 0 | 794 | 0.0 | no |
| TMC-05 | Mansarover Metro | 0 | 0 | 1,647 | 0.0 | no |
| TMC-05 | Sanganer Stadium | 0 | 0 | 874 | 0.0 | no |
| TMC-06 | Mansarover Metro | 0 | 0 | n/a | 0.0 | leaves study area |
| TMC-06 | Sanganer Stadium | 0 | 0 | 1,647 | 0.0 | no |

**0 of 12 queues reach the junction behind them inside the peak hour.** No queue is reported longer than the road can physically hold: past the point where a queue blocks the junction upstream, the approaches stop being independent and the deterministic model has left the regime it is valid in. A metre figure beyond that would be a fiction dressed as a measurement.

Over the 4.62 km corridor a through trip takes **6.9 minutes** at free flow and **6.9 minutes** at the peak in the southbound direction — an effective **40.0 km/h**. Grade-separated through traffic does not enter the junctions and so returns to the free-flow figure, a saving of **0.0 minutes per trip**. The peak figure is a floor: it sums queues as though independent, and several are not.

Approaches are over capacity for a mean of **0.0 hours a day**, counted from the survey's own 96 intervals rather than assumed from a nominal peak period. That accumulates **0 vehicle-hours** of delay daily.

| Case | Annual cost of delay |
|---|---|
| Do nothing | Rs 0–0 crore |
| Grade separated | Rs 0–0 crore |
| **Annual benefit** | **Rs 0–0 crore** |

**These rupee figures are indicative and deliberately banded.** The delay is measured; the value of time is a policy input and not ours to set. Authorities appraise against their own approved rates, so quoting a single figure derived from a rate the authority has not adopted would present a policy choice as an engineering result. The method is the deliverable; substituting JDA's rates changes one table in `src/economics.py`.

Excluded entirely: vehicle operating cost, fuel, emissions, accident cost, reliability. Each is real and each would raise the figure, so what is quoted is a lower bound. Queue carry-over between consecutive oversaturated hours is also not modelled, for the same reason the queue lengths are capped, and that too makes this conservative.

## 8. Do these conclusions survive their own assumptions?

Both were re-run across **144 combinations** of PCU uplift, lane capacity, effective lane count, critical gap and growth rate.

- **U-turn scheme fails:** holds. Robust across the grid.
- **Grade separation relieves on opening:** all 12 approaches pass in **23 of 24** combinations.

No single assumption dominates the outcome — the swing across the grid is negligible, so naming a most-influential parameter would overstate what the analysis shows.

## 9. Limitations

- The survey covers **one day**, not the two the workbooks present. Day two is derived from day one; see the integrity audit report.
- Composite vehicle classes prevent a point PCU estimate. Bands are reported throughout and no band is collapsed to its midpoint.
- Critical gap values are from literature, not measured at this corridor. They are **not** conservative: an earlier version of this report said so, and it was withdrawn. They sit mid-pack against the four-lane median-opening studies that match this geometry, so measurement could move the finding either way. The same test is published across twelve bases so the reader can pick one.
- E-rickshaw has no IRC PCU factor and no column in the survey. It is excluded rather than assumed, and its absence understates demand by an unknown amount.
- Three of the six junction positions are inferred from the scheme description and are labelled as such. The survey location schedule would confirm them.
- **TMC-03 width is measured from 4 transects against a typical 9.** The surveyed drawing runs 4.62 km and TMC-03 sits 1306 m from its end, so a width band around that junction falls largely outside the drawing. Its width figure rests on fewer measurements than the others and should be treated as the least certain of the six.

**Corridor order.** Chainage along the surveyed alignment places the junctions in the order TMC-06, TMC-05, TMC-04, TMC-03, TMC-02, TMC-01. For the 0 junctions matched by name this is independent geometric evidence, and the full sequence reproduces the order the scheme itself lists. For the inferred three it only restates the assumed position and confirms nothing.

This resolves a question the flow data could not. Deriving the order from corridor continuity - matching each junction's southbound outflow to the next junction's inflow - separated the leading candidates by too small a margin to call, and was reported as inconclusive. The surveyed geometry answers it directly.

## The critical gap, across every published basis

The critical gap is the single most attackable input in this report: it was chosen from the literature, not measured on this corridor. Rather than defend one value, the serviceability test is re-run on every basis reachable.

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