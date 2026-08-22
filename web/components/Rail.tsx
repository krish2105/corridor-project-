"use client";
import { motion, useScroll, useSpring } from "motion/react";

/** Reading-progress rail. Scroll-linked, so it costs one transform per frame. */
export default function Rail() {
  const { scrollYProgress } = useScroll();
  const x = useSpring(scrollYProgress, { stiffness: 220, damping: 40, mass: .3 });
  return <motion.div className="rail" style={{ scaleX: x }} aria-hidden />;
}
