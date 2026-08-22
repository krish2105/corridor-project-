"use client";

/**
 * Every input and output a reviewer needs to reproduce the findings.
 *
 * This exists because "check me" is a stronger position than "trust me", and because an
 * audit that cannot itself be audited is just an assertion with better typography. The
 * client's raw survey workbooks are deliberately NOT here - those are JDA's to share, not
 * ours - but everything derived from them is.
 */
const FILES = [
  { f: "corridor.json", label: "Full analysis dataset",
    note: "Every figure on this page, as produced by the pipeline", kind: "JSON" },
  { f: "audit_report.md", label: "Integrity audit report",
    note: "Seven checks, each with its own pass/fail and the discrepancy register", kind: "MD" },
  { f: "capacity_report.md", label: "Capacity and design-year assessment",
    note: "Measured widths, v/c by approach, and the grade-separation relief table", kind: "MD" },
  { f: "method_statement.md", label: "Method statement",
    note: "Standards applied, every acceptance gate, and where this stops being reliable", kind: "MD" },
  { f: "corridor_constraint_atlas.pdf", label: "Corridor Constraint Atlas",
    note: "A3 print sheet: all constraint layers, north arrow, scale bar, profile", kind: "PDF" },
  { f: "atlas.geojson", label: "Constraint layers",
    note: "Buildings, utilities, drainage, trees, medians in WGS84", kind: "GeoJSON" },
  { f: "median_openings.geojson", label: "Median openings",
    note: "All 30 gaps with width and classification; 27 are U-turn capable", kind: "GeoJSON" },
  { f: "junction_candidates.geojson", label: "Junction candidates",
    note: "All 39 signal clusters considered, with head counts", kind: "GeoJSON" },
  { f: "constraint_profile.json", label: "Pier-siting profile",
    note: "182 stations at 25 m with weighted and hard constraint scores", kind: "JSON" },
  { f: "capacity.json", label: "Capacity analysis",
    note: "Measured widths, v/c, and the grade-separation relief table", kind: "JSON" },
  { f: "scheme_test.json", label: "U-turn scheme test",
    note: "Gap-acceptance results for all 12 corridor approaches", kind: "JSON" },
  { f: "sensitivity.json", label: "Sensitivity analysis",
    note: (n?: number) => n
      ? `Both conclusions across ${n} assumption combinations`
      : "Both conclusions across the full assumption grid",
    kind: "JSON" },
];

/**
 * `combinations` comes from the pipeline so this note can never drift from the data.
 * Optional because the downloads section renders even if sensitivity output is absent -
 * in which case the note drops the count rather than inventing one.
 */
export default function Downloads({ combinations }: { combinations?: number }) {
  return (
    <div className="card">
      <header>
        <h3>Check the work</h3>
        <span className="tag">every figure regenerable</span>
      </header>
      <div className="body">
        <p className="col">Nothing here has to be taken on trust. These are the derived
        datasets behind every claim on this page, in open formats. The code that produces
        them is public, and the acceptance gates are stated in each report.</p>
        <div className="dl">
          {FILES.map((x) => (
            <a key={x.f} href={`/${x.f}`} download className="dlrow">
              <span className="k">{x.kind}</span>
              <span>
                <strong>{x.label}</strong>
                <em>{typeof x.note === "function" ? x.note(combinations) : x.note}</em>
              </span>
            </a>
          ))}
        </div>
        <p style={{ fontSize: ".78rem", color: "var(--muted)" }}>
          The twelve JDA survey workbooks and the CAD drawing are <strong>not</strong>{" "}
          included. They are the authority&rsquo;s data, not ours, and it is theirs to
          share. Every figure above is nevertheless reproducible from them by anyone who
          holds them.
        </p>
      </div>
    </div>
  );
}
