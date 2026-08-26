"use client";
import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import type { Corridor } from "@/lib/types";

/**
 * The three learned applications, each shown with the thing that could have failed.
 *
 * A model output is exactly the kind of number a reader takes on trust, so none of these
 * panels leads with its result. Each leads with its gate: what the model was made to fail
 * at, and whether it did. The screen had to re-find defects it was never told about; the
 * typology had to recover a label held out of the fitting; the count model had to beat
 * doing no modelling at all.
 *
 * The negative result is shown as prominently as the positive one. Temporal shape found
 * no typology, and burying that while showing the composition result would turn two tests
 * into one, which is the whole reason the p-value on the second is worth anything.
 */

const nf = new Intl.NumberFormat("en-US");
const TABS = ["Integrity screen", "Approach typology", "Count length"] as const;

export default function Learned({
  anomaly: an, cluster: cl, forecast: fc,
}: Pick<Corridor, "anomaly" | "cluster" | "forecast">) {
  const [tab, setTab] = useState<string>(TABS[0]);
  const reduce = useReducedMotion();

  return (
    <div className="stack">
      <div className="picker" role="tablist" aria-label="Three learned applications">
        {TABS.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} aria-pressed={tab === t}
                  onClick={() => setTab(t)}>
            {tab === t && (reduce
              ? <span className="pill" />
              : <motion.span layoutId="lrn-pill" className="pill"
                  transition={{ type: "spring", stiffness: 420, damping: 34 }} />)}
            <span className="lab">{t}</span>
          </button>
        ))}
      </div>

      {tab === TABS[0] && an && (
        <div className="stack">
          <p className="gate">
            <b>Gate</b> &mdash; the screen must re-find what the audit proved by hand,
            without being told it exists.{" "}
            <b className={an.gate.rediscovered === an.gate.known_defects ? "ok" : "bad"}>
              {an.gate.rediscovered} of {an.gate.known_defects} rediscovered
            </b>: the duplicated second day, and the broken stored totals.
          </p>
          <p className="col">Six detectors, each looking for a different signature of a
          data problem. Nothing about <em>this</em> survey is written into them, so the
          same code runs on the next contractor&rsquo;s submission &mdash; which is the
          point. JDA commissions surveys continuously and has no way to screen one before
          accepting it.</p>
          <div className="tscroll">
            <table>
              <caption>Each detector scaled 0 to 1 across the six on its <em>effect</em>,
                not on whether it reaches significance: at this many counts everything
                does. Summed unweighted. An ordering of what to ask about, not a verdict.</caption>
              <thead><tr><th>Junction</th><th>Name</th>
                <th className="num">Copied series</th><th className="num">0/5 excess</th>
                <th className="num">Flatlines</th><th className="num">Spikes /1000</th>
                <th className="num">Mix</th><th className="num">Arithmetic</th>
                <th className="num">Score</th></tr></thead>
              <tbody>
                {an.junctions.map((r) => (
                  <tr key={r.junction}>
                    <td className="mono">{r.junction}</td>
                    <td style={{ textAlign: "left" }}>{r.jda_name}</td>
                    <td className="num">{(100 * r.duplicate_series_share).toFixed(0)}%</td>
                    <td className="num">{r.terminal_digit_excess_pct > 0 ? "+" : ""}
                      {r.terminal_digit_excess_pct.toFixed(1)}pp</td>
                    <td className="num">{r.flatline_series}</td>
                    <td className="num">{r.spike_bins_per_1000.toFixed(1)}</td>
                    <td className="num">{r.mix_intervals}</td>
                    <td className={"num " + (r.stored_total_breaks ? "bad" : "")}>
                      {r.stored_total_breaks}</td>
                    <td className="num"><b>{r.integrity_flag_score.toFixed(2)}</b></td>
                  </tr>))}
              </tbody>
            </table>
          </div>
          <p className="src">{an.caveat[0].toUpperCase() + an.caveat.slice(1)}. Every
          signature above has an innocent explanation &mdash; a festival, a lane closure, a
          genuinely quiet class. What it buys is minutes instead of months.</p>
        </div>
      )}

      {tab === TABS[1] && cl && (
        <div className="stack">
          <p className="gate">
            <b>Gate</b> &mdash; the clusters must recover a label held out of the fitting:
            corridor arm against cross-street arm. Clustering always returns clusters, so a
            silhouette alone proves nothing.
          </p>
          <p className="col"><b>{cl.feature_sets_tested} feature sets were fitted and both
          are shown.</b> {cl.multiple_comparison_note[0].toUpperCase()}
          {cl.multiple_comparison_note.slice(1)}.</p>
          <div className="lrn-grid">
            {cl.results.map((r) => {
              const ok = r.structure_found && r.external_label.recovered;
              return (
                <div key={r.feature_set} className={"lrn-card " + (ok ? "ok" : "null")}>
                  <header>
                    <span className="mono">{r.feature_set}</span>
                    <span className={"chip " + (ok ? "fixed" : "critical")}>
                      {ok ? "typology found" : "no typology"}</span>
                  </header>
                  <dl>
                    <div><dt>silhouette</dt>
                      <dd>{r.silhouette.toFixed(3)} at k={r.k}
                        <em>threshold {cl.silhouette_min}</em></dd></div>
                    <div><dt>held-out label</dt>
                      <dd>{(100 * r.external_label.purity).toFixed(1)}% pure
                        <em>vs {(100 * r.external_label.null_mean).toFixed(1)}% at random,
                          p = {r.external_label.p.toFixed(4)}</em></dd></div>
                  </dl>
                  <p className="src" style={{ marginTop: ".5rem" }}>
                    {ok
                      ? <>{r.clusters.length} groups. The corridor arms and the cross-street
                          arms fall on different sides of them, and that label never entered
                          the distance matrix.</>
                      : <>The approaches do not separate. Reported as no typology rather
                          than forced into k groups &mdash; and that is a finding: {cl.n_approaches}{" "}
                          approaches on the same clock is what makes one corridor-wide peak
                          hour defensible.</>}
                  </p>
                </div>);
            })}
          </div>
          {cl.two_wheeler_split && (
            <p className="src">
              What they separate on is the stream, not the clock. Two-wheelers are{" "}
              <b>{(100 * cl.two_wheeler_split.cross_mean).toFixed(1)}%</b> of the
              cross-street approaches against{" "}
              <b>{(100 * cl.two_wheeler_split.corridor_mean).toFixed(1)}%</b> of the
              corridor ones (p = {cl.two_wheeler_split.p.toFixed(4)}). The gap is real and
              small. The figure underneath it is not: the <em>lowest</em> two-wheeler share
              on any of the {cl.n_approaches} approaches is{" "}
              <b>{(100 * cl.two_wheeler_split.min_share).toFixed(1)}%</b>, four times the
              10% at which IRC:106 requires 0.75. The survey used 0.50 throughout, so the
              understatement is not concentrated anywhere &mdash; it is everywhere.
            </p>
          )}
        </div>
      )}

      {tab === TABS[2] && fc && (
        <div className="stack">
          <p className="gate">
            <b>Gate</b> &mdash; beat doing no modelling at all. The baseline assumes a
            window carries its pro-rata share of the day.{" "}
            <b className="ok">{fc.gate.predictable} of {fc.gate.targets}</b> targets clear
            it under {fc.mape_gate}% error.
          </p>
          <p className="col">Not a forecast of 2046 &mdash; one independent day cannot
          support that. The question a client actually pays for: <b>how short can a count
          be?</b> A 24-hour classified count at six junctions is expensive, and most of
          those hours are counted only to scale the ones that matter.</p>
          <div className="tscroll">
            <table>
              <caption>Expansion factors fitted leave-one-out across the{" "}
                {fc.n_approaches} approaches, so no approach predicts itself.</caption>
              <thead><tr><th>Window</th><th className="num">Hours</th><th>Predicts</th>
                <th className="num">Factor</th><th className="num">Error</th>
                <th className="num">No model</th><th className="num">Worst approach</th></tr></thead>
              <tbody>
                {fc.windows.map((w, i) => (
                  <tr key={i}>
                    <td className="mono">{w.clock}</td>
                    <td className="num">{w.hours}</td>
                    <td style={{ textAlign: "left" }}>
                      {w.target === "daily_total" ? "24-hour total" : "peak hour"}</td>
                    <td className="num">{w.factor.toFixed(3)}</td>
                    <td className={"num " + (w.mape < fc.mape_gate ? "good" : "bad")}>
                      {w.mape.toFixed(1)}%</td>
                    <td className="num dim">{w.baseline_mape.toFixed(1)}%</td>
                    <td className="num">{w.worst_approach_pct.toFixed(1)}%</td>
                  </tr>))}
              </tbody>
            </table>
          </div>
          <p className="src">
            <b>Read the unselected figures.</b> The window was chosen on the same
            leave-one-out error it is reported with, over{" "}
            {fc.selection.combinations_searched} combinations, so the headline is the best
            of a search and optimistic by an unknown amount. The leave-one-out protects the
            factor, not the choice of window. What is not selected: the worst single
            approach in each row, and the 8- and 12-hour windows, which clear the gate with
            no search at all. {fc.caveat[0].toUpperCase() + fc.caveat.slice(1)}.
          </p>
        </div>
      )}
    </div>
  );
}
