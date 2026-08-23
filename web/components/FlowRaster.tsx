"use client";
import { useGridCursor } from "@/lib/useGridCursor";
import Readout from "./Readout";

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
 *
 * Every one of the 96 bins is drawn. An earlier version rendered every other bin while
 * the caption still claimed 96, so the reader was told one thing and shown half of it.
 * At 6 px a column the full day is ~580 px, which fits the scroller already here.
 */
type Cell = { link: number; junction: string; t: string; veh: number };

export default function FlowRaster({ cells, order }: { cells: Cell[]; order: string[] }) {
  const times = [...new Set(cells.map((c) => c.t))].sort();
  const max = Math.max(...cells.map((c) => c.veh));
  const byKey = new Map(cells.map((c) => [`${c.link}|${c.t}`, c]));
  const at = (link: number, t: string) => byKey.get(`${link}|${t}`);

  const { active, pinned, cellProps, bodyProps, clear } = useGridCursor(order.length, times.length);

  // with nothing selected, show the busiest cell — the one the reader would look for
  const peak = cells.reduce((a, b) => (b.veh > a.veh ? b : a), cells[0]);
  const sel = active ? at(active.r, times[active.c]) : peak;
  const shareOfPeak = sel && max ? Math.round((100 * sel.veh) / max) : 0;

  return (
    <div className="card">
      <header>
        <h3>The peak, along the corridor and through the day</h3>
        <span className="tag">{order.length} links &times; {times.length} bins</span>
      </header>
      <div className="body">
        <div className="tscroll">
          <table style={{ minWidth: `${times.length * 6 + 90}px`, borderCollapse: "collapse" }}
                 role="grid" aria-label="Through flow by link and fifteen-minute bin">
            <thead>
              <tr>
                <th style={{ position: "sticky", left: 0, background: "var(--sunk)", zIndex: 3 }}>
                  Junction</th>
                {times.filter((_, i) => i % 12 === 0).map((t) => (
                  <th key={t} colSpan={12} className="num">{t}</th>
                ))}
              </tr>
            </thead>
            <tbody {...bodyProps}>
              {order.map((code, link) => (
                <tr key={code}>
                  <th style={{ textAlign: "left", position: "sticky", left: 0,
                               background: "var(--sunk)", zIndex: 2 }}>{code}</th>
                  {times.map((t, ci) => {
                    const v = at(link, t)?.veh ?? 0;
                    const f = max ? v / max : 0;
                    return (
                      <td key={t} className="gcell" {...cellProps(link, ci)}
                          aria-label={`${code} ${t}, ${v} vehicles`}
                          style={{
                            padding: 0, width: 6, height: 26, border: 0,
                            background: `color-mix(in srgb, var(--defect) ${Math.round(f * 100)}%, var(--surface))`,
                          }} />
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="tscroll-note">scrolls sideways &mdash; {times.length} bins, 08:00 to 08:00</p>

        <div style={{ display: "flex", alignItems: "center", gap: ".6rem", fontSize: ".7rem",
                      color: "var(--muted)", marginTop: ".5rem" }}>
          <span className="mono">0</span>
          <span style={{ flex: 1, height: 8, borderRadius: 2,
                         background: "linear-gradient(to right, var(--surface), var(--defect))" }} />
          <span className="mono">{max.toLocaleString("en-US")} veh / 15 min</span>
        </div>

        {sel && (
          <Readout
            title={`${sel.junction} · ${sel.t}`}
            pinned={!!pinned}
            onClear={clear}
            hint={active ? "click to pin" : "busiest bin · pick any cell"}
            fields={[
              { k: "through flow", v: `${sel.veh.toLocaleString("en-US")} veh / 15 min` },
              { k: "hourly rate", v: `${(sel.veh * 4).toLocaleString("en-US")} veh/hr` },
              { k: "share of corridor peak", v: `${shareOfPeak}%`,
                tone: shareOfPeak >= 80 ? "bad" : undefined },
              { k: "link", v: `${sel.junction}, position ${sel.link + 1} of ${order.length}` },
            ]}
          />
        )}

        <p className="col">Rows run north to south along the corridor in chainage order,
        columns run 08:00 to 08:00. Colour is through flow on that link in that
        fifteen-minute bin. Pick any cell &mdash; tap, click or arrow-key &mdash; and it
        reads out below; click again to pin it.</p>

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
