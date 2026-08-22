"use client";
import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

/** Entrance reveal. Only transform and opacity animate, so it stays on the compositor. */
export default function Reveal({ children, delay = 0, y = 14 }:
  { children: ReactNode; delay?: number; y?: number }) {
  const reduce = useReducedMotion();
  if (reduce) return <>{children}</>;
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: .5, delay, ease: [0.22, 1, 0.36, 1] }}
    >{children}</motion.div>
  );
}
