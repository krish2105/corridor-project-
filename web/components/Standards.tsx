"use client";
import Evidence from "./Evidence";

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

type Gap = {
  gap_benchmark?: { junction: string; scheme_no: number; scheme_label: string;
                    approach: string; t_c_optimistic: number;
                    t_c_required: number; margin_s: number; works_at_our_optimistic: boolean }[];
  gap_required_median_s?: number; gap_ours_median_s?: number; gap_margin_s?: number;
  irc_sp41_car_gap_s?: number;
};

export default function Standards({ s, gap }: { s: S; gap?: Gap }) {
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
          <Evidence
            label="How the turning share was measured"
            rows={[
              { k: "JDA's stated figure", v: `${s.jda_turning_claim_pct}%`, tone: "bad",
                note: "attributed to a JDA statement in news reporting, not a JDA document" },
              { k: "measured from the survey", v: `${s.measured_turning_pct}%`,
                note: "left plus right, as a share of all movements, across all six junctions" },
              { k: "overstatement", v: `${s.claim_overstatement}x`, tone: "bad" },
              { k: "going straight through", v: `${(100 - s.measured_turning_pct).toFixed(1)}%`,
                tone: "ok", note: "the movement the scheme does not serve" },
            ]}
            source={"Measured in src/analyse.py from the twelve movement sheets per " +
                    "junction - the same survey JDA commissioned. We hold no DPR, board " +
                    "resolution or cost breakdown for the scheme, so the 50% is compared " +
                    "as reported rather than as sourced."} />
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

      {gap?.gap_benchmark && (
        <div className="card">
          <header>
            <h3>The critical gap, benchmarked against the code</h3>
            <span className="tag">{gap.gap_margin_s}s margin</span>
          </header>
          <div className="body">
            <p className="col">The critical gap is the one input we did not measure, so
            the useful question is not whether it is right but <strong>how wrong it would
            have to be to change the answer</strong>. A lower gap means more bay capacity,
            which favours the scheme.</p>

            <div className="scope">
              <div><span className="k num">{gap.gap_ours_median_s}s</span>
                <span className="l">our weighted gap, optimistic</span></div>
              <div><span className="k num" style={{ color: "var(--defect)" }}>
                {gap.gap_required_median_s}s</span>
                <span className="l">needed for the bays to work</span></div>
              {/* Same rule as the rows below. This tile was hardcoded green while the
                  table coloured the identical quantity red, because a POSITIVE margin is
                  bad: it means the approach needs a gap shorter than we already assume
                  before its bay could serve the demand. The summary was contradicting
                  the detail directly beneath it. */}
              <div><span className="k num"
                        style={{ color: (gap.gap_margin_s ?? 0) > 0 ? "var(--defect)" : "var(--ok)" }}>
                {(gap.gap_margin_s ?? 0) > 0 ? "+" : ""}{gap.gap_margin_s}s</span>
                <span className="l">margin &mdash; positive means the bay cannot work</span></div>
              <div><span className="k num">{gap.irc_sp41_car_gap_s}s</span>
                <span className="l">IRC:SP:41 passenger car</span></div>
            </div>

            <div className="tscroll">
              <table>
                <thead><tr><th>Junction</th><th>Approach</th>
                  <th className="num">Ours</th><th className="num">Needed</th>
                  <th className="num">Margin</th></tr></thead>
                <tbody>
                  {gap.gap_benchmark.map((r, i) => (
                    <tr key={i}>
                      <td className="mono">{r.scheme_label}</td><td>{r.approach}</td>
                      <td className="num">{r.t_c_optimistic.toFixed(2)}</td>
                      <td className="num">{r.t_c_required.toFixed(2)}</td>
                      <td className={"num " + (r.margin_s > 0 ? "bad" : "good")}>
                        {r.margin_s > 0 ? "+" : ""}{r.margin_s.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="col" style={{ borderLeft: "3px solid var(--accent)", paddingLeft: ".9rem" }}>
              <strong>Withdrawn: we used to call our gaps the generous end.</strong>{" "}
              IRC:SP:41 Appendix III Table III-2 gives {gap.irc_sp41_car_gap_s}s for a
              passenger car crossing a four-lane road under stop control, with the
              large-city adjustment applied, and our composition-weighted figure sits
              below it. We read that gap as conservatism. It is mostly arithmetic: a
              mixed-traffic weighted mean sits below a single-class car value because
              two-wheelers are half this stream, not because we were being careful.
              Against the four-lane median-opening studies that match this geometry our
              gap sits mid-pack, which is why the same test is published across twelve
              bases above rather than defended at one.
            </p>

            <p className="src">Positive margin means that approach needs a gap
            <em> shorter</em> than we already assume before its bay could serve the
            demand. These values are literature, not measured on this corridor; a field
            measurement is the outstanding item.</p>
          </div>
        </div>
      )}

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
