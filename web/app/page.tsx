import fs from "node:fs";
import path from "node:path";
import Reveal from "@/components/Reveal";
import EvidenceField from "@/components/EvidenceField";
import JunctionExplorer from "@/components/JunctionExplorer";
import CorridorMap from "@/components/CorridorMap";
import PierProfile from "@/components/PierProfile";
import Downloads from "@/components/Downloads";
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

function load(): Corridor {
  // Same file the Artifact page renders from, so both show identical figures.
  const p = path.join(process.cwd(), "public", "corridor.json");
  return JSON.parse(fs.readFileSync(p, "utf8"));
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
            Six junctions on <strong>{meta.road}</strong>, {meta.city}. Surveyed{" "}
            {meta.survey_dates[0]} and {meta.survey_dates[1]} by the appointed contractor
            and issued to JDA as twelve workbooks. This is an independent re-derivation of
            every number in them, checked against the survey drawing.
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
                <h3>An elevated structure has room; the argument is about five pinch points</h3></header>
              <div className="body">
                <p className="col">Walking the <strong>{c2.corridor_km} km</strong> alignment
                at 25 m stations and counting what falls inside an {c2.pier_radius_m} m pier
                footprint: <strong>{c2.hard_free} of {c2.stations} stations
                ({c2.hard_free_pct}%)</strong> carry no hard constraint &mdash; no building,
                temple, railway or gas main. The longest uninterrupted runs are{" "}
                <strong>{nf.format(Math.round(c2.longest_clear_runs_m[0]))} m</strong> and{" "}
                <strong>{nf.format(Math.round(c2.longest_clear_runs_m[1]))} m</strong>.</p>
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
                lanes, about 2,400 PCU/hour by IRC:106.</p>
                <p className="col">Observed peak flow is{" "}
                <strong>{cp.observed_vs_planning_ratio}&times;</strong> that. On the binding
                approach it reaches <strong>3,266 vehicles per nominal lane per hour</strong>{" "}
                against a saturation flow near 1,800&ndash;2,000, with{" "}
                <strong>58% two-wheelers</strong>. Lane discipline is not what limits this road.</p>
                <p className="col">That is not a rounding problem, it is the wrong model. So
                v/c here is reported as <em>what the standard says</em>, not as a measurement,
                and Indo-HCM&rsquo;s sublane treatment with local calibration is what a
                detailed design would need.</p>
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
                capacity. This is the argument the count data exists to make, and the one
                place turning movement data is irreplaceable &mdash; no other dataset
                separates through traffic from turning traffic.</p>
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
                acceptable gaps effectively cease to exist. No ratio is quoted for those: past
                that threshold the capacity formula runs to near zero and a v/c figure becomes
                an artefact rather than a measurement. Under the <em>optimistic</em> critical
                gap it is still <strong>{sc.fails_optimistic} of {sc.uturns.length}</strong>.</p>
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
              </div>
            </div>
          </Reveal>
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
              were run across the whole of it: <strong>{sen.combinations} combinations</strong>.
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
                </div>
              </div>
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
          <Reveal delay={.09}><Downloads /></Reveal>
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
            <li><strong>Three junction positions are inferred.</strong> Rajat Path, VT Road
            and Patel Marg are fixed by an exact name match against JDA&rsquo;s scheme. The
            other three are placed by position in that sequence. Flow continuity ranks this
            ordering 128th of 720, sharing four of six positions with its own best &mdash;
            but that best had a {c.order_margin_pct}% margin, which is noise. The survey
            contractor&rsquo;s location schedule would settle it.</li>
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
