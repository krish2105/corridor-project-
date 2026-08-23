"use client";

/**
 * Corridor flow raster: distance along the corridor against time.
 *
 * This is what stands in place of a time-space diagram, and the substitution is
 * deliberate. A time-space diagram reads a green band across successive signals, and
 * bandwidth is DEFINED as time inside a green phase. This corridor is being made
 * signal-free, so there would be no band to read and no efficiency to quote — an
 * engineer who knows that discounts every exhibit standing next to it.
 *
 * What survives is the frame, not the figure. Distance up the vertical, time across,
 * colour by through flow on each link. It shows the same physical thing a time-space
 * diagram is usually wheeled out to show — whether the peak arrives everywhere at once
 * or travels along the corridor — using only counts we actually hold.
 */
type Cell = { link: number; junction: string; t: string; veh: number };

export default function FlowRaster({ cells, order }: { cells: Cell[]; order: string[] }) {
  const times = [...new Set(cells.map((c) => c.t))].sort();
  const max = Math.max(...cells.map((c) => c.veh));
  const at = (link: number, t: string) => cells.find((c) => c.link === link && c.t === t);

  // one column per bin is unreadable at phone width, so show every other bin
  const cols = times.filter((_, i) => i % 2 === 0);

  return (
    <div className="card">
      <header>
        <h3>The peak, along the corridor and through the day</h3>
        <span className="tag">{order.length} links &times; {times.length} bins</span>
      </header>
      <div className="body">
        <div className="tscroll">
          <table style={{ minWidth: "46rem", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ position: "sticky", left: 0, background: "var(--sunk)" }}>Junction</th>
                {cols.filter((_, i) => i % 6 === 0).map((t) => (
                  <th key={t} colSpan={6} className="num">{t}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {order.map((code, link) => (
                <tr key={code}>
                  <th style={{ textAlign: "left", position: "sticky", left: 0,
                               background: "var(--sunk)" }}>{code}</th>
                  {cols.map((t) => {
                    const c = at(link, t);
                    const v = c?.veh ?? 0;
                    const f = max ? v / max : 0;
                    return (
                      <td key={t} style={{
                        padding: 0, width: 6, height: 26, border: 0,
                        background: `color-mix(in srgb, var(--defect) ${Math.round(f * 100)}%, var(--surface))`,
                      }} title={`${code} ${t} — ${v.toLocaleString("en-US")} veh through, 15 min`} />
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: ".6rem", fontSize: ".7rem",
                      color: "var(--muted)" }}>
          <span className="mono">0</span>
          <span style={{ flex: 1, height: 8, borderRadius: 2,
                         background: "linear-gradient(to right, var(--surface), var(--defect))" }} />
          <span className="mono">{max.toLocaleString("en-US")} veh / 15 min</span>
        </div>

        <p className="col">Rows run north to south along the corridor in chainage order,
        columns run 08:00 to 08:00. Colour is through flow on that link in that
        fifteen-minute bin. Hover any cell for the count.</p>

        <p className="col" style={{ borderLeft: "3px solid var(--accent)", paddingLeft: ".9rem" }}>
          <strong>This replaces a time-space diagram, deliberately.</strong> A time-space
          diagram exists to show a green band travelling across successive signals, and
          bandwidth is <em>defined</em> as time inside a green phase. This corridor is
          being made signal-free: there would be no band to read and no efficiency to
          quote. The frame survives, the figure does not. What is left shows the same
          physical question &mdash; does the peak arrive everywhere at once, or travel
          along the corridor &mdash; from counts we actually hold.
        </p>
      </div>
    </div>
  );
}
