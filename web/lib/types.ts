export type Factor = {
  cls: string; label: string; share: number; surveyed: number;
  irc_low: number; irc_point: number | null; irc_high: number; composite: boolean;
};
export type Junction = {
  code: string; arms: string[]; daily_veh: number; peak_start: string;
  peak_veh: number; peak15: number; phf: number; through_pct: number;
  corridor_through_pct: number; pcu_surveyed: number; pcu_corrected: number;
  pcu_band: [number, number]; uplift_pct: number;
  matrix_veh: number[][]; matrix_pcu: number[][];
  composition: { cls: string; label: string; count: number; share: number }[];
  profile: { t: string; v: number }[];
};
export type Corridor = {
  meta: { corridor: string; city: string; survey_dates: string[];
          analysis_date: string; n_junctions: number; bins_parsed: number; note: string };
  audit: {
    arithmetic: { discrepancies: number; understate: number; overstate: number; net_grand_total: number };
    derived_sheets: { cells_checked: number; exact: number; conclusion: string };
    day2: { series: number; identical: number; greater: number; smaller: number };
    pcu: { factors: Factor[]; uplift_floor_pct: number; band_low_pct: number; band_high_pct: number };
    flow_diagram: { ref_errors: number; files_affected: number; mislabelled: [string, number, string][] };
    survey_design: string[];
  };
  junctions: Junction[];
  corridor: {
    through_pct_mean: number; through_pct_range: [number, number];
    order_best: string[]; order_margin_pct: number; order_conclusive: boolean;
    order_candidates: { cost: number; order: string[] }[];
    links: Record<string, string | number>[];
  };
};
