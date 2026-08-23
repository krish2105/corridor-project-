"use client";

/**
 * The corridor measured against the codes that govern it.
 *
 * The strongest item here is not our finding. JDA states the scheme's basis as roughly
 * half of all traffic being turning movements; the survey JDA commissioned says 29.6%.
 * And the PCU correction this audit makes is already made, in the same numbers, inside
 * another Rajasthan government transport document.
 */
type S = {
  jda_turning_claim_pct: number; measured_turning_pct: number; claim_overstatement: number;
  jmrc_dpr_pcu: Record<string, number>; survey_pcu: Record<string, number>;
  interchange_warrant_pcu: number;
  interchange: { junction: string; corridor_arms_pcu: number; floor_vs_warrant: number }[];
  zebra_ceiling_pcu_dir: number; zebra_over: number; zebra_total: number;
  median: { openings: number; gaps: number; closer_than_500m: number; closest_m: number;
            median_gap_m: number; within_18_20m: number };
  surveys_required_by_sp90: number; surveys_run: number;
  pedestrian_row_in_sp41_table_3_1: boolean; pedestrian_row_filled: boolean;
  unverified: string[];
};
const nf = new Intl.NumberFormat("en-US");

export default function Standards({ s }: { s: S }) {
  return (
    <div className="stack">
      <div className="card">
        <header>
          <h3>JDA&rsquo;s stated basis, against the survey JDA commissioned</h3>
          <span className="chip critical">{s.claim_overstatement}&times; overstated</span>
        </header>
        <div className="body">
          <div className="scope">
            <div><span className="k num" style={{ color: "var(--defect)" }}>
              {s.jda_turning_claim_pct}%</span><span className="l">JDA: traffic that is turning</span></div>
            <div><span className="k num">{s.measured_turning_pct}%</span>
              <span className="l">the survey&rsquo;s own figure</span></div>
            <div><span className="k num" style={{ color: "var(--ok)" }}>
              {(100 - s.measured_turning_pct).toFixed(1)}%</span>
              <span className="l">going straight through</span></div>
          </div>
          <p className="col">The scheme is built to serve turning traffic. Seven in ten
          vehicles on this corridor are not turning &mdash; which is the case for taking
          the through movement out of the junctions, and against a scheme that reorganises
          them around the minority movement.</p>
          <p className="src">The 50% figure is news reporting of a JDA statement
          (Patrika, 7 April 2026), not a JDA document. We could find no published DPR,
          board resolution or cost breakdown for the scheme.</p>
        </div>
      </div>

      <div className="card">
        <header>
          <h3>The PCU correction, already made inside the state government</h3>
          <span className="chip fixed">corroborated</span>
        </header>
        <div className="body">
          <div className="tscroll">
            <table>
              <thead><tr><th>Class</th>
                <th className="num">This survey</th>
                <th className="num">JMRC Phase-II DPR</th>
                <th className="num">Our correction</th></tr></thead>
              <tbody>
                <tr><td>Two-wheeler</td>
                  <td className="num bad">{s.survey_pcu["two wheeler"]}</td>
                  <td className="num good">{s.jmrc_dpr_pcu["two wheeler"]}</td>
                  <td className="num good">{s.jmrc_dpr_pcu["two wheeler"]}</td></tr>
                <tr><td>Multi-axle</td>
                  <td className="num bad">{s.survey_pcu["MAV"]}</td>
                  <td className="num good">{s.jmrc_dpr_pcu["MAV"]}</td>
                  <td className="num good">{s.jmrc_dpr_pcu["MAV"]}</td></tr>
              </tbody>
            </table>
          </div>
          <p className="col"><strong>The Jaipur Metro Phase-II DPR of March 2012 uses
          exactly the two values this audit corrects the survey to</strong>, and cites
          IRC:106 for them. Another Rajasthan government transport document had already
          settled the question. The correction is not our interpretation of the standard.</p>
        </div>
      </div>

      <div className="card">
        <header><h3>Measured against the code</h3></header>
        <div className="body">
          <div className="tscroll">
            <table>
              <thead><tr><th>Clause</th><th>Requirement</th><th className="num">This corridor</th></tr></thead>
              <tbody>
                <tr>
                  <td>IRC:103 draft</td>
                  <td>Zebra crossing not provided above ~{nf.format(s.zebra_ceiling_pcu_dir)} PCU/h/dir</td>
                  <td className="num bad">{s.zebra_over} of {s.zebra_total} approaches over</td>
                </tr>
                <tr>
                  <td>IRC:SP:84 cl. 2.14.1</td>
                  <td>Median openings &ge; 500 m apart in built-up areas</td>
                  <td className="num bad">{s.median.closer_than_500m} of {s.median.gaps} closer</td>
                </tr>
                <tr>
                  <td>IRC:SP:84 cl. 2.14.4</td>
                  <td>Median opening length 18&ndash;20 m</td>
                  <td className="num bad">{s.median.within_18_20m} of {s.median.openings} within</td>
                </tr>
                <tr>
                  <td>IRC:SP:90 cl. 5.6</td>
                  <td>Seven traffic surveys required to justify a grade separator</td>
                  <td className="num bad">{s.surveys_run} of {s.surveys_required_by_sp90} run</td>
                </tr>
                <tr>
                  <td>IRC:SP:41 Table 3.1</td>
                  <td>Pedestrian row in the survey proforma</td>
                  <td className="num bad">present, left empty</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="col"><strong>The survey&rsquo;s ten-column class scheme is
          IRC:SP:41 Table 3.1.</strong> That is the standard proforma for an intersection
          survey, and its static PCU factors are defensible as a starting point. The same
          table carries a <strong>PEDESTRIAN Nos.</strong> row, which clause 3.1(iv)
          requires where pedestrian movement is substantial. It was left empty. That is a
          clause-level omission, not a matter of judgement.</p>

          <p className="col" style={{ borderLeft: "3px solid var(--accent)", paddingLeft: ".9rem" }}>
            <strong>The seven-survey gap cuts both ways, and is reported both ways.</strong>{" "}
            IRC:SP:90 cl. 5.6.7 makes an intersection volume-delay survey a <em>must</em>{" "}
            for justifying a grade separator. It was never done &mdash; which is a gap in
            the evidence base for any grade separation here, including the one we argue
            for.
          </p>

          <p className="src"><strong>Not fully verified:</strong> {s.unverified.join("; ")}.</p>
        </div>
      </div>
    </div>
  );
}
