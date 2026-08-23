"use client";
import {
  Area, ComposedChart, CartesianGrid, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

/**
 * Newell's cumulative arrival-departure diagram.
 *
 * The vertical gap between the curves is the queue at that instant. The horizontal gap
 * is the delay to a vehicle arriving then. The area between them is total delay. All
 * three are read off one picture with a ruler, which is why this beats a bar chart
 * captioned "mean delay 17.5 minutes" — the bar asserts a number, this shows the
 * mechanism that produced it.
 *
 * Arrivals are MEASURED, a running sum of counted vehicles. Departures need a discharge
 * rate that a classified count does not contain, so they are drawn as a band. The one
 * contestable line on the figure is on the page where a reader can argue with it.
 */
type Pt = { t: string; arrivals: number; departures: number; dep_low: number;
            dep_high: number; queue: number };
type C = { junction: string; approach: string; capacity: number;
           peak_queue_pcu: number; peak_queue_band: number[]; series: Pt[] };

const nf = new Intl.NumberFormat("en-US");

export default function CumulativeQueue({ c }: { c: C }) {
  const data = c.series.map((p) => ({
    ...p,
    // Recharts stacks an Area from a base, so the band is drawn as [low, high]
    band: [p.dep_low, p.dep_high] as [number, number],
  }));
  return (
    <div className="card">
      <header>
        <h3>Cumulative arrivals against departures</h3>
        <span className="tag">{c.junction} {c.approach.replace("from ", "")}</span>
        <span className="tag">{nf.format(c.capacity)} PCU/hr</span>
      </header>
      <div className="body">
        <div style={{ width: "100%", height: 300 }}>
          <ResponsiveContainer>
            <ComposedChart data={data} margin={{ top: 6, right: 10, bottom: 0, left: 4 }}>
              <CartesianGrid stroke="var(--rule)" vertical={false} />
              <XAxis dataKey="t" interval={11} tick={{ fontSize: 10, fill: "var(--faint)" }}
                     tickLine={false} axisLine={{ stroke: "var(--rule)" }} />
              <YAxis tick={{ fontSize: 10, fill: "var(--faint)" }} width={58}
                     tickLine={false} axisLine={false}
                     tickFormatter={(v: number) => nf.format(v)} />
              <Tooltip
                contentStyle={{ background: "var(--surface)", border: "1px solid var(--rule)",
                                borderRadius: 4, fontSize: 12, color: "var(--ink)",
                                fontFamily: "IBM Plex Mono, monospace" }}
                labelStyle={{ color: "var(--muted)" }}
                formatter={(v: number | number[], n: string) =>
                  [Array.isArray(v) ? `${nf.format(v[0])}–${nf.format(v[1])}` : nf.format(v), n]} />
              <Legend wrapperStyle={{ fontSize: 11, color: "var(--muted)" }} />
              <Area dataKey="band" name="departures, discharge band"
                    stroke="none" fill="var(--defect)" fillOpacity={.16} />
              <Line dataKey="arrivals" name="arrivals (measured)" dot={false}
                    stroke="var(--accent)" strokeWidth={2} />
              <Line dataKey="departures" name="departures (assumed)" dot={false}
                    stroke="var(--defect)" strokeWidth={1.6} strokeDasharray="5 3" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="scope">
          <div><span className="k num" style={{ color: "var(--defect)" }}>
            {nf.format(c.peak_queue_pcu)}</span><span className="l">peak queue, PCU</span></div>
          <div><span className="k num">
            {nf.format(c.peak_queue_band[0])}&ndash;{nf.format(c.peak_queue_band[1])}</span>
            <span className="l">band across discharge</span></div>
        </div>

        <p className="col">The <strong>vertical</strong> gap between the curves is the
        queue at that moment. The <strong>horizontal</strong> gap is the delay to a
        vehicle arriving then. The <strong>area</strong> between them is total delay. All
        three are read off one figure, which is why this is here instead of a bar labelled
        with an averaged number.</p>

        <p className="col" style={{ borderLeft: "3px solid var(--accent)", paddingLeft: ".9rem" }}>
          <strong>Arrivals are measured; departures are assumed.</strong> The arrival
          curve is a running sum of counted vehicles. The departure curve needs a
          discharge rate, which a classified count does not contain &mdash; so it is drawn
          as a band rather than a line. It is the one contestable assumption on this
          figure and it is on the page, not buried inside an averaged delay.
        </p>
      </div>
    </div>
  );
}
