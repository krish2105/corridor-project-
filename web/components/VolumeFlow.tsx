"use client";

/**
 * The twelve-arrow intersection volume flow diagram.
 *
 * This is the exhibit an Indian traffic engineer looks for first, and a turning-movement
 * matrix is a substitute some will not accept as equivalent. Its absence was more
 * conspicuous than anything we could have added in its place.
 *
 * Arms are drawn clockwise from north, which is how the survey sheets order them. Ribbon
 * width is proportional to peak-hour volume. The centre is deliberately empty: no U-turn
 * was ever counted, and the hole is the point.
 */
type Move = { from_arm: string; to_arm: string; from_i: number; to_i: number; turn: string; veh: number };
type J = { junction: string; jda_name: string; arms: string[]; peak_start: string; movements: Move[] };

const R = 128, CX = 190, CY = 190;
const COLOUR: Record<string, string> = {
  Left: "var(--ok)", Straight: "var(--accent)", Right: "var(--defect)",
};

function point(i: number, entering: boolean, r = R) {
  const a = (Math.PI / 2) * i;           // arm 0 = north, clockwise
  const ox = Math.sin(a), oy = -Math.cos(a);
  const px = Math.cos(a), py = Math.sin(a);
  const s = (entering ? -1 : 1) * 0.2;   // left-hand traffic: enter left, leave left
  return [CX + (ox + px * s) * r, CY + (oy + py * s) * r];
}

export default function VolumeFlow({ j }: { j: J }) {
  const max = Math.max(...j.movements.map((m) => m.veh));
  return (
    <div className="card">
      <header>
        <h3>{j.junction} &mdash; {j.jda_name}</h3>
        <span className="tag">peak hour from {j.peak_start}</span>
        <span className="tag">no U-turn counted</span>
      </header>
      <div className="body">
        <div style={{ overflowX: "auto" }}>
          <svg viewBox="0 0 380 380" width="100%" style={{ maxWidth: 380, display: "block", margin: "0 auto" }}
               role="img" aria-label={`Turning movements at ${j.junction}`}>
            {/* arms */}
            {j.arms.map((a, i) => {
              const [x, y] = point(i, true, R + 34);
              const [x2, y2] = point(i, false, R + 34);
              return (
                <g key={a}>
                  <line x1={(x + x2) / 2} y1={(y + y2) / 2} x2={CX} y2={CY}
                        stroke="var(--rule)" strokeWidth={26} strokeLinecap="round" />
                  <text x={(x + x2) / 2} y={(y + y2) / 2} textAnchor="middle"
                        dominantBaseline="middle" fontSize={9.5} fill="var(--muted)"
                        fontFamily="IBM Plex Mono, monospace">
                    {a.length > 15 ? a.slice(0, 14) + "…" : a}
                  </text>
                </g>
              );
            })}
            {/* movements */}
            {j.movements.map((m, k) => {
              const [x1, y1] = point(m.from_i, true);
              const [x2, y2] = point(m.to_i, false);
              const w = 1.4 + 11 * (m.veh / max);
              return (
                <path key={k}
                      d={`M ${x1} ${y1} Q ${CX} ${CY} ${x2} ${y2}`}
                      fill="none" stroke={COLOUR[m.turn] ?? "var(--muted)"}
                      strokeWidth={w} strokeOpacity={0.72} strokeLinecap="round">
                  <title>{`${m.from_arm} → ${m.to_arm} (${m.turn}): ${m.veh.toLocaleString("en-US")} veh`}</title>
                </path>
              );
            })}
            <circle cx={CX} cy={CY} r={16} fill="var(--paper)" stroke="var(--rule)" strokeDasharray="3 3" />
          </svg>
        </div>
        <div className="scope">
          {(["Left", "Straight", "Right"] as const).map((t) => {
            const v = j.movements.filter((m) => m.turn === t).reduce((s, m) => s + m.veh, 0);
            return (
              <div key={t}>
                <span className="k num" style={{ color: COLOUR[t] }}>{v.toLocaleString("en-US")}</span>
                <span className="l">{t.toLowerCase()} turns, peak hr</span>
              </div>
            );
          })}
        </div>
        <p className="col">Ribbon width is peak-hour volume. Left turns are the next arm
        clockwise, because India drives on the left, so the <strong>right turn</strong> is
        the movement that crosses opposing traffic &mdash; and the one the signal-free
        scheme converts into a U-turn. The dashed centre is empty because no U-turn was
        ever counted.</p>
      </div>
    </div>
  );
}
