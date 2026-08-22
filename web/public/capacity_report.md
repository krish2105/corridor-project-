# Capacity and design-year assessment
### New Sanganer Road, Jaipur — six surveyed junctions

**Base year** 2026  |  **Design horizon** 20 years to 2046  |  **Survey date** 2026-05-11
**Generated** 2026-08-23 from `out/data/capacity.json`. Every figure in this document is read from the pipeline output at generation time; none is transcribed.

---

## 1. Finding

**12 of 12 surveyed approaches already exceed their carrying capacity at the 2026 peak hour.** The worst, TMC-05 from Mansarover Metro, runs at a volume-to-capacity ratio of **2.41** — Level of Service **F**. This is a present-day measurement, not a projection.

The corridor carries **1.66x** the traffic that the planning-stage assumption implies, which is the gap this assessment exists to quantify.

## 2. Basis of assessment

| Parameter | Value | Source |
|---|---|---|
| Lane capacity | 1200 PCU/lane/hr | Indo-HCM 2017, urban arterial, mixed traffic |
| Lane width | 3.5 m | IRC:86 urban arterial |
| Shy distance | 1.0 m | kerb and median clearance |
| Peak hour factor | applied | derived per approach from 15-minute bins |
| Growth | 4.0% / 6.0% / 8.0% | low / medium / high scenario |
| PCU | share-dependent, interpolated | IRC:106 |

**Carriageway widths are measured, not assumed.** They come from transects cut across the surveyed CAD alignment, taking the outermost kerb either side of the median. This matters: the alignment is offset from the median, so measuring to the nearest kerb returns the median offset rather than the carriageway.

| Junction | JDA name | Measured width | Transects | Lanes/dir | Capacity |
|---|---|---|---|---|---|
| TMC-01 | B-2 Bypass | 7.2 m | 5 | 2 | 2,400 PCU/hr |
| TMC-02 | Vijay Path | 7.1 m | 31 | 2 | 2,400 PCU/hr |
| TMC-03 | Patel Marg | 7.1 m | 30 | 2 | 2,400 PCU/hr |
| TMC-04 | VT Road | 7.2 m | 27 | 2 | 2,400 PCU/hr |
| TMC-05 | Rajat Path | 7.0 m | 30 | 2 | 2,400 PCU/hr |
| TMC-06 | Bhrigu Path | 7.0 m | 27 | 2 | 2,400 PCU/hr |

## 3. Demand against capacity, by approach

PCU is reported as a band, not a point. The survey's composite vehicle classes (car/taxi/tempo/auto/pickup in one column) cannot be resolved to a single IRC:106 factor, so a point estimate would be false precision. The low figure assumes the bucket behaves as cars; the high figure assumes the heavier mix.

| Junction | Approach | Peak | Capacity | PCU low | PCU high | v/c | LOS |
|---|---|---|---|---|---|---|---|
| TMC-01 | Mansarover Metro | 09:15 | 2,400 | 3,301 | 4,860 | 1.38–2.02 | F |
| TMC-01 | Sanganer Stadium | 08:30 | 2,400 | 3,938 | 5,704 | 1.64–2.38 | F |
| TMC-02 | Mansarover Metro | 09:15 | 2,400 | 3,115 | 4,830 | 1.30–2.01 | F |
| TMC-02 | Sanganer Stadium | 18:15 | 2,400 | 2,971 | 4,496 | 1.24–1.87 | F |
| TMC-03 | Mansarover Metro | 09:00 | 2,400 | 3,744 | 5,256 | 1.56–2.19 | F |
| TMC-03 | Sanganer Stadium | 18:30 | 2,400 | 3,735 | 5,315 | 1.56–2.21 | F |
| TMC-04 | Mansarover Metro | 09:15 | 2,400 | 3,502 | 5,029 | 1.46–2.10 | F |
| TMC-04 | Sanganer Stadium | 17:45 | 2,400 | 3,182 | 5,064 | 1.33–2.11 | F |
| TMC-05 | Mansarover Metro | 09:45 | 2,400 | 5,773 | 8,437 | 2.41–3.52 | F |
| TMC-05 | Sanganer Stadium | 09:15 | 2,400 | 4,070 | 6,183 | 1.70–2.58 | F |
| TMC-06 | Mansarover Metro | 09:15 | 2,400 | 3,788 | 5,436 | 1.58–2.26 | F |
| TMC-06 | Sanganer Stadium | 09:30 | 2,400 | 3,537 | 5,649 | 1.47–2.35 | F |

## 4. The published scheme does not resolve this

The scheme under construction — signal-free New Sanganer Road, 7 U-turns — replaces signalised turning with U-turn bays. Tested by gap acceptance against the measured opposing flow, **11 of 12 approaches fail** under conservative critical-gap assumptions and **9 still fail** under optimistic ones.

On **10** approaches the opposing flow is heavy enough that gap acceptance degenerates entirely: there is no usable gap, and no capacity figure is quoted because none would be meaningful.

The mechanism is that removing a signalised right turn does not remove the demand — it converts it into a U-turn. Across the corridor that forces **3,781 additional U-turning vehicles per hour** onto bays sized for far less.

## 5. Grade separation returns the corridor to service

Removing the through movement from the at-grade surface — the elevated option — leaves only turning traffic at the junction. Applying the measured through percentage to each approach returns **all 12 approaches** to acceptable operation.

| Junction | Approach | Through % | Peak PCU | Residual | v/c before | v/c after | LOS after |
|---|---|---|---|---|---|---|---|
| TMC-01 | Mansarover Metro | 57.2% | 3,317 | 1,420 | 1.38 | 0.59 | B |
| TMC-01 | Sanganer Stadium | 57.2% | 3,963 | 1,696 | 1.65 | 0.71 | C |
| TMC-02 | Mansarover Metro | 68.3% | 3,126 | 991 | 1.30 | 0.41 | B |
| TMC-02 | Sanganer Stadium | 68.3% | 2,990 | 948 | 1.25 | 0.39 | A |
| TMC-03 | Mansarover Metro | 77.4% | 3,750 | 847 | 1.56 | 0.35 | A |
| TMC-03 | Sanganer Stadium | 77.4% | 3,757 | 849 | 1.57 | 0.35 | A |
| TMC-04 | Mansarover Metro | 67.9% | 3,510 | 1,127 | 1.46 | 0.47 | B |
| TMC-04 | Sanganer Stadium | 67.9% | 3,194 | 1,025 | 1.33 | 0.43 | B |
| TMC-05 | Mansarover Metro | 78.7% | 5,777 | 1,231 | 2.41 | 0.51 | B |
| TMC-05 | Sanganer Stadium | 78.7% | 4,086 | 870 | 1.70 | 0.36 | A |
| TMC-06 | Mansarover Metro | 72.9% | 3,797 | 1,029 | 1.58 | 0.43 | B |
| TMC-06 | Sanganer Stadium | 72.9% | 3,566 | 966 | 1.49 | 0.40 | B |

## 6. Do these conclusions survive their own assumptions?

Both were re-run across **144 combinations** of PCU uplift, lane capacity, effective lane count, critical gap and growth rate.

- **U-turn scheme fails:** holds. Robust across the grid.
- **Grade separation relieves:** all 12 approaches pass in **23 of 24** combinations.

No single assumption dominates the outcome — the swing across the grid is negligible, so naming a most-influential parameter would overstate what the analysis shows.

## 7. Limitations

- The survey covers **one day**, not the two the workbooks present. Day two is derived from day one; see the integrity audit report.
- Composite vehicle classes prevent a point PCU estimate. Bands are reported throughout and no band is collapsed to its midpoint.
- Critical gap values are from literature, not measured at this corridor. They are Raff-derived and therefore likely biased high, which makes the U-turn finding **conservative** — measured values would tend to worsen it, not improve it.
- E-rickshaw has no IRC PCU factor and no column in the survey. It is excluded rather than assumed, and its absence understates demand by an unknown amount.
- Three of the six junction positions are inferred from the scheme description and are labelled as such. The survey location schedule would confirm them.
- **TMC-01 width is measured from 5 transects against a typical 30.** The surveyed drawing runs 6.52 km and TMC-01 sits 1 m from its end, so a width band around that junction falls largely outside the drawing. Its width figure rests on fewer measurements than the others and should be treated as the least certain of the six.

**Corridor order.** Chainage along the surveyed alignment places the junctions in the order TMC-06, TMC-05, TMC-04, TMC-03, TMC-02, TMC-01. For the 3 junctions matched by name this is independent geometric evidence, and the full sequence reproduces the order the scheme itself lists. For the inferred three it only restates the assumed position and confirms nothing.

This resolves a question the flow data could not. Deriving the order from corridor continuity - matching each junction's southbound outflow to the next junction's inflow - separated the leading candidates by too small a margin to call, and was reported as inconclusive. The surveyed geometry answers it directly.

---

Prepared from the JDA classified turning-movement survey dated 2026-05-11. Method, standards and acceptance gates are set out in the accompanying method statement.