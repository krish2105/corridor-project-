"use client";
import { useEffect, useState } from "react";
import ConflictDiagram from "./ConflictDiagram";
import LosHeatmap from "./LosHeatmap";
import ScenarioTool from "./ScenarioTool";
import VolumeFlow from "./VolumeFlow";
import Reveal from "./Reveal";

/**
 * The analytical exhibits, and the series they need.
 *
 * corridor.json is fetched on every page view, so it carries summaries only. The per-bin
 * series behind these figures — 1,116 LOS cells, 96-step cumulative curves, five
 * continuity series — are fetched here, when a reader reaches the section that needs
 * them. An officer opening this in a meeting should not wait for data they may never
 * scroll to.
 *
 * Kept out of page.tsx deliberately: that file is already long enough that finding
 * anything in it is work.
 */
type Series = {
  los_grid?: { junction: string; approach: string; hour: string; pcu: number; vc: number; los: string }[];
  cumulative?: { junction: string; approach: string; capacity: number; peak_queue_pcu: number;
                 series: { t: string; arrivals: number; departures: number; queue: number }[] };
  volume_flow?: never[];
  continuity?: { north: string; south: string; daily_out: number; daily_in: number;
                 mean_residual_pct: number; worst_residual_pct: number }[];
};

export default function Exhibits({ safety, profiles, exhibits, sensitivity, capacity }: {
  safety: never; profiles: never; exhibits: never; sensitivity: never; capacity: never;
}) {
  const [prof, setProf] = useState<Series | null>(null);
  const [exh, setExh] = useState<Series | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    setBusy(true);
    Promise.all([
      fetch("/profiles_series.json").then((r) => r.json()).catch(() => null),
      fetch("/exhibits_series.json").then((r) => r.json()).catch(() => null),
    ]).then(([a, b]) => {
      if (!live) return;
      setProf(a); setExh(b); setBusy(false);
    });
    return () => { live = false; };
  }, []);

  const s = safety as unknown as { junctions: { junction: string }[] } | null;
  const cap = capacity as unknown as {
    design_life: { junction: string; approach: string; vc_after: number }[];
    horizon_year: number; assumptions: { base_year: number };
  } | null;
  const sen = sensitivity as unknown as {
    axes: Record<string, (number | string)[]>;
    elevated: never[]; queue: never[]; uturn: Record<string, { fails: number; of: number }>;
  } | null;

  const junctions = s ? [...new Set(s.junctions.map((r) => r.junction))].sort() : [];

  return (
    <>
      {/* CONFLICT AND SAFETY */}
      {safety && (
        <section>
          <Reveal><p className="eyebrow">What the scheme does to conflicts</p></Reveal>
          <Reveal delay={.04}>
            <h2 style={{ marginTop: ".5rem" }}>Fewer conflict points. More exposure.</h2>
          </Reveal>
          <Reveal delay={.08}>
            <p className="col lede" style={{ marginTop: "1rem" }}>
              A signal-free scheme is sold as safer, and by one measure it is: removing the
              right turn from a junction removes eight of its thirty-two conflict points.
              The demand does not leave with them.
            </p>
          </Reveal>
          <div style={{ marginTop: "1.4rem" }}>
            <Reveal delay={.1}><ConflictDiagram s={safety} /></Reveal>
          </div>
        </section>
      )}

      {/* THE WHOLE DAY */}
      {profiles && (
        <section>
          <Reveal><p className="eyebrow">Beyond the peak hour</p></Reveal>
          <Reveal delay={.04}>
            <h2 style={{ marginTop: ".5rem" }}>The peak has already spread</h2>
          </Reveal>
          <Reveal delay={.08}>
            <p className="col lede" style={{ marginTop: "1rem" }}>
              Every volume-capacity ratio published above is the peak hour, which is the
              convention and which hides the finding. These approaches are over capacity
              for a mean of{" "}
              <strong>{(profiles as unknown as { mean_hours_over: number }).mean_hours_over} hours
              a day</strong>. A corridor with a real peak has a spike; one whose peak has
              spread has a plateau, and peak-hour capacity does not fix a plateau.
            </p>
          </Reveal>
          <div style={{ marginTop: "1.4rem" }}>
            {busy && <p className="col" style={{ color: "var(--muted)" }}>Loading hourly series…</p>}
            {prof?.los_grid && junctions.length > 0 && (
              <Reveal delay={.1}><LosHeatmap grid={prof.los_grid} junctions={junctions} /></Reveal>
            )}
          </div>
        </section>
      )}

      {/* VOLUME FLOW */}
      {exh?.volume_flow && (
        <section>
          <Reveal><p className="eyebrow">The movements themselves</p></Reveal>
          <Reveal delay={.04}>
            <h2 style={{ marginTop: ".5rem" }}>Where the traffic actually goes</h2>
          </Reveal>
          <Reveal delay={.08}>
            <p className="col lede" style={{ marginTop: "1rem" }}>
              The turning-movement diagram, drawn to volume. Left turns are the next arm
              clockwise because India drives on the left, so the right turn is the movement
              that crosses opposing traffic &mdash; and the one the scheme converts into a
              U-turn.
            </p>
          </Reveal>
          <div className="grid2" style={{ marginTop: "1.4rem" }}>
            {(exh.volume_flow as never[]).slice(0, 2).map((j, i) => (
              <Reveal key={i} delay={.1 + i * .04}><VolumeFlow j={j} /></Reveal>
            ))}
          </div>
        </section>
      )}

      {/* SCENARIO TOOL */}
      {sen && cap && (
        <section>
          <Reveal><p className="eyebrow">Try to break it</p></Reveal>
          <Reveal delay={.04}>
            <h2 style={{ marginTop: ".5rem" }}>Change the assumptions yourself</h2>
          </Reveal>
          <Reveal delay={.08}>
            <p className="col lede" style={{ marginTop: "1rem" }}>
              Every conclusion above rests on judgements. Rather than ask you to accept
              ours, here they are as controls. If the problem can be made to disappear
              inside the defensible range, that is worth knowing &mdash; and if it cannot,
              you proving that is worth more than us claiming it.
            </p>
          </Reveal>
          <div style={{ marginTop: "1.4rem" }}>
            <Reveal delay={.1}>
              <ScenarioTool axes={sen.axes} elevated={sen.elevated} queue={sen.queue}
                            uturn={sen.uturn} designLife={cap.design_life}
                            baseYear={cap.assumptions.base_year} horizon={cap.horizon_year} />
            </Reveal>
          </div>
        </section>
      )}
    </>
  );
}
