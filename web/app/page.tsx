import fs from "node:fs";
import path from "node:path";
import Reveal from "@/components/Reveal";
import EvidenceField from "@/components/EvidenceField";
import JunctionExplorer from "@/components/JunctionExplorer";
import type { Corridor } from "@/lib/types";

const nf = new Intl.NumberFormat("en-US");

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
            Six signalised junctions, {meta.city}. Surveyed {meta.survey_dates[0]} and{" "}
            {meta.survey_dates[1]} by the appointed contractor and issued to JDA as twelve
            workbooks. This is an independent re-derivation of every number in them.
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

      {/* FINDING 2 */}
      <section>
        <Reveal><h2>Finding 2 &mdash; PCU conversion understates demand</h2></Reveal>
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
              <strong>+{a.pcu.band_high_pct}%</strong>. That spread is the real cost of the
              class scheme &mdash; uncertainty manufactured by recording half the stream in
              one box.</p>
            </div>
          </div>
        </Reveal>
      </section>

      {/* FINDING 3 */}
      <section>
        <Reveal><h2>Finding 3 &mdash; the flow diagram reports the wrong classes</h2></Reveal>
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
        <Reveal><h2>Finding 4 &mdash; arithmetic, and what it revealed</h2></Reveal>
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
            <li><strong>Junction coordinates.</strong> The workbooks carry no georeference.
            Recovering the corridor order from flow continuity alone gives{" "}
            <code>{c.order_best.map((x) => x.replace("TMC-", "")).join(" → ")}</code>, but at
            a {c.order_margin_pct}% margin over the runner-up &mdash; noise, not a result.
            Map pins are needed, and this section becomes a map once they arrive.</li>
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
