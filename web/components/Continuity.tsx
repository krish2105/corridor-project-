"use client";
import { useState } from "react";
import {
  Bar, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

/**
 * Corridor continuity, with the residual PUBLISHED.
 *
 * Southbound traffic leaving one junction must arrive at the next as traffic entering
 * from Mansarover Metro. The difference is mid-block access — driveways, side lanes,
 * parking — plus whatever the counts got wrong. The two cannot be separated without a
 * cordon survey nobody ran.
 *
 * Volume balancing across simultaneously-counted junctions is standard practice.
 * Publishing the residual is not, and that is exactly why it is here: it is a measured
 * error rate on someone else's data, derived from their own numbers. A consultant's
 * report reconciles the counts quietly and presents the reconciled figures. This shows
 * what had to be reconciled.
 */
type Link = {
  north: string; south: string; daily_out: number; daily_in: number;
  mean_residual_pct: number; worst_residual_pct: number;
  series: { t: string; out: number; inn: number; residual: number }[];
};
const nf = new Intl.NumberFormat("en-US");

export default function Continuity({ links }: { links: Link[] }) {
  const [i, setI] = useState(0);
  const L = links[i];
  const worst = links.reduce((a, b) =>
    Math.abs(b.mean_residual_pct) > Math.abs(a.mean_residual_pct) ? b : a);

  return (
    <div className="card">
      <header>
        <h3>Corridor continuity, and the residual nobody publishes</h3>
        <span className="tag">{links.length} links</span>
      </header>
      <div className="body">
        <p className="col">Southbound traffic leaving one junction has to arrive at the
        next one. The difference is mid-block access plus count error, and the two cannot
        be separated without a cordon survey nobody ran. Balancing volumes across
        simultaneously-counted junctions is routine; <strong>publishing what had to be
        balanced is not</strong>.</p>

        <div className="picker" role="group" aria-label="Choose a corridor link">
          {links.map((l, k) => (
            <button key={k} aria-pressed={k === i} onClick={() => setI(k)}>
              {k === i && <span className="pill" />}
              <span className="lab">{l.north}&rarr;{l.south}</span>
            </button>
          ))}
        </div>

        <div style={{ width: "100%", height: 260 }}>
          <ResponsiveContainer>
            <ComposedChart data={L.series} margin={{ top: 6, right: 10, bottom: 0, left: 4 }}>
              <CartesianGrid stroke="var(--rule)" vertical={false} />
              <XAxis dataKey="t" interval={11} tick={{ fontSize: 10, fill: "var(--faint)" }}
                     tickLine={false} axisLine={{ stroke: "var(--rule)" }} />
              <YAxis tick={{ fontSize: 10, fill: "var(--faint)" }} width={52}
                     tickLine={false} axisLine={false}
                     tickFormatter={(v: number) => nf.format(v)} />
              <Tooltip
                contentStyle={{ background: "var(--surface)", border: "1px solid var(--rule)",
                                borderRadius: 4, fontSize: 12, color: "var(--ink)",
                                fontFamily: "IBM Plex Mono, monospace" }}
                labelStyle={{ color: "var(--muted)" }}
                formatter={(v: number, n: string) => [nf.format(v), n]} />
              <Legend wrapperStyle={{ fontSize: 11, color: "var(--muted)" }} />
              <ReferenceLine y={0} stroke="var(--rule-hard)" />
              <Bar dataKey="residual" name="residual (in − out)" fill="var(--defect)"
                   fillOpacity={.45} />
              <Line dataKey="out" name={`leaving ${L.north}`} dot={false}
                    stroke="var(--accent)" strokeWidth={1.6} />
              <Line dataKey="inn" name={`arriving ${L.south}`} dot={false}
                    stroke="var(--ok)" strokeWidth={1.6} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="scope">
          <div><span className="k num">{nf.format(L.daily_out)}</span>
            <span className="l">leaving {L.north}, day</span></div>
          <div><span className="k num">{nf.format(L.daily_in)}</span>
            <span className="l">arriving {L.south}, day</span></div>
          <div><span className="k num" style={{ color: "var(--defect)" }}>
            {L.mean_residual_pct > 0 ? "+" : ""}{L.mean_residual_pct}%</span>
            <span className="l">mean residual</span></div>
          <div><span className="k num">{L.worst_residual_pct}%</span>
            <span className="l">worst 15-min bin</span></div>
        </div>

        <div className="tscroll">
          <table>
            <thead><tr><th>Link</th>
              <th className="num">Leaving</th><th className="num">Arriving</th>
              <th className="num">Mean residual</th><th className="num">Worst bin</th></tr></thead>
            <tbody>
              {links.map((l, k) => (
                <tr key={k} onClick={() => setI(k)} style={{ cursor: "pointer",
                    background: k === i ? "var(--sunk)" : undefined }}>
                  <td>{l.north} &rarr; {l.south}</td>
                  <td className="num">{nf.format(l.daily_out)}</td>
                  <td className="num">{nf.format(l.daily_in)}</td>
                  <td className={"num " + (Math.abs(l.mean_residual_pct) > 15 ? "bad" : "")}>
                    {l.mean_residual_pct > 0 ? "+" : ""}{l.mean_residual_pct}%</td>
                  <td className="num">{l.worst_residual_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="col" style={{ borderLeft: "3px solid var(--defect)", paddingLeft: ".9rem" }}>
          <strong>The residual runs to {worst.mean_residual_pct > 0 ? "+" : ""}
          {worst.mean_residual_pct}% on {worst.north}&rarr;{worst.south}.</strong> Some of
          that is genuine mid-block access on a corridor the statutory plan designates for
          continuous commercial frontage. The rest is count error. We cannot say which is
          which, and neither can anyone else without a survey that was not commissioned
          &mdash; so the whole quantity is published rather than reconciled away.
        </p>

        <p className="src">This is also what the corridor ordering was derived from. Flow
        continuity alone separated the leading candidate orders by too little to call; the
        chainage along the survey drawing settled it.</p>
      </div>
    </div>
  );
}
