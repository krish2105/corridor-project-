"use client";
import { useEffect, useRef, useState } from "react";
import { motion, useInView, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

/**
 * Entrance reveal that cannot leave content invisible.
 *
 * The obvious implementation — `initial={{opacity:0}}` plus `whileInView` — hides
 * the entire page until an IntersectionObserver fires. If anything stops it firing
 * (a smooth-scroll library hijacking scroll, a restored bfcache page, an inert
 * background tab) the reader gets a blank page. So a timer forces the visible state
 * regardless, and motion is only ever an enhancement on top of readable content.
 */
export default function Reveal({ children, delay = 0, y = 14 }:
  { children: ReactNode; delay?: number; y?: number }) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const [failsafe, setFailsafe] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setFailsafe(true), 800);
    return () => clearTimeout(t);
  }, []);

  if (reduce) return <div ref={ref}>{children}</div>;

  const shown = inView || failsafe;
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y }}
      animate={shown ? { opacity: 1, y: 0 } : { opacity: 0, y }}
      transition={{ duration: .5, delay: inView ? delay : 0, ease: [0.22, 1, 0.36, 1] }}
    >{children}</motion.div>
  );
}
