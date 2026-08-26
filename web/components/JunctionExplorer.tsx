"use client";
import Readout from "./Readout";
import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import {
  Area, AreaChart, CartesianGrid, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { Junction } from "@/lib/types";

const nf = new Intl.NumberFormat("en-US");

export default function JunctionExplorer({ junctions }: { junctions: Junction[] }) {
  // Ordered and labelled by SCHEME number: J1 at the top of the corridor. The survey
  // code stays as the selection key, because that is what every figure is keyed on.
  const ordered = [...junctions].sort((a, b) => a.scheme_no - b.scheme_no);
  const [code, setCode] = useState(ordered[0].code);
  // Composition bars: click to isolate a class, same pattern as every other exhibit here.
  // They were the last block on the page carrying numbers with no way to reach them.
  const [pinnedCls, setPinnedCls] = useState<string | null>(null);
  const [hoverCls, setHoverCls] = useState<string | null>(null);
  const activeCls = pinnedCls ?? hoverCls;
  const j = junctions.find((x) => x.code === code)!;
  const shown = j.composition.filter((c) => c.share > 0.0005);
  const selCls = shown.find((c) => c.cls === activeCls)
    ?? shown.reduce((a, b) => (b.share > a.share ? b : a), shown[0]);
  const reduce = useReducedMotion();

  const peakIdx = j.profile.findIndex((p) => p.t === j.peak_start);
  const peakEnd = j.profile[Math.min(peakIdx + 3, j.profile.length - 1)]?.t;
  const maxCell = Math.max(...j.matrix_veh.flat());

  return (
    <div className="stack">
      <div className="picker" role="group" aria-label="Choose a junction">
        {ordered.map((x) => (
          <button
            key={x.code}
            aria-pressed={x.code === code}
            onClick={() => setCode(x.code)}
          >
            {x.code === code && !reduce && (
              <motion.span layoutId="pill" className="pill"
                transition={{ type: "spring", stiffness: 420, damping: 34 }} />
            )}
            {x.code === code && reduce && <span className="pill" />}
            <span className="lab">{x.scheme_label}</span>
          </button>
        ))}
      </div>

      {/*
        No AnimatePresence, and deliberately so. `mode="wait"` holds the outgoing panel
        mounted until its exit animation completes, and that completion depends on
        requestAnimationFrame. rAF is paused in a hidden tab and throttled on some
        devices, so the selected junction could read TMC-02 while the table below it
        still showed TMC-01's arms.

        On a page whose entire value is that its numbers can be trusted, a state where
        the label and the data disagree is the worst failure available, and a 280 ms
        crossfade is not worth buying it. Keying the panel on `code` with an entrance
        animation only means the content swaps with React state, synchronously, whatever
        the animation does.
      */}
      <motion.div
        key={code}
        initial={reduce ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: .28, ease: [0.22, 1, 0.36, 1] }}
        className="stack"
      >
        <div className="scope">
          <div><span className="k num">{nf.format(j.daily_veh)}</span>
            <span className="l">vehicles / day</span></div>
          <div><span className="k num">{j.peak_start}</span>
            <span className="l">peak hour start</span></div>
          <div><span className="k num">{j.phf.toFixed(3)}</span>
            <span className="l">peak hour factor</span></div>
          <div><span className="k num" style={{ color: j.through_pct >= 70 ? "var(--ok)" : "var(--ink)" }}>
            {j.through_pct.toFixed(1)}%</span><span className="l">through movements</span></div>
          <div><span className="k num">{nf.format(j.peak15)}</span>
            <span className="l">busiest 15 min</span></div>
          <div><span className="k num" style={{ color: "var(--defect)" }}>+{j.uplift_pct}%</span>
            <span className="l">PCU correction</span></div>
        </div>

        <div className="grid2">
          <div className="card">
            <header><h3>Daily profile</h3>
              <span className="tag">96 &times; 15 min, 08:00&ndash;08:00</span></header>
            <div className="body">
              <div style={{ width: "100%", height: 230 }}>
                <ResponsiveContainer>
                  <AreaChart data={j.profile} margin={{ top: 4, right: 6, bottom: 0, left: 0 }}>
                    <defs>
                      <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--accent)" stopOpacity={.42} />
                        <stop offset="100%" stopColor="var(--accent)" stopOpacity={.03} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="var(--rule)" vertical={false} />
                    <XAxis dataKey="t" tick={{ fontSize: 11, fill: "var(--faint)" }}
                      interval={11} tickLine={false} axisLine={{ stroke: "var(--rule)" }} />
                    <YAxis tick={{ fontSize: 11, fill: "var(--faint)" }}
                      tickLine={false} axisLine={false} width={52}
                      tickFormatter={(v: number) => nf.format(v)} />
                    {peakIdx >= 0 && peakEnd && (
                      <ReferenceArea x1={j.peak_start} x2={peakEnd}
                        fill="var(--defect)" fillOpacity={.13} />
                    )}
                    <Tooltip
                      contentStyle={{
                        background: "var(--surface)", border: "1px solid var(--rule)",
                        borderRadius: 4, fontSize: 12, fontFamily: "IBM Plex Mono, monospace",
                        color: "var(--ink)",
                      }}
                      labelStyle={{ color: "var(--muted)" }}
                      formatter={(v: number) => [nf.format(v), "vehicles"]} />
                    <Area type="monotone" dataKey="v" stroke="var(--accent)"
                      strokeWidth={1.6} fill="url(#g)" isAnimationActive={!reduce} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <p style={{ fontSize: ".78rem", color: "var(--muted)" }}>
                Shaded band is the peak hour: {nf.format(j.peak_veh)} vehicles,
                PHF {j.phf.toFixed(3)}.
              </p>
            </div>
          </div>

          <div className="card">
            <header><h3>Composition</h3><span className="tag">day 1</span></header>
            <div className="body">
              <div className="bars">
                {j.composition.filter((c) => c.share > 0.0005).map((c) => (
                  <div className="bar grow" key={c.cls}
                       tabIndex={0} role="button"
                       aria-selected={pinnedCls === c.cls}
                       aria-label={`${c.cls.replace("_", " ")}, ${(100 * c.share).toFixed(2)} percent of the stream`}
                       onMouseEnter={() => setHoverCls(c.cls)}
                       onMouseLeave={() => setHoverCls(null)}
                       onFocus={() => setHoverCls(c.cls)}
                       onBlur={() => setHoverCls(null)}
                       onClick={() => setPinnedCls((x) => (x === c.cls ? null : c.cls))}
                       onKeyDown={(e) => {
                         if (e.key === "Enter" || e.key === " ") {
                           e.preventDefault();
                           setPinnedCls((x) => (x === c.cls ? null : c.cls));
                         }
                         if (e.key === "Escape") setPinnedCls(null);
                       }}
                       style={{ cursor: "pointer",
                                opacity: activeCls && activeCls !== c.cls ? .4 : 1,
                                transition: "opacity .15s" }}>
                    <span className="mono" style={{ fontSize: ".68rem", color: "var(--muted)" }}>
                      {c.cls.replace("_", " ").slice(0, 10)}</span>
                    <span className="track">
                      <motion.i className="fill2"
                        initial={reduce ? false : { width: 0 }}
                        animate={{ width: (100 * c.share) + "%" }}
                        transition={{ duration: .55, ease: [0.22, 1, 0.36, 1] }} />
                    </span>
                    <span className="num" style={{ fontSize: ".7rem", color: "var(--muted)" }}>
                      {(100 * c.share).toFixed(2)}%</span>
                  </div>
                ))}
              </div>
              {selCls && (
                <Readout
                  title={selCls.cls.replace("_", " ")}
                  pinned={!!pinnedCls}
                  onClear={() => setPinnedCls(null)}
                  hint={activeCls ? "click to pin" : "largest share \u00b7 pick any class"}
                  fields={[
                    { k: "share of stream", v: `${(100 * selCls.share).toFixed(2)}%`,
                      tone: selCls.share >= 0.10 ? "bad" : undefined },
                    { k: "vehicles counted", v: nf.format(Math.round(selCls.count ?? 0)) },
                    { k: "IRC:106 band", v: selCls.share >= 0.10 ? "high-share factor applies"
                        : selCls.share <= 0.05 ? "low-share factor applies"
                        : "interpolated between the two",
                      note: "the factor depends on this share, which is what the survey held fixed" },
                  ]}
                />
              )}
              <p style={{ fontSize: ".78rem", color: "var(--muted)" }}>
                Two columns carry 97% of the stream, and one of them lumps cars,
                autos and pickups together. That is what makes the PCU correction
                only partly resolvable.
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <header><h3>Turning movements</h3>
            <span className="tag">vehicles / day</span>
            <span className="tag">no U-turn column exists</span></header>
          <div className="body">
            <div className="tscroll">
              <table>
                <caption>Rows are the entry arm, columns the exit. Left turn = next arm
                  clockwise, because India drives on the left.</caption>
                <thead>
                  <tr><th>From &darr; &nbsp; To &rarr;</th>
                    {j.arms.map((a) => <th key={a}>{a}</th>)}</tr>
                </thead>
                <tbody>
                  {j.matrix_veh.map((row, r) => (
                    <tr key={r}>
                      <th style={{ textAlign: "left" }}>{j.arms[r]}</th>
                      {row.map((v, c) => r === c
                        ? <td key={c} className="diag">&mdash;</td>
                        : <td key={c} className={"num" + (v > .45 * maxCell ? " hot" : "")}>
                            {nf.format(v)}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
