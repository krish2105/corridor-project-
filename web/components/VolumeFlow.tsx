"use client";
import { useState } from "react";

/**
 * Intersection volume flow diagram — the exhibit an Indian traffic engineer looks for
 * first, and one a turning-movement matrix does not substitute for.
 *
 * GEOMETRY, AND WHY IT IS DRAWN THIS WAY
 * Arms run clockwise from north because that is how the survey sheets order them. India
 * drives on the LEFT, so a vehicle approaches on the left of its own arm and leaves on
 * the left of the exit arm. Every movement is therefore drawn between two DIFFERENT
 * sides of the carriageway, which is what makes a left turn short and tight against the
 * kerb and a right turn swing across the whole junction. Draw both from the centreline
 * and the picture is wrong in the one way that matters: it stops showing which movement
 * crosses opposing traffic.
 *
 * The right turn is the capacity-limiting movement, and the one the signal-free scheme
 * converts into a U-turn. It is drawn in the defect colour throughout.
 *
 * The centre is left open. No U-turn was surveyed, and the hole is the finding.
 */
type Move = { from_arm: string; to_arm: string; from_i: number; to_i: number;
              turn: string; veh: number;
              permitted?: string; bay?: string | null; rejoins?: string | null;
              legs?: string[] };
type Detour = { bay: string; detour_m: number | null; one_way_m: number | null;
                beyond: boolean; at_junction_mouth: boolean | null };
type J = { junction: string; scheme_no: number; scheme_label: string;
           jda_name: string; arms: string[]; peak_start: string;
           movements: Move[]; width_m?: number | null; lanes_per_dir?: number | null;
           width_measured_on?: string; detours?: Detour[] };

const SIZE = 460, C = SIZE / 2, R = 120, ARM = 178, LANE = 26;

// Metres per pixel, fixed by the measured corridor width.
//
// The grey band on the corridor arms is 2 x LANE x 1.25 pixels wide and represents the
// full measured carriageway, both directions. Deriving the scale from that rather than
// picking a round number means the scale bar below the drawing is true for THIS junction,
// and a reader can measure off it. Cross streets are drawn at the same band width because
// nothing here has measured one - transects are cast along the corridor - and the note
// under the diagram says so rather than letting the picture imply otherwise.
const BAND_PX = LANE * 2.5;
function scaleOf(widthM?: number | null) {
  return widthM ? (2 * widthM) / BAND_PX : null;   // metres per pixel
}
const COLOUR: Record<string, string> = {
  Left: "var(--ok)", Straight: "var(--accent)", Right: "var(--defect)",
};
// A through movement is not a turn. The first version of this component labelled the
// group "straight turns", which is the kind of phrase an engineer stops reading after.
const GROUP: Record<string, string> = {
  Left: "left turns", Straight: "through movements", Right: "right turns",
};
const nf = new Intl.NumberFormat("en-US");

/** Unit outward vector for arm i, and the perpendicular, in SVG coordinates (y down). */
function axes(i: number) {
  const t = (Math.PI / 2) * i;
  return { ox: Math.sin(t), oy: -Math.cos(t), px: Math.cos(t), py: Math.sin(t) };
}

/** Where a movement touches the junction: entering on its left, leaving on its left. */
function node(i: number, entering: boolean, r = R) {
  const { ox, oy, px, py } = axes(i);
  const s = entering ? 1 : -1;          // left-hand traffic
  return [C + ox * r + px * s * LANE, C + oy * r + py * s * LANE];
}

/**
 * The path a vehicle actually takes, from the tangents rather than from a tuned bow.
 *
 * The previous version bent every arc by a hand-picked `pull` factor: -0.40 for a left
 * turn, 0.55 for a right. Those numbers set how far the control point sits from the
 * junction centre, which is not a property of the manoeuvre, and at -0.40 the control
 * lands 1.4x further out than the chord midpoint - so left-turn arcs bulged OUTSIDE the
 * kerb line and the diagram showed vehicles driving off the road.
 *
 * A real turning path leaves the entry lane along the arm and joins the exit lane along
 * the exit arm. That is fully determined: the tangent at the entry is inward along the
 * entry arm, the tangent at the exit is outward along the exit arm, and a quadratic
 * Bezier with those tangents has its control point exactly where the two tangent lines
 * meet. Nothing is chosen.
 *
 * Left turns then fall tight into the near corner because that is where their tangents
 * cross, and right turns swing across the middle because that is where theirs do. The
 * through movement's tangents are parallel, so it is a straight line - which it is.
 */
function pathFor(fromI: number, toI: number, off: number) {
  const [x1, y1] = node(fromI, true);
  const [x2, y2] = node(toI, false);
  if (off === 2) return `M ${x1} ${y1} L ${x2} ${y2}`;   // through: tangents are parallel
  const a = axes(fromI), b = axes(toI);
  // entry travels INWARD along its arm (-a.o); exit travels OUTWARD along its arm (+b.o),
  // so walk back from the exit along -b.o. Solve P1 - t*a.o = P2 - u*b.o.
  const det = -a.ox * -b.oy - -a.oy * -b.ox;
  if (Math.abs(det) < 1e-9) return `M ${x1} ${y1} L ${x2} ${y2}`;
  const rx = x2 - x1, ry = y2 - y1;
  const tt = (rx * -b.oy - ry * -b.ox) / det;
  const cx = x1 + tt * -a.ox, cy = y1 + tt * -a.oy;
  return `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;
}

/**
 * The route a right-turning driver takes once the junction is signal-free.
 *
 * Drawn for the northbound corridor approach, which is the one every conversation about
 * this scheme is actually about. Four legs, in order: through the junction, out to the
 * median opening, 180 degrees, back, then the left turn. The opening is off the diagram -
 * it is hundreds of metres away, and drawing it to scale would leave the junction a dot -
 * so the run-out is truncated with the real distance written on it.
 *
 * That truncation is the point rather than a compromise. The manoeuvre does not fit in
 * the junction, which is exactly what a diagram of the junction should show.
 */
function mutPath(j: J, m: Move) {
  const d = (j.detours ?? []).find((x) => x.bay === m.bay);

  // The heading the driver leaves the junction on, which is NOT the way they wanted to
  // go. A corridor right turn overshoots and keeps its heading; a cross-street movement
  // can only turn LEFT out of its arm and takes whatever heading that gives it. Same rule
  // as routes.py, and the bay side it produces is checked against the one published there.
  const corridor = m.from_i === 0 || m.from_i === 2;
  const headI = corridor ? (m.from_i + 2) % 4 : (m.from_i + 1) % 4;
  const backI = (headI + 2) % 4;

  const [x1, y1] = node(m.from_i, true);
  // Out along the heading arm, then back on its opposite carriageway. `node(headI, false)`
  // is the far-side lane of that arm, which is exactly the one a driver runs out on.
  const [ox, oy] = node(headI, false);
  const [rx, ry] = node(headI, true);
  const [ex, ey] = node(m.to_i, false);

  // Truncate the run-out: the opening is hundreds of metres away and drawing it to scale
  // would leave the junction a dot. That the manoeuvre does not fit in the junction is
  // the thing worth seeing, so the truncation is labelled rather than hidden.
  const f = 0.78;
  const tx = C + (ox - C) * f, ty = C + (oy - C) * f;
  const bx = C + (rx - C) * f, by = C + (ry - C) * f;
  const cap = 0.94;
  const capx = C + (ox - C) * cap, capy = C + (oy - C) * cap;
  const capbx = C + (rx - C) * cap, capby = C + (ry - C) * cap;

  const leave = pathFor(m.from_i, headI, (headI - m.from_i + 4) % 4);
  const rejoin = pathFor(backI, m.to_i, (m.to_i - backI + 4) % 4);

  return (
    <g style={{ pointerEvents: "none" }}>
      {/* 1 - out of the junction on the only heading the scheme allows */}
      <path d={leave} fill="none" stroke="var(--caution)" strokeWidth={3}
            strokeDasharray="7 4" />
      {/* 2 - the run out to the opening, truncated */}
      <path d={`M ${node(headI, false)[0]} ${node(headI, false)[1]} L ${tx} ${ty}`}
            fill="none" stroke="var(--caution)" strokeWidth={3} strokeDasharray="7 4" />
      {/* 3 - the U-turn itself, crossing the median to the opposite carriageway */}
      <path d={`M ${tx} ${ty} L ${capx} ${capy}
                A ${LANE} ${LANE} 0 0 1 ${capbx} ${capby} L ${bx} ${by}`}
            fill="none" stroke="var(--caution)" strokeWidth={3} strokeDasharray="7 4" />
      {/* 4 - back to the junction and out the arm they wanted all along */}
      <path d={`M ${bx} ${by} L ${node(backI, true)[0]} ${node(backI, true)[1]}`}
            fill="none" stroke="var(--caution)" strokeWidth={3} strokeDasharray="7 4" />
      <path d={rejoin} fill="none" stroke="var(--caution)" strokeWidth={3}
            strokeDasharray="7 4" markerEnd="url(#ah-Mut)" />
      <circle cx={x1} cy={y1} r={5} fill="var(--caution)" />

      {/* Parked in the top-left rather than on the heading arm. On the arm it landed on
          top of the carriageway dimension whenever the route ran south, and two captions
          fighting for the same 40 px is how a drawing stops being readable. */}
      <text x={14} y={20} fontSize={9} fill="var(--caution)"
            fontFamily="IBM Plex Mono, monospace">
        {d?.beyond || !d
          ? "no opening on this side within the drawing"
          : `${(d.one_way_m ?? 0).toLocaleString("en-US")} m out, ` +
            `${(d.detour_m ?? 0).toLocaleString("en-US")} m round trip`}
      </text>
      {d && !d.beyond && d.at_junction_mouth && (
        <text x={14} y={32} fontSize={8.5} fill="var(--defect)"
              fontFamily="IBM Plex Mono, monospace">
          and that opening is a junction mouth
        </text>
      )}
    </g>
  );
}

export default function VolumeFlow({ junctions }: { junctions: J[] }) {
  const ordered = [...junctions].sort((a, b) => a.scheme_no - b.scheme_no);
  const [code, setCode] = useState(ordered[0].junction);
  // Click to isolate, hover to preview.
  //
  // Hover alone would have been wrong: there is no hover on a phone, and a phone in a
  // meeting is the whole reason this is a link rather than a PDF. Pinning by click works
  // on both, is keyboard-reachable, and is the only one of the two that can be tested.
  const [pinned, setPinned] = useState<number | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  const active = pinned ?? hover;
  // Show how a right turn ACTUALLY travels once the signals are gone. Off by default:
  // the diagram's job is the survey, and the scheme is an overlay on it.
  // The overlay follows whichever movement is selected, so a reader can trace ANY of
  // them rather than the one route the component used to hard-code. That hard-coding is
  // what the reviewer caught: it drew a single path and implied it was the only one.
  const [mut, setMut] = useState(false);
  const j = junctions.find((x) => x.junction === code)!;
  const mpp = scaleOf(j.width_m);
  const sel = active !== null ? j.movements[active] : null;
  const rerouted = j.movements.filter((m) => m.permitted === "re-routed");
  const max = Math.max(...j.movements.map((m) => m.veh));
  const total = j.movements.reduce((s, m) => s + m.veh, 0);

  return (
    <div className="card">
      <header>
        <h3>{j.scheme_label} &mdash; {j.jda_name}</h3>
        <span className="tag">peak hour from {j.peak_start}</span>
        <span className="tag">{nf.format(total)} veh</span>
        <span className="tag">survey sheet {j.junction}</span>
        <span className="tag">no U-turn counted</span>
      </header>
      <div className="body">
        <div className="picker" role="group" aria-label="Choose a junction">
          {ordered.map((x) => (
            <button key={x.junction} aria-pressed={x.junction === code}
                    onClick={() => { setCode(x.junction); setHover(null); setPinned(null); }}>
              {x.junction === code && <span className="pill" />}
              <span className="lab">{x.scheme_label}</span>
            </button>
          ))}
        </div>

        <div className="stack" style={{ gap: ".45rem", marginTop: ".6rem" }}>
          <div className="picker">
            <button aria-pressed={mut} onClick={() => setMut(!mut)}>
              {mut && <span className="pill" />}
              <span className="lab">
                {mut ? "hide" : "show"} how each banned movement has to travel
              </span>
            </button>
          </div>
          {mut && (
            <>
              <p className="src" style={{ margin: 0 }}>
                <strong>{rerouted.length} of {j.movements.length} movements cannot be
                made at this junction once the signals go.</strong> Pick one to trace the
                route a driver is left with. The other {j.movements.length - rerouted.length}{" "}
                &mdash; the left turns and the corridor through movement &mdash; are
                unaffected.
              </p>
              <div className="picker">
                {rerouted.map((m) => {
                  const k = j.movements.indexOf(m);
                  return (
                    <button key={k} aria-pressed={pinned === k}
                            onClick={() => setPinned(pinned === k ? null : k)}>
                      {pinned === k && <span className="pill" />}
                      <span className="lab">
                        {m.from_arm.split(" ")[0]} &rarr; {m.to_arm.split(" ")[0]}
                      </span>
                    </button>
                  );
                })}
              </div>
              {sel && sel.permitted === "re-routed" && (
                <ol className="legs">
                  {(sel.legs ?? []).map((l, i) => <li key={i}>{l}</li>)}
                </ol>
              )}
              {sel && sel.permitted !== "re-routed" && (
                <p className="src" style={{ margin: 0 }}>
                  <b>{sel.from_arm} &rarr; {sel.to_arm}</b> is unaffected by the scheme:
                  it is {sel.turn === "Straight" ? "the corridor through movement"
                    : "a left turn, which crosses nothing under left-hand traffic"}.
                </p>
              )}
            </>
          )}
        </div>

        <div style={{ overflowX: "auto" }}>
          <svg viewBox={`0 0 ${SIZE} ${SIZE}`} width="100%"
               style={{ maxWidth: SIZE, display: "block", margin: "0 auto" }}
               role="img" aria-label={`Turning movements at ${j.scheme_label}, peak hour`}>
            <defs>
              <marker id="ah-Mut" viewBox="0 0 10 10" refX="9" refY="5"
                      markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--caution)" />
              </marker>
              {Object.entries(COLOUR).map(([k, v]) => (
                <marker key={k} id={`ah-${k}`} viewBox="0 0 10 10" refX="9" refY="5"
                        markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 1 L 10 5 L 0 9 z" fill={v} />
                </marker>
              ))}
            </defs>

            {/* carriageways */}
            {j.arms.map((a, i) => {
              const { ox, oy, px, py } = axes(i);
              const ex = C + ox * ARM, ey = C + oy * ARM;
              return (
                <g key={a}>
                  <line x1={C + ox * 24} y1={C + oy * 24} x2={ex} y2={ey}
                        stroke="var(--sunk)" strokeWidth={LANE * 2.5} strokeLinecap="butt" />
                  <line x1={C} y1={C} x2={ex} y2={ey}
                        stroke="var(--rule)" strokeWidth={1} strokeDasharray="5 5" />
                  <text x={C + ox * (ARM + 26) + px * 0} y={C + oy * (ARM + 26)}
                        textAnchor={i === 1 ? "end" : i === 3 ? "start" : "middle"}
                        dominantBaseline={i === 0 ? "auto" : i === 2 ? "hanging" : "middle"}
                        fontSize={11} fill="var(--muted)"
                        fontFamily="IBM Plex Mono, monospace">{a}</text>
                </g>
              );
            })}

            {/* movements */}
            {j.movements.map((m, k) => {
              const [x1, y1] = node(m.from_i, true);
              const [x2, y2] = node(m.to_i, false);
              const off = (m.to_i - m.from_i + 4) % 4;
              const d = pathFor(m.from_i, m.to_i, off);
              const w = 1.6 + 10 * (m.veh / max);
              const dim = active !== null && active !== k;
              return (
                <path key={k} d={d}
                      fill="none" stroke={COLOUR[m.turn]}
                      strokeWidth={pinned === k ? w + 2 : w}
                      strokeLinecap="round" strokeLinejoin="round"
                      markerEnd={`url(#ah-${m.turn})`}
                      strokeOpacity={dim ? 0.13 : 0.85}
                      style={{ cursor: "pointer", transition: "stroke-opacity .15s" }}
                      onClick={() => setPinned(pinned === k ? null : k)}
                      onMouseEnter={() => setHover(k)} onMouseLeave={() => setHover(null)}>
                  <title>{`${m.from_arm} → ${m.to_arm} · ${m.turn === "Straight" ? "through" : m.turn.toLowerCase() + " turn"} · ${nf.format(m.veh)} veh`}</title>
                </path>
              );
            })}

            {/* Dimension line on the corridor carriageway.
                The only width in this project that is measured is the corridor's, from
                transects along JDA's centreline. Drawing a figure on a cross street would
                be inventing one. */}
            {j.width_m && (
              <g>
                <line x1={C - BAND_PX / 2} y1={C + ARM - 6} x2={C + BAND_PX / 2}
                      y2={C + ARM - 6} stroke="var(--muted)" strokeWidth={0.9} />
                {[-1, 1].map((s) => (
                  <line key={s} x1={C + s * BAND_PX / 2} y1={C + ARM - 11}
                        x2={C + s * BAND_PX / 2} y2={C + ARM - 1}
                        stroke="var(--muted)" strokeWidth={0.9} />
                ))}
                <text x={C} y={C + ARM - 13} textAnchor="middle" fontSize={9}
                      fill="var(--muted)" fontFamily="IBM Plex Mono, monospace">
                  {(2 * j.width_m).toFixed(1)} m both directions
                </text>
                <text x={C} y={C + ARM + 8} textAnchor="middle" fontSize={8.5}
                      fill="var(--faint)" fontFamily="IBM Plex Mono, monospace">
                  {j.width_m.toFixed(1)} m/dir &middot; {j.lanes_per_dir} lanes &middot; provisional
                </text>
              </g>
            )}

            {/* Scale bar, true for this junction because the scale is derived from its
                own measured width rather than assumed. */}
            {mpp && (() => {
              const target = 20;                       // metres
              const px = target / mpp;
              const x0 = 14, y0 = SIZE - 14;
              return (
                <g>
                  <line x1={x0} y1={y0} x2={x0 + px} y2={y0}
                        stroke="var(--ink)" strokeWidth={1.4} />
                  {[0, 1].map((k) => (
                    <line key={k} x1={x0 + k * px} y1={y0 - 4} x2={x0 + k * px} y2={y0 + 4}
                          stroke="var(--ink)" strokeWidth={1.4} />
                  ))}
                  <text x={x0 + px / 2} y={y0 - 7} textAnchor="middle" fontSize={9}
                        fill="var(--ink)" fontFamily="IBM Plex Mono, monospace">
                    {target} m
                  </text>
                </g>
              );
            })()}

            {/* HOW A RIGHT TURN ACTUALLY TRAVELS UNDER THE SCHEME.
                The reviewer's question, drawn. With the signals gone the right turn does
                not happen at the junction: the driver goes THROUGH, runs to a median
                opening, turns 180 degrees, comes back, and only then turns left. Four
                manoeuvres where there was one, and the return leg re-enters the stream
                the scheme exists to speed up. */}
            {mut && sel && sel.permitted === "re-routed" && mutPath(j, sel)}

            {/* the uncounted U-turn */}
            <circle cx={C} cy={C} r={19} fill="var(--paper)" stroke="var(--rule-hard)"
                    strokeDasharray="4 4" />
            <text x={C} y={C} textAnchor="middle" dominantBaseline="middle"
                  fontSize={8.5} fill="var(--faint)"
                  fontFamily="IBM Plex Mono, monospace">U?</text>
          </svg>
        </div>

        <div className="scope">
          {(["Left", "Straight", "Right"] as const).map((t) => {
            const v = j.movements.filter((m) => m.turn === t).reduce((s, m) => s + m.veh, 0);
            return (
              <div key={t}>
                <span className="k num" style={{ color: COLOUR[t] }}>{nf.format(v)}</span>
                <span className="l">{GROUP[t]}, peak hr</span>
              </div>
            );
          })}
          <div>
            <span className="k num">{(100 * j.movements.filter((m) => m.turn === "Straight")
              .reduce((s, m) => s + m.veh, 0) / total).toFixed(1)}%</span>
            <span className="l">going straight through</span>
          </div>
        </div>

        <div className="tscroll">
          <table>
            <thead><tr><th>From</th><th>To</th><th>Movement</th><th className="num">Veh, peak hr</th></tr></thead>
            <tbody>
              {[...j.movements].sort((a, b) => b.veh - a.veh).map((m, k) => (
                <tr key={k}
                    onClick={() => setPinned(pinned === j.movements.indexOf(m)
                      ? null : j.movements.indexOf(m))}
                    onMouseEnter={() => setHover(j.movements.indexOf(m))}
                    onMouseLeave={() => setHover(null)}
                    aria-selected={pinned === j.movements.indexOf(m)}
                    style={{ cursor: "pointer",
                             background: active === j.movements.indexOf(m)
                               ? "var(--sunk)" : undefined }}>
                  <td>{m.from_arm}</td><td>{m.to_arm}</td>
                  <td style={{ color: COLOUR[m.turn] }}>
                    {m.turn === "Straight" ? "through" : `${m.turn.toLowerCase()} turn`}</td>
                  <td className="num">{nf.format(m.veh)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="col">Ribbon width is peak-hour volume. <strong>Tap or click any
        movement, or any row below, to isolate it</strong>; tap again to release. Every
        path is drawn from its own tangents &mdash; it leaves the entry lane along the
        approach and joins the exit lane along the exit arm &mdash; so the shapes are not
        chosen. Left turns fall tight into the near corner because that is where their
        tangents cross; the <strong>right turn</strong> swings across the whole junction
        because that is where its tangents cross, and it is the capacity-limiting movement
        the signal-free scheme converts into a U-turn.</p>

        <p className="col"><strong>Turn on the amber overlay</strong> to see what that
        conversion means for one driver. It follows the Sanganer Stadium right turn, which
        under left-hand traffic is heading for Patrika Gate. With the signals gone that
        driver goes <em>through</em> the junction past the exit they want, runs out to a
        median opening, turns 180&deg; onto the opposite carriageway, comes back, and only
        then makes the left. Four manoeuvres where there was one, and the return leg
        re-enters the through stream the scheme exists to speed up. The run-out is
        truncated because the opening is hundreds of metres away &mdash; the real distance
        is written on it, and the fact that the manoeuvre does not fit inside the junction
        is the thing worth seeing.</p>

        <p className="col">The dashed centre is marked <span className="mono">U?</span>{" "}
        because no U-turn was counted anywhere in this survey. The scheme depends on that
        movement.</p>

        {j.width_m && (
          <p className="src">
            <strong>Drawn to scale, for this junction.</strong> The corridor band is{" "}
            {(2 * j.width_m).toFixed(1)} m across both directions &mdash;{" "}
            {j.width_m.toFixed(1)} m and {j.lanes_per_dir} lanes each way &mdash; and the
            scale bar is derived from it, so a distance measured off this drawing is true
            here and nowhere else. <strong>The cross streets are not dimensioned.</strong>{" "}
            Transects are cast along JDA&rsquo;s centreline, which runs north to south, so
            nothing in this project has measured a cross-street width; they are drawn at
            the same band so the picture does not imply a figure we do not hold. Every
            width is scaled off CAD linework and provisional.
          </p>
        )}
      </div>
    </div>
  );
}
