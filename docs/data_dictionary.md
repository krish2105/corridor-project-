# Data dictionary
### Every field in every published dataset

Generated 2026-08-26 from the files in `out/data`. The field list is read from the data itself, so a field added to the pipeline and not described here is reported below as undocumented rather than quietly omitted.

**All spatial data is EPSG:32643 (UTM zone 43N, metres).** GeoJSON is written in EPSG:4326 because the format requires it, and is converted at that boundary only.

## Files

| File | Contents |
|---|---|
| `corridor.json` | Everything the dashboard reads. Bundles the sections below. |
| `capacity.json` | Measured widths, demand against capacity, relief, design life. |
| `delay.json` | Queue, spillback, delay and corridor journey time. |
| `economics.json` | Cost of delay. Every figure banded. |
| `scheme_test.json` | Gap-acceptance test of the JDA U-turn scheme. |
| `sensitivity.json` | Every conclusion re-run across its assumption grid. |
| `constraint_profile.json` | Pier-siting score at 25 m stations along the alignment. |
| `atlas_summary.json` | Constraint counts by category over the whole drawing. |
| `atlas.geojson` | Constraint geometry: buildings, utilities, drainage, trees, medians. |
| `median_openings.geojson` | Every median gap with width and classification. |
| `junction_candidates.geojson` | All signal clusters considered when placing the six junctions. |
| `safety.json` | Conflict points and flow-weighted exposure, counted from geometry. |
| `profiles.json` | Level of service by approach and hour, and peak spreading. |
| `exhibits.json` | Volume-flow, tornado, continuity and flow-raster series. |
| `standards.json` | The corridor measured against the codes it is built under. |
| `anomaly.json` | Integrity screen: six detectors over the parsed survey, scored. |
| `cluster.json` | Approach typology learned from the counts, and its held-out test. |
| `forecast.json` | How short a count can be and still predict the day, with its error. |
| `uturn_framework.json` | Per-bay criteria ladder, the binding constraint, and the back-solve. |

## Fields

| Field | Meaning |
|---|---|
| `2w` | Two-wheeler. |
| `3w` | Three-wheeler. |
| `4w` | Four-wheeler. |
| `LCV` | PCU factor for light commercial vehicles. |
| `MAV` | PCU factor for multi-axle vehicles. |
| `after_grade_separation` | Approach state once the through movement is elevated. |
| `alignment_km` | Length of the surveyed alignment. |
| `alternatives` | The ladder of what to do instead, ordered by cost. |
| `analysis_date` | Survey day the figures come from. Day two is derived; see the audit. |
| `analysis_days` | Independent days the model is fitted on. One. |
| `annual_benefit_crore` | [low, high] difference between the two. |
| `annual_cost_after_crore` | [low, high] annual cost once grade separated. |
| `annual_cost_crore` | [low, high] annual cost of delay, crore rupees. |
| `any_typology_found` | Whether any feature set cleared both gates. |
| `approach` | Which arm traffic enters from. Only the two corridor arms carry a v/c. |
| `approach_hours_F` | Of those, how many are at Level of Service F. |
| `approach_hours_total` | Approach-hours assessed: approaches x rolling hours. |
| `approaches` | Per-approach rows. Two corridor approaches at each junction. |
| `approaches_ok_after_grade_separation` | Approaches under capacity on opening. |
| `arms` | Arm names, clockwise from north. |
| `arrivals` | Cumulative PCU arriving at the stop line. Measured. |
| `articulated` | Minimum turning radius band, metres. |
| `assumption_driven` | Whether any single assumption changes the conclusion. |
| `auto` | PCU factor for auto-rickshaws. |
| `back_solve` | What would have to change for the binding criterion to clear. |
| `band_high_pct` | High end of the PCU correction band, %. |
| `band_low_pct` | Low end of the PCU correction band, %. |
| `base_capacity_pcu_per_dir` | Tabulated capacity per direction at the base width, PCU/hour. Scaled by measured width, not by lane count. |
| `base_pcu` | Corridor peak PCU on the survey's own factors, before correction. |
| `base_total` | Total conflict points at a four-arm junction, from geometry. |
| `base_width_per_dir_m` | Carriageway width per direction the tabulated capacity applies to, metres. |
| `base_year` | Year the survey and all present-day figures refer to. |
| `baseline` | The no-model comparison the windows are scored against. |
| `baseline_mape` | Error of that baseline: the window carries its pro-rata share. |
| `bay` | Which U-turn bay the demand feeds: the one merging into northbound traffic, or into southbound. |
| `bay_beyond_drawing` | True where the CAD ends before the next opening, so the detour cannot be measured in that direction. A limit of the survey extent, not a finding about the road. |
| `bay_ceiling_veh_hr` | The most a single opening can pass, 3600 / follow-up headway, with no opposing traffic at all. Nothing lifts it. |
| `bay_chainage_m` | Distance of the U-turn opening along the same alignment, metres. |
| `bay_storage_m` | Assumed deceleration and storage length. No bay geometry supplied. |
| `bays` | One entry per U-turn bay: two per junction, north and south. |
| `bays_above_bay_ceiling` | Bays whose demand exceeds that ceiling. For these the bay is the wrong instrument, not a badly sited one. |
| `bays_planned_by_jda` | U-turn bays in the published scheme. |
| `benefit_to_first_failure_crore` | Undiscounted benefit over the years the relief lasts. |
| `binding_criterion` | The first criterion to fail. Criteria below it are untested. |
| `binding_need_pcu` | What the binding approach would need by then, PCU/hour. |
| `bins_parsed` | 15-minute class bins parsed across all workbooks. |
| `blocked_criteria_now` | Union of blocked_on across bays. |
| `blocked_criteria_once_binding_cleared` | Union of blocked_if_binding_cleared. |
| `blocked_if_binding_cleared` | Criteria BELOW the binding one lacking data. They do not block today's verdict; they are what would need measuring if the binding criterion were cleared. |
| `blocked_on` | Criteria ABOVE the binding one that could not be evaluated. These block today's verdict. |
| `breaks` | Arithmetic breaks at this junction. |
| `bus_truck` | Minimum turning radius band, metres. |
| `cap_conservative` | Bay capacity at the conservative gap, veh/hour. |
| `cap_optimistic` | Bay capacity at the optimistic gap, veh/hour. |
| `capacity` | Approach capacity, PCU/hour, lanes x lane capacity. |
| `capacity_pcu_hr` | That approach's capacity, PCU/hour. |
| `capacity_source` | The document and table the capacity comes from. |
| `car` | PCU factor for cars. |
| `category` | Constraint category. |
| `caveat` | What the figure is NOT. Read before quoting it. |
| `cells_checked` | Cells re-derived when checking stored totals. |
| `chainage_m` | Distance along the alignment from its start, metres. |
| `change_pct` | Change in crossing exposure between the two schemes, %. |
| `checks` | The five criteria for this bay, each with status, value and reason. |
| `chi2` | Chi-square statistic of the last-digit test. |
| `city` | City. |
| `claim_overstatement` | The ratio between the two. |
| `classes` | Vehicle classes with their counts and shares. |
| `classification` | Width band this opening falls in. |
| `clock` | The same window in clock time. |
| `closer_than_500m` | Spacings below the IRC:SP:84 built-up minimum. |
| `closest_m` | Smallest spacing, metres. |
| `cls` | Vehicle class code. |
| `cluster` | Cluster id. |
| `clusters` | One entry per cluster. |
| `code` | Junction code. |
| `combinations` | Grid size for the capacity and scheme conclusions. |
| `combinations_elevated` | How many combinations the elevated-relief conclusion is run across: PCU uplift x lane capacity x lanes per direction. |
| `combinations_queue` | How many combinations the queue-spillback conclusion is run across, on its own grid of packing, footprint and capacity. |
| `combinations_searched` | Window-target combinations the shortest was picked from. |
| `combinations_uturn` | How many assumption combinations the U-turn conclusion is actually run across - not the size of the whole space. |
| `composition` | Share of each vehicle class. |
| `conclusion` | Which conclusion this row belongs to. |
| `conflicting_flow` | Opposing through movement the U-turn must cross, veh/hour. |
| `conflicting_stream` | Which movement the U-turn must cross. |
| `continuity` | Southbound outflow against next-junction inflow, per link. |
| `corridor` | Corridor-level aggregates. |
| `corridor_arms_pcu` | Peak PCU on the two corridor approaches. A FLOOR on all-arm volume: the cross-street arms are counted but unmeasured. |
| `corridor_km` | Length of the surveyed alignment between the end junctions. |
| `corridor_mean` | Mean share on the twelve corridor arms. |
| `corridor_order` | Junction order along the alignment, from chainage. |
| `corridor_through_pct` | Through share used for the relief calculation, %. |
| `cost` | Mismatch between those pairs, as a fraction of flow. |
| `criteria` | The five criteria, in the order they are evaluated. |
| `critical_gap` | Which critical-gap assumption was used. |
| `critical_gap_source` | Where the critical-gap values come from. |
| `cross_mean` | Mean share on the twelve cross-street arms. |
| `crossing` | Conflict points where two paths cross. |
| `csir_crri_design_gap_s` | CSIR-CRRI's recommended design critical gap for Indian median openings, seconds. |
| `csir_crri_design_source` | Where the CSIR-CRRI design gap comes from. |
| `daily_in` | Vehicles entering the junction over the surveyed day. |
| `daily_out` | Vehicles leaving the junction over the surveyed day. |
| `daily_veh` | Vehicles counted over the survey day. |
| `delay_veh_hr_day` | Vehicle-hours of delay accumulated per day. A lower bound. |
| `demand` | Vehicles per peak hour that must use this bay. |
| `dep_high` | Departure curve at the fast end of the discharge band. |
| `dep_low` | Departure curve at the slow end of the discharge band. |
| `departures` | Cumulative PCU discharged. ASSUMED - the contestable line. |
| `design_horizon_years` | Design horizon length, years. |
| `design_life` | Years until each approach exceeds capacity, by growth rate. |
| `design_life_first_failure_med` | Earliest of fails_med across all approaches. |
| `design_life_last_failure_med` | Latest of fails_med. |
| `design_life_survives_horizon` | How many approaches still hold at horizon_year. |
| `detour burden` | What the diversion costs the traffic it diverts. |
| `detour_bays_beyond_drawing` | How many it does not. |
| `detour_bays_measured` | How many bays the drawing covers in that direction. |
| `detour_m` | Extra distance a converted movement travels, out and back, metres. |
| `detour_max_m` | Longest measured detour, metres. |
| `detour_mean_m` | Mean detour across every bay the drawing covers, metres. |
| `detour_mean_typical_m` | Mean detour excluding rows over 1 km, which are driven by the drawing ending rather than by the road. |
| `detour_min_m` | Shortest measured detour on the corridor, metres. |
| `detour_outliers_excluded` | Rows over 1 km held out of the typical figure. |
| `detour_tolerable_m` | Round-trip detour above which the diversion is the problem. A stated threshold, not a standard. |
| `detour_veh_km_per_hour` | Extra vehicle-kilometres per peak hour, all measured bays. |
| `detour_veh_km_typical` | The same, excluding the over-1-km rows. |
| `digit_min_count` | Counts below this are excluded from the digit test: their last digit IS the count, so it is skewed for honest reasons. |
| `discharge_band` | The capacity multipliers the departure band is drawn across. |
| `discrepancies` | Stored totals that disagreed with their own components. |
| `diverging` | Points where one stream splits. |
| `duplicate_series_share` | Share of this junction's series that reproduce the previous day in every live bin. |
| `easting` | Easting, EPSG:32643, metres. |
| `effective_kmh` | Corridor length divided by peak_journey_min. |
| `elevated` | Approaches returned under capacity, per assumption combination. |
| `elevated_all_pass_combinations` | Combinations where all approaches are relieved. |
| `elevated_total_combinations` | Size of the elevated grid. |
| `excess_0_5_pct` | As terminal_digit_excess_pct. |
| `excess_pcu` | Excess ARRIVALS per day, PCU. Not PCU-hours. |
| `excluded` | Cost components deliberately not counted. |
| `external_label` | A label held out of the fitting, used to test whether the clusters mean anything. |
| `f_share_pct` | That as a percentage. |
| `factor` | Expansion factor, the mean of the approaches' total-over-partial ratios. |
| `factor_cv` | Coefficient of variation of those ratios. Low means the factor travels. |
| `factors` | Back-solved PCU factor per class, one row per workbook. |
| `fails` | Approaches failing under that assumption. |
| `fails_conservative` | Approaches the bays cannot serve, conservative gap. |
| `fails_high` | Year it returns to capacity at the high growth rate. |
| `fails_low` | Year the approach returns to capacity at the low growth rate. |
| `fails_med` | Year it returns to capacity at the medium growth rate. |
| `fails_optimistic` | Approaches they cannot serve even optimistically. |
| `feature_set` | What each approach was represented by. |
| `feature_sets_tested` | How many feature sets were fitted. All are published; reporting only the winner would invalidate the p-value. |
| `features` | What each position in that vector is. |
| `feeds_bay` | Which movements have to use a U-turn bay under the scheme. Right turns from all four arms, plus the cross-street through movement. |
| `files_affected` | Workbooks containing at least one discrepancy. |
| `flatline_min` | Consecutive identical non-zero intervals that count as a flatline. |
| `flatline_series` | Series holding one non-zero count across 4+ consecutive intervals. |
| `floor_vs_warrant` | That floor as a multiple of the interchange warrant. |
| `flow_raster` | Through flow per link per fifteen-minute bin. |
| `follow_up_four_lane_measured_s` | The only follow-up headway measured on four-lane median openings in India, seconds - two-wheelers, Khan 2022 thesis Table 8.2. |
| `follow_up_measured_s` | The only measured Indian follow-up headways found, seconds, against which our assumed band is checked. |
| `follow_up_s` | Follow-up headway band, seconds. |
| `followup_implied_by_indo_hcm` | [optimistic, conservative] follow-up time implied by Indo-HCM's ratio applied to our weighted gaps. |
| `followup_ours` | The follow-up headways we use, seconds. |
| `followup_ratio_convention` | The tf = 0.6 x tc rule of thumb. A convention stated as an assumption in Indian studies, not a code relation; published here to show where our follow-up departs from it toward the four-lane measurement. |
| `footprint` | Footprint scale tested. |
| `footprint_scale` | Scale applied to the vehicle footprints tested. |
| `forced_uturns_per_hour` | Vehicles per peak hour forced across a stream with no gap. |
| `frac` | ok divided by total. |
| `free_flow_kmh` | Free-flow speed used for journey time, km/h. |
| `free_flow_min` | Through journey time at the free-flow speed. |
| `gap capacity` | Can the bay serve its demand from gaps in the opposing stream? |
| `gap_bases_tested` | How many published critical-gap bases the test was re-run on. |
| `gap_benchmark` | Per-approach critical gap needed against the gap we assume. |
| `gap_conclusion_holds_in` | How many of the tested gap bases return the same finding. |
| `gap_direction_note` | Which way our critical-gap assumption errs against the field evidence, and what that does to the finding. |
| `gap_evidence_spread` | The same capacity test re-run on every published critical-gap basis reachable, rather than on one chosen value. |
| `gap_margin_s` | The difference between them. |
| `gap_ours_median_s` | Median of our optimistic weighted gaps. |
| `gap_required_median_s` | Median t_c_required across the corridor. |
| `gap_source` | Where the critical gaps come from and what they are benchmarked against. |
| `gaps` | Spacings between consecutive openings. |
| `geometric_match` | How closely the source geometry matches this corridor. |
| `greater` | Series where day two exceeds day one. |
| `growth` | Demand multiple at the horizon, one row per growth rate. |
| `growth_handled_in` | Where the growth-rate assumption is varied, given it is not an axis in this module. |
| `growth_high_pct` | High growth scenario. |
| `growth_low_pct` | Low growth scenario, % per year. |
| `growth_med_pct` | Medium growth scenario. |
| `growth_pct` | Growth rate applied, % per year. |
| `hard_free` | Stations with no undivertible constraint. |
| `hard_free_pct` | That as a percentage. |
| `horizon_year` | End of the stated design horizon. |
| `hour` | Rolling-hour label, one per fifteen-minute step. |
| `hours` | Window length, hours. |
| `hours_over` | Hours per day this approach is over capacity. Counted, not assumed. |
| `identical` | Series reproducing the previous day to the exact vehicle. |
| `indo_hcm_form_differs` | How Indo-HCM's capacity equation differs from the HCM form we use, and why the difference is not applied. |
| `indo_hcm_gap_source` | Where those Indo-HCM figures came from, and why they are marked secondary. |
| `indo_hcm_no_uturn_chapter` | Indo-HCM 2017 publishes no chapter or parameter set for mid-block median openings, so no Indian code carries a design gap for the manoeuvre this scheme is built on. |
| `integrity_flag_score` | Unweighted sum of the six detector scores, 0 to 6. Not a verdict: an ordering of what to ask about first. |
| `interchange` | Each junction's corridor-arm total against the interchange warrant. |
| `interchange_warrant_pcu` | IRC:SP:90-2010 threshold above which an interchange is justified, PCU/hr across all arms. |
| `intervals` | As mix_intervals, for one junction-day. |
| `irc_high` | IRC:106 factor at or above 10% share. |
| `irc_low` | IRC:106 factor at or below 5% share. |
| `irc_point` | Interpolated factor at the observed share. null for composites. |
| `irc_sp41_car_gap_s` | IRC:SP:41-1994 App III Table III-2 passenger-car critical gap, four-lane crossing under stop control, large-city adjustment applied. Our weighted gaps sit below it because two-wheelers are half the stream, so our figures favour the scheme. |
| `jam_packing` | Packing efficiency of a jammed queue. |
| `jda_name` | The authority's own name for the junction in its scheme documents. |
| `jda_scheme` | The authority's scheme as described in its documents. |
| `jda_turning_claim_pct` | JDA's stated basis for the scheme: the share of traffic it says is turning. News reporting, not a JDA document. |
| `junction` | Survey code, TMC-01 to TMC-06. |
| `junction_chainage_m` | Distance of the junction along the surveyed alignment, metres. |
| `junctions` | Per-junction rows. One entry for each of the six. |
| `junctions_worse` | Junctions where crossing exposure rises under the scheme. |
| `k` | Clusters chosen, by silhouette across k = 2..6. |
| `known_defects` | Defects the audit proved independently of this screen. |
| `label` | Human-readable name. |
| `lane_cap` | Lane capacity tested, PCU per lane. |
| `lane_capacity_pcu` | Lane capacity tested, PCU per lane. |
| `lane_model_applicable` | Whether lane-based capacity describes this stream at all. |
| `lane_width_m` | Assumed lane width, metres. |
| `lanes` | Lanes per direction tested. |
| `lanes_per_dir` | Lanes per direction from the measured width. |
| `lanes_per_direction` | Lanes per direction tested. |
| `lat` | Latitude, EPSG:4326, display only. |
| `layer` | Source CAD layer. |
| `layers` | CAD layers read. |
| `link` | One corridor link, between two consecutive junctions. |
| `links` | The five links between the six junctions, in corridor order. |
| `live` | Whether it can move the binding term here. |
| `location_confidence` | Whether the position is name-matched or inferred. |
| `lon` | Longitude, EPSG:4326. |
| `longest_clear_runs_m` | Longest continuous constraint-free runs, metres. |
| `los` | Level of service. |
| `los_after` | Level of service after relief, on opening. |
| `los_grid` | Level of service for every approach at every rolling hour. |
| `los_hi` | Level of service at vc_hi. |
| `los_pt` | Level of service at vc_pt, IRC bands. F is over capacity. |
| `magnitude` | The larger absolute swing, used to sort the tornado. |
| `mape` | Leave-one-out mean absolute percentage error. |
| `mape_gate` | The threshold a window must clear, matching the count gate. |
| `margin_s` | t_c_optimistic minus t_c_required. Positive means the bay would need a gap SHORTER than we already assume before it could serve the demand. |
| `matrix_pcu` | The same matrix in PCU. |
| `matrix_veh` | Turning-movement matrix in vehicles. |
| `max_pcu_hr` | Highest rolling-hour demand seen on this approach. |
| `max_share` | Highest. |
| `mean_change_pct` | Mean change in crossing exposure across the corridor, %. |
| `mean_delay_min` | Mean delay per arriving vehicle, minutes. |
| `mean_hours_over` | Mean of hours_over across approaches. |
| `mean_residual_pct` | Mean continuity mismatch across links, as a share of flow. |
| `measure` | The alternative. |
| `measured_turning_pct` | The turning share the commissioned survey actually shows. |
| `measurement_status` | That every width here is scaled from CAD linework and provisional pending a total station survey. |
| `median width` | Does the design vehicle physically fit the turning path? |
| `median_gap_m` | Median spacing between openings, metres. |
| `median_openings` | Median gaps found. |
| `merging` | Points where two streams join. |
| `method` | How the figure was produced. |
| `min_share` | Lowest share on any approach. |
| `minutes_to_spillback` | Minutes into the peak before the upstream junction blocks. |
| `mislabelled` | Series whose label does not match the column it reads. |
| `mix_intervals` | Intervals whose class mix departs from the site's own by L1>0.5. |
| `mix_l1` | L1 distance between share vectors that counts as a changed mix. |
| `model` | Which model produced the figure. |
| `most_influential` | Assumption with the largest swing, or null when none swings. |
| `movements` | The twelve arm x turn movements at a junction. |
| `multiple` | Demand multiple by the horizon year. |
| `multiple_comparison_note` | Statement of that, carried with the data. |
| `n` | Count of constraints at that station. |
| `n_approaches` | Approaches clustered: six junctions by four arms. |
| `n_bays` | Bays assessed. |
| `n_corridor` | Corridor approaches. |
| `n_cross` | Cross-street approaches. |
| `n_fail` | Bays failing a criterion. |
| `n_features` | Dimensions in that representation. |
| `n_junctions` | Junctions surveyed. |
| `n_undecided` | Bays with no verdict because a criterion could not be evaluated. |
| `nearest_label` | Nearest text label in the drawing. |
| `nearest_label_m` | Distance to it, metres. |
| `net_grand_total` | Net effect of all discrepancies on the grand total. |
| `net_high_pct` | Net effect at the high end, %. |
| `net_low_pct` | Net effect of correcting every class, low end, %. |
| `next` | Junction after it. |
| `no_gap_vc` | v/c above which no capacity number is reported at all. |
| `no_gap_vc_threshold` | v/c past which no capacity figure is reported. |
| `no_viable_gap` | Approaches where gap acceptance degenerates; no number is quoted. |
| `northbound_in` | Northbound flow arriving at the northern one. |
| `northbound_out` | Northbound flow leaving the southern junction. |
| `northing` | Northing, EPSG:32643. |
| `note` | Free-text qualifier. |
| `observed_vs_planning_ratio` | Counted flow divided by the planning-stage assumption. |
| `of` | Approaches assessed. |
| `ok` | Approaches under capacity in that combination. |
| `one_way_m` | Junction to U-turn bay, metres. |
| `openings` | Median openings found in the survey drawing. |
| `order` | Junction order along the corridor. |
| `order_best` | Best-scoring order from flow continuity. |
| `order_candidates` | Top-scoring orders considered. |
| `order_conclusive` | Whether the margin is large enough to call. |
| `order_cost` | Continuity cost of that order. Lower is better. |
| `order_margin_pct` | Gap to the runner-up, %. Small means inconclusive. |
| `oversaturated_count` | Approaches over capacity at the peak. |
| `overstate` | Discrepancies where it was too high. |
| `p` | Significance level of the test named in the same record. |
| `packing` | Jam packing efficiency tested. |
| `pcu` | PCU correction results. |
| `pcu_band` | [low, high] corrected PCU. |
| `pcu_corrected` | PCU after IRC:106 share-dependent correction. |
| `pcu_hi` | Peak-hour demand with composite classes treated as their heaviest. |
| `pcu_lo` | Peak-hour demand, PCU/hour, composite classes treated as their lightest. |
| `pcu_per_vehicle` | Stream mean, used to convert PCU back to vehicles. |
| `pcu_pt` | Point estimate. Uses the survey's own factors for composite classes. |
| `pcu_surveyed` | PCU as the survey reported it. |
| `pcu_uplift_pct` | PCU uplift tested, %. |
| `peak` | Start of the peak hour, re-derived from 15-minute bins. |
| `peak15` | Busiest 15-minute bin. |
| `peak_delay_min` | Junction delay along the worst direction, minutes. |
| `peak_journey_min` | Through journey time at the peak, worst direction. A floor. |
| `peak_pcu` | Peak-hour demand, PCU/hour. |
| `peak_queue_band` | That peak across the discharge band, low to high. |
| `peak_queue_pcu` | Largest queue on the cumulative curve, in PCU. |
| `peak_start` | As `peak`. |
| `peak_veh` | Peak-hour vehicles. |
| `pedestrian_column_present` | Whether the survey counts pedestrians at all. It does not. |
| `pedestrian_row_filled` | Whether the survey filled it. It did not. |
| `pedestrian_row_in_sp41_table_3_1` | Whether the proforma this survey was written from carries a pedestrian row. It does. |
| `phf` | Peak hour factor: peak hour over four times the busiest 15 minutes. |
| `phf_applied` | Whether a peak hour factor was applied. |
| `pier_radius_m` | Half-footprint used when testing a pier position, metres. |
| `predictable` | Targets predictable from a short count at the gate. |
| `previous` | Junction before this one along the alignment. |
| `profile` | The cluster's mean share vector. |
| `queue` | Spillback count per combination of packing, footprint and lane capacity. |
| `queue_carryover` | Whether queues carrying between hours are modelled. |
| `queue_high` | Queue at the slow discharge - the longer of the pair. |
| `queue_low` | Queue at the fast discharge - the shorter of the pair. |
| `queue_m` | Queue length, metres, by vehicle footprint against the measured width. |
| `queue_model_in_regime` | False once the queue reaches the junction behind it. Past that point the deterministic model is outside the regime where its output means anything. |
| `queue_pcu` | Excess arrivals over the peak hour, PCU. |
| `queue_robust` | Whether spillback survives every combination. |
| `queue_spillback_central` | Spillback count at the CENTRAL assumptions - the cell that reproduces delay.py. Published separately because the grid maximum was being quoted as if it were this. |
| `queue_spillback_max` | Most approaches spilling back. |
| `queue_spillback_min` | Fewest approaches spilling back, across the queue grid. |
| `queue_unconstrained_m` | What the deterministic model returns before the physical cap - published so the magnitude is not hidden, but it is not a queue the link can hold. |
| `queue_vehicles` | That queue converted to vehicles using the observed composition. |
| `radii_note` | That the design-vehicle radii are a policy input, banded, and that the governing IRC clause must be confirmed before design. |
| `rediscovered` | How many of them the screen re-found without being told. |
| `ref_errors` | #REF! errors found in the flow-diagram sheets. |
| `relief` | What an elevated through-carriageway returns to each approach. |
| `residual_pcu` | What remains at grade once the through movement is elevated. |
| `results` | One entry per feature set tested. |
| `right_turn_becomes_uturn` | Whether removed right turns are re-added as U-turns. |
| `road` | Corridor name. |
| `road_source` | Where the road name came from. It was our inference once, and wrong; it is now JDA's, from their KML. |
| `s0_los` | Do-nothing level of service. |
| `s0_vc` | Do-nothing v/c. |
| `s1_serviceable` | Junctions the JDA scheme serves. |
| `s1_uturn_vc_cons` | JDA scheme v/c at the conservative gap. |
| `s1_uturn_vc_opt` | JDA scheme v/c at the optimistic gap. |
| `s1_works` | Whether the JDA scheme serves that junction. |
| `s2_los` | Elevated-option level of service. |
| `s2_vc` | Elevated-option v/c. |
| `s_arith` | Arithmetic detector, normalised. |
| `s_digit` | Terminal-digit detector, on effect size, clipped at 0. |
| `s_duplicate` | Duplicate-day detector, normalised 0 to 1 across the six junctions. |
| `s_flatline` | Flatline detector, normalised. |
| `s_mix` | Composition detector, normalised. |
| `s_spike` | Spike detector, normalised. |
| `saving_min_per_trip` | Delay avoided by a through trip on an elevated carriageway. |
| `scenarios` | Pre-computed cells of the assumption grid the scenario tool walks. |
| `scheme_crossing_exposure` | The same measure under the signal-free scheme, including the U-turn openings the removed right turns move to. |
| `scheme_junction_points` | Conflict points remaining after the right turn is removed. |
| `series` | Movement-class series compared between the two survey days. |
| `series_available` | Per-bin series split into a separate file and fetched on demand. |
| `share` | That class's share of the stream. |
| `share_pct` | That class's share of the stream, %. |
| `shy_distance_m` | Kerb and median clearance deducted, metres. |
| `signal_cluster` | Cluster id this junction was matched to. |
| `signal_data` | Whether the survey contains signal timings. It does not. |
| `signal_heads` | Signal heads counted in that cluster. |
| `silhouette` | Mean silhouette at the chosen k. Higher is tighter separation. |
| `silhouette_by_k` | Silhouette at each k tested. |
| `silhouette_min` | Below this, reported as no typology rather than forced into k groups. |
| `smaller` | Series where it falls short. |
| `source` | Publication the values are taken from. |
| `southbound_in` | Southbound flow arriving at the southern one. |
| `southbound_out` | Southbound flow leaving the northern junction. |
| `speed_flow` | Why a speed-flow diagram is deliberately absent. |
| `spike_bins_per_1000` | Bins per thousand departing from their neighbours' line by both |z|>3.5 and 10+ vehicles. |
| `spike_min_veh` | Vehicles a spike must also differ by, so the detector does not fire on slow classes where the local spread is a vehicle or two. |
| `spike_z` | Modified-z threshold for a spike. |
| `spillback` | True when the queue is longer than the available storage. |
| `spillback_count` | Approaches whose queue exceeds their storage. |
| `start_hour_from_0800` | Window start, hours after the 08:00 survey boundary. |
| `station_step_m` | Spacing between stations, metres. |
| `stations` | As `profile`. |
| `storage` | Does the queue fit the bay without blocking the through lane? |
| `storage_m` | Distance to the junction behind. null at a corridor end. |
| `stored_total_breaks` | Written totals disagreeing with their own components. |
| `structure_found` | Whether the silhouette cleared that threshold. |
| `survey_dates` | Dates as stated in the workbooks. |
| `survey_design` | What the survey design was against IRC:SP:19. |
| `surveyed_factor` | The static PCU factor the survey applied. |
| `surveys_required_by_sp90` | Traffic surveys IRC:SP:90 cl. 5.6 requires. |
| `surveys_run` | How many this programme ran. |
| `swept_allowance_m` | Working allowance either side of the turning path. |
| `swing` | Size of that swing, in approaches. |
| `swing_high_pct` | The same at the IRC:106 high value, %. |
| `swing_low_pct` | Effect on corridor PCU of correcting this class to the IRC:106 low value, %. Negative means the survey overstated it. |
| `t` | Rolling-hour index. |
| `t_c` | Critical gap, seconds - the smallest gap a driver will accept. |
| `t_c_conservative` | The same at the conservative end. |
| `t_c_hi` | Critical gap, conservative. |
| `t_c_lo` | Critical gap, optimistic, seconds. |
| `t_c_optimistic` | Composition-weighted critical gap, optimistic end, seconds. |
| `t_c_required` | The critical gap at which this bay would exactly serve its demand. The question about an unmeasured input is not whether it is right but how wrong it would have to be to change the answer. |
| `t_f` | Follow-up headway, seconds - spacing between successive entering vehicles. |
| `t_hours` | Analysis period, hours. |
| `target` | What is being predicted: the daily total or the peak hour. |
| `targets` | How many targets were tested. |
| `terminal_digit` | Per-junction last-digit test of every count of 10 or more. |
| `terminal_digit_excess_pct` | Percentage points by which digits 0 and 5 exceed the expected 20%. This is what the score uses. |
| `terminal_digit_p` | Chi-square p against a uniform last digit. Rejects on a tiny effect at this sample size, so it is reported, not scored. |
| `through_journey_min_after` | Through journey time once grade separated. |
| `through_pct` | Share of approach traffic going straight through, %. |
| `through_pct_mean` | Mean through share across junctions, %. |
| `through_pct_range` | [min, max] through share, %. |
| `time_space` | Why a time-space diagram is deliberately absent. |
| `to_next_m` | Distance to the next, metres. |
| `to_previous_m` | Distance to the previous junction, metres. |
| `today_crossing_exposure` | Crossing exposure today: the product of each conflicting pair's flows, summed. Meaningful only as a ratio. |
| `today_points` | Conflict points at this junction as built. |
| `total` | Approaches assessed in that combination. |
| `total_delay_pcu_hr` | Delay accumulated over the analysis period, PCU-hours. |
| `total_excess_pcu_day` | Corridor sum of excess_pcu. |
| `transects` | How many cross-sections the width was measured on. Fewer is weaker. |
| `truck` | PCU factor for trucks. |
| `two wheeler` | PCU factor for two-wheelers in the cited document. |
| `two_wheeler_gap_basis` | Source for the two-wheeler critical gap actually used. |
| `two_wheeler_gap_indo_hcm` | Indo-HCM's published base value for the same class. |
| `two_wheeler_gap_ours` | Our optimistic two-wheeler critical gap, seconds. |
| `understate` | Discrepancies where the stored total was too low. |
| `unservable` | Movements out of 12 whose demand exceeds the bay capacity on this basis. |
| `unverified` | Clauses that could not be checked against a primary source. |
| `uplift` | PCU uplift tested, %. |
| `uplift_floor_pct` | Minimum PCU correction, %. The floor, not the estimate. |
| `uplift_pct` | PCU correction for one junction, %. |
| `upstream` | The junction that gets blocked. |
| `uturn_analogue` | Which manoeuvre the U-turn is modelled as. Load-bearing: a merge into the opposing stream needs a smaller gap than a crossing of it. |
| `uturn_crossing_exposure` | The share of that arising at the mid-block U-turn openings. |
| `uturn_demand` | Right-turn demand that becomes a U-turn once signals are removed. |
| `uturn_detour` | Per bay: how much further a converted movement travels, measured from the drawing as junction chainage against the nearest median opening wide enough to turn in, doubled for the return leg. |
| `uturn_per_km` | Those per kilometre. |
| `uturn_possible` | Gaps wide enough to turn in. |
| `uturn_robust` | Whether the U-turn conclusion holds across the whole grid. |
| `uturns` | Per-approach U-turn demand against gap-acceptance bay capacity. |
| `vc` | Volume/capacity used for the queue calculation. |
| `vc_after` | Volume/capacity after relief, on opening. |
| `vc_before` | Volume/capacity today. |
| `vc_conservative` | Demand over conservative capacity. |
| `vc_hi` | Volume/capacity at pcu_hi. |
| `vc_lo` | Volume/capacity at pcu_lo. |
| `vc_optimistic` | Demand over optimistic capacity. |
| `vc_pt` | Volume/capacity at pcu_pt. |
| `veh` | Vehicle count, as counted rather than converted to PCU. |
| `veh_class` | Vehicle class code. |
| `veh_km_per_hour` | Extra vehicle-kilometres this bay generates in the peak hour. |
| `vehicle_class` | The class being compared. |
| `verdict` | fails, viable, or undecided. |
| `volume_flow` | Peak-hour movement volumes for the volume-flow diagram. |
| `vot_status` | That value of time is a policy input, not a measurement. |
| `weave_per_lane_m` | Metres needed to cross one lane after re-entering. |
| `weaving` | Is there room to cross to the left before the next junction? |
| `wholly_identical` | Series identical to the previous day across all live bins. |
| `wide_transect_range_m` | Low and high of the flagged transects, metres per direction. |
| `wide_transect_threshold_m` | That width, per direction, in metres. |
| `wide_transects` | How many measured transects exceed the width above which a service road is a likelier reading than five running lanes. |
| `width_caveat` | Why the widths on the northern junctions should be read as an upper bound: capacity scales linearly with them, and a transect cannot tell a through lane from a service road. |
| `width_m` | Carriageway width, metres, ONE direction. Measured, not assumed. |
| `widths_checked` | Openings whose width was measurable. |
| `windows` | Every window-target combination evaluated. |
| `within_18_20m` | Openings within the IRC:SP:84 18-20 m length rule. |
| `working_days` | [low, high] equivalent working days per year. |
| `works_at_our_optimistic` | Whether this bay serves its demand at our optimistic gap. |
| `worst_approach_pct` | Largest single-approach error. Not selected, so read it. |
| `worst_direction` | Which of southbound/northbound is slower. |
| `worst_residual_pct` | Largest single-link continuity mismatch. |
| `years_to_first_failure` | Years from the base year to design_life_first_failure_med. |
| `zebra_ceiling_pcu_dir` | IRC:103 draft: above this, pedestrian delay passes 45 s and a zebra crossing shall not be provided. |
| `zebra_over` | Approaches above that ceiling. |
| `zebra_total` | Approaches assessed for it. |

## Reading the bands

Several quantities are published as a low/high pair rather than a single number. That is deliberate and it is not uncertainty in the measurement:

- **PCU bands** exist because the survey pools car, taxi, tempo, auto-rickshaw and pickup into one column at one factor. No IRC:106 factor resolves that bucket, so a point estimate would be false precision.
- **Cost bands** exist because value of time is a policy input. The delay is measured; the rate is the authority's to set.
- **Critical gap bands** exist because the values are from literature rather than measured at this corridor. They are Raff-derived and so likely biased high, which makes the U-turn finding conservative.

No band is collapsed to its midpoint anywhere in the outputs.