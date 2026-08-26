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
              turn: string; veh: number };
type J = { junction: string; jda_name: string; arms: string[]; peak_start: string;
           movements: Move[] };

const SIZE = 460, C = SIZE / 2, R = 120, ARM = 178, LANE = 26;
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

export default function VolumeFlow({ junctions }: { junctions: J[] }) {
  const [code, setCode] = useState(junctions[0].junction);
  // Click to isolate, hover to preview.
  //
  // Hover alone would have been wrong: there is no hover on a phone, and a phone in a
  // meeting is the whole reason this is a link rather than a PDF. Pinning by click works
  // on both, is keyboard-reachable, and is the only one of the two that can be tested.
  const [pinned, setPinned] = useState<number | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  const active = pinned ?? hover;
  const j = junctions.find((x) => x.junction === code)!;
  const max = Math.max(...j.movements.map((m) => m.veh));
  const total = j.movements.reduce((s, m) => s + m.veh, 0);

  return (
    <div className="card">
      <header>
        <h3>{j.junction} &mdash; {j.jda_name}</h3>
        <span className="tag">peak hour from {j.peak_start}</span>
        <span className="tag">{nf.format(total)} veh</span>
        <span className="tag">no U-turn counted</span>
      </header>
      <div className="body">
        <div className="picker" role="group" aria-label="Choose a junction">
          {junctions.map((x) => (
            <button key={x.junction} aria-pressed={x.junction === code}
                    onClick={() => { setCode(x.junction); setHover(null); setPinned(null); }}>
              {x.junction === code && <span className="pill" />}
              <span className="lab">{x.junction}</span>
            </button>
          ))}
        </div>

        <div style={{ overflowX: "auto" }}>
          <svg viewBox={`0 0 ${SIZE} ${SIZE}`} width="100%"
               style={{ maxWidth: SIZE, display: "block", margin: "0 auto" }}
               role="img" aria-label={`Turning movements at ${j.junction}, peak hour`}>
            <defs>
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
              // Left turns hug the kerb, through runs straight, right swings wide.
              //
              // The comment said that before and the numbers did the opposite of all
              // three. `pull` runs the wrong way round: at pull = 1 the control point
              // lands on the junction centre, which is MAXIMUM bow, and at pull = 0 it
              // lands on the chord, which is a straight line. So through movements
              // (pull 1.0) were the most bowed thing on the diagram, left turns swung
              // through the middle, and right turns were drawn as near-straight
              // diagonals. A reader could not tell which traffic was going straight,
              // and the turns curved the wrong way.
              //
              //   negative -> control pushed OUTWARD, away from the junction centre
              //   zero     -> control on the chord, a straight line
              //   positive -> control pulled toward the centre, a wide swing
              const pull = off === 1 ? -0.40   // left: tight, hugging the near kerb
                         : off === 2 ? 0       // through: dead straight
                         : 0.55;               // right: swings wide across the junction
              const cx = C + (x1 + x2 - 2 * C) * (1 - pull) * 0.5;
              const cy = C + (y1 + y2 - 2 * C) * (1 - pull) * 0.5;
              const w = 1.6 + 10 * (m.veh / max);
              const dim = active !== null && active !== k;
              return (
                <path key={k} d={`M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`}
                      fill="none" stroke={COLOUR[m.turn]}
                      strokeWidth={pinned === k ? w + 2 : w}
                      strokeLinecap="round" markerEnd={`url(#ah-${m.turn})`}
                      strokeOpacity={dim ? 0.13 : 0.85}
                      style={{ cursor: "pointer", transition: "stroke-opacity .15s" }}
                      onClick={() => setPinned(pinned === k ? null : k)}
                      onMouseEnter={() => setHover(k)} onMouseLeave={() => setHover(null)}>
                  <title>{`${m.from_arm} → ${m.to_arm} · ${m.turn === "Straight" ? "through" : m.turn.toLowerCase() + " turn"} · ${nf.format(m.veh)} veh`}</title>
                </path>
              );
            })}

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
        movement, or any row below, to isolate it</strong>; tap again to release. Left turns are the next arm clockwise because India drives on the
        left, so they hug the kerb and cross nothing. The <strong>right turn</strong>
        swings across the whole junction against opposing traffic &mdash; it is the
        capacity-limiting movement, and the one the signal-free scheme converts into a
        U-turn at a mid-block opening.</p>

        <p className="col">The dashed centre is marked <span className="mono">U?</span>{" "}
        because no U-turn was counted anywhere in this survey. The scheme depends on that
        movement.</p>
      </div>
    </div>
  );
}
