"use client";
import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  Area, AreaChart, CartesianGrid, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { Junction } from "@/lib/types";

const nf = new Intl.NumberFormat("en-US");

export default function JunctionExplorer({ junctions }: { junctions: Junction[] }) {
  const [code, setCode] = useState(junctions[0].code);
  const j = junctions.find((x) => x.code === code)!;
  const reduce = useReducedMotion();

  const peakIdx = j.profile.findIndex((p) => p.t === j.peak_start);
  const peakEnd = j.profile[Math.min(peakIdx + 3, j.profile.length - 1)]?.t;
  const maxCell = Math.max(...j.matrix_veh.flat());

  return (
    <div className="stack">
      <div className="picker" role="group" aria-label="Choose a junction">
        {junctions.map((x) => (
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
            <span className="lab">{x.code}</span>
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={code}
          initial={reduce ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduce ? undefined : { opacity: 0, y: -8 }}
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
                      <XAxis dataKey="t" tick={{ fontSize: 10, fill: "var(--faint)" }}
                        interval={11} tickLine={false} axisLine={{ stroke: "var(--rule)" }} />
                      <YAxis tick={{ fontSize: 10, fill: "var(--faint)" }}
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
                    <div className="bar" key={c.cls}>
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
      </AnimatePresence>
    </div>
  );
}
