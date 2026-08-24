"use client";
import { motion, useReducedMotion, useScroll, useSpring } from "motion/react";

/**
 * Reading-progress rail. Scroll-linked, so it costs one transform per frame.
 *
 * The spring is gated on prefers-reduced-motion. The CSS escape hatch elsewhere in
 * globals.css cannot reach Motion — Motion drives transforms through the Web Animations
 * API and inline style, both of which win over a stylesheet rule — so a reader who has
 * asked the OS for less motion still got a spring-damped bar chasing their scroll.
 * Reduced motion keeps the rail and its information, and drops the springiness.
 */
export default function Rail() {
  const { scrollYProgress } = useScroll();
  const reduced = useReducedMotion();
  const smooth = useSpring(scrollYProgress, { stiffness: 220, damping: 40, mass: .3 });
  return <motion.div className="rail"
                     style={{ scaleX: reduced ? scrollYProgress : smooth }} aria-hidden />;
}
