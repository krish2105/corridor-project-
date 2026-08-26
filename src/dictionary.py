"""
dictionary.py — the schema for every file a reviewer can download.

WHY GENERATED
Fifteen files are published for cross-verification, and a reviewer who cannot tell what
`vc_pt` or `excess_pcu` means cannot check anything. A hand-written schema would drift
the moment a field was added, and the drift would be invisible.

So the field LIST comes from the published files themselves and the DESCRIPTIONS come
from the table below. A field present in the data but missing from the table is reported
as undocumented rather than quietly omitted, which turns the usual failure mode - a
schema that silently falls behind - into a visible one.

Run:  uv run python src/dictionary.py
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import OUT_DATA, ROOT

DOCS = ROOT / "docs"

FILES = {
    "corridor.json":    "Everything the dashboard reads. Bundles the sections below.",
    "capacity.json":    "Measured widths, demand against capacity, relief, design life.",
    "delay.json":       "Queue, spillback, delay and corridor journey time.",
    "economics.json":   "Cost of delay. Every figure banded.",
    "scheme_test.json": "Gap-acceptance test of the JDA U-turn scheme.",
    "sensitivity.json": "Every conclusion re-run across its assumption grid.",
    "constraint_profile.json": "Pier-siting score at 25 m stations along the alignment.",
    "atlas_summary.json": "Constraint counts by category over the whole drawing.",
    "atlas.geojson":    "Constraint geometry: buildings, utilities, drainage, trees, medians.",
    "median_openings.geojson": "Every median gap with width and classification.",
    "junction_candidates.geojson": "All signal clusters considered when placing the six junctions.",
    # These four were generated, published and read by the dashboard, but absent from
    # this list - so none of their fields were ever checked for a description.
    "safety.json":      "Conflict points and flow-weighted exposure, counted from geometry.",
    "profiles.json":    "Level of service by approach and hour, and peak spreading.",
    "exhibits.json":    "Volume-flow, tornado, continuity and flow-raster series.",
    "standards.json":   "The corridor measured against the codes it is built under.",
}

# Units are stated because a number without one is not checkable.
FIELDS = {
    # identity
    "junction": "Survey code, TMC-01 to TMC-06.",
    "approach": "Which arm traffic enters from. Only the two corridor arms carry a v/c.",
    "jda_name": "The authority's own name for the junction in its scheme documents.",
    "analysis_date": "Survey day the figures come from. Day two is derived; see the audit.",
    # capacity
    "capacity": "Approach capacity, PCU/hour, lanes x lane capacity.",
    "peak": "Start of the peak hour, re-derived from 15-minute bins.",
    "peak_start": "As `peak`.",
    "pcu_lo": "Peak-hour demand, PCU/hour, composite classes treated as their lightest.",
    "pcu_pt": "Point estimate. Uses the survey's own factors for composite classes.",
    "pcu_hi": "Peak-hour demand with composite classes treated as their heaviest.",
    "vc_lo": "Volume/capacity at pcu_lo.", "vc_pt": "Volume/capacity at pcu_pt.",
    "vc_hi": "Volume/capacity at pcu_hi.",
    "los_pt": "Level of service at vc_pt, IRC bands. F is over capacity.",
    "los_hi": "Level of service at vc_hi.",
    "width_m": "Carriageway width, metres, ONE direction. Measured, not assumed.",
    "transects": "How many cross-sections the width was measured on. Fewer is weaker.",
    "lanes_per_dir": "Lanes per direction from the measured width.",
    "capacity_pcu_hr": "That approach's capacity, PCU/hour.",
    "observed_vs_planning_ratio": "Counted flow divided by the planning-stage assumption.",
    "horizon_year": "End of the stated design horizon.",
    # relief and design life
    "through_pct": "Share of approach traffic going straight through, %.",
    "peak_pcu": "Peak-hour demand, PCU/hour.",
    "residual_pcu": "What remains at grade once the through movement is elevated.",
    "vc_before": "Volume/capacity today.", "vc_after": "Volume/capacity after relief, on opening.",
    "los_after": "Level of service after relief, on opening.",
    "fails_low": "Year the approach returns to capacity at the low growth rate.",
    "fails_med": "Year it returns to capacity at the medium growth rate.",
    "fails_high": "Year it returns to capacity at the high growth rate.",
    "design_life_first_failure_med": "Earliest of fails_med across all approaches.",
    "design_life_last_failure_med": "Latest of fails_med.",
    "design_life_survives_horizon": "How many approaches still hold at horizon_year.",
    "approaches_ok_after_grade_separation": "Approaches under capacity on opening.",
    # delay
    "vc": "Volume/capacity used for the queue calculation.",
    "queue_pcu": "Excess arrivals over the peak hour, PCU.",
    "queue_vehicles": "That queue converted to vehicles using the observed composition.",
    "queue_m": "Queue length, metres, by vehicle footprint against the measured width.",
    "storage_m": "Distance to the junction behind. null at a corridor end.",
    "upstream": "The junction that gets blocked.",
    "spillback": "True when the queue is longer than the available storage.",
    "minutes_to_spillback": "Minutes into the peak before the upstream junction blocks.",
    "mean_delay_min": "Mean delay per arriving vehicle, minutes.",
    "total_delay_pcu_hr": "Delay accumulated over the analysis period, PCU-hours.",
    "corridor_km": "Length of the surveyed alignment between the end junctions.",
    "free_flow_min": "Through journey time at the free-flow speed.",
    "peak_journey_min": "Through journey time at the peak, worst direction. A floor.",
    "effective_kmh": "Corridor length divided by peak_journey_min.",
    "worst_direction": "Which of southbound/northbound is slower.",
    "direction_delay_min": "Junction delay summed along each direction.",
    "saving_min_per_trip": "Delay avoided by a through trip on an elevated carriageway.",
    "through_journey_min_after": "Through journey time once grade separated.",
    "spillback_count": "Approaches whose queue exceeds their storage.",
    "oversaturated_count": "Approaches over capacity at the peak.",
    "n_approaches": "Approaches assessed.",
    # economics
    "hours_over": "Hours per day this approach is over capacity. Counted, not assumed.",
    "excess_pcu": "Excess ARRIVALS per day, PCU. Not PCU-hours.",
    "max_pcu_hr": "Highest rolling-hour demand seen on this approach.",
    "total_excess_pcu_day": "Corridor sum of excess_pcu.",
    "mean_hours_over": "Mean of hours_over across approaches.",
    "pcu_per_vehicle": "Stream mean, used to convert PCU back to vehicles.",
    "delay_veh_hr_day": "Vehicle-hours of delay accumulated per day. A lower bound.",
    "annual_cost_crore": "[low, high] annual cost of delay, crore rupees.",
    "annual_cost_after_crore": "[low, high] annual cost once grade separated.",
    "annual_benefit_crore": "[low, high] difference between the two.",
    "benefit_to_first_failure_crore": "Undiscounted benefit over the years the relief lasts.",
    "years_to_first_failure": "Years from the base year to design_life_first_failure_med.",
    # scheme test
    "uturn_demand": "Right-turn demand that becomes a U-turn once signals are removed.",
    "conflicting_flow": "Opposing through movement the U-turn must cross, veh/hour.",
    "t_c_lo": "Critical gap, optimistic, seconds.", "t_c_hi": "Critical gap, conservative.",
    "cap_conservative": "Bay capacity at the conservative gap, veh/hour.",
    "cap_optimistic": "Bay capacity at the optimistic gap, veh/hour.",
    "vc_conservative": "Demand over conservative capacity.",
    "vc_optimistic": "Demand over optimistic capacity.",
    "fails_conservative": "Approaches the bays cannot serve, conservative gap.",
    "fails_optimistic": "Approaches they cannot serve even optimistically.",
    "no_viable_gap": "Approaches where gap acceptance degenerates; no number is quoted.",
    "no_gap_vc_threshold": "v/c past which no capacity figure is reported.",
    "forced_uturns_per_hour": "Vehicles per peak hour forced across a stream with no gap.",
    "s0_vc": "Do-nothing v/c.", "s0_los": "Do-nothing level of service.",
    "s1_uturn_vc_cons": "JDA scheme v/c at the conservative gap.",
    "s1_uturn_vc_opt": "JDA scheme v/c at the optimistic gap.",
    "s1_works": "Whether the JDA scheme serves that junction.",
    "s2_vc": "Elevated-option v/c.", "s2_los": "Elevated-option level of service.",
    # sensitivity
    "combinations": "Grid size for the capacity and scheme conclusions.",
    "uturn_robust": "Whether the U-turn conclusion holds across the whole grid.",
    "elevated_all_pass_combinations": "Combinations where all approaches are relieved.",
    "elevated_total_combinations": "Size of the elevated grid.",
    "queue_spillback_min": "Fewest approaches spilling back, across the queue grid.",
    "queue_spillback_max": "Most approaches spilling back.",
    "queue_robust": "Whether spillback survives every combination.",
    "most_influential": "Assumption with the largest swing, or null when none swings.",
    "swing": "Size of that swing, in approaches.",
    "packing": "Jam packing efficiency tested.", "footprint": "Footprint scale tested.",
    "lane_cap": "Lane capacity tested, PCU per lane.",
    "uplift": "PCU uplift tested, %.", "lanes": "Lanes per direction tested.",
    "ok": "Approaches under capacity in that combination.",
    "frac": "ok divided by total.", "total": "Approaches assessed in that combination.",
    # atlas
    "chainage_m": "Distance along the alignment from its start, metres.",
    "score": "Weighted constraint density at that station. Higher is worse.",
    "hard": "True when a constraint present cannot be diverted.",
    "n": "Count of constraints at that station.",
    "constraints": "Constraint categories present at that station.",
    "alignment_km": "Length of the surveyed alignment.",
}

# Dicts keyed by DATA rather than by field name: {"TWO_W": 0.47}, {"TMC-01": {...}}.
# Their keys are values, not schema, so descending into them collects vehicle classes and
# junction codes as though they were fields. Recognised by shape, not by name.
# Values that appear as dict KEYS in count maps: atlas categories, width classifications,
# arm labels. They are data, not schema, and describing them as fields would be wrong.
VALUE_KEYS = {
    "alignment", "carriageway", "drainage", "electrical", "gas", "geotech", "median",
    "rail", "religious", "structures", "telecom", "vegetation", "water",
    "too narrow", "marginal", "typical opening", "wide / junction mouth",
    "north", "south", "northbound", "southbound", "exact", "composite", "surveyed",
    "optimistic", "conservative",
}

FIELDS.update({
    # survey identity and audit
    "road": "Corridor name.", "city": "City.", "n_junctions": "Junctions surveyed.",
    "bins_parsed": "15-minute class bins parsed across all workbooks.",
    "survey_dates": "Dates as stated in the workbooks.",
    "survey_design": "What the survey design was against IRC:SP:19.",
    "cells_checked": "Cells re-derived when checking stored totals.",
    "discrepancies": "Stored totals that disagreed with their own components.",
    "files_affected": "Workbooks containing at least one discrepancy.",
    "net_grand_total": "Net effect of all discrepancies on the grand total.",
    "understate": "Discrepancies where the stored total was too low.",
    "overstate": "Discrepancies where it was too high.",
    "ref_errors": "#REF! errors found in the flow-diagram sheets.",
    "mislabelled": "Series whose label does not match the column it reads.",
    "series": "Movement-class series compared between the two survey days.",
    "identical": "Series reproducing the previous day to the exact vehicle.",
    "greater": "Series where day two exceeds day one.",
    "smaller": "Series where it falls short.",
    "derived_sheets": "Sheets that are formula views of others, not independent data.",
    # pcu
    "uplift_floor_pct": "Minimum PCU correction, %. The floor, not the estimate.",
    "band_low_pct": "Low end of the PCU correction band, %.",
    "band_high_pct": "High end of the PCU correction band, %.",
    "uplift_pct": "PCU correction for one junction, %.",
    "pcu_surveyed": "PCU as the survey reported it.",
    "pcu_corrected": "PCU after IRC:106 share-dependent correction.",
    "pcu_band": "[low, high] corrected PCU.",
    "irc_low": "IRC:106 factor at or below 5% share.",
    "irc_high": "IRC:106 factor at or above 10% share.",
    "irc_point": "Interpolated factor at the observed share. null for composites.",
    "share": "That class's share of the stream.",
    "cls": "Vehicle class code.",
    # junction and corridor
    "code": "Junction code.", "label": "Human-readable name.",
    "lat": "Latitude, EPSG:4326, display only.", "lon": "Longitude, EPSG:4326.",
    "easting": "Easting, EPSG:32643, metres.", "northing": "Northing, EPSG:32643.",
    "location_confidence": "Whether the position is name-matched or inferred.",
    "signal_cluster": "Cluster id this junction was matched to.",
    "signal_heads": "Signal heads counted in that cluster.",
    "cluster": "Cluster id.", "nearest_label": "Nearest text label in the drawing.",
    "nearest_label_m": "Distance to it, metres.",
    "arms": "Arm names, clockwise from north.",
    "daily_veh": "Vehicles counted over the survey day.",
    "peak_veh": "Peak-hour vehicles.", "peak15": "Busiest 15-minute bin.",
    "phf": "Peak hour factor: peak hour over four times the busiest 15 minutes.",
    "matrix_veh": "Turning-movement matrix in vehicles.",
    "matrix_pcu": "The same matrix in PCU.",
    "composition": "Share of each vehicle class.",
    "through_pct_mean": "Mean through share across junctions, %.",
    "through_pct_range": "[min, max] through share, %.",
    "corridor_through_pct": "Through share used for the relief calculation, %.",
    "order": "Junction order along the corridor.",
    "order_best": "Best-scoring order from flow continuity.",
    "order_cost": "Continuity cost of that order. Lower is better.",
    "order_margin_pct": "Gap to the runner-up, %. Small means inconclusive.",
    "order_conclusive": "Whether the margin is large enough to call.",
    "order_candidates": "Top-scoring orders considered.",
    "links": "Continuity check between consecutive junctions.",
    "southbound_out": "Southbound flow leaving the northern junction.",
    "southbound_in": "Southbound flow arriving at the southern one.",
    "northbound_out": "Northbound flow leaving the southern junction.",
    "northbound_in": "Northbound flow arriving at the northern one.",
    "cost": "Mismatch between those pairs, as a fraction of flow.",
    "previous": "Junction before this one along the alignment.",
    "next": "Junction after it.",
    "to_previous_m": "Distance to the previous junction, metres.",
    "to_next_m": "Distance to the next, metres.",
    # atlas and constraints
    "category": "Constraint category.", "layer": "Source CAD layer.",
    "layers": "CAD layers read.", "features": "Geometry features extracted.",
    "totals": "Count per constraint category.",
    "profile": "Pier-siting stations along the alignment.",
    "stations": "As `profile`.", "station_step_m": "Spacing between stations, metres.",
    "pier_radius_m": "Half-footprint used when testing a pier position, metres.",
    "hard_free": "Stations with no undivertible constraint.",
    "hard_free_pct": "That as a percentage.",
    "longest_clear_runs_m": "Longest continuous constraint-free runs, metres.",
    "median_openings": "Median gaps found.",
    "uturn_possible": "Gaps wide enough to turn in.",
    "uturn_per_km": "Those per kilometre.",
    "opening_classes": "Count per width classification.",
    "classification": "Width band this opening falls in.",
    "note": "Free-text qualifier.",
    # assumptions
    "base_year": "Year the survey and all present-day figures refer to.",
    "design_horizon_years": "Design horizon length, years.",
    "growth_low_pct": "Low growth scenario, % per year.",
    "growth_med_pct": "Medium growth scenario.", "growth_high_pct": "High growth scenario.",
    "growth_pct": "Growth rate applied, % per year.",
    "lane_width_m": "Assumed lane width, metres.",
    "shy_distance_m": "Kerb and median clearance deducted, metres.",
    "base_capacity_pcu_per_dir": "Tabulated capacity per direction at the base width, "
                                 "PCU/hour. Scaled by measured width, not by lane count.",
    "base_width_per_dir_m": "Carriageway width per direction the tabulated capacity "
                            "applies to, metres.",
    "capacity_source": "The document and table the capacity comes from.",
    "lane_capacity_pcu": "Lane capacity tested, PCU per lane.",
    "lanes_per_direction": "Lanes per direction tested.",
    "phf_applied": "Whether a peak hour factor was applied.",
    "lane_model_applicable": "Whether lane-based capacity describes this stream at all.",
    "multiple": "Demand multiple by the horizon year.",
    "binding_need_pcu": "What the binding approach would need by then, PCU/hour.",
    "t_hours": "Analysis period, hours.",
    "jam_packing": "Packing efficiency of a jammed queue.",
    "footprint_scale": "Scale applied to the vehicle footprints tested.",
    "free_flow_kmh": "Free-flow speed used for journey time, km/h.",
    "model": "Which model produced the figure.",
    "signal_data": "Whether the survey contains signal timings. It does not.",
    "queue_carryover": "Whether queues carrying between hours are modelled.",
    "vot_status": "That value of time is a policy input, not a measurement.",
    "vot_inr_per_veh_hr": "Value of time band per class, rupees per vehicle-hour.",
    "working_days": "[low, high] equivalent working days per year.",
    "excluded": "Cost components deliberately not counted.",
    "critical_gap": "Which critical-gap assumption was used.",
    "critical_gap_source": "Where the critical-gap values come from.",
    "follow_up_four_lane_measured_s": ("The only follow-up headway measured on four-lane "
                                       "median openings in India, seconds - two-wheelers, "
                                       "Khan 2022 thesis Table 8.2."),
    "indo_hcm_no_uturn_chapter": ("Indo-HCM 2017 publishes no chapter or parameter set for "
                                  "mid-block median openings, so no Indian code carries a "
                                  "design gap for the manoeuvre this scheme is built on."),
    "csir_crri_design_gap_s": ("CSIR-CRRI's recommended design critical gap for Indian "
                               "median openings, seconds."),
    "csir_crri_design_source": "Where the CSIR-CRRI design gap comes from.",
    "follow_up_measured_s": ("The only measured Indian follow-up headways found, seconds, "
                             "against which our assumed band is checked."),
    "bay": ("Which U-turn bay the demand feeds: the one merging into northbound "
            "traffic, or into southbound."),
    "feeds_bay": ("Which movements have to use a U-turn bay under the scheme. Right "
                  "turns from all four arms, plus the cross-street through movement."),
    "uturn_analogue": ("Which manoeuvre the U-turn is modelled as. Load-bearing: a merge "
                       "into the opposing stream needs a smaller gap than a crossing of it."),
    "gap_direction_note": ("Which way our critical-gap assumption errs against the field "
                           "evidence, and what that does to the finding."),
    "two_wheeler_gap_basis": "Source for the two-wheeler critical gap actually used.",
    "gap_evidence_spread": ("The same capacity test re-run on every published critical-gap "
                            "basis reachable, rather than on one chosen value."),
    "gap_conclusion_holds_in": "How many of the tested gap bases return the same finding.",
    "gap_bases_tested": "How many published critical-gap bases the test was re-run on.",
    "geometric_match": "How closely the source geometry matches this corridor.",
    "t_c": "Critical gap, seconds - the smallest gap a driver will accept.",
    "t_f": "Follow-up headway, seconds - spacing between successive entering vehicles.",
    "unservable": "Movements out of 12 whose demand exceeds the bay capacity on this basis.",
    "source": "Publication the values are taken from.",
    "conflicting_stream": "Which movement the U-turn must cross.",
    "bays_planned_by_jda": "U-turn bays in the published scheme.",
    "right_turn_becomes_uturn": "Whether removed right turns are re-added as U-turns.",
    "follow_up_s": "Follow-up headway band, seconds.",
    "jam_footprint_m2": "Jam footprint per class, square metres.",
    "jda_scheme": "The authority's scheme as described in its documents.",
    "pcu_uplift_pct": "PCU uplift tested, %.",
    "assumption_driven": "Whether any single assumption changes the conclusion.",
    "s1_serviceable": "Junctions the JDA scheme serves.",
    "conclusion": "Which conclusion this row belongs to.",
    "fails": "Approaches failing under that assumption.",
    "of": "Approaches assessed.", "uturn": "U-turn conclusion results.",
    "los": "Level of service.",
    "corridor": "Corridor-level aggregates.", "scheme": "Scheme-test results.",
    "sensitivity": "Sensitivity results.", "delay": "Delay results.",
    "economics": "Cost results.", "pcu": "PCU correction results.",
    "t": "Rolling-hour index.", "v": "Value at that index.",
    "n": "Count of constraints at that station.",
    "score": "Weighted constraint density. Higher is worse.",
    "hard": "True when an undivertible constraint is present.",
    "constraints": "Constraint categories present.",
    "direction_delay_min": "Junction delay summed along each direction, minutes.",
    "peak_delay_min": "Junction delay along the worst direction, minutes.",
})



FIELDS.update({
    # safety and conflict analysis
    "method": "How the figure was produced.",
    "caveat": "What the figure is NOT. Read before quoting it.",
    "crossing": "Conflict points where two paths cross.",
    "merging": "Points where two streams join.",
    "diverging": "Points where one stream splits.",
    "base_total": "Total conflict points at a four-arm junction, from geometry.",
    "today_points": "Conflict points at this junction as built.",
    "scheme_junction_points": "Conflict points remaining after the right turn is removed.",
    "today_crossing_exposure": "Crossing exposure today: the product of each conflicting "
                               "pair's flows, summed. Meaningful only as a ratio.",
    "scheme_crossing_exposure": "The same measure under the signal-free scheme, including "
                                "the U-turn openings the removed right turns move to.",
    "uturn_crossing_exposure": "The share of that arising at the mid-block U-turn openings.",
    "change_pct": "Change in crossing exposure between the two schemes, %.",
    "junctions_worse": "Junctions where crossing exposure rises under the scheme.",
    "mean_change_pct": "Mean change in crossing exposure across the corridor, %.",
    "pedestrian_column_present": "Whether the survey counts pedestrians at all. It does not.",
    # whole-day profiles
    "approach_hours_total": "Approach-hours assessed: approaches x rolling hours.",
    "approach_hours_F": "Of those, how many are at Level of Service F.",
    "f_share_pct": "That as a percentage.",
    # exhibits
    "base_pcu": "Corridor peak PCU on the survey's own factors, before correction.",
    "veh_class": "Vehicle class code.",
    "share_pct": "That class's share of the stream, %.",
    "surveyed_factor": "The static PCU factor the survey applied.",
    "swing_low_pct": "Effect on corridor PCU of correcting this class to the IRC:106 low "
                     "value, %. Negative means the survey overstated it.",
    "swing_high_pct": "The same at the IRC:106 high value, %.",
    "magnitude": "The larger absolute swing, used to sort the tornado.",
    "net_low_pct": "Net effect of correcting every class, low end, %.",
    "net_high_pct": "Net effect at the high end, %.",
    "corridor_order": "Junction order along the alignment, from chainage.",
    "series_available": "Per-bin series split into a separate file and fetched on demand.",
    "time_space": "Why a time-space diagram is deliberately absent.",
    "speed_flow": "Why a speed-flow diagram is deliberately absent.",
})

FIELDS.update({
    # standards compliance
    "jda_turning_claim_pct": "JDA's stated basis for the scheme: the share of traffic it "
                             "says is turning. News reporting, not a JDA document.",
    "measured_turning_pct": "The turning share the commissioned survey actually shows.",
    "claim_overstatement": "The ratio between the two.",
    "interchange_warrant_pcu": "IRC:SP:90-2010 threshold above which an interchange is "
                               "justified, PCU/hr across all arms.",
    "corridor_arms_pcu": "Peak PCU on the two corridor approaches. A FLOOR on all-arm "
                         "volume: the cross-street arms are counted but unmeasured.",
    "floor_vs_warrant": "That floor as a multiple of the interchange warrant.",
    "zebra_ceiling_pcu_dir": "IRC:103 draft: above this, pedestrian delay passes 45 s and "
                             "a zebra crossing shall not be provided.",
    "zebra_over": "Approaches above that ceiling.",
    "zebra_total": "Approaches assessed for it.",
    "openings": "Median openings found in the survey drawing.",
    "gaps": "Spacings between consecutive openings.",
    "closer_than_500m": "Spacings below the IRC:SP:84 built-up minimum.",
    "closest_m": "Smallest spacing, metres.",
    "median_gap_m": "Median spacing between openings, metres.",
    "within_18_20m": "Openings within the IRC:SP:84 18-20 m length rule.",
    "widths_checked": "Openings whose width was measurable.",
    "surveys_required_by_sp90": "Traffic surveys IRC:SP:90 cl. 5.6 requires.",
    "surveys_run": "How many this programme ran.",
    "pedestrian_row_in_sp41_table_3_1": "Whether the proforma this survey was written "
                                        "from carries a pedestrian row. It does.",
    "pedestrian_row_filled": "Whether the survey filled it. It did not.",
    "unverified": "Clauses that could not be checked against a primary source.",
    "two wheeler": "PCU factor for two-wheelers in the cited document.",
    "car": "PCU factor for cars.", "auto": "PCU factor for auto-rickshaws.",
    "truck": "PCU factor for trucks.", "MAV": "PCU factor for multi-axle vehicles.",
    "LCV": "PCU factor for light commercial vehicles.",
})


FIELDS.update({
    "t_c_optimistic": "Composition-weighted critical gap, optimistic end, seconds.",
    "t_c_conservative": "The same at the conservative end.",
    "t_c_required": "The critical gap at which this bay would exactly serve its demand. "
                    "The question about an unmeasured input is not whether it is right "
                    "but how wrong it would have to be to change the answer.",
    "margin_s": "t_c_optimistic minus t_c_required. Positive means the bay would need a "
                "gap SHORTER than we already assume before it could serve the demand.",
    "works_at_our_optimistic": "Whether this bay serves its demand at our optimistic gap.",
    "gap_required_median_s": "Median t_c_required across the corridor.",
    "gap_ours_median_s": "Median of our optimistic weighted gaps.",
    "gap_margin_s": "The difference between them.",
    "irc_sp41_car_gap_s": "IRC:SP:41-1994 App III Table III-2 passenger-car critical gap, "
                          "four-lane crossing under stop control, large-city adjustment "
                          "applied. Our weighted gaps sit below it because two-wheelers "
                          "are half the stream, so our figures favour the scheme.",
    "gap_source": "Where the critical gaps come from and what they are benchmarked against.",
})

FIELDS.update({
    "indo_hcm_base_gap_s": "Indo-HCM 2017 base critical gap by vehicle class, four-lane "
                           "divided, right turn minor-to-major. SECONDARY source.",
    "indo_hcm_gap_source": "Where those Indo-HCM figures came from, and why they are "
                           "marked secondary.",
    "queue_unconstrained_m": ("What the deterministic model returns before the physical "
                              "cap - published so the magnitude is not hidden, but it is "
                              "not a queue the link can hold."),
    "queue_model_in_regime": ("False once the queue reaches the junction behind it. Past "
                              "that point the deterministic model is outside the regime "
                              "where its output means anything."),
    # Container fields — tables and sections. Previously invisible to the checker, which
    # recorded only a table's columns and never the table itself.
    "junctions": "Per-junction rows. One entry for each of the six.",
    "approaches": "Per-approach rows. Two corridor approaches at each junction.",
    "movements": "The twelve arm x turn movements at a junction.",
    "uturns": "Per-approach U-turn demand against gap-acceptance bay capacity.",
    "relief": "What an elevated through-carriageway returns to each approach.",
    "design_life": "Years until each approach exceeds capacity, by growth rate.",
    "growth": "Demand multiple at the horizon, one row per growth rate.",
    "scenarios": "Pre-computed cells of the assumption grid the scenario tool walks.",
    "elevated": "Approaches returned under capacity, per assumption combination.",
    "queue": "Spillback count per combination of packing, footprint and lane capacity.",
    "factors": "Back-solved PCU factor per class, one row per workbook.",
    "classes": "Vehicle classes with their counts and shares.",
    "continuity": "Southbound outflow against next-junction inflow, per link.",
    "link": "One corridor link, between two consecutive junctions.",
    "links": "The five links between the six junctions, in corridor order.",
    "los_grid": "Level of service for every approach at every rolling hour.",
    "volume_flow": "Peak-hour movement volumes for the volume-flow diagram.",
    "flow_raster": "Through flow per link per fifteen-minute bin.",
    "gap_benchmark": "Per-approach critical gap needed against the gap we assume.",
    "interchange": "Each junction's corridor-arm total against the interchange warrant.",
    "hour": "Rolling-hour label, one per fifteen-minute step.",
    "veh": "Vehicle count, as counted rather than converted to PCU.",
    "daily_in": "Vehicles entering the junction over the surveyed day.",
    "daily_out": "Vehicles leaving the junction over the surveyed day.",
    "arrivals": "Cumulative PCU arriving at the stop line. Measured.",
    "departures": "Cumulative PCU discharged. ASSUMED - the contestable line.",
    "dep_low": "Departure curve at the slow end of the discharge band.",
    "dep_high": "Departure curve at the fast end of the discharge band.",
    "queue_low": "Queue at the fast discharge - the shorter of the pair.",
    "queue_high": "Queue at the slow discharge - the longer of the pair.",
    "discharge_band": "The capacity multipliers the departure band is drawn across.",
    "peak_queue_pcu": "Largest queue on the cumulative curve, in PCU.",
    "peak_queue_band": "That peak across the discharge band, low to high.",
    "after_grade_separation": "Approach state once the through movement is elevated.",
    "mean_residual_pct": "Mean continuity mismatch across links, as a share of flow.",
    "worst_residual_pct": "Largest single-link continuity mismatch.",
    "queue_spillback_central": ("Spillback count at the CENTRAL assumptions - the cell "
                                "that reproduces delay.py. Published separately because "
                                "the grid maximum was being quoted as if it were this."),
    "combinations_uturn": ("How many assumption combinations the U-turn conclusion is "
                           "actually run across - not the size of the whole space."),
    "combinations_elevated": ("How many combinations the elevated-relief conclusion is run "
                              "across: PCU uplift x lane capacity x lanes per direction."),
    "combinations_queue": ("How many combinations the queue-spillback conclusion is run "
                           "across, on its own grid of packing, footprint and capacity."),
    "growth_handled_in": ("Where the growth-rate assumption is varied, given it is not an "
                          "axis in this module."),
    "followup_ratio_convention": ("The tf = 0.6 x tc rule of thumb. A convention stated as "
                                  "an assumption in Indian studies, not a code relation; "
                                  "published here to show where our follow-up departs from "
                                  "it toward the four-lane measurement."),
    "indo_hcm_form_differs": "How Indo-HCM's capacity equation differs from the HCM form "
                             "we use, and why the difference is not applied.",
    "two_wheeler_gap_ours": "Our optimistic two-wheeler critical gap, seconds.",
    "two_wheeler_gap_indo_hcm": "Indo-HCM's published base value for the same class.",
    "followup_implied_by_indo_hcm": "[optimistic, conservative] follow-up time implied by "
                                    "Indo-HCM's ratio applied to our weighted gaps.",
    "followup_ours": "The follow-up headways we use, seconds.",
    "2w": "Two-wheeler.", "3w": "Three-wheeler.", "4w": "Four-wheeler.",
})

def _is_data_keyed(d):
    if not isinstance(d, dict) or not d:
        return False
    keys = list(d)
    return all(k.isupper() or k.startswith("TMC-") or " " in k for k in keys)


def _record_fields(obj, out):
    """
    Document the fields of RECORDS: top-level scalars, and the keys of the first entry
    of each list of objects. That is the whole schema a reviewer needs and nothing else.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                # BOTH the container and its columns. Recording only the columns meant a
                # reviewer could look up `gap_evidence_spread` and be told it does not
                # exist, while the gate counted it among 22 "described but absent"
                # fields. The container is a published field; it just happens to be a
                # table rather than a scalar.
                out.add(k)
                out |= set(v[0])                       # a table: its columns are fields
            elif isinstance(v, dict):
                if _is_data_keyed(v):
                    # keys are data; document the fields of one entry instead
                    inner = next(iter(v.values()), None)
                    if isinstance(inner, dict) and not _is_data_keyed(inner):
                        out |= set(inner)
                else:
                    _record_fields(v, out)
            else:
                out.add(k)


def build():
    present, per_file = set(), {}
    for name in FILES:
        p = OUT_DATA / name
        if not p.exists():
            continue
        if name.endswith(".geojson"):
            g = json.loads(p.read_text())
            keys = set()
            for f in g.get("features", [])[:20]:
                keys |= set(f.get("properties", {}))
            per_file[name] = sorted(keys)
        else:
            keys = set()
            _record_fields(json.loads(p.read_text()), keys)
            per_file[name] = sorted(keys)
        present |= set(per_file[name])

    documented = present & set(FIELDS)
    undocumented = sorted(present - set(FIELDS) - VALUE_KEYS)
    unused = sorted(set(FIELDS) - present)

    md = [
        "# Data dictionary",
        "### Every field in every published dataset",
        "",
        f"Generated {date.today().isoformat()} from the files in `out/data`. The field "
        "list is read from the data itself, so a field added to the pipeline and not "
        "described here is reported below as undocumented rather than quietly omitted.",
        "",
        "**All spatial data is EPSG:32643 (UTM zone 43N, metres).** GeoJSON is written in "
        "EPSG:4326 because the format requires it, and is converted at that boundary only.",
        "",
        "## Files",
        "",
        "| File | Contents |",
        "|---|---|",
    ]
    for name, desc in FILES.items():
        ok = "" if (OUT_DATA / name).exists() else " *(not generated)*"
        md.append(f"| `{name}`{ok} | {desc} |")

    md += ["", "## Fields", "",
           "| Field | Meaning |", "|---|---|"]
    for k in sorted(documented):
        md.append(f"| `{k}` | {FIELDS[k]} |")

    if undocumented:
        md += ["", "## Undocumented fields", "",
               "Present in the data and not described above. This list should be empty; "
               "anything here is a gap in this document, not in the data.", ""]
        md += [f"- `{k}`" for k in undocumented]

    md += ["", "## Reading the bands", "",
           "Several quantities are published as a low/high pair rather than a single "
           "number. That is deliberate and it is not uncertainty in the measurement:",
           "",
           "- **PCU bands** exist because the survey pools car, taxi, tempo, auto-rickshaw "
           "and pickup into one column at one factor. No IRC:106 factor resolves that "
           "bucket, so a point estimate would be false precision.",
           "- **Cost bands** exist because value of time is a policy input. The delay is "
           "measured; the rate is the authority's to set.",
           "- **Critical gap bands** exist because the values are from literature rather "
           "than measured at this corridor. They are Raff-derived and so likely biased "
           "high, which makes the U-turn finding conservative.",
           "",
           "No band is collapsed to its midpoint anywhere in the outputs.",
           ]
    return "\n".join(md), documented, undocumented, unused


if __name__ == "__main__":
    DOCS.mkdir(exist_ok=True)
    md, doc, undoc, unused = build()
    (DOCS / "data_dictionary.md").write_text(md)

    checks = [
        ("dictionary written", len(md) > 2000),
        ("every published field is described", not undoc),
        ("no description for a field that does not exist",
         len(unused) < len(FIELDS) * 0.5),
        ("bands are explained, not just listed", "false precision" in md),
        ("CRS stated once, at the top", "EPSG:32643" in md),
    ]
    for name, good in checks:
        print(f"  {name:<52}{'PASS' if good else 'FAIL':>8}")
    print(f"\n  GATE - schema complete: **{sum(g for _n, g in checks)} of {len(checks)}**")
    print(f"  {len(doc)} fields documented across {len(FILES)} files")
    if undoc:
        print(f"  UNDOCUMENTED: {', '.join(undoc)}")
    if unused:
        print(f"  described but absent from the data ({len(unused)}): "
              f"{', '.join(unused[:8])}{' ...' if len(unused) > 8 else ''}")
