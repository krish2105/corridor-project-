"use client";
import { useEffect, useState } from "react";
import {
  Area, ComposedChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid,
} from "recharts";

/**
 * The pier-siting profile: what falls inside an 8 m pier footprint at every 25 m station.
 *
 * Reported elsewhere as a single number (92% of stations free of hard constraint). That
 * number is the conclusion; this is the evidence. The five pinch points are visible here
 * and nowhere else, and their chainage is what a designer actually needs.
 */
type Row = { ch: number; score: number; hard: number };

export default function PierProfile() {
  const [rows, setRows] = useState<Row[] | null>(null);
  useEffect(() => {
    fetch("/constraint_profile.json").then((r) => r.json()).then(setRows).catch(() => setRows([]));
  }, []);

  if (!rows) return <p style={{ color: "var(--muted)", fontSize: ".8rem" }}>Loading profile…</p>;
  if (!rows.length) return null;

  const data = rows.map((r) => ({ km: r.ch / 1000, all: r.score, hard: r.hard * 5 }));
  const pinch = rows.filter((r) => r.hard > 0);

  return (
    <div className="card">
      <header>
        <h3>Pier-siting profile</h3>
        <span className="tag">{rows.length} stations at 25 m</span>
        <span className="tag">8 m footprint</span>
      </header>
      <div className="body">
        <div style={{ width: "100%", height: 240 }}>
          <ResponsiveContainer>
            <ComposedChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--rule)" vertical={false} />
              <XAxis dataKey="km" tick={{ fontSize: 10, fill: "var(--faint)" }}
                tickLine={false} axisLine={{ stroke: "var(--rule)" }}
                tickFormatter={(v: number) => v.toFixed(1)}
                label={{ value: "chainage (km)", position: "insideBottom", offset: -2,
                         fontSize: 10, fill: "var(--muted)" }} />
              <YAxis tick={{ fontSize: 10, fill: "var(--faint)" }} tickLine={false}
                axisLine={false} width={34} />
              <Tooltip contentStyle={{ background: "var(--surface)",
                border: "1px solid var(--rule)", borderRadius: 4, fontSize: 12,
                fontFamily: "IBM Plex Mono, monospace", color: "var(--ink)" }}
                labelFormatter={(v) => `ch ${(Number(v) * 1000).toFixed(0)} m`}
                formatter={(v: number, n: string) =>
                  [n === "hard" ? (v / 5).toFixed(0) : v.toFixed(0),
                   n === "hard" ? "hard constraints" : "weighted score"]} />
              <ReferenceLine y={0} stroke="var(--rule)" />
              <Area type="stepAfter" dataKey="all" stroke="#8B938E" fill="#8B938E"
                fillOpacity={.28} strokeWidth={.8} isAnimationActive={false} />
              <Area type="stepAfter" dataKey="hard" stroke="var(--defect)"
                fill="var(--defect)" fillOpacity={.6} strokeWidth={0} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <p style={{ fontSize: ".78rem", color: "var(--muted)" }}>
          <span style={{ color: "var(--defect)", fontWeight: 600 }}>Red</span> is hard
          constraint — buildings, temples, rail, gas — where a pier cannot go without
          demolition or diversion. <span style={{ fontWeight: 600 }}>Grey</span> is
          everything weighted, including street furniture that relocates as routine.
          Reporting only the grey made the corridor look 74% blocked; the red is the real
          picture.
        </p>
        <div className="tscroll">
          <table>
            <caption>The {pinch.length} stations carrying a hard constraint. These are the
              locations a design has to work around; everywhere else is open.</caption>
            <thead><tr><th>Chainage</th><th>Hard constraints</th><th>Weighted score</th></tr></thead>
            <tbody>
              {pinch.map((r) => (
                <tr key={r.ch}>
                  <td className="num">{r.ch.toLocaleString("en-US")} m</td>
                  <td className="num bad">{r.hard}</td>
                  <td className="num">{r.score}</td>
                </tr>))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
