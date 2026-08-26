"use client";
import { useState } from "react";
import type { Corridor } from "@/lib/types";

/**
 * The U-turn decision ladder.
 *
 * The scheme test above returns a verdict. This returns the reasoning: five criteria in
 * the order they are evaluated, the first failure binding, and everything below it marked
 * NOT REACHED rather than passed. That distinction is the component's whole job, so it is
 * carried in the colour and in the word, never in the colour alone.
 *
 * Interactive because the interesting part is per bay: which criterion binds here, what
 * the back-solve says would change it, and what could not be evaluated at all.
 */

const nf = new Intl.NumberFormat("en-US");

const TONE: Record<string, string> = {
  pass: "good", fail: "bad", "cannot evaluate": "warn", "not reached": "dim",
};
const MARK: Record<string, string> = {
  pass: "clears", fail: "binds", "cannot evaluate": "no data", "not reached": "untested",
};

export default function Ladder({ f }: { f: NonNullable<Corridor["uturn_framework"]> }) {
  const bays = [...f.bays].sort((a, b) => a.scheme_no - b.scheme_no
    || a.bay.localeCompare(b.bay));
  const [open, setOpen] = useState<string>(bays[0].junction + bays[0].bay);
  const bay = bays.find((b) => b.junction + b.bay === open) ?? bays[0];
  const s = bay.back_solve;

  return (
    <div className="stack">
      <div className="picker" role="group" aria-label="Choose a U-turn bay">
        {bays.map((b) => {
          const id = b.junction + b.bay;
          return (
            <button key={id} aria-pressed={id === open} onClick={() => setOpen(id)}>
              {id === open && <span className="pill" />}
              <span className="lab">{b.scheme_label} {b.bay === "northbound" ? "N" : "S"}</span>
            </button>
          );
        })}
      </div>

      <div className="lad">
        <div className="lad-head">
          <span className="mono">{bay.scheme_label} &middot; {bay.jda_name} &middot; {bay.bay}<br /><span style={{ color: "var(--faint)" }}>survey sheet {bay.junction}</span></span>
          <span className={"chip " + (bay.verdict === "fails" ? "critical" : "")}>
            {bay.verdict} &middot; {nf.format(bay.uturn_demand)} veh/h
          </span>
        </div>
        <ol className="lad-steps">
          {f.criteria.map((c, i) => {
            const k = bay.checks[c];
            return (
              <li key={c} className={TONE[k.status] ?? ""}>
                <span className="lad-n">{i + 1}</span>
                <span className="lad-c">{c}</span>
                <span className="lad-s">{MARK[k.status] ?? k.status}</span>
                <span className="lad-d">{k.detail}</span>
              </li>
            );
          })}
        </ol>
      </div>

      {s && (
        <div className="lad-solve">
          <p className="src" style={{ marginTop: 0 }}>
            <strong>What would have to change.</strong> Solved backwards from the binding
            criterion, not asserted.
          </p>
          {s.above_bay_ceiling ? (
            <p className="col bad-note">
              Nothing on the opposing side reaches this bay.{" "}
              <strong>{nf.format(s.demand_now)} veh/h</strong> is above the{" "}
              <strong>{nf.format(s.bay_ceiling_veh_hr)} veh/h</strong> a single opening
              passes with <em>no opposing traffic at all</em> &mdash; 3600 divided by the
              follow-up headway. This is not a badly sited bay. It is the wrong instrument
              for the demand, and no metering, median widening or opposing-flow relief
              changes that.
            </p>
          ) : (
            <div className="scope">
              <div><span className="k">{nf.format(s.conflicting_now)}</span>
                <span className="l">opposing flow now, veh/h</span></div>
              <div><span className="k">{nf.format(s.conflicting_needed ?? 0)}</span>
                <span className="l">needed for this bay to work</span></div>
              <div><span className="k">{s.conflicting_reduction_pct?.toFixed(0)}%</span>
                <span className="l">of it would have to go elsewhere</span></div>
              <div><span className="k">{nf.format(s.demand_servable)}</span>
                <span className="l">veh/h the bay can serve today</span></div>
            </div>
          )}
        </div>
      )}

      <div className="lad-alts">
        <p className="src" style={{ marginTop: 0 }}>
          <strong>What to do instead.</strong> Ordered by cost. A rung is dead when it
          cannot move the criterion that binds here, however cheap it is.
        </p>
        <ul className="alts">
          {f.alternatives.map((a) => (
            <li key={a.measure} className={a.live ? "live" : "dead"}>
              <span className="alt-h">
                <span className="alt-m">{a.measure}</span>
                <span className="alt-c">{a.cost}</span>
                <span className="alt-s">{a.live ? "available" : "cannot help here"}</span>
              </span>
              <span className="alt-n">{a.note}</span>
            </li>
          ))}
        </ul>
      </div>

      <p className="src">
        {f.blocked_criteria_now.length === 0 ? (
          <>Nothing needs measuring to reach today&rsquo;s verdict, and that is itself the
          finding. All {f.n_bays} bays fail on gap capacity, which binds on counts and
          opposing flows already in hand. The criteria below it &mdash;{" "}
          {f.blocked_criteria_once_binding_cleared.join(", ")} &mdash; do need survey data,
          and they matter the moment the opposing flow is treated, not before.</>
        ) : (
          <>{f.n_undecided} of {f.n_bays} bays are undecided on data not held, blocked on{" "}
          {f.blocked_criteria_now.join(", ")}.</>
        )}{" "}
        {f.measurement_status[0].toUpperCase() + f.measurement_status.slice(1)}.
      </p>
    </div>
  );
}
