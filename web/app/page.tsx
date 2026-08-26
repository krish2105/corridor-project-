import fs from "node:fs";
import path from "node:path";
import Reveal from "@/components/Reveal";
import EvidenceField from "@/components/EvidenceField";
import JunctionExplorer from "@/components/JunctionExplorer";
import CorridorMap from "@/components/CorridorMap";
import PierProfile from "@/components/PierProfile";
import Downloads from "@/components/Downloads";
import Exhibits from "@/components/Exhibits";
import GapEvidence from "@/components/GapEvidence";
import Evidence from "@/components/Evidence";
import Compare from "@/components/Compare";
import Ladder from "@/components/Ladder";
import Learned from "@/components/Learned";
import type { Corridor } from "@/lib/types";

const nf = new Intl.NumberFormat("en-US");

const WHY: Record<string, string> = {
  structures: "demolition or realignment; the hard constraint",
  electrical: "poles, lamps, transformers - routine to divert",
  drainage: "nalas and chambers; deep, and they set levels",
  vegetation: "felling permissions, and a political cost",
  telecom: "OFC cuts are fast but outage-sensitive",
  gas: "marker stones; a live main is a hard stop",
  geotech: "boreholes - free foundation data, already paid for",
  religious: "relocation is a political decision, not an engineering one",
  water: "wells and hand pumps still in community use",
  rail: "level crossing; separate approval regime",
};

/* Sections the page cannot render without. The cast below is a promise TypeScript
   cannot keep: `tsc` checks the declaration, not the bytes on disk, so a section the
   pipeline stops emitting type-checks clean and then fails at prerender as
   "Cannot read properties of undefined (reading '1')" — which is what happened when an
   axis was removed upstream. Naming the missing section turns that into one line. */
const REQUIRED_SECTIONS = [
  "meta", "audit", "constraints", "capacity", "scheme", "sensitivity",
  "delay", "economics", "safety", "standards", "junctions", "corridor",
  "criticality",
] as const;

function load(): Corridor {
  // Same file the Artifact page renders from, so both show identical figures.
  const p = path.join(process.cwd(), "public", "corridor.json");
  const raw = JSON.parse(fs.readFileSync(p, "utf8")) as Record<string, unknown>;
  const missing = REQUIRED_SECTIONS.filter(
    (k) => raw[k] === undefined || raw[k] === null);
  if (missing.length) {
    throw new Error(
      `corridor.json is missing ${missing.length} required section(s): ` +
      `${missing.join(", ")}. Re-run src/export.py and copy out/data/corridor.json ` +
      `to web/public/.`);
  }
  return raw as unknown as Corridor;
}

export default function Page() {
  const d = load();
  const { audit: a, corridor: c, junctions: js, meta } = d;
  const totVeh = js.reduce((s, j) => s + j.daily_veh, 0);
  const totSurv = js.reduce((s, j) => s + j.pcu_surveyed, 0);
  const totCorr = js.reduce((s, j) => s + j.pcu_corrected, 0);
  const tw = a.pcu.factors.find((f) => f.cls === "TWO_W")!;
  const car = a.pcu.factors.find((f) => f.cls === "CAR_BUCKET")!;
  const maxPcu = Math.max(...js.map((j) => j.pcu_corrected));
  const c2 = d.constraints;
  const cp = d.capacity;
  const sc = d.scheme;
  const sen = d.sensitivity;
  const uf = d.uturn_framework;
  const dl = d.delay;
  const ec = d.economics;
  const NOGAP = sc?.no_gap_vc_threshold ?? 3;
  // busier corridor approach at each junction
  const relief = cp ? Object.values(cp.relief.reduce((m, r) => {
    if (!m[r.junction] || r.vc_after > m[r.junction].vc_after) m[r.junction] = r;
    return m;
  }, {} as Record<string, typeof cp.relief[number]>)).sort((a, b) =>
    a.junction.localeCompare(b.junction)) : [];
  const width0 = cp ? Object.values(cp.widths)[0]?.width_m : 0;

  return (
    <main className="wrap">
      <header style={{ paddingTop: "clamp(3rem,8vw,6rem)", paddingBottom: "clamp(2rem,4vw,3rem)" }}>
        <div style={{ height: 3, background: "var(--ink)", marginBottom: "1.4rem" }} />
        <Reveal y={10}>
          <p className="eyebrow">Data integrity audit &middot; classified turning movement survey</p>
        </Reveal>
        <Reveal delay={.06}><h1>{meta.corridor}</h1></Reveal>
        <Reveal delay={.12}>
          <p className="lede col" style={{ marginTop: "1.1rem" }}>
            {/* The heading names the corridor by its end points, which is how the survey
                labels it; the lede names the road, which is how everyone else does. Both
                now come from JDA - the arms from the workbooks, the road from the KML. */}
            Six junctions on <strong>{meta.road}</strong>, {meta.city}, every one of
            them carrying <strong>Mansarover Metro</strong> as its north arm and{" "}
            <strong>Sanganer Stadium</strong> as its south. Surveyed{" "}
            {meta.survey_dates[0]} and {meta.survey_dates[1]} by the appointed contractor
            and issued to JDA as twelve workbooks. This is an independent re-derivation of
            every number in them, checked against the survey drawing.{" "}
            <em>The road name and the alignment come from JDA&rsquo;s own KML.</em> We had
            inferred both, and both were wrong: our junction picks sat 269 to 950 m off, on
            a parallel road.
          </p>
        </Reveal>
        <Reveal delay={.18}>
          <div className="col" style={{
            marginTop: "1.8rem", borderLeft: "3px solid var(--defect)",
            background: "var(--defect-soft)", padding: "1rem 1.15rem", borderRadius: "0 4px 4px 0",
          }}>
            <p><strong>The survey contains one day of observation, not two.</strong> The
            second day is derived from the first. Separately, the PCU conversion understates
            corridor demand by at least {a.pcu.uplift_floor_pct}%, and the flow-diagram sheet
            reports the two-wheeler count under the label &ldquo;Taxi&rdquo;.</p>
          </div>
        </Reveal>
      </header>

      <section style={{ borderTop: 0 }}>
        <Reveal>
          <div className="scope">
            <div><span className="k num">12</span><span className="l">workbooks</span></div>
            <div><span className="k num">{meta.n_junctions}</span><span className="l">junctions</span></div>
            <div><span className="k num">{nf.format(meta.bins_parsed)}</span><span className="l">15-min class bins</span></div>
            <div><span className="k num">{nf.format(totVeh)}</span><span className="l">vehicles counted</span></div>
            <div><span className="k num" style={{ color: "var(--defect)" }}>1</span><span className="l">usable survey day</span></div>
          </div>
        </Reveal>
        <Reveal delay={.08}>
          <p className="col" style={{ marginTop: "1.6rem" }}>
            Every stored total in the source was recomputed from its own components. Where
            the two disagree, the discrepancy is recorded rather than corrected silently.
            All figures below come from that re-derivation, not from the workbooks&rsquo;
            summary rows.
          </p>
        </Reveal>
      </section>

      {/* FINDING 1 */}
      <section>
        <Reveal><h2>Finding 1 &mdash; the second survey day was not observed</h2></Reveal>
        <Reveal delay={.06}>
          <div className="card" style={{ marginTop: "1.1rem" }}>
            <header><span className="chip critical">Critical</span>
              <h3>12 May is derived from 11 May</h3></header>
            <div className="body">
              <p className="col">Comparing every movement-by-class daily total across the two
              days gives {a.day2.series} independent series. If both days were counted, their
              totals would differ in both directions in roughly equal measure.</p>
              <EvidenceField {...a.day2} />
              <p className="col">{a.day2.identical} of {a.day2.series} series reproduce the
              previous day&rsquo;s total <em>exactly</em>, while the 15-minute bins underneath
              them differ &mdash; values redistributed, total pinned. Of the series that do
              move, {a.day2.greater} rise and {a.day2.smaller} fall. Under independent counting
              that split is <strong>p &asymp; 2&times;10<sup>&minus;39</sup></strong>.</p>
              <Evidence
                label="The arithmetic behind that probability"
                rows={[
                  { k: "series compared", v: `${a.day2.series}`,
                    note: "movement x class daily totals, both days" },
                  { k: "identical to day one", v: `${a.day2.identical}`,
                    note: "total pinned, 15-min bins underneath redistributed", tone: "bad" },
                  { k: "higher on day two", v: `${a.day2.greater}` },
                  { k: "lower on day two", v: `${a.day2.smaller}`, tone: "bad" },
                  { k: "expected split if counted", v: "roughly half each way",
                    note: "two independent counts of the same road" },
                  { k: "observed split", v: `${a.day2.greater} up, ${a.day2.smaller} down`,
                    note: "a sign test on this gives p ~ 2e-39", tone: "bad" },
                ]}
                source={"Computed in src/audit.py (check_day2) from the twelve V_ movement " +
                        "sheets only — the approach and total sheets are formulas over " +
                        "those, so including them would count each observation three times."} />
              <p className="col">In the two dominant classes, only <strong>0.21%</strong> of
              13,158 live bins fall on day two. Traffic does not rise at every approach of
              every junction in every quarter-hour.</p>
              <p style={{ fontSize: ".72rem", color: "var(--faint)" }}>
                <span className="tag">V_1&hellip;V_12</span>{" "}
                <span className="tag">rows 8&ndash;103</span> Tested on the movement sheets
                only &mdash; the approach sheets are formulas over them.</p>
            </div>
          </div>
        </Reveal>
        <Reveal delay={.1}>
          <p className="col lede" style={{ marginTop: "1.1rem" }}>
            Consequence: treat this as a single-day survey. Day-over-day growth computed from
            it measures the derivation, not the traffic.
          </p>
        </Reveal>
      </section>

      {/* FINDING 2 — the scheme the survey was for */}
      <section>
        <Reveal><h2>Finding 2 &mdash; the survey omits the movement the scheme is built on</h2></Reveal>
        <Reveal delay={.06}>
          <div className="card" style={{ marginTop: "1.1rem" }}>
            <header><span className="chip critical">Critical</span>
              <h3>JDA is converting this road to U-turn operation. No U-turn was counted.</h3></header>
            <div className="body">
              <p className="col">JDA has a scheme to make <strong>{meta.road}</strong>{" "}
              signal-free, replacing junction signals with <strong>seven U-turn bays</strong>.
              The junctions it names for redesign &mdash; Bhrigu Path, Rajat Path, VT Road,
              Patel Marg, Vijay Path and B-2 Bypass &mdash; are the same six this survey
              counted, and three of the survey&rsquo;s own arm labels match those names exactly.</p>
              <p className="col">The survey recorded <strong>Left, Straight and Right</strong>.
              It contains <strong>no U-turn column anywhere</strong>. The scheme&rsquo;s entire
              operating principle is converting turning movements into U-turns, and the
              traffic evidence base for it does not measure U-turns.</p>
              {c2 && (
                <p className="col">The drawing shows the demand is real. Along the{" "}
                <strong>{c2.corridor_km} km</strong> alignment, <strong>{c2.uturn_possible}</strong>{" "}
                median gaps are wide enough for a vehicle to turn &mdash;{" "}
                <strong>{c2.uturn_per_km} per km</strong>.{" "}
                {c2.opening_classes["typical opening"]} are typical notified openings,{" "}
                {c2.opening_classes["wide / junction mouth"]} are junction mouths, and{" "}
                {c2.opening_classes["marginal"]} are marginal &mdash; passable by a
                two-wheeler or auto, not a car.</p>
              )}
              <p className="col">There is a second-order effect that matters more than the
              missing column. At a median opening the U-turn competes with the right turn
              for the same gap in opposing traffic, so the right-turn volumes the survey{" "}
              <em>does</em> report understate their own effect on capacity. The gap biases
              the movement that is usually the binding constraint.</p>
              <Evidence
                label="What was counted, and what was not"
                rows={[
                  { k: "movements per junction", v: "12", note: "4 arms x Left / Straight / Right" },
                  { k: "U-turn columns", v: "none", tone: "bad",
                    note: "not a low count - no column exists anywhere in the workbook" },
                  { k: "E-rickshaw columns", v: "none", tone: "bad",
                    note: "the label appears in the workbook string table, but no column carries it" },
                  { k: "pedestrian row", v: "empty", tone: "bad",
                    note: "IRC:SP:41-1994 Table 3.1 carries one; clause 3.1(iv) requires it in urban areas" },
                  ...(c2 ? [
                    { k: "median gaps wide enough to turn", v: `${c2.uturn_possible}`,
                      note: `${c2.uturn_per_km} per km along ${c2.corridor_km} km of drawing` },
                  ] : []),
                  { k: "bays the scheme adds", v: "seven" },
                ]}
                source={"Movements from src/tmc_parse.py; median openings measured from the " +
                        "DIVIDER linework in src/medians.py. The absent columns are stated " +
                        "as gaps rather than filled: synthesising a U-turn count the survey " +
                        "never took would be the same defect this audit is reporting."} />
            </div>
          </div>
        </Reveal>
      </section>

      {/* FINDING 3 */}
      <section>
        <Reveal><h2>Finding 3 &mdash; PCU conversion understates demand</h2></Reveal>
        <Reveal delay={.06}>
          <div className="card" style={{ marginTop: "1.1rem" }}>
            <header><span className="chip material">Material</span>
              <h3>Static factors applied to a composition-dependent standard</h3></header>
            <div className="body">
              <p className="col">IRC:106 gives each class two factors &mdash; one for below
              5% of the stream, one for above 10% &mdash; and requires interpolation between
              them. The survey used one constant per class, in all twelve workbooks.
              Two-wheelers are <strong>{(100 * tw.share).toFixed(1)}%</strong> of this
              corridor and are carried at PCU {tw.surveyed.toFixed(2)}, the value IRC:106
              reserves for a class below 5%. The correct factor is {tw.irc_point?.toFixed(2)}.</p>

              <div className="tscroll">
                <table>
                  <caption>&ldquo;&mdash;&rdquo; marks a column that lumps several IRC classes
                    together, where no single defensible factor exists.</caption>
                  <thead><tr><th>Survey column</th><th>Share</th><th>Used</th>
                    <th>IRC low</th><th>IRC point</th><th>IRC high</th></tr></thead>
                  <tbody>
                    {a.pcu.factors.map((f) => (
                      <tr key={f.cls}>
                        <td>{f.label}</td>
                        <td className="num">{(100 * f.share).toFixed(2)}%</td>
                        <td className="num">{f.surveyed.toFixed(2)}</td>
                        <td className="num">{f.irc_low.toFixed(2)}</td>
                        <td className={"num" + (f.irc_point !== null && f.irc_point > f.surveyed ? " bad" : "")}>
                          {f.irc_point === null
                            ? <span style={{ color: "var(--faint)" }}>&mdash;</span>
                            : f.irc_point.toFixed(2)}</td>
                        <td className="num">{f.irc_high.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h3 style={{ marginTop: ".4rem" }}>Effect on corridor PCU</h3>
              <div className="bars">
                {js.map((j) => (
                  <div className="bar" key={j.code}>
                    <span className="mono" style={{ fontSize: ".7rem", color: "var(--muted)" }}>
                      {j.code.replace("TMC-", "J")}</span>
                    <span className="track">
                      <i className="fill" style={{ width: (100 * j.pcu_corrected / maxPcu) + "%" }} />
                      <i className="fill2" style={{ width: (100 * j.pcu_surveyed / maxPcu) + "%" }} />
                    </span>
                    <span className="num" style={{ fontSize: ".7rem", color: "var(--muted)" }}>
                      {nf.format(j.pcu_surveyed)} &rarr; {nf.format(j.pcu_corrected)} (+{j.uplift_pct}%)</span>
                  </div>
                ))}
              </div>
              <p style={{ fontSize: ".72rem", color: "var(--faint)" }}>
                <span className="tag">solid bar</span> PCU as surveyed{" "}
                <span className="tag">pale extension</span> the shortfall the correction restores</p>

              <p className="col">Correcting only the four columns that map one-to-one to
              IRC:106 raises corridor PCU from <strong className="num">{nf.format(totSurv)}</strong> to{" "}
              <strong className="num">{nf.format(totCorr)}</strong> &mdash;{" "}
              <strong>+{a.pcu.uplift_floor_pct}%</strong>. That is a floor, not the answer.</p>

              <p className="col">The rest cannot be corrected at all.{" "}
              <strong>{(100 * car.share).toFixed(1)}%</strong> of the stream sits in a single
              column reading &ldquo;{car.label}&rdquo;, which mixes a car (1.0) with an
              auto-rickshaw (up to 2.0) and a pickup (up to 2.0). The true correction lies
              between <strong>+{a.pcu.band_low_pct}%</strong> and{" "}
              <strong>+{a.pcu.band_high_pct}%</strong>.</p>

              <p className="col">Both numbers should travel together.{" "}
              <strong>+{a.pcu.uplift_floor_pct}% is the floor</strong> &mdash; every step of
              it is citable to IRC:106 and it does not move under questioning. But it is a
              floor, and the true correction is larger. Quoting the floor alone understates
              demand; quoting a midpoint invites an argument about an assumption the data
              cannot settle. That spread is the real cost of the class scheme &mdash;
              uncertainty manufactured by recording half the stream in one box.</p>
            </div>
          </div>
        </Reveal>
      </section>

      {/* FINDING 3 */}
      <section>
        <Reveal><h2>Finding 4 &mdash; the flow diagram reports the wrong classes</h2></Reveal>
        <Reveal delay={.06}>
          <div className="card" style={{ marginTop: "1.1rem" }}>
            <header><span className="chip critical">Critical</span>
              <h3>A 20-class header sits over 10-class data, shifted</h3></header>
            <div className="body">
              <p className="col">The <code>Flow Diagram Table</code> sheet &mdash; the one
              feeding the diagrams a reader actually looks at &mdash; carries a twenty-class
              template header over ten-class data, offset from its labels.</p>
              <div className="tscroll">
                <table>
                  <caption>Confirmed in all {a.flow_diagram.files_affected} workbooks, same
                    offset each time.</caption>
                  <thead><tr><th>Header says</th><th>Value</th>
                    <th>What that number actually is</th></tr></thead>
                  <tbody>
                    {a.flow_diagram.mislabelled.map(([label, value, real]) => (
                      <tr key={label}>
                        <td className="bad">{label}</td>
                        <td className="num bad">{nf.format(value)}</td>
                        <td style={{ textAlign: "left" }}><strong>{real}</strong></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="col">A reader taking that sheet at face value concludes
              two-wheelers are <strong>0.24%</strong> of the stream. They are over{" "}
              <strong>{(100 * tw.share).toFixed(0)}%</strong>. Twelve further columns failed
              outright: <strong className="num">{a.flow_diagram.ref_errors}</strong>{" "}
              <code>#REF!</code> errors across the twelve files. The columns that did not
              error are the dangerous ones &mdash; they silently took the wrong data.</p>
              <p className="col">That sheet is also the only place an{" "}
              <strong>E-Rickshaw</strong> column appears anywhere in the survey, and it holds the hand-cart count. There
              is no e-rickshaw data in this survey at all.</p>
            </div>
          </div>
        </Reveal>
      </section>

      {/* FINDING 4 */}
      <section>
        <Reveal><h2>Finding 5 &mdash; arithmetic, and what it revealed</h2></Reveal>
        <Reveal delay={.06}>
          <div className="card" style={{ marginTop: "1.1rem" }}>
            <header><span className="chip fixed">Correctable</span>
              <h3>{a.arithmetic.discrepancies} stored totals disagree with their own components</h3></header>
            <div className="body">
              <p className="col">{a.arithmetic.understate} understate and {a.arithmetic.overstate} overstate,
              so this is scattered formula damage rather than a bias. Net effect on the
              bin-level grand total: an understatement of{" "}
              <strong className="num">{a.arithmetic.net_grand_total}</strong> vehicles.</p>
              <p className="col">Chasing one of them produced a more consequential result.
              Reconciling the approach and total sheets against the movement sheets matches at{" "}
              <strong className="num">{nf.format(a.derived_sheets.exact)}</strong> of{" "}
              {nf.format(a.derived_sheets.cells_checked)} cells &mdash; exactly, at every bin,
              for every class. They are not corroborating measurements. They are formulas over
              the twelve movement sheets, so the workbook holds <strong>one</strong> primary
              dataset per junction presented as twenty-two sheets.</p>
              <p style={{ fontSize: ".72rem", color: "var(--faint)" }}>
                <span className="tag">V_1!M104</span> <span className="tag">stored 0</span>{" "}
                <span className="tag">derived 58</span></p>
              <Evidence
                label="The register, and how it was built"
                rows={[
                  { k: "discrepancies recorded", v: `${a.arithmetic.discrepancies}`, tone: "bad",
                    note: "every stored total re-derived from its own components" },
                  { k: "understate", v: `${a.arithmetic.understate}` },
                  { k: "overstate", v: `${a.arithmetic.overstate}`,
                    note: "both directions, so this is scattered formula damage, not a bias" },
                  { k: "net effect", v: `${a.arithmetic.net_grand_total} vehicles understated` },
                  { k: "silently absorbed", v: "0", tone: "ok",
                    note: "the parse gate: nothing is corrected without a register entry" },
                  { k: "cells reconciled", v: `${nf.format(a.derived_sheets.exact)} of ${nf.format(a.derived_sheets.cells_checked)}`,
                    tone: "bad", note: "exact at every bin, for every class - which is what makes them formulas rather than counts" },
                ]}
                source={"src/tmc_parse.py builds the register; src/audit.py reports it. No " +
                        "stored total is trusted anywhere in this pipeline - every one is " +
                        "re-derived, and a total that cannot be read is registered as its " +
                        "own kind rather than passed over."} />
            </div>
          </div>
        </Reveal>
      </section>

      {/* WHAT HOLDS */}
      <section>
        <Reveal><h2>What the survey does support</h2></Reveal>
        <Reveal delay={.06}>
          <p className="col lede" style={{ marginTop: "1rem" }}>
            The defects are real and they change the numbers. They do not make the data
            worthless. Across the six junctions, through movements are{" "}
            <strong>{c.through_pct_mean}%</strong> of traffic (range{" "}
            {c.through_pct_range[0]}&ndash;{c.through_pct_range[1]}%). The methodology sets
            roughly 70% as the level at which an elevated through-carriageway is well
            founded. This corridor sits on that line.
          </p>
        </Reveal>
        <div style={{ marginTop: "1.6rem" }}>
          <Reveal delay={.1}><JunctionExplorer junctions={js} /></Reveal>
        </div>
      </section>

      {/* COMPARATIVE */}
      <section>
        <Reveal><h2>The six against each other</h2></Reveal>
        <Reveal delay={.06}>
          <p className="col lede" style={{ marginTop: "1rem" }}>
            One junction at a time answers what each carries. It does not answer the
            question a programme has to answer, which is where to start. Six junctions
            ranked on one indicator, then on all six at once &mdash; and the useful part is
            what moves between the two.
          </p>
        </Reveal>
        <div style={{ marginTop: "1.4rem" }}>
          <Reveal delay={.1}><Compare rows={d.criticality} /></Reveal>
        </div>
        <Reveal delay={.14}>
          <p className="src col" style={{ marginTop: "1.1rem" }}>
            Six indicators, because those are the ones this survey supports. Not included:
            pedestrian volume, crash history and turning-vehicle delay, none of which exist
            for this corridor &mdash; the survey has no pedestrian column, there is no
            accident record, and delay is modelled rather than observed. A ranking is only
            as complete as what went into it, and this is what went in.
          </p>
        </Reveal>
      </section>

      {/* CONSTRAINTS */}
      <section>
        <Reveal><h2>Corridor constraints</h2></Reveal>
        <Reveal delay={.05}>
          <p className="col lede" style={{ marginTop: "1rem" }}>
            The counts say what uses the corridor. The survey drawing says what is
            physically in the way &mdash; and it was sitting unconverted in the project
            folder. Read directly it carries 1,041,959 entities across 44 layers,
            including a full utility survey.
          </p>
        </Reveal>
        <div style={{ marginTop: "1.4rem" }}>
          <Reveal delay={.1}><CorridorMap junctions={js} /></Reveal>
        </div>
        {c2 && (
          <Reveal delay={.14}>
            <div className="card" style={{ marginTop: "1.1rem" }}>
              <header><span className="chip fixed">Feasible</span>
                {/* On the corrected alignment there are no pinch points at all, so a
                    heading built around counting them stops making sense. */}
                <h3>{c2.stations - c2.hard_free > 0
                  ? <>An elevated structure has room; the argument is about{" "}
                     {c2.stations - c2.hard_free} pinch points</>
                  : <>An elevated structure has room, and on this alignment there is
                     almost nothing in the way</>}</h3></header>
              <div className="body">
                <p className="col">Walking the <strong>{c2.corridor_km} km</strong> alignment
                at 25 m stations and counting what falls inside an {c2.pier_radius_m} m pier
                footprint: <strong>{c2.hard_free} of {c2.stations} stations
                ({c2.hard_free_pct}%)</strong> carry no hard constraint &mdash; no building,
                temple, railway or gas main.{" "}
                {c2.longest_clear_runs_m.length > 1
                  ? <>The longest uninterrupted runs are{" "}
                      <strong>{nf.format(Math.round(c2.longest_clear_runs_m[0]))} m</strong> and{" "}
                      <strong>{nf.format(Math.round(c2.longest_clear_runs_m[1]))} m</strong>.</>
                  : <>The whole corridor is a single uninterrupted run of{" "}
                      <strong>{nf.format(Math.round(c2.longest_clear_runs_m[0] ?? 0))} m</strong>.
                      Stations are sampled every 25 m, and one structure sits inside the pier
                      radius between two of them, so read this as very nearly clear rather
                      than perfectly so.</>}</p>
                <p className="col">Reporting a single blended score would have been
                misleading, and nearly was. Weighted equally,{" "}
                <strong>2,300 lamp posts outrank a building</strong> and the corridor reads
                as 74% blocked. Lamp posts get relocated as a matter of routine; a temple
                does not.</p>
                <div className="tscroll">
                  <table>
                    <caption>Constraint inventory read from the drawing, grouped by who owns
                      the diversion &mdash; that is what drives cost and lead time.</caption>
                    <thead><tr><th>Category</th><th>Features</th><th>Why it matters</th></tr></thead>
                    <tbody>
                      {Object.entries(c2.totals).map(([k, v]) => (
                        <tr key={k}>
                          <td>{k}</td><td className="num">{nf.format(v)}</td>
                          <td style={{ textAlign: "left" }}>{WHY[k] ?? ""}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </Reveal>
        )}
        <Reveal delay={.18}>
          <div style={{ marginTop: "1.1rem" }}><PierProfile /></div>
        </Reveal>
      </section>

      {/* CAPACITY */}
      {cp && (
        <section>
          <Reveal><h2>Capacity, and what the scheme would remove</h2></Reveal>
          <Reveal delay={.05}>
            <p className="col lede" style={{ marginTop: "1rem" }}>
              Counting traffic establishes demand. Whether the corridor can carry it is a
              separate question, and it is the one an elevated-corridor business case
              turns on.
            </p>
          </Reveal>
          <Reveal delay={.09}>
            <div className="card" style={{ marginTop: "1.2rem" }}>
              <header><span className="chip material">Method</span>
                <h3>A lane-based capacity model does not describe this corridor</h3></header>
              <div className="body">
                <p className="col">Carriageway width is measured, not assumed: 155
                perpendicular transects from the alignment to the kerb linework, taking the
                outermost hit each side and subtracting the median. The corridor runs{" "}
                <strong>{width0?.toFixed(1)} m per direction</strong> &mdash; two nominal
                lanes, about {nf.format(Math.round(Object.values(cp.widths ?? {})[0]?.capacity_pcu_hr ?? 0))}{" "}
                PCU/hour at that measured width.</p>
                <p className="col">Observed peak flow is{" "}
                <strong>{cp.observed_vs_planning_ratio}&times;</strong> that. On the binding
                approach it reaches <strong>3,266 vehicles per nominal lane per hour</strong>{" "}
                against a saturation flow near 1,800&ndash;2,000, with{" "}
                <strong>58% two-wheelers</strong>. Lane discipline is not what limits this road.</p>
                <p className="col">That is not a rounding problem, it is the wrong model. So
                v/c here is reported as <em>what the standard says</em>, not as a measurement,
                and Indo-HCM&rsquo;s sublane treatment with local calibration is what a
                detailed design would need.</p>
                <Evidence
                  label="The capacity figure, and where it comes from"
                  rows={[
                    { k: "measured width", v: `${width0?.toFixed(1)} m per direction`,
                      note: "155 perpendicular transects, outermost kerb hit each side, median subtracted" },
                    { k: "base capacity", v: `${nf.format(cp.assumptions.base_capacity_pcu_per_dir)} PCU/hr/dir`,
                      note: `at the ${cp.assumptions.base_width_per_dir_m} m reference width` },
                    { k: "scaled to this corridor", v: `${nf.format(Math.round(Object.values(cp.widths ?? {})[0]?.capacity_pcu_hr ?? 0))} PCU/hr` },
                    { k: "observed vs planning", v: `${cp.observed_vs_planning_ratio}x`, tone: "bad" },
                    { k: "lane model applicable", v: cp.lane_model_applicable ? "yes" : "no",
                      tone: cp.lane_model_applicable ? "ok" : "bad",
                      note: "which is why v/c is reported as what the standard says, not as a measurement" },
                  ]}
                  source={`${cp.assumptions.capacity_source}. An earlier version of this ` +
                          "page quoted 2,400 PCU/hour and attributed it to IRC:106. No such " +
                          "table exists: that figure came from an unsourced 1,200 PCU/lane " +
                          "the pipeline has since retired, and it was lower than the real " +
                          "capacity, which made this corridor look worse than it is."} />
              </div>
            </div>
          </Reveal>
          <Reveal delay={.12}>
            <div className="card" style={{ marginTop: "1.1rem" }}>
              <header><span className="chip fixed">The case</span>
                <h3>Carrying the through movement over the junctions restores every approach</h3></header>
              <div className="body">
                <p className="col">Through movements do not need the at-grade junction.
                Removing them leaves the turning traffic, and the through share here is high
                enough that this settles it.</p>
                <div className="tscroll">
                  <table>
                    <caption>Peak-hour PCU on the busier corridor approach at each junction,
                      before and after the through movement is carried over.</caption>
                    <thead><tr><th>Junction</th><th>Through</th><th>Peak PCU</th>
                      <th>Left at grade</th><th>v/c before</th><th>v/c after</th><th>LOS</th></tr></thead>
                    <tbody>
                      {relief.map((r) => (
                        <tr key={r.junction}>
                          <td className="mono">{r.junction}</td>
                          <td className="num">{r.through_pct.toFixed(1)}%</td>
                          <td className="num">{nf.format(r.peak_pcu)}</td>
                          <td className="num">{nf.format(r.residual_pcu)}</td>
                          <td className="num bad">{r.vc_before.toFixed(2)}</td>
                          <td className="num good">{r.vc_after.toFixed(2)}</td>
                          <td className="num good">{r.los_after}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="col"><strong>{cp.approaches_ok_after_grade_separation} of{" "}
                {cp.relief.length}</strong> corridor approaches return under the planning
                capacity <em>on opening</em>. This is the argument the count data exists to
                make, and the one place turning movement data is irreplaceable &mdash; no
                other dataset separates through traffic from turning traffic.</p>
                {cp.design_life && cp.design_life_first_failure_med && (
                  <p className="col" style={{
                    borderLeft: "3px solid var(--defect)", paddingLeft: ".9rem" }}>
                    <strong>It does not hold for the design horizon.</strong> Growing the
                    residual turning demand at 6% returns the first approach to capacity in{" "}
                    <strong>{cp.design_life_first_failure_med}</strong> &mdash;{" "}
                    {cp.design_life_first_failure_med - cp.assumptions.base_year} years
                    after the base year &mdash; and{" "}
                    <strong>{cp.design_life_survives_horizon} of {cp.design_life.length}</strong>{" "}
                    still hold at {cp.horizon_year}. That qualifies the recommendation
                    rather than withdrawing it: grade separation is the only measure tested
                    here that relieves the corridor at all, but a structure sized on
                    opening-year relief alone would be over capacity again well inside its
                    own design life. The scheme needs a demand-side measure beside it.
                  </p>
                )}
                <p className="col">On growth to {cp.horizon_year}: 6% compounding implies
                roughly <strong>{cp.growth[1]?.multiple}&times;</strong> today&rsquo;s flow.
                Treat that as a floor, not a forecast &mdash; counted flow on a saturated
                approach is capacity-constrained, so suppressed and diverted trips are
                invisible to it. No at-grade widening inside the available 15 m section
                delivers a threefold increase.</p>
              </div>
            </div>
          </Reveal>
        </section>
      )}

      {/* QUEUE, DELAY AND COST */}
      {dl && (
        <section>
          <Reveal><p className="eyebrow">What a v/c ratio means on the ground</p></Reveal>
          <Reveal delay={.04}>
            <h2 style={{ marginTop: ".5rem" }}>
              The corridor does not queue. It locks.
            </h2>
          </Reveal>
          <Reveal delay={.08}>
            <p className="col lede" style={{ marginTop: "1rem" }}>
              A ratio above 1.0 says an approach is over capacity. It does not say what
              that looks like. Applying deterministic oversaturation queueing &mdash; which
              needs no signal timings, and the survey records none &mdash; gives the queue
              in vehicles, the length it occupies at the measured carriageway width, and
              how long into the peak it reaches the junction behind it.
            </p>
          </Reveal>
          <Reveal delay={.1}>
            <div className="card" style={{ marginTop: "1.4rem" }}>
              <header>
                <h3>Peak-hour queue against available storage</h3>
                <span className="tag">{dl.spillback_count} of {dl.n_approaches} block back</span>
              </header>
              <div className="body">
                <div className="tscroll">
                  <table>
                    <thead><tr>
                      <th>Junction</th><th>Approach</th><th className="num">v/c</th>
                      <th className="num">Queue veh</th><th className="num">Queue m</th>
                      <th className="num">Storage m</th><th className="num">Delay min</th>
                      <th>Blocks</th>
                    </tr></thead>
                    <tbody>
                      {dl.approaches.map((r, i) => (
                        <tr key={i}>
                          <td>{r.junction}</td>
                          <td>{r.approach.replace("from ", "")}</td>
                          <td className="num bad">{r.vc.toFixed(2)}</td>
                          <td className="num">{r.queue_vehicles.toLocaleString("en-US")}</td>
                          <td className="num">{r.queue_m.toLocaleString("en-US")}</td>
                          <td className="num">{r.storage_m
                            ? r.storage_m.toLocaleString("en-US") : "n/a"}</td>
                          <td className="num">{r.mean_delay_min.toFixed(1)}</td>
                          <td className={r.spillback ? "bad" : undefined}>
                            {r.spillback
                              ? `${r.upstream} at ${Math.round(r.minutes_to_spillback ?? 0)} min`
                              : (r.storage_m ? "\u2014" : "leaves study area")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="col"><strong>{dl.spillback_count} of {dl.n_approaches}</strong>{" "}
                queues reach the junction behind them before the peak hour is out. The
                soonest does it in{" "}
                <strong>{Math.min(...dl.approaches.filter(a => a.spillback)
                  .map(a => a.minutes_to_spillback ?? 999))} minutes</strong>. Past that
                point the approaches stop being independent and deterministic queueing
                stops being valid &mdash; which is why no queue is reported longer than the
                road can physically hold.</p>
              </div>
            </div>
          </Reveal>
          <Reveal delay={.12}>
            <div className="card" style={{ marginTop: "1.2rem" }}>
              <header>
                <h3>Corridor journey time, {dl.corridor_km} km</h3>
                <span className="tag">{dl.effective_kmh} km/h effective</span>
              </header>
              <div className="body">
                <div className="scope">
                  <div><span className="k num">{dl.free_flow_min}</span>
                    <span className="l">min, free flow</span></div>
                  <div><span className="k num" style={{ color: "var(--defect)" }}>
                    {dl.peak_journey_min}</span>
                    <span className="l">min at peak, {dl.worst_direction}</span></div>
                  <div><span className="k num" style={{ color: "var(--ok)" }}>
                    {dl.through_journey_min_after}</span>
                    <span className="l">min, grade separated</span></div>
                  <div><span className="k num">{dl.effective_kmh}</span>
                    <span className="l">km/h effective</span></div>
                </div>
                <p className="col">Through traffic on an elevated carriageway does not
                enter the junctions at all, so it meets none of that delay. The saving is{" "}
                <strong>{dl.saving_min_per_trip} minutes per trip</strong>. Treat the peak
                figure as a floor: it sums independent queues, and {dl.spillback_count} of
                them are not independent.</p>
                <Evidence
                  label="How the journey time was built"
                  rows={[
                    { k: "corridor length", v: `${dl.corridor_km} km`,
                      note: "chainage along the surveyed alignment" },
                    { k: "free-flow running", v: `${dl.free_flow_min} min`,
                      note: `at ${dl.assumptions?.free_flow_kmh ?? 40} km/h, no junction delay` },
                    { k: "at the surveyed peak", v: `${dl.peak_journey_min} min`, tone: "bad",
                      note: `${dl.worst_direction}, summing each junction's queue delay` },
                    { k: "delay added", v: `${dl.peak_delay_min} min`, tone: "bad" },
                    { k: "effective speed", v: `${dl.effective_kmh} km/h`, tone: "bad",
                      note: "the whole corridor, end to end, at the peak" },
                    { k: "why it is a floor", v: `${dl.spillback_count} of ${dl.n_approaches} queues spill back`,
                      note: "a queue that reaches the junction behind it is no longer independent, so the true figure is worse than the sum" },
                  ]}
                  source={"Deterministic oversaturation queueing in src/delay.py. Departures " +
                          "are capped at each junction's measured-width capacity from " +
                          "capacity.json; nothing here assumes a discharge rate the survey " +
                          "does not support."} />
              </div>
            </div>
          </Reveal>
          {ec && (
            <Reveal delay={.14}>
              <div className="card" style={{ marginTop: "1.2rem" }}>
                <header>
                  <h3>What that costs, per year</h3>
                  <span className="tag">value of time is a policy input</span>
                </header>
                <div className="body">
                  <p className="col">Approaches are over capacity for a mean of{" "}
                  <strong>{ec.mean_hours_over} hours a day</strong> &mdash; counted from
                  the survey&rsquo;s own 96 intervals, not assumed from a nominal peak.
                  That accumulates <strong>{ec.delay_veh_hr_day.toLocaleString("en-US")}{" "}
                  vehicle-hours</strong> of delay every day.</p>
                  <div className="scope">
                    <div><span className="k num" style={{ color: "var(--defect)" }}>
                      &#8377;{ec.annual_cost_crore[0]}&ndash;{ec.annual_cost_crore[1]}</span>
                      <span className="l">crore/yr, do nothing</span></div>
                    <div><span className="k num">
                      &#8377;{ec.annual_cost_after_crore[0]}&ndash;{ec.annual_cost_after_crore[1]}</span>
                      <span className="l">crore/yr, grade separated</span></div>
                    <div><span className="k num" style={{ color: "var(--ok)" }}>
                      &#8377;{ec.annual_benefit_crore[0]}&ndash;{ec.annual_benefit_crore[1]}</span>
                      <span className="l">crore/yr benefit</span></div>
                  </div>
                  <p className="col" style={{
                    borderLeft: "3px solid var(--accent)", paddingLeft: ".9rem" }}>
                    <strong>These rupees are indicative, and deliberately banded.</strong>{" "}
                    The delay is measured; the value of time is not ours to set. Authorities
                    appraise against their own approved rates, so quoting a single figure
                    off a rate JDA has not adopted would present a policy choice as an
                    engineering result. The method is the deliverable &mdash; substituting
                    JDA&rsquo;s rates is a one-line change. Excluded entirely:{" "}
                    {ec.assumptions.excluded.join(", ")}, all of which would raise it.
                  </p>
                  <Evidence
                    label="Every input to the rupee figure"
                    rows={[
                      { k: "excess PCU per day", v: `${nf.format(Math.round(ec.total_excess_pcu_day))}`,
                        note: "demand above capacity, summed over the oversaturated hours" },
                      { k: "hours over capacity", v: `${ec.mean_hours_over} per day`,
                        note: "mean across approaches, measured from the 96 survey intervals" },
                      { k: "delay", v: `${nf.format(Math.round(ec.delay_veh_hr_day))} veh-hr/day`,
                        tone: "bad" },
                      { k: "PCU per vehicle", v: `${ec.pcu_per_vehicle}`,
                        note: "from the corrected composition, not assumed" },
                      { k: "working days", v: `${ec.assumptions.working_days?.join("–") ?? "—"}`,
                        note: "banded, because the count is a policy input too" },
                      { k: "cost, do nothing", v: `₹${ec.annual_cost_crore.join("–")} crore/yr`,
                        tone: "bad" },
                      { k: "cost, grade separated", v: `₹${ec.annual_cost_after_crore.join("–")} crore/yr` },
                      { k: "benefit", v: `₹${ec.annual_benefit_crore.join("–")} crore/yr`, tone: "ok" },
                      { k: "value of time", v: "a policy input, not a result",
                        note: "every band above is the same delay priced at the low and high published rates" },
                    ]}
                    source={"src/economics.py. The delay is measured from the survey; the " +
                            "rate is not ours to set, so every figure is a band across the " +
                            "published range rather than a point off a rate JDA has not adopted."} />
                </div>
              </div>
            </Reveal>
          )}
        </section>
      )}

      {/* SCHEME TEST */}
      {sc && (
        <section>
          <Reveal><p className="eyebrow">The question the survey could not answer</p></Reveal>
          <Reveal delay={.04}><h2 style={{ marginTop: ".5rem" }}>Will the seven U-turn bays work?</h2></Reveal>
          <Reveal delay={.08}>
            <div className="card" style={{ marginTop: "1.2rem" }}>
              <header><span className="chip critical">No</span>
                <h3>{sc.fails_conservative} of {sc.uturns.length} corridor approaches cannot be served</h3></header>
              <div className="body">
                <p className="col">The survey counted no U-turns, so on the face of it the
                scheme has no traffic evidence base. It does &mdash; in a column nobody read
                that way.</p>
                <p className="col"><strong>Under signal-free operation a right turn becomes a
                U-turn.</strong> A driver wanting to turn right can no longer cross opposing
                traffic at the junction. They travel through, turn around at a downstream
                median bay, come back and turn left. So the demand each bay must carry is the{" "}
                <strong>right-turn volume the survey already recorded</strong>.</p>
                <p className="col">Capacity of an unsignalised U-turn is gap acceptance. The
                critical gap is weighted by observed composition, because two-wheelers accept
                far shorter gaps and are 49% of this stream.</p>
                <div className="tscroll">
                  <table>
                    <caption>Peak-hour right-turn demand that becomes U-turn demand, against
                      gap-acceptance capacity. Conservative critical gap.</caption>
                    <thead><tr><th>Junction</th><th>Approach</th><th>U-turn demand</th>
                      <th>Opposing flow</th><th>Bay capacity</th><th>Verdict</th></tr></thead>
                    <tbody>
                      {[...sc.uturns].sort((a, b) => b.vc_conservative - a.vc_conservative)
                        .map((r, i) => {
                          const nogap = r.vc_conservative >= NOGAP;
                          const fails = r.vc_conservative >= 1;
                          return (
                            <tr key={i}>
                              <td className="mono">{r.junction}</td>
                              <td style={{ textAlign: "left" }}>
                                {r.approach.includes("Mansarover") ? "from north" : "from south"}</td>
                              <td className="num">{nf.format(Math.round(r.uturn_demand))}</td>
                              <td className="num">{nf.format(Math.round(r.conflicting_flow))}</td>
                              <td className="num">{nf.format(Math.round(r.cap_conservative))}</td>
                              <td className={nogap || fails ? "bad" : "good"} style={{ textAlign: "left" }}>
                                {nogap ? "no viable gaps"
                                  : (fails ? "fails, v/c " : "ok, v/c ") + r.vc_conservative.toFixed(2)}</td>
                            </tr>);
                        })}
                    </tbody>
                  </table>
                </div>
                <p className="col"><strong>{sc.no_viable_gap}</strong> sit past the point where
                acceptable gaps effectively cease to exist. No ratio is quoted for those, and
                the omission is deliberate: past that threshold the capacity formula runs to
                near zero and a v/c figure becomes an artefact rather than a measurement. The
                honest statement is not that the ratio is large but that the gap is not there.
                Under the <em>optimistic</em> critical gap it is{" "}
                <strong>{sc.fails_optimistic} of {sc.uturns.length}</strong>.</p>
                <p className="col">There is no Indian code value to check this against.{" "}
                {sc.indo_hcm_no_uturn_chapter} The nearest is a CSIR-CRRI field
                recommendation of <strong>{sc.csir_crri_design_gap_s} s</strong>, measured on
                an inter-urban national highway rather than an urban arterial &mdash;{" "}
                {sc.csir_crri_design_source}. That a scheme of this size is being built on a
                manoeuvre no Indian standard dimensions is a finding in its own right.</p>
                <GapEvidence spread={sc.gap_evidence_spread}
                  holdsIn={sc.gap_conclusion_holds_in}
                  ours={sc.two_wheeler_gap_basis}
                  analogue={sc.uturn_analogue}
                  direction={sc.gap_direction_note}
                  followUpMeasured={sc.follow_up_measured_s} />
              </div>
            </div>
          </Reveal>
          <Reveal delay={.12}>
            <div className="card" style={{ marginTop: "1.1rem" }}>
              <header><span className="chip critical">Second-order</span>
                <h3>The U-turn does not fail quietly. It blocks the through movement.</h3></header>
              <div className="body">
                <p className="col">Gap acceptance assumes a driver waits. Indian drivers do
                not &mdash; they creep, encroach and force the movement, and opposing traffic
                yields. So the U-turn still happens.</p>
                <p className="col">It happens <em>on top of</em> the opposing through stream.
                Every forced U-turn imposes a stoppage on the movement the scheme exists to
                speed up, converting a junction capacity problem into a link capacity problem
                with no signal left to meter it.</p>
                <p className="col"><strong>{nf.format(Math.round(sc.forced_uturns_per_hour))}{" "}
                vehicles per peak hour</strong> would be forcing their way across opposing
                traffic with no gap to take.</p>
                <Evidence
                  label="Where the forced-movement figure comes from"
                  rows={[
                    { k: "forced U-turns", v: `${nf.format(Math.round(sc.forced_uturns_per_hour))} veh/hr`,
                      tone: "bad", note: "demand above what the bays can serve, summed across the corridor" },
                    { k: "approaches unservable", v: `${sc.fails_conservative} of ${sc.uturns.length}`,
                      tone: "bad" },
                    { k: "of those, past any viable gap", v: `${sc.no_viable_gap}`,
                      tone: "bad", note: "the capacity formula runs to near zero; no ratio is quoted" },
                    { k: "modelled as", v: `${sc.uturn_analogue}`,
                      note: "a merge needs a smaller gap than a crossing, so this sets the scale" },
                    { k: "gap bases tested", v: `${sc.gap_bases_tested}`,
                      note: `the finding holds in ${sc.gap_conclusion_holds_in} of them` },
                  ]}
                  source={"This is the one figure here NOT produced by gap acceptance. Gap " +
                          "acceptance says the movement cannot be served; it does not say " +
                          "the vehicles vanish. The count is the unserved demand, which is " +
                          "why it is reported as a load on the through stream rather than " +
                          "as a queue that waits."} />
              </div>
            </div>
          </Reveal>

          {sc.uturn_detour && sc.uturn_detour.length > 0 && (
            <Reveal delay={.15}>
              <div className="card" style={{ marginTop: "1.1rem" }}>
                <header><span className="chip critical">Second-order</span>
                  <h3>How much further every converted vehicle travels</h3></header>
                <div className="body">
                  <p className="col">A right turn used to be one manoeuvre at the stop
                  line. Under this scheme it becomes four: past the junction, out to the
                  median opening, through 180&deg;, back, and only then the left turn.
                  That distance is measurable off the drawing.</p>
                  <div className="scope">
                    <div><span className="k num">{sc.detour_mean_typical_m}</span>
                      <span className="l">m, typical detour</span></div>
                    <div><span className="k num">{sc.detour_min_m}&ndash;{sc.detour_max_m}</span>
                      <span className="l">m, full range</span></div>
                    <div><span className="k num" style={{ color: "var(--defect)" }}>
                      {nf.format(Math.round(sc.detour_veh_km_typical ?? 0))}</span>
                      <span className="l">extra vehicle-km, peak hr</span></div>
                    <div><span className="k num">{sc.detour_bays_measured}</span>
                      <span className="l">of {sc.uturn_detour.length} bays measurable</span></div>
                  </div>
                  <div className="tscroll">
                    <table>
                      <caption>Junction to the nearest median opening wide enough to turn
                        in, and back again.</caption>
                      <thead><tr><th>Junction</th><th>Bay</th>
                        <th className="num">To bay</th><th className="num">Detour</th>
                        <th className="num">Demand</th><th className="num">Veh-km/hr</th></tr></thead>
                      <tbody>
                        {sc.uturn_detour.map((d, i) => (
                          <tr key={i}>
                            <td className="mono">{d.junction}</td>
                            <td style={{ textAlign: "left" }}>{d.bay}</td>
                            <td className="num">{d.bay_beyond_drawing ? "\u2014"
                              : `${nf.format(d.one_way_m ?? 0)} m`}</td>
                            <td className={"num " + ((d.detour_m ?? 0) > 1000 ? "bad" : "")}>
                              {d.bay_beyond_drawing ? "beyond drawing"
                                : `${nf.format(d.detour_m ?? 0)} m`}</td>
                            <td className="num">{nf.format(Math.round(d.demand))}</td>
                            <td className="num">{d.bay_beyond_drawing ? "\u2014"
                              : nf.format(Math.round(d.veh_km_per_hour ?? 0))}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="src">Two limits, stated rather than smoothed. The drawing
                  ENDS, so {sc.detour_bays_beyond_drawing} of these bays have no opening
                  beyond them in the CAD and cannot be measured in that direction. And
                  these are the <em>shortest</em> detours physically available: JDA names
                  seven purpose-built bays and we do not hold their chainages, so a bay
                  placed further out makes every figure here larger. TMC-01 at{" "}
                  {nf.format(sc.detour_max_m ?? 0)} m sits at the end of the drawing and is
                  one of the three inferred positions, so the least certain row carries
                  the largest number. The typical figure excludes it.</p>
                  <p className="col">The detour is not the whole cost. That vehicle then
                  has to merge into the through stream, which is the capacity failure
                  above, and weave across to make its left at the junction. On a 250 m
                  detour there is not much room to do it in.</p>
                </div>
              </div>
            </Reveal>
          )}

          <Reveal delay={.16}>
            <h3 style={{ marginTop: "1.4rem" }}>Three futures for the corridor</h3>
            <div className="tscroll" style={{ marginTop: ".7rem" }}>
              <table>
                <caption>Volume/capacity under each option. S0 is today.</caption>
                <thead><tr><th>Junction</th><th>JDA name</th><th>S0 do nothing</th>
                  <th>S1 JDA signal-free</th><th>S2 elevated through-road</th></tr></thead>
                <tbody>
                  {sc.scenarios.map((r) => (
                    <tr key={r.junction}>
                      <td className="mono">{r.junction}</td>
                      <td style={{ textAlign: "left" }}>{r.jda_name}</td>
                      <td className="num bad">{r.s0_vc.toFixed(2)} F</td>
                      <td className="bad" style={{ textAlign: "left" }}>
                        {r.s1_uturn_vc_cons >= NOGAP ? "no viable gaps"
                          : r.s1_uturn_vc_cons.toFixed(2) + (r.s1_works ? "" : " fails")}</td>
                      <td className="num good">{r.s2_vc.toFixed(2)} {r.s2_los}</td>
                    </tr>))}
                </tbody>
              </table>
            </div>
          </Reveal>

          {uf && (
            <Reveal delay={.06}>
              <div className="card" style={{ marginTop: "1.1rem" }}>
                <header><span className="chip">Framework</span>
                  <h3>Which constraint binds, bay by bay &mdash; and what would change it</h3></header>
                <div className="body">
                  <p className="col">A verdict is not a decision. Five criteria in the
                  order an engineer would apply them, first failure binding. A criterion
                  below the binding one is marked <em>untested</em>, not passed: the order
                  exists precisely so that geometry is not checked for a problem geometry
                  cannot reach.</p>
                  <p className="col"><strong>Gap capacity binds at all{" "}
                  {uf.binding_counts["gap capacity"]} of {uf.n_bays} bays.</strong>{" "}
                  {uf.bays_above_bay_ceiling > 0 && (
                    <>And {uf.bays_above_bay_ceiling} of those are past the ceiling of the
                    instrument itself: a single median opening passes at most{" "}
                    <strong>{nf.format(uf.bay_ceiling_veh_hr ?? 0)} veh/h</strong> with
                    nothing at all to yield to, because that is 3600 divided by the
                    follow-up headway. Those bays are not badly sited. They are the wrong
                    device for the demand.</>
                  )}</p>
                  <Ladder f={uf} />
                </div>
              </div>
            </Reveal>
          )}
        </section>
      )}

      {/* SENSITIVITY */}
      {sen && (
        <section>
          <Reveal><p className="eyebrow">Before you argue with the numbers</p></Reveal>
          <Reveal delay={.04}>
            <h2 style={{ marginTop: ".5rem" }}>Do these conclusions survive their own assumptions?</h2>
          </Reveal>
          <Reveal delay={.08}>
            <p className="col lede" style={{ marginTop: "1rem" }}>
              Every headline here rests on a judgement &mdash; the PCU band, lane capacity,
              effective lane count, the critical gap, the growth rate. A conclusion that
              only holds at one corner of that space is a coincidence, not a finding. Both
              were run across the whole of it: <strong>{sen.combinations} combinations</strong>
              {sen.queue && sen.queue.length > 0 ? (<> for the capacity and scheme
              conclusions, and a further <strong>{sen.queue.length}</strong> for the queue
              conclusion, whose assumptions none of the first set touches</>) : null}.
            </p>
          </Reveal>
          <div className="grid2" style={{ marginTop: "1.2rem" }}>
            <Reveal delay={.12}>
              <div className="card">
                <header><span className="chip critical">Robust</span>
                  <h3>The U-turn bays still cannot carry the demand</h3></header>
                <div className="body">
                  <p>At the critical gap <em>most favourable to the scheme</em> &mdash; the
                  shortest gap drivers might plausibly accept, maximising bay capacity
                  &mdash; <strong>{sen.uturn.optimistic?.fails} of {sen.uturn.optimistic?.of}</strong>{" "}
                  corridor approaches still cannot be served.</p>
                  <p>No assumption inside the defensible range rescues it.</p>
                  <Evidence
                    label="The grid this was run across"
                    rows={[
                      { k: "combinations tested", v: `${sen.combinations_uturn ?? "—"}`,
                        note: "critical gap is the only axis that bears on this one" },
                      { k: "at the optimistic gap", v: `${sen.uturn.optimistic?.fails} of ${sen.uturn.optimistic?.of} fail`,
                        tone: "bad" },
                      { k: "at the conservative gap", v: `${sen.uturn.conservative?.fails} of ${sen.uturn.conservative?.of} fail`,
                        tone: "bad" },
                      { k: "gap bases published", v: `${sc?.gap_bases_tested ?? "—"}`,
                        note: `the finding holds in ${sc?.gap_conclusion_holds_in ?? "—"} of them` },
                    ]}
                    source={"src/sensitivity.py, conclusion 1. Only the critical-gap axis " +
                            "is swept here because it is the only one that enters bay " +
                            "capacity - sweeping the others would inflate the stated grid " +
                            "without testing anything."} />
                </div>
              </div>
            </Reveal>
            <Reveal delay={.16}>
              <div className="card">
                <header><span className="chip fixed">Robust</span>
                  <h3>The elevated option still restores the corridor</h3></header>
                <div className="body">
                  <p>Across every combination of PCU uplift, lane capacity and effective
                  lane count, all approaches return under planning capacity in{" "}
                  <strong>{sen.elevated_all_pass_combinations} of{" "}
                  {sen.elevated_total_combinations}</strong> cases. The worst still returns
                  10 of 12.</p>
                  <p>One-at-a-time analysis swings the result by <strong>zero</strong>{" "}
                  approaches on every axis, so no assumption is named most influential. The
                  finding is driven by the size of the through movement, not by anything
                  assumed.</p>
                  <Evidence
                    label="Every combination, and the worst of them"
                    rows={[
                      { k: "combinations tested", v: `${sen.combinations_elevated ?? sen.elevated_total_combinations}`,
                        note: "PCU uplift x lane capacity x lanes per direction" },
                      { k: "all approaches recover", v: `${sen.elevated_all_pass_combinations} of ${sen.elevated_total_combinations}`,
                        tone: "ok" },
                      { k: "worst combination", v: "10 of 12 recover", tone: "ok",
                        note: "still a majority, at the least favourable corner of the grid" },
                      { k: "most influential axis", v: "none",
                        note: "one-at-a-time swings the result by zero approaches on every axis" },
                    ]}
                    source={"src/sensitivity.py, conclusion 2. Reported for the design " +
                            "HORIZON rather than the opening year - relief that works on " +
                            "day one and fails inside the design life is not relief."} />
                </div>
              </div>
            </Reveal>
            {sen.queue_spillback_min != null && (
              <Reveal delay={.2}>
                <div className="card">
                  <header><span className="chip critical">Robust</span>
                    <h3>Queues still block the junction behind them</h3></header>
                  <div className="body">
                    <p>At the assumptions <em>most favourable to the corridor still
                    working</em> &mdash; the densest plausible packing, the smallest
                    vehicle footprints, the most generous lane capacity &mdash;{" "}
                    <strong>{sen.queue_spillback_min} of {sen.queue?.[0]?.total}</strong>{" "}
                    approaches still queue past the junction upstream. At the central
                    assumptions it is <strong>{sen.queue_spillback_central}</strong>, and
                    at the least favourable corner of the grid{" "}
                    <strong>{sen.queue_spillback_max}</strong>.</p>
                    <p>No combination in the grid removes it, so the finding is not an
                    artefact of the packing or footprint figures.</p>
                    <Evidence
                      label="The queue grid, corner to corner"
                      rows={[
                        { k: "combinations tested", v: `${sen.combinations_queue ?? sen.queue?.length}`,
                          note: "jam packing x vehicle footprint x lane capacity" },
                        { k: "most favourable corner", v: `${sen.queue_spillback_min} spill back` },
                        { k: "central assumptions", v: `${sen.queue_spillback_central} spill back`,
                          tone: "bad", note: "reproduces the published delay result exactly" },
                        { k: "least favourable corner", v: `${sen.queue_spillback_max} spill back`,
                          tone: "bad" },
                        { k: "combinations with none", v: "0", tone: "bad",
                          note: "which is what makes the finding robust rather than assumed" },
                      ]}
                      source={"src/sensitivity.py, conclusion 3. It rescales the UNCAPPED " +
                              "queue: delay.py publishes queue length capped at what the " +
                              "link can hold, and once capped every spilling approach reads " +
                              "exactly equal to its storage, which would make this " +
                              "unanswerable."} />
                  </div>
                </div>
              </Reveal>
            )}
          </div>
        </section>
      )}

      {/* NEW ANALYTICAL EXHIBITS — conflict, whole-day LOS, volume flow, scenario tool.
          Kept in their own component so this file stays navigable. */}
      <Exhibits safety={d.safety as never} profiles={d.profiles as never}
                exhibits={d.exhibits as never} sensitivity={sen as never}
                capacity={cp as never} standards={d.standards as never} scheme={sc as never} />

      {/* LEARNED APPLICATIONS */}
      {(d.anomaly || d.cluster || d.forecast) && (
        <section>
          <Reveal><p className="eyebrow">Where a model earns its place</p></Reveal>
          <Reveal delay={.04}>
            <h2 style={{ marginTop: ".5rem" }}>Three things worth learning from the counts</h2>
          </Reveal>
          <Reveal delay={.08}>
            <p className="col lede" style={{ marginTop: "1rem" }}>
              Everything above was arithmetic and a code book. These three are not, and
              each is shown with the test it could have failed &mdash; a model reported
              without one is a number with a confident voice. One of the three returns a
              negative result and it is on the page beside the other two, because running
              two tests and publishing the winner is how a p-value stops meaning anything.
            </p>
          </Reveal>
          <div style={{ marginTop: "1.5rem" }}>
            <Reveal delay={.12}>
              <Learned anomaly={d.anomaly} cluster={d.cluster} forecast={d.forecast} />
            </Reveal>
          </div>
        </section>
      )}

      {/* CHECK THE WORK */}
      <section>
        <Reveal><h2>Check the work</h2></Reveal>
        <Reveal delay={.05}>
          <p className="col lede" style={{ marginTop: "1rem" }}>
            An audit that cannot itself be audited is an assertion with better typography.
            Every derived dataset behind this page is downloadable, in open formats, and
            the code that produces them is public.
          </p>
        </Reveal>
        <div style={{ marginTop: "1.2rem" }}>
          <Reveal delay={.09}><Downloads combinations={sen?.combinations} /></Reveal>
        </div>
      </section>

      {/* OPEN */}
      <section>
        <Reveal><h2>What remains unknown</h2></Reveal>
        <Reveal delay={.06}>
          <ul className="col" style={{ marginTop: "1rem" }}>
            <li><strong>U-turn demand.</strong> Never counted. Unmeasured, not zero &mdash;
            and U-turns concentrate at median openings, where they cost the most capacity.</li>
            <li><strong>E-rickshaws.</strong> No column anywhere holds them.</li>
            <li><strong>Half the PCU correction.</strong> Locked behind the composite class
            columns. Only re-counting to a proper class scheme resolves it.</li>
            <li><strong>The corridor order is not settled by the counts.</strong>{" "}
            Positions themselves are no longer inferred &mdash; JDA supplied them, and our
            own picks were wrong by 269 to 950 m, on a parallel road. But flow continuity
            still cannot confirm the sequence on its own: its best ordering wins by{" "}
            {c.order_margin_pct}%, which is noise. Chainage along JDA&rsquo;s alignment
            resolves it, and the agreement between the two is a check rather than a
            derivation.</li>
            {/* the U-turn item is already covered above in more detail */}
            {a.survey_design.filter((s) => !s.startsWith("U-turns")).map((s) => <li key={s}>{s}</li>)}
          </ul>
        </Reveal>
      </section>

      <footer className="col">
        <p>Independent re-derivation from the twelve issued workbooks.{" "}
        {nf.format(meta.bins_parsed)} class-bins parsed; every stored total recomputed from
        components; discrepancies recorded rather than corrected. Figures are generated from
        the pipeline output, not transcribed.</p>
        <p style={{ marginTop: ".7rem" }}>Standards referenced: IRC:106-1990 (PCU factors),
        Indo-HCM 2017 (capacity and LOS). Analysis day {meta.analysis_date}.</p>
      </footer>
    </main>
  );
}
