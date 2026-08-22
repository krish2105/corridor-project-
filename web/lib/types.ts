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
export type Corridor = {
  meta: { corridor: string; road: string; jda_scheme: string; city: string; survey_dates: string[];
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
    observed_vs_planning_ratio: number; horizon_year: number;
    approaches_ok_after_grade_separation: number;
    widths: Record<string, { width_m: number; lanes_per_dir: number; capacity_pcu_hr: number }>;
    relief: { junction: string; approach: string; through_pct: number; peak_pcu: number;
              residual_pcu: number; vc_before: number; vc_after: number; los_after: string }[];
    growth: { growth_pct: number; multiple: number; binding_need_pcu: number }[];
  } | null;
  scheme: {
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
    combinations: number; uturn_robust: boolean;
    uturn: Record<string, { fails: number; of: number }>;
    elevated_all_pass_combinations: number; elevated_total_combinations: number;
    most_influential: string | null; swing: number; assumption_driven: boolean;
  } | null;
  junctions: Junction[];
  corridor: {
    through_pct_mean: number; through_pct_range: [number, number];
    order_best: string[]; order_margin_pct: number; order_conclusive: boolean;
    order_candidates: { cost: number; order: string[] }[];
    links: Record<string, string | number>[];
  };
};
