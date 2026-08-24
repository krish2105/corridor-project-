"use client";
import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";

type Basis = {
  label: string; t_c: number; t_f: number;
  unservable: number; no_viable_gap: number; of: number;
  source: string; geometric_match: string;
};

/* The single most attackable number in the whole audit is the critical gap, because
   we chose it and it is not measured on this corridor. So rather than defend one
   value, the reader re-runs the finding on every published basis reachable and sees
   for themselves where it holds and where it does not. */
export default function GapEvidence({
  spread, holdsIn, ours, analogue, direction, followUpMeasured,
}: {
  spread: Basis[]; holdsIn: number; ours: string; analogue: string; direction: string;
  followUpMeasured?: number[];
}) {
  // Motion writes inline transforms, which a stylesheet's prefers-reduced-motion rule
  // cannot override — the cells have to opt out in JS or they animate regardless.
  const reduced = useReducedMotion();
  const [sel, setSel] = useState(
    Math.max(0, spread.findIndex(b => b.label.startsWith("ours, optimistic"))));
  const b = spread[sel];
  if (!b) return null;
  const fails = b.unservable >= 6;
  const max = Math.max(...spread.map(s => s.of));

  return (
    <div className="gapev">
      <p className="col">Every critical gap in this section is a value we chose from the
        literature, not one measured on this corridor &mdash; so it is the most attackable
        number in the audit. Rather than defend one value, here is the same test re-run on
        every published basis we could reach. Pick one.</p>

      <div className="gapev-pick" role="group" aria-label="Critical-gap basis">
        {spread.map((s, i) => (
          <button key={s.label} onClick={() => setSel(i)}
            aria-pressed={i === sel}
            className={"gapev-btn" + (i === sel ? " on" : "")}>
            <span className="gapev-btn-l">{s.label}</span>
            <span className="gapev-btn-n">{s.t_c.toFixed(2)}s</span>
          </button>
        ))}
      </div>

      <div className="gapev-out">
        <div className="gapev-bar" aria-hidden>
          {Array.from({ length: max }, (_, i) => (
            /* scaleY, not opacity: the CSS mutes served cells to .45 and animating
               opacity would override that inline and flatten the distinction. */
            <motion.span key={i}
              className={"gapev-cell" + (i < b.unservable ? " bad" : "")}
              initial={reduced ? false : { scaleY: .3 }}
              animate={{ scaleY: 1 }}
              transition={reduced ? { duration: 0 } : { duration: .18, delay: i * .012 }} />
          ))}
        </div>
        <p className="gapev-verdict">
          <strong className={fails ? "bad" : "ok"}>{b.unservable} of {b.of}</strong>{" "}
          corridor approaches cannot be served at a critical gap of{" "}
          <strong>{b.t_c.toFixed(2)} s</strong> and a follow-up headway of{" "}
          <strong>{b.t_f.toFixed(2)} s</strong>
          {b.no_viable_gap > 0 && <> &mdash; {b.no_viable_gap} of them past the point where
            acceptable gaps effectively cease to exist</>}.
        </p>
        <dl className="gapev-meta">
          <div><dt>Source</dt><dd>{b.source}</dd></div>
          <div><dt>Geometry</dt><dd>{b.geometric_match}</dd></div>
        </dl>
      </div>

      <p className="col gapev-hold">The finding holds in{" "}
        <strong>{holdsIn} of {spread.length}</strong> bases. It does not hold at{" "}
        <em>{spread.filter(s => s.unservable < 6).map(s => s.label).join(", ")}</em> &mdash;
        the traditional Raff method, which the same authors who published it recommend
        against for mixed traffic. We report that rather than omit it.</p>

      <div className="gapev-notes">
        <p><span className="k">U-turn modelled as</span> {analogue}. A merge needs a smaller
          gap than a crossing does, so this choice sets the whole scale.</p>
        <p><span className="k">Where ours sits</span> {direction}.</p>
        <p><span className="k">Two-wheeler basis</span> {ours}.</p>
        {followUpMeasured?.length && (
          <p><span className="k">Follow-up headway</span> our band was assumed before any
            measurement was found. Every Indian value that exists falls inside it &mdash;{" "}
            {followUpMeasured.map((v) => `${v.toFixed(2)}s`).join(", ")} &mdash; and the
            optimistic end is pinned to the lowest, which is the only one measured on
            four-lane median openings.</p>
        )}
      </div>
    </div>
  );
}
