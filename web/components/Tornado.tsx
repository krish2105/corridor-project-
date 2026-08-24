"use client";
import { useState } from "react";
import Readout from "./Readout";

/**
 * How far each PCU assumption moves corridor demand, sorted, both directions.
 *
 * The audit finding as one picture. The survey applied one static factor per class;
 * IRC:106 makes the factor depend on that class's share of the stream. Two-wheelers are
 * understated, cycles and the heavy buckets overstated — showing only the favourable
 * half would repeat exactly the error the survey made.
 */
type Row = { veh_class: string; share_pct: number; surveyed_factor: number;
             irc_low: number | null; irc_high: number | null; exact: boolean;
             swing_low_pct: number; swing_high_pct: number; magnitude: number };

export default function Tornado({ t }: {
  t: { base_pcu: number; net_low_pct: number; net_high_pct: number; classes: Row[] };
}) {
  const rows = t.classes.filter((r) => r.magnitude >= 0.05);
  // The bars carried their numbers in a native `title` tooltip - no touch, no keyboard,
  // no way to hold one while reading. Same defect removed from the data grids earlier;
  // it survived here because a bar does not look like a control.
  const [pinned, setPinned] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const activeCls = pinned ?? hover;
  const sel = rows.find((r) => r.veh_class === activeCls)
    ?? rows.reduce((a, b) => (b.magnitude > a.magnitude ? b : a), rows[0]);
  const max = Math.max(...rows.map((r) => Math.max(Math.abs(r.swing_low_pct), Math.abs(r.swing_high_pct))));
  const half = 50;                       // centre of the plot, in %

  return (
    <div className="card">
      <header>
        <h3>Which PCU assumption moves the answer</h3>
        <span className="tag">net {t.net_low_pct > 0 ? "+" : ""}{t.net_low_pct}% to +{t.net_high_pct}%</span>
      </header>
      <div className="body">
        <div style={{ display: "flex", flexDirection: "column", gap: ".55rem" }}>
          {rows.map((r) => {
            const lo = r.swing_low_pct, hi = r.swing_high_pct;
            const left = half + (Math.min(lo, hi, 0) / max) * half;
            const width = (Math.abs(hi - lo) || Math.abs(hi || lo)) / max * half;
            const negative = Math.min(lo, hi) < 0;
            return (
              <div key={r.veh_class}
                   className="grow"
                   tabIndex={0}
                   role="button"
                   aria-selected={pinned === r.veh_class}
                   aria-label={`${r.veh_class.replace("_", " ")}, swings corridor demand ${lo}% to ${hi}%`}
                   onMouseEnter={() => setHover(r.veh_class)}
                   onMouseLeave={() => setHover(null)}
                   onFocus={() => setHover(r.veh_class)}
                   onBlur={() => setHover(null)}
                   onClick={() => setPinned((x) => (x === r.veh_class ? null : r.veh_class))}
                   onKeyDown={(e) => {
                     if (e.key === "Enter" || e.key === " ") {
                       e.preventDefault();
                       setPinned((x) => (x === r.veh_class ? null : r.veh_class));
                     }
                     if (e.key === "Escape") setPinned(null);
                   }}
                   style={{ display: "grid", gridTemplateColumns: "8.5rem 1fr 5.5rem",
                            gap: ".7rem", alignItems: "center", cursor: "pointer",
                            opacity: activeCls && activeCls !== r.veh_class ? .35 : 1,
                            transition: "opacity .15s" }}>
                <span className="mono" style={{ fontSize: ".67rem", color: "var(--muted)" }}>
                  {r.veh_class.replace("_", " ")}
                </span>
                <div style={{ position: "relative", height: 16, background: "var(--sunk)",
                              borderRadius: 2 }}>
                  <span style={{ position: "absolute", left: `${half}%`, top: 0, bottom: 0,
                                 width: 1, background: "var(--rule-hard)" }} />
                  <span style={{ position: "absolute", left: `${left}%`, width: `${Math.max(width, 0.6)}%`,
                                 top: 3, bottom: 3, borderRadius: 2,
                                 background: negative ? "var(--ok)" : "var(--defect)",
                                 opacity: r.exact ? 1 : .55 }} />
                </div>
                <span className="num" style={{ fontSize: ".7rem", color: "var(--muted)" }}>
                  {lo === hi ? `${lo > 0 ? "+" : ""}${lo}%` : `${lo > 0 ? "+" : ""}${lo}…${hi > 0 ? "+" : ""}${hi}%`}
                </span>
              </div>
            );
          })}
        </div>

        {sel && (
          <Readout
            title={sel.veh_class.replace("_", " ")}
            pinned={!!pinned}
            onClear={() => setPinned(null)}
            hint={activeCls ? "click to pin" : "largest swing \u00b7 pick any bar"}
            fields={[
              { k: "share of stream", v: `${sel.share_pct}%` },
              { k: "factor the survey used", v: `${sel.surveyed_factor}` },
              { k: "IRC:106 range", v: sel.irc_low != null && sel.irc_high != null
                  ? `${sel.irc_low} \u2013 ${sel.irc_high}` : "no 1:1 mapping",
                tone: sel.exact ? undefined : "bad" },
              { k: "swings corridor demand", v: `${sel.swing_low_pct > 0 ? "+" : ""}${sel.swing_low_pct}% to ${sel.swing_high_pct > 0 ? "+" : ""}${sel.swing_high_pct}%`,
                tone: sel.swing_high_pct > 0 ? "bad" : "ok" },
              { k: "correctable", v: sel.exact ? "yes, 1:1 onto IRC:106" : "no \u2014 composite column",
                tone: sel.exact ? "ok" : "bad" },
            ]}
          />
        )}

        <p className="col">Solid bars are classes that map one-to-one onto IRC:106, where
        the correction is exact. Faded bars are the survey&rsquo;s composite columns
        &mdash; car with taxi, tempo, auto-rickshaw and pickup in one bucket at one factor
        &mdash; where no single factor is recoverable and only a range is honest.</p>

        <p className="col"><strong>Both directions are shown.</strong> Two-wheelers are
        carried at 0.50 while they are half the stream and IRC:106 requires 0.75. Cycles
        and the multi-axle bucket are carried too high. Reporting only the half that
        favours our conclusion would be the same error the survey made.</p>
      </div>
    </div>
  );
}
