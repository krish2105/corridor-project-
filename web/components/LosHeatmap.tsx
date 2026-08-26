"use client";
import { useState } from "react";
import { useGridCursor } from "@/lib/useGridCursor";
import Readout from "./Readout";

/**
 * Level of service for every corridor approach at every hour of the surveyed day.
 *
 * Every v/c published elsewhere on this page is the peak hour, which is the convention
 * and which hides the finding: these approaches are over capacity for eight to twelve
 * hours. A peak-hour number understates the problem by most of the day.
 *
 * That argument only lands if the hours are actually on screen. An earlier version drew
 * every fourth hour — 144 cells — while the heading counted all 558, so the exhibit was
 * quietly discarding three quarters of its own evidence. All 93 rolling hours are drawn.
 *
 * The LETTER is printed in every cell, never colour alone. Red-green deficiency affects
 * roughly eight percent of men, and a green-to-red LOS ramp is precisely the failure
 * case for it.
 */
type Cell = { junction: string; approach: string; hour: string; pcu: number; vc: number; los: string };

/*
 * The LOS ramp is FIXED, not theme-derived, and every pair clears WCAG AA.
 *
 * A and F used to take var(--ok) and var(--defect), which flip with the theme while B–E
 * stayed hardcoded. Two things broke in dark mode. Four of the six grades fell below
 * 4.5:1 — A at 2.08, F at 2.40 — and worse, --defect resolves to a LIGHT red in dark, so
 * F rendered lighter than E and the ramp inverted at exactly the grade that matters most.
 * The worst level of service looked milder than the one above it.
 *
 * A data encoding is not chrome: these cells carry their own ground and should read the
 * same in both themes. Measured contrasts, identical light and dark:
 *   A 7.12   B 4.68   C 6.27   D 4.91   E 8.10   F 11.96
 * Luminance from C down to F descends monotonically, so severity now reads as intensity
 * on the half of the scale where it matters.
 */
const RAMP: Record<string, string> = {
  A: "#2C6249", B: "#4A7F5E", C: "#B8952B", D: "#A85E12", E: "#8E3020", F: "#6B1710",
};
const INK: Record<string, string> = {
  A: "#fff", B: "#fff", C: "#14181A", D: "#fff", E: "#fff", F: "#fff",
};
const MEANING: Record<string, string> = {
  A: "free flow", B: "reasonably free", C: "stable", D: "approaching unstable",
  E: "at capacity", F: "over capacity",
};

export default function LosHeatmap({ grid, junctions }: { grid: Cell[]; junctions: string[] }) {
  const [dir, setDir] = useState<"Mansarovar" | "Sanganer">("Mansarovar");
  const rows = junctions;
  const hours = [...new Set(grid.map((c) => c.hour))].sort();
  const shown = grid.filter((c) => c.approach.includes(dir));
  const byKey = new Map(shown.map((c) => [`${c.junction}|${c.hour}`, c]));
  const at = (j: string, h: string) => byKey.get(`${j}|${h}`);
  const fCount = shown.filter((c) => c.los === "F").length;

  const { active, pinned, cellProps, bodyProps, clear } = useGridCursor(rows.length, hours.length);

  // default to the worst cell, so the readout opens on the thing worth seeing
  const worst = shown.reduce((a, b) => (b.vc > a.vc ? b : a), shown[0]);
  const sel = active ? at(rows[active.r], hours[active.c]) : worst;
  // how long this approach stays over capacity — the finding the exhibit exists for
  const hoursAtF = sel ? shown.filter((c) => c.junction === sel.junction && c.los === "F").length : 0;

  return (
    <div className="card">
      <header>
        <h3>Level of service, every approach, every hour</h3>
        <span className="tag">{fCount} of {shown.length} approach-hours at F</span>
      </header>
      <div className="body">
        <div className="picker" role="group" aria-label="Choose a direction">
          {(["Mansarovar", "Sanganer"] as const).map((d) => (
            <button key={d} aria-pressed={d === dir} onClick={() => { setDir(d); clear(); }}>
              {d === dir && <span className="pill" />}
              <span className="lab">from {d}</span>
            </button>
          ))}
        </div>

        <div className="tscroll">
          <table style={{ minWidth: `${hours.length * 15 + 90}px` }}
                 role="grid" aria-label={`Level of service by junction and hour, from ${dir}`}>
            <thead>
              <tr>
                <th style={{ position: "sticky", left: 0, background: "var(--sunk)", zIndex: 3 }}>
                  Junction</th>
                {hours.map((h, i) => (
                  <th key={h} className="num"
                      /* 0.54rem rendered at 8.6px, which is not a readable size on a
                         phone. Only every fourth label is visible, so each has four
                         columns of room and can afford to be legible. */
                      style={{ padding: "0 2px", fontSize: ".68rem",
                               color: i % 4 === 0 ? "var(--muted)" : "transparent" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody {...bodyProps}>
              {rows.map((j, ri) => (
                <tr key={j}>
                  <th style={{ textAlign: "left", position: "sticky", left: 0,
                               background: "var(--sunk)", zIndex: 2 }}>{j}</th>
                  {hours.map((h, ci) => {
                    const c = at(j, h);
                    if (!c) return <td key={h} className="num">&mdash;</td>;
                    return (
                      <td key={h} className="num gcell" {...cellProps(ri, ci)}
                          aria-label={`${j} ${h}, level of service ${c.los}, v over c ${c.vc.toFixed(2)}`}
                          style={{ background: RAMP[c.los], color: INK[c.los], fontWeight: 600,
                                   letterSpacing: ".02em", padding: "0 2px", fontSize: ".64rem" }}>
                        {c.los}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="tscroll-note">scrolls sideways &mdash; all {hours.length} rolling hours</p>

        {sel && (
          <Readout
            title={`${sel.junction} · ${sel.hour} · from ${dir}`}
            pinned={!!pinned}
            onClear={clear}
            hint={active ? "click to pin" : "worst hour · pick any cell"}
            fields={[
              { k: "level of service", v: `${sel.los} — ${MEANING[sel.los]}`,
                tone: sel.los === "F" ? "bad" : sel.los === "A" || sel.los === "B" ? "ok" : undefined },
              { k: "v/c", v: sel.vc.toFixed(2), tone: sel.vc >= 1 ? "bad" : undefined },
              { k: "demand", v: `${sel.pcu.toLocaleString("en-US")} PCU/hr` },
              { k: "hours at F here", v: `${hoursAtF} of ${hours.length}`,
                tone: hoursAtF >= 8 ? "bad" : undefined },
            ]}
          />
        )}

        <p className="col">The letter is printed in every cell rather than carried by
        colour alone, because a green-to-red ramp is unreadable to roughly one engineer
        in twelve. Pick any cell &mdash; tap, click or arrow-key &mdash; for its v/c,
        hourly PCU, and how much of the day that approach spends over capacity.</p>
      </div>
    </div>
  );
}
