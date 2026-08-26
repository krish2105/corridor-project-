export type Factor = {
  cls: string; label: string; share: number; surveyed: number;
  irc_low: number; irc_point: number | null; irc_high: number; composite: boolean;
};
export type Junction = {
  code: string; arms: string[]; daily_veh: number; peak_start: string;
  lat: number; lon: number; jda_name: string;
  signal_cluster: string; location_confidence: string;
  peak_veh: number; peak15: number; phf: number; through_pct: number;
  corridor_through_pct: number; pcu_surveyed: number; pcu_corrected: number;
  pcu_band: [number, number]; uplift_pct: number;
  matrix_veh: number[][]; matrix_pcu: number[][];
  composition: { cls: string; label: string; count: number; share: number }[];
  profile: { t: string; v: number }[];
};
export type Criticality = {
  junction: string; jda_name: string;
  daily_veh: number; peak_veh: number; worst_vc: number; uturn_demand: number;
  exposure_change_pct: number; turning_share_pct: number;
  n_daily_veh: number; n_peak_veh: number; n_worst_vc: number; n_uturn_demand: number;
  n_exposure_change_pct: number; n_turning_share_pct: number;
  score: number; rank: number;
};

export type AnomalyScore = {
  junction: string; jda_name: string;
  duplicate_series_share: number; terminal_digit_p: number;
  terminal_digit_excess_pct: number; flatline_series: number;
  spike_bins_per_1000: number; mix_intervals: number; stored_total_breaks: number;
  s_duplicate: number; s_digit: number; s_flatline: number; s_spike: number;
  s_mix: number; s_arith: number; integrity_flag_score: number;
};

export type ClusterResult = {
  feature_set: string; n_features: number; k: number; silhouette: number;
  silhouette_by_k: Record<string, number>; structure_found: boolean;
  external_label: { label: string; held_out: boolean; purity: number; null_mean: number;
                    p: number; permutations: number; recovered: boolean };
  clusters: { cluster: number; size: number; corridor_arms: number; cross_arms: number;
              profile: number[]; features: string[]; members: string[];
              peak_hour?: number; share_in_busiest_4h?: number;
              dominant_class?: string; dominant_share?: number }[];
};

export type ForecastWindow = {
  start_hour_from_0800: number; hours: number; clock: string; target: string;
  mape: number; baseline_mape: number; factor: number; factor_cv: number;
  worst_approach_pct: number;
};

export type BayCheck = { status: string; value: number | null; detail: string };

export type Bay = {
  junction: string; jda_name: string; bay: string; uturn_demand: number;
  verdict: string; binding_criterion: string | null;
  blocked_on: string[]; blocked_if_binding_cleared: string[];
  checks: Record<string, BayCheck>;
  back_solve: {
    conflicting_now: number; demand_now: number; demand_servable: number;
    demand_reduction_pct: number | null; bay_ceiling_veh_hr: number;
    above_bay_ceiling: boolean; gap_needed_s: number; gap_ours_s: number;
    conflicting_needed: number | null; conflicting_reduction_pct: number | null;
    note: string | null;
  } | null;
};

export type Corridor = {
  meta: { corridor: string; road: string; road_source: string; jda_scheme: string;
          city: string; survey_dates: string[];
          analysis_date: string; n_junctions: number; bins_parsed: number; note: string };
  audit: {
    arithmetic: { discrepancies: number; understate: number; overstate: number; net_grand_total: number };
    derived_sheets: { cells_checked: number; exact: number; conclusion: string };
    day2: { series: number; identical: number; greater: number; smaller: number };
    pcu: { factors: Factor[]; uplift_floor_pct: number; band_low_pct: number; band_high_pct: number };
    flow_diagram: { ref_errors: number; files_affected: number; mislabelled: [string, number, string][] };
    survey_design: string[];
  };
  constraints: {
    corridor_km: number; stations: number; pier_radius_m: number;
    hard_free: number; hard_free_pct: number; longest_clear_runs_m: number[];
    totals: Record<string, number>; median_openings: number;
    uturn_possible: number; uturn_per_km: number;
    opening_classes: Record<string, number>;
  } | null;
  capacity: {
    observed_vs_planning_ratio: number; lane_model_applicable?: boolean; horizon_year: number;
    approaches_ok_after_grade_separation: number;
    widths: Record<string, { width_m: number; lanes_per_dir: number; capacity_pcu_hr: number;
                             transects: number }>;
    approaches_over_saturation?: number;
    veh_per_nominal_lane_range?: [number, number];
    saturation_flow_reference?: [number, number];
    two_wheeler_share_pct?: number; lane_model_basis?: string;
    width_caveat?: string; wide_transects?: number; transects_total?: number;
    wide_transect_pct?: number; wide_transect_threshold_m?: number;
    wide_transect_range_m?: [number, number] | null;
    relief: { junction: string; approach: string; through_pct: number; peak_pcu: number;
              residual_pcu: number; vc_before: number; vc_after: number; los_after: string }[];
    growth: { growth_pct: number; multiple: number; binding_need_pcu: number }[];
    assumptions: { base_year: number; design_horizon_years: number;
                   base_capacity_pcu_per_dir: number; base_width_per_dir_m: number;
                   capacity_source: string };
    design_life?: { junction: string; approach: string; vc_after: number;
                    fails_low: number; fails_med: number; fails_high: number }[];
    design_life_first_failure_med?: number;
    design_life_last_failure_med?: number;
    design_life_survives_horizon?: number;
  } | null;
  delay: {
    corridor_km: number; free_flow_min: number; peak_delay_min: number;
    peak_journey_min: number; effective_kmh: number; worst_direction: string;
    direction_delay_min: Record<string, number>;
    assumptions?: { free_flow_kmh?: number; [k: string]: unknown };
    spillback_count: number; oversaturated_count: number; n_approaches: number;
    through_journey_min_after: number; saving_min_per_trip: number;
    approaches: { junction: string; approach: string; vc: number; queue_vehicles: number;
                  queue_m: number; storage_m: number | null; upstream: string | null;
                  spillback: boolean; minutes_to_spillback: number | null;
                  mean_delay_min: number }[];
  } | null;
  economics: {
    annual_cost_crore: number[]; annual_cost_after_crore: number[];
    annual_benefit_crore: number[]; benefit_to_first_failure_crore: number[] | null;
    pcu_per_vehicle: number;
    years_to_first_failure: number | null; mean_hours_over: number;
    delay_veh_hr_day: number; total_excess_pcu_day: number;
    assumptions: { vot_status: string; working_days: number[]; excluded: string[] };
    approaches: { junction: string; approach: string; hours_over: number;
                  excess_pcu: number }[];
  } | null;
  standards: {
    jda_turning_claim_pct: number; measured_turning_pct: number; claim_overstatement: number;
    jmrc_dpr_pcu: Record<string, number>; survey_pcu: Record<string, number>;
    interchange_warrant_pcu: number;
    interchange: { junction: string; corridor_arms_pcu: number; floor_vs_warrant: number }[];
    zebra_ceiling_pcu_dir: number; zebra_over: number; zebra_total: number;
    median: { openings: number; gaps: number; closer_than_500m: number; closest_m: number;
              median_gap_m: number; within_18_20m: number; widths_checked: number };
    surveys_required_by_sp90: number; surveys_run: number;
    pedestrian_row_in_sp41_table_3_1: boolean; pedestrian_row_filled: boolean;
    unverified: string[];
  } | null;
  safety: {
    base_counts: Record<string, number>; base_total: number;
    junctions: { junction: string; jda_name: string; today_points: number;
                 scheme_junction_points: number; today_crossing_exposure: number;
                 scheme_crossing_exposure: number; uturn_crossing_exposure: number;
                 change_pct: number | null }[];
    junctions_worse: number; mean_change_pct: number; pedestrian_column_present: boolean;
  } | null;
  profiles: {
    los_distribution: Record<string, number>; approach_hours_total: number;
    approach_hours_F: number; f_share_pct: number; mean_hours_over: number;
    series_available: string[];
  } | null;
  exhibits: {
    tornado: { base_pcu: number; net_low_pct: number; net_high_pct: number;
               classes: { veh_class: string; share_pct: number; surveyed_factor: number;
                          irc_low: number | null; irc_high: number | null; exact: boolean;
                          swing_low_pct: number; swing_high_pct: number; magnitude: number }[] };
    corridor_order: string[];
    omitted: Record<string, string>;
    series_available: string[];
  } | null;
  scheme: {
    indo_hcm_no_uturn_chapter: string;
    csir_crri_design_gap_s: number;
    csir_crri_design_source: string;
    follow_up_measured_s: number[];
    uturn_detour?: { junction: string; bay: string; demand: number;
      bay_beyond_drawing: boolean; junction_chainage_m?: number; bay_chainage_m?: number;
      one_way_m?: number | null; detour_m?: number | null;
      veh_km_per_hour?: number | null }[];
    detour_min_m?: number; detour_max_m?: number; detour_mean_m?: number;
    detour_mean_typical_m?: number; detour_veh_km_per_hour?: number;
    detour_veh_km_typical?: number; detour_bays_measured?: number;
    detour_bays_beyond_drawing?: number; detour_outliers_excluded?: number;
    detour_bays_at_junction_mouth?: number; detour_bays_midblock?: number;
    detour_midblock_mean_m?: number; detour_midblock_veh_km?: number;
    detour_mouth_mean_m?: number;
    opening_kinds?: { openings: number; junction_mouths: number; midblock: number;
                      midblock_threshold_m: number;
                      mouth_detail: { chainage_m: number; nearest_junction: string;
                                      metres_from_junction: number }[];
                      midblock_detail: { chainage_m: number; nearest_junction: string;
                                         metres_from_junction: number }[] };
    gap_evidence_spread: { label: string; t_c: number; t_f: number; unservable: number;
      no_viable_gap: number; of: number; source: string; geometric_match: string }[];
    gap_conclusion_holds_in: number;
    gap_bases_tested: number;
    uturn_analogue: string;
    gap_direction_note: string;
    two_wheeler_gap_basis: string;
    gap_benchmark?: { junction: string; approach: string; t_c_optimistic: number;
                      t_c_conservative: number; t_c_required: number; margin_s: number;
                      works_at_our_optimistic: boolean }[];
    gap_required_median_s?: number; gap_ours_median_s?: number; gap_margin_s?: number;
    irc_sp41_car_gap_s?: number; gap_source?: string;
    no_gap_vc_threshold: number; fails_conservative: number; fails_optimistic: number;
    no_viable_gap: number; forced_uturns_per_hour: number;
    s1_serviceable: number; n_junctions: number;
    uturns: { junction: string; approach: string; uturn_demand: number;
              conflicting_flow: number; cap_conservative: number;
              vc_conservative: number }[];
    scenarios: { junction: string; jda_name: string; s0_vc: number;
                 s1_uturn_vc_cons: number; s1_works: boolean;
                 s2_vc: number; s2_los: string }[];
  } | null;
  sensitivity: {
    queue?: { packing: number; footprint: number; lane_cap: number;
              spillback: number; total: number }[];
    queue_spillback_min?: number | null; queue_spillback_max?: number | null;
    queue_spillback_central?: number | null;
    combinations_uturn?: number; combinations_elevated?: number;
    combinations_queue?: number;
    queue_robust?: boolean | null;
    combinations: number; uturn_robust: boolean;
    uturn: Record<string, { fails: number; of: number }>;
    elevated_all_pass_combinations: number; elevated_total_combinations: number;
    elevated_worst_ok: number; elevated_worst_of: number;
    most_influential: string | null; swing: number; assumption_driven: boolean;
  } | null;
  criticality: Criticality[];
  measurement: {
    source: string; status: string;
    published_step_m: number; steps_tested: number[]; converged_tolerance_m: number;
    convergence: {
      junction: string; jda_name: string; converged_at_step: number | null;
      spread_m: number | null;
      by_step: { step_m: number; width_m: number | null; transects: number | null }[];
    }[];
    transects_by_step: { step_m: number; transects: number }[];
    bootstrap: {
      junction: string; n: number; median_m: number | null;
      ci_m: [number, number] | null; ci_width_m?: number;
      min_m?: number; max_m?: number; above_wide_threshold?: boolean;
      unquantified?: string;
    }[];
    bootstrap_resamples: number;
    registration: { feature: string; n: number; median_m?: number; p90_m?: number;
                    max_m?: number; unquantified?: string }[];
    dimensions: { dimension: string; used_for: string; method: string;
                  uncertainty: string; resolved_by: string }[];
    junctions_above_wide_threshold: number; wide_threshold_m: number;
  } | null;
  anomaly: {
    method: string; caveat: string;
    thresholds: Record<string, number>;
    detectors: {
      duplicate: { series: number; wholly_identical: number };
      terminal_digit: { junction: string; n: number; chi2: number; p: number;
                        excess_0_5_pct: number }[];
      flatline: { series: number }; spike: { series: number };
      mix: { intervals: number }; arithmetic: { breaks: number };
    };
    junctions: AnomalyScore[];
    gate: { known_defects: number; rediscovered: number };
  } | null;
  cluster: {
    method: string; feature_sets_tested: number; multiple_comparison_note: string;
    silhouette_min: number; n_approaches: number; any_typology_found: boolean;
    results: ClusterResult[];
    two_wheeler_split: { vehicle_class: string; corridor_mean: number; cross_mean: number;
                         n_corridor: number; n_cross: number; p: number;
                         min_share: number; max_share: number } | null;
  } | null;
  forecast: {
    method: string; baseline: string; caveat: string; mape_gate: number;
    n_approaches: number; analysis_days: number;
    selection: { combinations_searched: number; note: string };
    windows: ForecastWindow[];
    shortest_window: Record<string, ForecastWindow | null>;
    gate: { targets: number; predictable: number };
  } | null;
  uturn_framework: {
    method: string; criteria: string[]; n_bays: number; n_fail: number;
    n_undecided: number; measurement_status: string;
    bay_ceiling_veh_hr: number | null; bays_above_bay_ceiling: number;
    binding_counts: Record<string, number>;
    blocked_criteria_now: string[]; blocked_criteria_once_binding_cleared: string[];
    assumptions: Record<string, unknown>;
    bays: Bay[];
    alternatives: { measure: string; cost: string; note: string; live: boolean }[];
  } | null;
  junctions: Junction[];
  corridor: {
    through_pct_mean: number; through_pct_range: [number, number];
    order_best: string[]; order_margin_pct: number; order_conclusive: boolean;
    order_candidates: { cost: number; order: string[] }[];
    links: Record<string, string | number>[];
  };
};
