"use client";
import { useState } from "react";
import Readout from "./Readout";

/**
 * Conflict points, and what the signal-free scheme does to them.
 *
 * A signal-free scheme is usually sold as safer. The engineering question is narrower:
 * does removing the signals REMOVE conflicts or RELOCATE them? Counting says the former,
 * exposure says the latter, and exposure is the one that matters — a conflict between
 * two streams of 30 veh/hr is not the hazard that two streams of 1,500 are.
 *
 * Not a crash prediction. There is no accident data for this corridor and none is
 * invented; this is opportunity for conflict, reported as a ratio between schemes.
 */
type Row = {
  junction: string; jda_name: string; today_points: number; scheme_junction_points: number;
  today_crossing_exposure: number; scheme_crossing_exposure: number;
  uturn_crossing_exposure: number; change_pct: number | null;
};
type Safety = {
  base_counts: Record<string, number>; base_total: number;
  junctions: Row[]; junctions_worse: number; mean_change_pct: number;
  pedestrian_column_present: boolean;
  caveat?: string;
};

export default function ConflictDiagram({ s }: { s: Safety }) {
  const worst = Math.max(...s.junctions.map((r) => Math.max(r.today_crossing_exposure, r.scheme_crossing_exposure)));
  // Pick a junction to isolate it. The table and the bars are two views of one row, so
  // selecting in either has to light up both — otherwise the reader has to hold the row
  // order in their head to connect a bar to its number.
  const [pinned, setPinned] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const activeCode = pinned ?? hover;
  // default to the junction the scheme hurts most: the row the argument rests on
  const sel = s.junctions.find((r) => r.junction === activeCode)
    ?? s.junctions.reduce((a, b) => ((b.change_pct ?? 0) > (a.change_pct ?? 0) ? b : a), s.junctions[0]);
  const rowProps = (code: string) => ({
    className: "grow",
    tabIndex: 0,
    role: "button" as const,
    "aria-selected": pinned === code,
    "aria-label": `Isolate ${code}`,
    onMouseEnter: () => setHover(code),
    onMouseLeave: () => setHover(null),
    onFocus: () => setHover(code),
    onBlur: () => setHover(null),
    onClick: () => setPinned((p) => (p === code ? null : code)),
    onKeyDown: (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setPinned((p) => (p === code ? null : code)); }
      if (e.key === "Escape") setPinned(null);
    },
  });
  const dim = (code: string) => (activeCode && activeCode !== code ? .28 : 1);
  return (
    <div className="card">
      <header>
        <h3>Conflict points, and where they go</h3>
        <span className="chip critical">exposure rises at {s.junctions_worse} of {s.junctions.length}</span>
      </header>
      <div className="body">
        <div className="scope">
          <div><span className="k num">{s.base_counts.crossing}</span><span className="l">crossing</span></div>
          <div><span className="k num">{s.base_counts.merging}</span><span className="l">merging</span></div>
          <div><span className="k num">{s.base_counts.diverging}</span><span className="l">diverging</span></div>
          <div><span className="k num">{s.base_total}</span><span className="l">points today</span></div>
          <div><span className="k num" style={{ color: "var(--ok)" }}>
            {s.junctions[0]?.scheme_junction_points}</span><span className="l">points after</span></div>
          <div><span className="k num" style={{ color: "var(--defect)" }}>
            {s.mean_change_pct > 0 ? "+" : ""}{s.mean_change_pct}%</span>
            <span className="l">crossing exposure</span></div>
        </div>

        {s.caveat && <p className="src">{s.caveat[0].toUpperCase() + s.caveat.slice(1)}.</p>}

        <p className="col">Counted from geometry rather than quoted: each movement is a
        chord across the junction, offset to the left of the centreline because India
        drives on the left. The construction returns <strong>32 points &mdash; 16 crossing,
        8 merging, 8 diverging</strong>, which is what every text on four-leg intersections
        reports. That agreement is the check that the geometry is right, and it caught a
        real error while it was being built.</p>

        <div className="tscroll">
          <table>
            <thead><tr>
              <th>Junction</th><th>Name</th>
              <th className="num">Points now</th><th className="num">After</th>
              <th className="num">Exposure now</th><th className="num">After</th>
              <th className="num">Change</th>
            </tr></thead>
            <tbody>
              {s.junctions.map((r) => (
                <tr key={r.junction} {...rowProps(r.junction)}>
                  <td>{r.junction}</td><td>{r.jda_name}</td>
                  <td className="num">{r.today_points}</td>
                  <td className="num good">{r.scheme_junction_points}</td>
                  <td className="num">{r.today_crossing_exposure.toLocaleString("en-US")}</td>
                  <td className="num bad">{r.scheme_crossing_exposure.toLocaleString("en-US")}</td>
                  <td className="num bad">+{r.change_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* exposure comparison, drawn to scale */}
        <div style={{ display: "flex", flexDirection: "column", gap: ".5rem" }}>
          {s.junctions.map((r) => (
            <div key={r.junction} {...rowProps(r.junction)}
                 style={{ display: "grid", gridTemplateColumns: "5rem 1fr", gap: ".7rem",
                          alignItems: "center", opacity: dim(r.junction), transition: "opacity .15s",
                          cursor: "pointer" }}>
              <span className="mono" style={{ fontSize: ".68rem", color: "var(--muted)" }}>{r.junction}</span>
              <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                <div style={{ height: 9, width: `${100 * r.today_crossing_exposure / worst}%`,
                              background: "var(--rule-hard)", borderRadius: 2 }} />
                <div style={{ height: 9, width: `${100 * r.scheme_crossing_exposure / worst}%`,
                              background: "var(--defect)", borderRadius: 2 }} />
              </div>
            </div>
          ))}
          <p style={{ fontSize: ".72rem", color: "var(--muted)" }}>
            Upper bar: today. Lower bar: signal-free scheme. Drawn to one scale.
            Pick any junction, in the table or the bars, to isolate it.
          </p>
        </div>

        <Readout
          title={`${sel.junction} · ${sel.jda_name}`}
          pinned={!!pinned}
          onClear={() => setPinned(null)}
          hint={activeCode ? "click to pin" : "worst change · pick any junction"}
          fields={[
            { k: "points today", v: `${sel.today_points}` },
            { k: "points after", v: `${sel.scheme_junction_points}`, tone: "ok" },
            { k: "crossing exposure now", v: sel.today_crossing_exposure.toLocaleString("en-US") },
            { k: "after", v: sel.scheme_crossing_exposure.toLocaleString("en-US"), tone: "bad" },
            { k: "change", v: `${(sel.change_pct ?? 0) > 0 ? "+" : ""}${sel.change_pct}%`,
              tone: (sel.change_pct ?? 0) > 0 ? "bad" : "ok" },
            { k: "of which at the U-turn", v: sel.uturn_crossing_exposure.toLocaleString("en-US"),
              tone: "bad" },
          ]}
        />

        <p className="col" style={{ borderLeft: "3px solid var(--defect)", paddingLeft: ".9rem" }}>
          <strong>The scheme removes eight conflict points per junction and raises
          crossing exposure by {s.mean_change_pct}%.</strong> Removing the right turn from
          the junction genuinely removes conflicts there. It does not remove the demand.
          Every one of those vehicles reappears at a mid-block U-turn opening, crossing the
          opposing through stream with no signal to meter it and no junction geometry to
          slow it. The conflicts are relocated from a controlled place to an uncontrolled
          one, which is the opposite of what the scheme is sold on.
        </p>

        {!s.pedestrian_column_present && (
          <p className="col" style={{ borderLeft: "3px solid var(--defect)", paddingLeft: ".9rem" }}>
            <strong>The survey contains no pedestrian column.</strong> Not a low count
            &mdash; no column at all. The red phase is the only protected crossing
            opportunity a pedestrian on this corridor currently has, and the scheme removes
            it without anyone having measured who uses it.
          </p>
        )}
      </div>
    </div>
  );
}
