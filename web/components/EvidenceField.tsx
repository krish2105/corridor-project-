"use client";
import { motion, useReducedMotion } from "motion/react";

/**
 * One square per movement-by-class daily series, coloured by how day 2 compares
 * with day 1. The block of "identical" squares is the finding — 71% of series
 * reproducing the previous day to the exact vehicle is not something counting does.
 */
export default function EvidenceField(
  { identical, greater, smaller }: { identical: number; greater: number; smaller: number }
) {
  const reduce = useReducedMotion();
  const cells = [
    ...Array(identical).fill("var(--defect)"),
    ...Array(greater).fill("var(--muted)"),
    ...Array(smaller).fill("var(--accent)"),
  ];
  const total = cells.length;
  return (
    <>
      <div className="field" aria-hidden>
        {cells.map((c, i) => (
          <motion.i
            key={i}
            style={{ background: c }}
            initial={reduce ? false : { opacity: 0, scale: .4 }}
            whileInView={reduce ? undefined : { opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            // stagger across the whole field in under a second, not per-cell delay
            transition={{ duration: .35, delay: (i / total) * .8, ease: "easeOut" }}
          />
        ))}
      </div>
      <p className="legend">
        <span><i className="sw" style={{ background: "var(--defect)" }} />
          <strong className="num">{identical}</strong>&nbsp;identical to the vehicle
          ({Math.round(100 * identical / total)}%)</span>
        <span><i className="sw" style={{ background: "var(--muted)" }} />
          <strong className="num">{greater}</strong>&nbsp;higher on day 2</span>
        <span><i className="sw" style={{ background: "var(--accent)" }} />
          <strong className="num">{smaller}</strong>&nbsp;lower on day 2</span>
      </p>
    </>
  );
}
