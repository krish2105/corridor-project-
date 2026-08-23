"use client";
import { useEffect, useMemo, useState } from "react";

/**
 * Change the assumptions and watch the conclusions.
 *
 * The obvious objection to handing a reader this control is that it invites them to hunt
 * for the combination where the problem disappears. That is exactly why it is here. Every
 * conclusion on this page was already re-run across its whole assumption grid before
 * publication; this exposes that grid instead of asserting the result of it. If the
 * problem cannot be made to disappear, the reader proving that to themselves is worth
 * more than us claiming it.
 *
 * Results are LOOKED UP from the precomputed grids, never approximated in the browser.
 * The one thing computed here is the design-life year, which is a closed form.
 */
type Elev = { uplift: number; lane_cap: number; lanes: number; ok: number; total: number };
type Queue = { packing: number; footprint: number; lane_cap: number; spillback: number; total: number };
type DL = { junction: string; approach: string; vc_after: number };
type Props = {
  axes: Record<string, (number | string)[]>;
  elevated: Elev[];
  queue: Queue[];
  uturn: Record<string, { fails: number; of: number }>;
  designLife: DL[];
  baseYear: number;
  horizon: number;
  /** the seconds each critical-gap mode actually means, so the control can say so */
  gapSeconds: { optimistic: number; conservative: number };
};

function failureYear(vc: number, growthPct: number, base: number) {
  if (vc >= 1) return base;
  return base + Math.ceil(Math.log(1 / vc) / Math.log(1 + growthPct / 100));
}

export default function ScenarioTool(p: Props) {
  const gapS = p.gapSeconds;
  const [uplift, setUplift] = useState(p.axes.pcu_uplift_pct[0] as number);
  const [laneCap, setLaneCap] = useState(p.axes.lane_capacity_pcu[0] as number);
  const [lanes, setLanes] = useState(p.axes.lanes_per_direction[0] as number);
  const [gap, setGap] = useState(p.axes.critical_gap[0] as string);
  const [growth, setGrowth] = useState(p.axes.growth_pct[1] as number);
  const [seen, setSeen] = useState<Set<string>>(new Set());

  const key = `${uplift}|${laneCap}|${lanes}|${gap}|${growth}`;
  const total = Object.values(p.axes).reduce((n, a) => n * a.length, 1);

  const result = useMemo(() => {
    const e = p.elevated.find((x) => x.uplift === uplift && x.lane_cap === laneCap && x.lanes === lanes);
    const q = p.queue.find((x) => x.lane_cap === laneCap && x.packing === 0.75 && x.footprint === 1.0)
           ?? p.queue.find((x) => x.lane_cap === laneCap);
    const u = p.uturn[gap];
    const years = p.designLife.map((d) => failureYear(d.vc_after, growth, p.baseYear));
    return {
      elevatedOk: e?.ok ?? null, elevatedTotal: e?.total ?? 12,
      spillback: q?.spillback ?? null, spillbackTotal: q?.total ?? 10,
      uturnFails: u?.fails ?? null, uturnTotal: u?.of ?? 12,
      firstFailure: Math.min(...years), survive: years.filter((y) => y > p.horizon).length,
      totalApproaches: years.length,
    };
  }, [uplift, laneCap, lanes, gap, growth, p]);

  // Record the combination once it has been viewed.
  //
  // In useEffect, not in render. The first version fired a setTimeout from the render
  // body, which React correctly warns about: a side effect during render can update a
  // component that has not mounted, and in StrictMode it runs twice.
  useEffect(() => {
    setSeen((s) => (s.has(key) ? s : new Set(s).add(key)));
  }, [key]);

  const held =
    (result.uturnFails ?? 0) > 0 &&
    (result.spillback ?? 0) > 0 &&
    result.survive === 0;

  const Row = ({ label, values, value, set, fmt }: {
    label: string; values: (number | string)[]; value: number | string;
    set: (v: never) => void; fmt?: (v: number | string) => string;
  }) => (
    <div style={{ display: "grid", gridTemplateColumns: "10rem 1fr", gap: ".8rem", alignItems: "center" }}>
      <span className="mono" style={{ fontSize: ".68rem", color: "var(--muted)" }}>{label}</span>
      <div className="picker">
        {values.map((v) => (
          <button key={String(v)} aria-pressed={v === value} onClick={() => set(v as never)}>
            {v === value && <span className="pill" />}
            <span className="lab">{fmt ? fmt(v) : String(v)}</span>
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div className="card">
      <header>
        <h3>Change the assumptions</h3>
        <span className="tag">{seen.size} of {total} combinations viewed</span>
      </header>
      <div className="body">
        <p className="col">Every conclusion here was already re-run across this whole
        grid before publication. This exposes the grid rather than asserting its result.
        Results are looked up from the precomputed runs, not approximated in the browser.</p>

        <div style={{ display: "flex", flexDirection: "column", gap: ".6rem" }}>
          <Row label="PCU uplift" values={p.axes.pcu_uplift_pct} value={uplift}
               set={setUplift as never} fmt={(v) => `+${v}%`} />
          <Row label="Lane capacity" values={p.axes.lane_capacity_pcu} value={laneCap}
               set={setLaneCap as never} fmt={(v) => `${v} PCU`} />
          <Row label="Lanes per dir" values={p.axes.lanes_per_direction} value={lanes}
               set={setLanes as never} />
          {/* "optimistic"/"conservative" alone tells the reader nothing about what
              they are choosing between - name the seconds each one means. */}
          <Row label="Critical gap" values={p.axes.critical_gap} value={gap}
               set={setGap as never}
               fmt={(v) => `${v} \u00b7 ${v === "optimistic"
                 ? gapS.optimistic.toFixed(2) : gapS.conservative.toFixed(2)}s`} />
          <Row label="Growth" values={p.axes.growth_pct} value={growth}
               set={setGrowth as never} fmt={(v) => `${v}%/yr`} />
        </div>

        <div className="scope">
          <div>
            <span className="k num" style={{ color: (result.uturnFails ?? 0) > 0 ? "var(--defect)" : "var(--ok)" }}>
              {result.uturnFails}/{result.uturnTotal}</span>
            <span className="l">U-turn approaches unservable</span>
          </div>
          <div>
            <span className="k num" style={{ color: result.elevatedOk === result.elevatedTotal ? "var(--ok)" : "var(--defect)" }}>
              {result.elevatedOk}/{result.elevatedTotal}</span>
            <span className="l">relieved on opening</span>
          </div>
          <div>
            <span className="k num" style={{ color: (result.spillback ?? 0) > 0 ? "var(--defect)" : "var(--ok)" }}>
              {result.spillback}/{result.spillbackTotal}</span>
            <span className="l">queues block upstream</span>
          </div>
          <div>
            <span className="k num" style={{ color: "var(--defect)" }}>{result.firstFailure}</span>
            <span className="l">first approach back over</span>
          </div>
          <div>
            <span className="k num" style={{ color: result.survive === 0 ? "var(--defect)" : "var(--ok)" }}>
              {result.survive}/{result.totalApproaches}</span>
            <span className="l">hold to {p.horizon}</span>
          </div>
        </div>

        <p className="col" style={{
          borderLeft: `3px solid ${held ? "var(--defect)" : "var(--ok)"}`, paddingLeft: ".9rem" }}>
          {held ? (
            <>
              <strong>All three conclusions still hold at these assumptions.</strong> The
              U-turn bays cannot serve the demand, queues still block the junction behind
              them, and no approach survives to {p.horizon}. You have viewed{" "}
              <strong>{seen.size}</strong> of {total} combinations.
            </>
          ) : (
            <>
              <strong>At least one conclusion changes here.</strong> That is worth knowing
              and it is why this control exists &mdash; the combination is{" "}
              <span className="mono">{key}</span>. Check whether it sits inside the
              defensible range for each assumption before treating it as a way out.
            </>
          )}
        </p>
      </div>
    </div>
  );
}
