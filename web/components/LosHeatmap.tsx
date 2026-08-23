"use client";
import { useState } from "react";

/**
 * Level of service for every corridor approach at every hour of the surveyed day.
 *
 * Every v/c published elsewhere on this page is the peak hour, which is the convention
 * and which hides the finding: these approaches are over capacity for eight to twelve
 * hours. A peak-hour number understates the problem by most of the day.
 *
 * The LETTER is printed in every cell, never colour alone. Red-green deficiency affects
 * roughly eight percent of men, and a green-to-red LOS ramp is precisely the failure
 * case for it.
 */
type Cell = { junction: string; approach: string; hour: string; pcu: number; vc: number; los: string };

const RAMP: Record<string, string> = {
  A: "var(--ok)", B: "#5E9E78", C: "#C8A93A", D: "#C8791A", E: "#B4442E", F: "var(--defect)",
};
const INK: Record<string, string> = { A: "#fff", B: "#fff", C: "#14181A", D: "#fff", E: "#fff", F: "#fff" };

export default function LosHeatmap({ grid, junctions }: { grid: Cell[]; junctions: string[] }) {
  const [dir, setDir] = useState<"Mansarover" | "Sanganer">("Mansarover");
  const rows = junctions;
  const hours = [...new Set(grid.map((c) => c.hour))].sort();
  const shown = grid.filter((c) => c.approach.includes(dir));
  const at = (j: string, h: string) => shown.find((c) => c.junction === j && c.hour === h);
  const fCount = shown.filter((c) => c.los === "F").length;

  return (
    <div className="card">
      <header>
        <h3>Level of service, every approach, every hour</h3>
        <span className="tag">{fCount} of {shown.length} approach-hours at F</span>
      </header>
      <div className="body">
        <div className="picker" role="group" aria-label="Choose a direction">
          {(["Mansarover", "Sanganer"] as const).map((d) => (
            <button key={d} aria-pressed={d === dir} onClick={() => setDir(d)}>
              {d === dir && <span className="pill" />}
              <span className="lab">from {d}</span>
            </button>
          ))}
        </div>

        <div className="tscroll">
          <table style={{ minWidth: "44rem" }}>
            <thead>
              <tr>
                <th>Junction</th>
                {hours.filter((_, i) => i % 4 === 0).map((h) => <th key={h} className="num">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((j) => (
                <tr key={j}>
                  <th style={{ textAlign: "left" }}>{j}</th>
                  {hours.filter((_, i) => i % 4 === 0).map((h) => {
                    const c = at(j, h);
                    if (!c) return <td key={h}>&mdash;</td>;
                    return (
                      <td key={h} className="num"
                          title={`${j} ${h} — v/c ${c.vc.toFixed(2)}, ${c.pcu.toLocaleString("en-US")} PCU/hr`}
                          style={{ background: RAMP[c.los], color: INK[c.los],
                                   fontWeight: 600, letterSpacing: ".04em" }}>
                        {c.los}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="col">The letter is printed in every cell rather than carried by
        colour alone, because a green-to-red ramp is unreadable to roughly one engineer
        in twelve. Hover any cell for its v/c and hourly PCU.</p>
      </div>
    </div>
  );
}
