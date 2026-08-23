"use client";
import { useEffect, useState } from "react";
import ConflictDiagram from "./ConflictDiagram";
import Standards from "./Standards";
import CumulativeQueue from "./CumulativeQueue";
import Tornado from "./Tornado";
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
  cumulative?: { junction: string; approach: string; capacity: number;
                 peak_queue_pcu: number; peak_queue_band: number[];
                 series: { t: string; arrivals: number; departures: number;
                           dep_low: number; dep_high: number; queue: number }[] };
  volume_flow?: never[];
  continuity?: { north: string; south: string; daily_out: number; daily_in: number;
                 mean_residual_pct: number; worst_residual_pct: number }[];
};

export default function Exhibits({ safety, profiles, exhibits, sensitivity, capacity, standards }: {
  safety: never; profiles: never; exhibits: never; sensitivity: never; capacity: never;
  standards: never;
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
      {/* MEASURED AGAINST THE CODE */}
      {standards && (
        <section>
          <Reveal><p className="eyebrow">Against the codes that govern it</p></Reveal>
          <Reveal delay={.04}>
            <h2 style={{ marginTop: ".5rem" }}>
              The scheme&rsquo;s own stated basis does not match the survey
            </h2>
          </Reveal>
          <Reveal delay={.08}>
            <p className="col lede" style={{ marginTop: "1rem" }}>
              Every check below compares a figure from this survey against a clause
              anyone can look up. Where a clause could not be verified from a primary
              source it is marked, because a stated uncertainty is more useful than a
              silent omission.
            </p>
          </Reveal>
          <div style={{ marginTop: "1.4rem" }}>
            <Reveal delay={.1}><Standards s={standards} /></Reveal>
          </div>
        </section>
      )}

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
            {prof?.cumulative && (
              <div style={{ marginTop: "1.2rem" }}>
                <Reveal delay={.12}><CumulativeQueue c={prof.cumulative} /></Reveal>
              </div>
            )}
          </div>
        </section>
      )}

      {/* VOLUME FLOW — all six junctions, selectable */}
      {exh?.volume_flow && (
        <section>
          <Reveal><p className="eyebrow">The movements themselves</p></Reveal>
          <Reveal delay={.04}>
            <h2 style={{ marginTop: ".5rem" }}>Where the traffic actually goes</h2>
          </Reveal>
          <Reveal delay={.08}>
            <p className="col lede" style={{ marginTop: "1rem" }}>
              The intersection volume diagram, drawn to peak-hour volume. Pick any of the
              six junctions and isolate any movement. Left turns hug the kerb because
              India drives on the left; the right turn swings across the whole junction
              against opposing traffic, and it is the one the scheme converts into a
              U-turn.
            </p>
          </Reveal>
          <div style={{ marginTop: "1.4rem" }}>
            <Reveal delay={.1}>
              <VolumeFlow junctions={exh.volume_flow as never} />
            </Reveal>
          </div>
        </section>
      )}

      {/* WHAT MOVES THE ANSWER */}
      {(exhibits as unknown as { tornado?: never })?.tornado && (
        <section>
          <Reveal><p className="eyebrow">Which assumption matters</p></Reveal>
          <Reveal delay={.04}>
            <h2 style={{ marginTop: ".5rem" }}>The correction runs both ways</h2>
          </Reveal>
          <Reveal delay={.08}>
            <p className="col lede" style={{ marginTop: "1rem" }}>
              The survey applied one static factor per vehicle class. IRC:106 makes the
              factor depend on that class&rsquo;s share of the stream. Correcting it does
              not simply raise the numbers.
            </p>
          </Reveal>
          <div style={{ marginTop: "1.4rem" }}>
            <Reveal delay={.1}>
              <Tornado t={(exhibits as unknown as { tornado: never }).tornado} />
            </Reveal>
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
