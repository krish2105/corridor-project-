"use client";
import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import Readout, { type Field } from "./Readout";
import type { Criticality } from "@/lib/types";

/**
 * The six-junction comparative view.
 *
 * Two things a reader wants from six junctions and cannot get from six separate panels:
 * the order on any one indicator, and whether that order survives changing the indicator.
 * So the bars re-rank on the chosen metric and animate between metrics, which makes a
 * junction that moves visible as movement rather than as two numbers to hold in mind.
 *
 * The composite is shown as a stacked bar of its six normalised parts, not as a single
 * length. An unweighted sum is only defensible if a reader can see what it is made of and
 * apply their own weights, and a stacked bar is that: the segment lengths ARE the
 * components. A solid bar would hide that TMC-01 leads on three indicators and trails on
 * one, which is the whole argument for publishing the parts.
 */

type Metric = { key: keyof Criticality; norm: keyof Criticality; label: string;
                unit: string; fmt: (v: number) => string; why: string };

const nf = new Intl.NumberFormat("en-US");
const int = (v: number) => nf.format(Math.round(v));
const one = (v: number) => v.toFixed(1);
const two = (v: number) => v.toFixed(2);

const METRICS: Metric[] = [
  { key: "daily_veh", norm: "n_daily_veh", label: "Daily vehicles", unit: "veh/day",
    fmt: int, why: "What the junction carries over the analysis day." },
  { key: "peak_veh", norm: "n_peak_veh", label: "Peak hour", unit: "veh/h", fmt: int,
    why: "The hour design is sized on, re-derived from the 15-minute bins." },
  { key: "worst_vc", norm: "n_worst_vc", label: "Worst v/c", unit: "", fmt: two,
    why: "Busiest approach against its measured capacity. Above 1.0 is over capacity." },
  { key: "uturn_demand", norm: "n_uturn_demand", label: "U-turn demand", unit: "veh/h",
    fmt: int,
    why: "What both bays would have to carry once the signals come out. Never surveyed." },
  { key: "exposure_change_pct", norm: "n_exposure_change_pct", label: "Exposure change",
    unit: "%", fmt: one,
    why: "Flow-weighted crossing exposure under the scheme against today. Not a crash rate." },
  { key: "turning_share_pct", norm: "n_turning_share_pct", label: "Turning share",
    unit: "%", fmt: one,
    why: "Share not going straight through. High means the junction is doing the work." },
];

const PARTS = METRICS.map((m) => m.norm);

export default function Compare({ rows }: { rows: Criticality[] }) {
  const [metric, setMetric] = useState<string>("composite");
  const [pinned, setPinned] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const reduce = useReducedMotion();
  const active = pinned ?? hover;

  const m = METRICS.find((x) => x.key === metric);
  const value = (r: Criticality) =>
    m ? (r[m.key] as number) : r.score;
  const max = Math.max(...rows.map(value), 1e-9);
  const sorted = [...rows].sort((a, b) => value(b) - value(a));
  const sel = sorted.find((r) => r.junction === active) ?? sorted[0];

  const fields: Field[] = m
    ? [{ k: m.label, v: `${m.fmt(sel[m.key] as number)}${m.unit ? " " + m.unit : ""}` },
       { k: "normalised", v: (sel[m.norm] as number).toFixed(2),
         note: "0 = lowest of the six, 1 = highest" },
       { k: "composite rank", v: `${sel.rank} of ${rows.length}` },
       { k: "what it is", v: m.why }]
    : [{ k: "Composite", v: sel.score.toFixed(2), note: `of ${METRICS.length}.00 possible` },
       { k: "rank", v: `${sel.rank} of ${rows.length}` },
       ...METRICS.map((x) => ({
         k: x.label,
         v: `${x.fmt(sel[x.key] as number)}${x.unit ? " " + x.unit : ""}`,
         note: `${(sel[x.norm] as number).toFixed(2)} normalised`,
       }))];

  return (
    <div className="stack">
      <div className="picker" role="group" aria-label="Compare the six junctions on">
        <button aria-pressed={metric === "composite"}
                onClick={() => setMetric("composite")}>
          {metric === "composite" && (reduce
            ? <span className="pill" />
            : <motion.span layoutId="cmp-pill" className="pill"
                transition={{ type: "spring", stiffness: 420, damping: 34 }} />)}
          <span className="lab">Composite</span>
        </button>
        {METRICS.map((x) => (
          <button key={x.key} aria-pressed={metric === x.key}
                  onClick={() => setMetric(x.key as string)}>
            {metric === x.key && (reduce
              ? <span className="pill" />
              : <motion.span layoutId="cmp-pill" className="pill"
                  transition={{ type: "spring", stiffness: 420, damping: 34 }} />)}
            <span className="lab">{x.label}</span>
          </button>
        ))}
      </div>

      <ul className="cmp" onMouseLeave={() => setHover(null)}>
        {sorted.map((r, i) => {
          const on = r.junction === (pinned ?? hover);
          return (
            <motion.li
              key={r.junction}
              layout={!reduce}
              transition={{ type: "spring", stiffness: 380, damping: 38 }}
              className={on ? "on" : ""}
            >
              <button
                onMouseEnter={() => setHover(r.junction)}
                onFocus={() => setHover(r.junction)}
                onClick={() => setPinned(pinned === r.junction ? null : r.junction)}
                aria-pressed={pinned === r.junction}
                aria-label={`${r.junction}, ${r.jda_name}, rank ${r.rank}`}
              >
                <span className="cmp-rank">{i + 1}</span>
                <span className="cmp-name">
                  <b>{r.junction}</b>
                  <em>{r.jda_name}</em>
                </span>
                <span className="cmp-track">
                  {m ? (
                    <span className="cmp-fill"
                          style={{ width: `${Math.max(1.5, 100 * value(r) / max)}%` }} />
                  ) : (
                    PARTS.map((p, k) => (
                      <span key={p} className="cmp-seg"
                            style={{
                              width: `${100 * (r[p] as number) / METRICS.length}%`,
                              opacity: 0.42 + 0.58 * (k / (PARTS.length - 1)),
                            }} />
                    ))
                  )}
                </span>
                <span className="cmp-val">
                  {m ? m.fmt(value(r)) : r.score.toFixed(2)}
                </span>
              </button>
            </motion.li>
          );
        })}
      </ul>

      {!m && (
        <ul className="cmp-key" aria-label="What each segment is">
          {METRICS.map((x, k) => (
            <li key={x.key}>
              <span className="cmp-swatch"
                    style={{ opacity: 0.42 + 0.58 * (k / (METRICS.length - 1)) }} />
              {x.label}
            </li>
          ))}
        </ul>
      )}

      <Readout
        title={`${sel.junction} · ${sel.jda_name}`}
        fields={fields}
        pinned={pinned !== null}
        onClear={() => setPinned(null)}
        hint="hover or tap a junction"
      />

      <p className="src">
        {m
          ? <>Ranked on one indicator. Switch to <b>Composite</b> to see whether the order
              holds when the others are counted too.</>
          : <>The composite is the six indicators each scaled 0 to 1 across the corridor
              and added, <b>unweighted</b>. Each segment is one indicator, so the bar shows
              what the total is made of. No weighting is applied because a weighting is a
              policy choice, and inventing one here would present a judgement as a
              result.</>}
      </p>
    </div>
  );
}
