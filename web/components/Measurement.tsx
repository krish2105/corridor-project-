"use client";
import { useState } from "react";
import type { Corridor } from "@/lib/types";

/**
 * How far every dimension on this page can be trusted.
 *
 * The drawing JDA supplied carries no dimension entities, so every width, chainage and
 * offset here is SCALED off georeferenced linework. A scaled number printed to one decimal
 * place is indistinguishable from a measured one, and capacity moves linearly with width,
 * so this is the most consequential uncertainty in the whole assessment. It belongs on the
 * page, not in a JSON file a reader has to know to open.
 *
 * The convergence table is shown first and deliberately. It is the evidence that our own
 * method was wrong once: at a 25 m transect spacing TMC-01 read 11.7 m from two transects
 * and 15.6 m at every finer spacing, which changed its lane count.
 */

const nf = new Intl.NumberFormat("en-US");

export default function Measurement({
  m, caveat,
}: { m: NonNullable<Corridor["measurement"]>; caveat?: string }) {
  const [open, setOpen] = useState(false);
  const steps = m.steps_tested;
  const moved = m.convergence.filter((c) => (c.spread_m ?? 0) > m.converged_tolerance_m);

  return (
    <div className="stack">
      {caveat && (
        <p className="col" style={{
          borderLeft: "3px solid var(--defect)", paddingLeft: ".9rem" }}>
          <strong>The load-bearing uncertainty.</strong> {caveat}
        </p>
      )}

      <div className="tscroll">
        <table>
          <caption>Does the width depend on the transect spacing, or on the road? The
            spacing is an arbitrary choice inside the method, so an answer that moves with
            it is measuring the choice. {m.published_step_m} m is published because that is
            where it stops moving.</caption>
          <thead>
            <tr>
              <th>Junction</th><th>Name</th>
              {steps.map((s) => <th key={s} className="num">{s} m</th>)}
              <th className="num">Spread</th><th>Settles at</th>
            </tr>
          </thead>
          <tbody>
            {m.convergence.map((c) => (
              <tr key={c.junction}>
                <td className="mono">{c.junction}</td>
                <td style={{ textAlign: "left" }}>{c.jda_name}</td>
                {c.by_step.map((b) => (
                  <td key={b.step_m}
                      className={"num " + (b.step_m === m.published_step_m ? "pub" : "")}>
                    {b.width_m === null ? "—" : b.width_m.toFixed(1)}
                  </td>
                ))}
                <td className={"num " + ((c.spread_m ?? 0) > m.converged_tolerance_m ? "bad" : "")}>
                  {c.spread_m?.toFixed(1)}</td>
                <td className="mono" style={{ textAlign: "left" }}>
                  {c.converged_at_step ? `${c.converged_at_step} m` : "still moving"}</td>
              </tr>))}
          </tbody>
        </table>
      </div>

      <p className="src">
        Usable transects on the whole corridor:{" "}
        {m.transects_by_step.map((t, i) => (
          <span key={t.step_m}>{i > 0 && ", "}<b>{t.transects}</b> at {t.step_m} m</span>
        ))}.
        {moved.length > 0 && (
          <> At the coarsest spacing{" "}
          <b>{moved.map((c) => c.junction).join(", ")}</b>{" "}
          {moved.length === 1 ? "moved" : "moved"} by{" "}
          {moved.map((c) => c.spread_m?.toFixed(1)).join(", ")} m &mdash; enough to change
          a lane count, off a sample of two transects. That is a defect in our own method,
          found by testing it against itself, and the published widths are the corrected
          ones.</>
        )}
      </p>

      <button className="disc" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span aria-hidden>{open ? "−" : "+"}</span>
        The rest of the register &mdash; intervals, source agreement, every dimension
      </button>

      {open && (
        <div className="stack">
          <div className="tscroll">
            <table>
              <caption>How much each width depends on which transects happened to land.{" "}
                {nf.format(m.bootstrap_resamples)} resamples of that junction&rsquo;s own
                transects. This is sampling error only &mdash; it says nothing about
                whether the kerb linework is in the right place.</caption>
              <thead><tr><th>Junction</th><th className="num">Transects</th>
                <th className="num">Width</th><th className="num">95% interval</th>
                <th className="num">Range seen</th>
                <th>Over {m.wide_threshold_m} m?</th></tr></thead>
              <tbody>
                {m.bootstrap.map((b) => (
                  <tr key={b.junction}>
                    <td className="mono">{b.junction}</td>
                    <td className="num">{b.n}</td>
                    <td className="num">{b.median_m?.toFixed(1) ?? "—"}</td>
                    <td className="num">{b.ci_m
                      ? `${b.ci_m[0].toFixed(1)}–${b.ci_m[1].toFixed(1)}` : "—"}</td>
                    <td className="num">{b.min_m !== undefined
                      ? `${b.min_m.toFixed(1)}–${b.max_m?.toFixed(1)}` : "—"}</td>
                    <td className={b.above_wide_threshold ? "bad" : "good"}
                        style={{ textAlign: "left" }}>
                      {b.unquantified ?? (b.above_wide_threshold ? "yes" : "no")}</td>
                  </tr>))}
              </tbody>
            </table>
          </div>

          <div className="tscroll">
            <table>
              <caption>Do JDA&rsquo;s KML and JDA&rsquo;s CAD agree about where the road
                is? Two independently produced descriptions of one corridor. Neither is
                checked against the ground here &mdash; what is measured is whether they
                are consistent, and by how much.</caption>
              <thead><tr><th>Measured to</th><th className="num">Stations</th>
                <th className="num">Median</th><th className="num">90th pct</th>
                <th className="num">Worst</th></tr></thead>
              <tbody>
                {m.registration.map((r) => (
                  <tr key={r.feature}>
                    <td style={{ textAlign: "left" }}>{r.feature}</td>
                    <td className="num">{r.n || "—"}</td>
                    <td className="num">{r.median_m?.toFixed(2) ?? r.unquantified}</td>
                    <td className="num">{r.p90_m?.toFixed(2) ?? "—"}</td>
                    <td className="num">{r.max_m?.toFixed(2) ?? "—"}</td>
                  </tr>))}
              </tbody>
            </table>
          </div>

          <dl className="dims">
            {m.dimensions.map((r) => (
              <div key={r.dimension}>
                <dt>{r.dimension}</dt>
                <dd>
                  <span className="dim-k">used for</span> {r.used_for}<br />
                  <span className="dim-k">method</span> {r.method}<br />
                  <span className="dim-k">uncertainty</span> {r.uncertainty}<br />
                  <span className="dim-k">resolved by</span> {r.resolved_by}
                </dd>
              </div>))}
          </dl>
        </div>
      )}

      <p className="src">{m.source}. {m.status[0].toUpperCase() + m.status.slice(1)}.</p>
    </div>
  );
}
