# JDA TMC Survey — Integrity Audit

Corridor: Mansarover Metro to Sanganer Stadium, Jaipur. Six junctions, surveyed 11 and 12 May 2026.
Source: 12 workbooks, 253,440 parsed 15-minute class-bins.

Every stored total in the source has been recomputed from its components. Where the two disagree the discrepancy is recorded and the derived value used.

---

## A — Arithmetic: stored totals vs recomputed

Discrepancies found: **225**. Every one is listed in the register; none is silently corrected.

Separately, a positive check: the clockwise turn mapping used throughout this pipeline — LEFT lands on the next arm clockwise, as it must under left-hand traffic — was tested against the `Direction From/To` header that each of the **144** `V_` sheets states about itself. All 144 agree. The survey's own geometry is internally consistent and correct for India.

| field                   |   count |   net_delta |
|:------------------------|--------:|------------:|
| Grand Total (Nos.)      |     106 |        -157 |
| Total Slow              |     104 |         -99 |
| Total Slow (unreadable) |       2 |           0 |
| day Grand Total (Nos.)  |       7 |        -157 |
| day Total Slow          |       6 |         -99 |

180 understate the true value and 43 overstate it, so this is scattered formula damage rather than a systematic bias. The net effect on the bin-level `Grand Total (Nos.)` is an understatement of **157 vehicles**.

Worst offenders:

| junction   | date       | sheet   |   row | field                  |   stored |   derived |   delta |
|:-----------|:-----------|:--------|------:|:-----------------------|---------:|----------:|--------:|
| TMC-01     | 2026-05-12 | V_1     |   103 | Grand Total (Nos.)     |      138 |       198 |     -60 |
| TMC-01     | 2026-05-11 | V_1     |   104 | day Total Slow         |        0 |        58 |     -58 |
| TMC-01     | 2026-05-11 | V_1     |   104 | day Grand Total (Nos.) |    14103 |     14161 |     -58 |
| TMC-01     | 2026-05-12 | V_1     |   104 | day Grand Total (Nos.) |    14444 |     14502 |     -58 |
| TMC-01     | 2026-05-11 | V_6     |   104 | day Grand Total (Nos.) |     8400 |      8421 |     -21 |
| TMC-01     | 2026-05-11 | V_6     |   104 | day Total Slow         |        4 |        25 |     -21 |
| TMC-06     | 2026-05-12 | V_2     |   104 | day Grand Total (Nos.) |    37443 |     37454 |     -11 |
| TMC-06     | 2026-05-11 | V_2     |   104 | day Total Slow         |        4 |        15 |     -11 |

The clearest case: `V_1` on TMC-01 stores `Total Slow = 0` where its own five slow-vehicle columns sum to **58**. The grand total inherits the error.

---

## B — Conservation: are the approach sheets independent data?

| comparison | cells | exact | max residual |
|---|---|---|---|
| IN_* vs movements leaving that arm | 46,080 | 46,080 (100.00%) | 0 |
| OUT_* vs movements landing on that arm | 46,080 | 46,080 (100.00%) | 0 |

**Both reconcile exactly, at every bin, for every class.** That is not corroboration — it means `IN_*`, `OUT_*`, `TOTAL_IN` and `TOTAL_OUT` are arithmetic views of the twelve `V_` movement sheets, not separately observed data. The workbook contains **one** primary dataset of 12 movement series per junction; the other 10 sheets are formulas over it.

Two consequences. Junction inflow/outflow balance is a formula identity and proves nothing about survey quality. And any statistical test must run on the `V_` sheets alone, or it counts the same observation three times.

It also resolves finding A: the 58-vehicle gap between TMC-01's arm-1 movements and its approach total is **entirely** the broken `Total Slow` formula. The underlying counts never disagreed.

---

## C — Corridor magnitude

Junction inflow/outflow balance is omitted deliberately: finding B shows it is a formula identity. What the totals do give is the corridor's scale.

| junction   | date       |   daily_vehicles |
|:-----------|:-----------|-----------------:|
| TMC-01     | 2026-05-11 |          127,998 |
| TMC-01     | 2026-05-12 |          130,668 |
| TMC-02     | 2026-05-11 |          129,047 |
| TMC-02     | 2026-05-12 |          131,297 |
| TMC-03     | 2026-05-11 |          128,195 |
| TMC-03     | 2026-05-12 |          132,322 |
| TMC-04     | 2026-05-11 |          153,323 |
| TMC-04     | 2026-05-12 |          156,066 |
| TMC-05     | 2026-05-11 |          127,981 |
| TMC-05     | 2026-05-12 |          131,819 |
| TMC-06     | 2026-05-11 |          114,811 |
| TMC-06     | 2026-05-12 |          119,021 |

Daily entering volume ranges **114,811–156,066 vehicles** across the six junctions.

---

## D — PCU method: are the factors static?

Factors back-solved from every workbook's own `Total (Veh.)` and `Total (PCUs)` rows:

| cls                                                 | code         |   factor | constant   |
|:----------------------------------------------------|:-------------|---------:|:-----------|
| Car, Taxi, Tempo, Auto Rickshaw & Pickup            | CAR_BUCKET   |      1   | yes        |
| Motor Cycle, Scooter                                | TWO_W        |      0.5 | yes        |
| Agricultural Tractor, LCV, Mini Bus                 | AGRI_LCV     |      1.5 | yes        |
| Three Wheeler (Auto), 3 Axle Truck, Buses           | AUTO_TRK_BUS |      3   | yes        |
| Tractor Trailer, Truck Trailer Units (3 Axle & MAV) | TRL_MAV      |      4.5 | yes        |
| Cycle                                               | CYCLE        |      0.5 | yes        |
| Cycle Rickshaw                                      | CYCLE_RIK    |      1.5 | yes        |
| Hand Cart                                           | HAND_CART    |      3   | yes        |
| Horse Drawn                                         | HORSE_DRAWN  |      4   | yes        |
| Bullock Carts                                       | BULLOCK      |      8   | yes        |

Interval-level test: the static factors above are applied to each class count on every 15-minute row and compared against that row's own stored `Grand Total (PCU's)`.

- rows tested: **25,344** across all sheets of all 12 workbooks
- rows where the static factors do not reproduce the stored PCU: **0**

**GATE — factor constant across all 25,344 intervals: PASS.** The survey uses a single fixed PCU per class, independent of composition.

### What IRC:106 requires instead

IRC:106 gives the low factor when a class is <=5% of the stream and the high factor when it is >=10%, interpolating between. It is a function of composition, not a constant.

| junction   | date       |   pcu_as_surveyed |   pcu_irc_corrected |   uplift_pct |
|:-----------|:-----------|------------------:|--------------------:|-------------:|
| TMC-01     | 2026-05-11 |           111,706 |             125,280 |         12.2 |
| TMC-01     | 2026-05-12 |           113,843 |             127,687 |         12.2 |
| TMC-02     | 2026-05-11 |           109,140 |             125,054 |         14.6 |
| TMC-02     | 2026-05-12 |           110,770 |             126,992 |         14.6 |
| TMC-03     | 2026-05-11 |           102,356 |             119,628 |         16.9 |
| TMC-03     | 2026-05-12 |           105,588 |             123,311 |         16.8 |
| TMC-04     | 2026-05-11 |           124,860 |             144,449 |         15.7 |
| TMC-04     | 2026-05-12 |           126,900 |             146,840 |         15.7 |
| TMC-05     | 2026-05-11 |           101,201 |             116,829 |         15.4 |
| TMC-05     | 2026-05-12 |           104,064 |             120,179 |         15.5 |
| TMC-06     | 2026-05-11 |            91,562 |             105,414 |         15.1 |
| TMC-06     | 2026-05-12 |            94,748 |             109,116 |         15.2 |

Correcting **only** the classes that map 1:1 to IRC:106 raises corridor PCU by **15.0%** on average (range 12.2% to 16.9%).

This is a floor, not the full correction. Six of the ten columns are composites mixing IRC classes with different factors and cannot be disaggregated from this data — they are held at the surveyed factor above. The true uplift is larger.

The driver is the two-wheeler. Its share of the stream ranges **42.5%–54.0%** across the corridor, far above the 10% threshold, yet it is carried at PCU 0.50 — the value IRC:106 reserves for a class below 5%. The correct factor is 0.75.

---

## E — Peak hour: re-derived vs the workbook's stated peaks

Peak hour is the four consecutive 15-min bins with the highest combined volume. PHF = hourly volume / (4 x highest single 15-min volume).

| junction   | date       | peak_start   |   peak_hour_veh |   phf |
|:-----------|:-----------|:-------------|----------------:|------:|
| TMC-01     | 2026-05-11 | 09:00        |          11,107 | 0.983 |
| TMC-01     | 2026-05-12 | 09:00        |          11,362 | 0.984 |
| TMC-02     | 2026-05-11 | 09:15        |           9,476 | 0.955 |
| TMC-02     | 2026-05-12 | 09:15        |           9,658 | 0.954 |
| TMC-03     | 2026-05-11 | 18:30        |           9,695 | 0.962 |
| TMC-03     | 2026-05-12 | 18:30        |          10,068 | 0.963 |
| TMC-04     | 2026-05-11 | 09:15        |          10,876 | 0.961 |
| TMC-04     | 2026-05-12 | 09:15        |          11,113 | 0.960 |
| TMC-05     | 2026-05-11 | 09:15        |          12,433 | 0.931 |
| TMC-05     | 2026-05-12 | 09:15        |          12,770 | 0.931 |
| TMC-06     | 2026-05-11 | 09:15        |           9,403 | 0.982 |
| TMC-06     | 2026-05-12 | 09:15        |           9,755 | 0.983 |

PHF range **0.931–0.984**.

**This is itself a finding.** `docs/jaipur_corridor_study.md` §5.5 gives 0.85–0.92 as typical for an urban Indian arterial, and a PHF approaching 1.0 means flow is almost perfectly uniform across the four peak quarter-hours. Real mixed traffic at an uncontrolled Jaipur junction does not behave that way. Combined with finding F, it suggests the 15-minute series has been smoothed rather than observed. Peak-15 design values derived from this data will be understated.

The workbooks state a Morning Peak of 0900-1000 and an Evening Peak of 1815-1915 for TMC-01. Those are stated per-junction constants in the `Table` sheet; the re-derived peaks above are computed per junction and per day from the bins.

### Against the workbooks' own rolling-hour sheets

| workbook           | wb_peak_window   |   wb_peak_veh |
|:-------------------|:-----------------|--------------:|
| 01_TMC (11-05-2026 | 0900 - 1000      |        11,107 |
| 02_TMC (11-05-2026 | 0915 - 1015      |         9,476 |
| 03_TMC (11-05-2026 | 1830 - 1930      |         9,695 |
| 04_TMC (11-05-2026 | 0915 - 1015      |        10,876 |
| 05_TMC (11-05-2026 | 0915 - 1015      |        12,433 |
| 06_TMC (11-05-2026 | 0915 - 1015      |         9,403 |
| 01_TMC (12-05-2026 | 0900 - 1000      |        11,362 |
| 02_TMC (12-05-2026 | 0915 - 1015      |         9,658 |
| 03_TMC (12-05-2026 | 1830 - 1930      |        10,068 |
| 04_TMC (12-05-2026 | 0915 - 1015      |        11,113 |
| 05_TMC (12-05-2026 | 0915 - 1015      |        12,770 |
| 06_TMC (12-05-2026 | 0915 - 1015      |         9,755 |

**GATE — re-derived peak volume matches the workbooks' own rolling-hour maximum: 12 of 12 agree to within 1 vehicle.**

---

## F — Is 12 May an independent count?

Run on the twelve `V_` movement sheets only. Finding B showed the approach and total sheets are formulas over these, so including them would count each observation three times.

**Daily totals — 555 movement x class series**

| | count | share |
|---|---|---|
| day 2 greater | 154 | 27.7% |
| day 2 **identical to the vehicle** | 396 | 71.4% |
| day 2 smaller | 5 | 0.9% |

Ignoring ties, n = 159. Under independent counting increases and decreases should be roughly equal. P(<= 5 decreases) = **2.25e-39**.

**15-minute bins, split by class group** — the two groups were manufactured differently, and averaging them together hides both signatures.

| class group | live bins | day2 up | identical | day2 down |
|---|---|---|---|---|
| dominant (car bucket, 2W) | 13,158 | 8,463 (64.3%) | 4,667 (35.5%) | **28 (0.2%)** |
| all other classes | 9,999 | 1,777 (17.8%) | 6,605 (66.1%) | **1,617 (16.2%)** |

Two distinct signatures:

1. **Dominant classes — monotonically inflated.** Only **0.21%** of 13,158 bins fall on day 2. Independent re-counting gives roughly 50%. Two-wheeler and car-bucket totals rise 1.2–3.2% at every single approach.

2. **Minor classes — daily total pinned, bins reshuffled.** 396 of 555 series reproduce the day-1 total to the exact vehicle while their underlying bins differ. Counting a several-hundred-vehicle class on two different days does not reproduce the total exactly.

**Conclusion: 12 May is derived from 11 May, not independently observed.** Treat the dataset as **one day of survey**. Any analysis presented as two-day evidence overstates its basis, and day-over-day growth computed from it is an artefact of the derivation, not of traffic. This is a question for the survey contractor.

---

## G — Flow Diagram Table: labels do not match the data beneath them

The `Flow Diagram Table` sheet carries a 20-class header — Car, Taxi, TW, Three Wheeler, four bus types, six goods types, Cycle, Cycle Rickshaw, **E-Rickshaw**, Others — but the data beneath it is the 10-class data, shifted one column left of its label.

| header says | value | what that number actually is |
|---|---|---|
| Car | 20,331 | Car, Taxi, Tempo, Auto Rickshaw & Pick up |
| **Taxi** | **19,012** | **Motar Cycle, Scooter — the two-wheelers** |
| **TW** | **305** | Agriculture Tractor, LCV Mini Bus |
| Three Wheeler (Auto) | 116 | 3W Auto Axle Truck, Buses |
| Govt./Roadways Bus | 395 | Tractor Trailor, Truck Trailor (3 Axle & MAV) |
| **E-Rickshaw** | **9** | **Hand Cart** |
| **Others** | **268** | **Horse Drawn** |

`#REF!` errors across the 12 workbooks: **960** (80 per file). The remaining columns did not error — they silently took the wrong data.

Column shift confirmed in **12/12** files.

Consequence: anyone reading the flow diagram concludes two-wheelers are 0.24% of the stream. They are over 40%. There is no E-rickshaw data anywhere in the workbooks — the column exists as a template header only.

---

## Survey design, against the project's own methodology

- **11 May 2026 is a Monday.** `docs/jaipur_corridor_study.md` §5.2 specifies Tuesday, Wednesday or Thursday and says never Monday or Friday.
- **May is pre-monsoon peak heat.** The recommended windows are October–November or February–March.
- **No weekend day was surveyed.** The stated minimum is three days including one Saturday and one Sunday.
- **U-turns were never counted.** Twelve movements per junction, not sixteen. U-turn demand is unmeasured, not zero.

## Gate summary

| check | result |
|---|---|
| A arithmetic discrepancies recorded | 225 (0 absorbed silently) |
| B movement-to-approach residuals | 0 (identity) |
| B approach sheets independent | **no** — exact formula views of V_ sheets |
| C corridor daily volume | 114,811-156,066 veh |
| D PCU factors static | confirmed; +15.0% floor correction |
| E PHF range | 0.931–0.984 |
| F day 2 independent | **no**, p=2.2e-39, 0.21% bins fall |
| G Flow Diagram Table #REF! cells | 960 |
