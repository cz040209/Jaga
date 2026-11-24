"use client";

import { motion } from "framer-motion";

/**
 * The soft "mesh" behind every screen: three large blurred colour blobs
 * (teal, sky, lavender) drifting very slowly. Fixed behind all content,
 * ignored by screen readers and clicks.
 */
const BLOBS = [
  { className: "left-[-20%] top-[-12%] size-[420px] bg-teal-200/60 dark:bg-teal-500/20", x: [0, 30, 0], y: [0, 20, 0], duration: 18 },
  { className: "right-[-25%] top-[18%] size-[380px] bg-sky-200/55 dark:bg-sky-600/15", x: [0, -24, 0], y: [0, 30, 0], duration: 22 },
  { className: "bottom-[-18%] left-[10%] size-[400px] bg-violet-200/40 dark:bg-violet-600/15", x: [0, 20, 0], y: [0, -24, 0], duration: 26 },
];

export function MeshBackground() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {BLOBS.map(({ className, x, y, duration }) => (
        <motion.div
          key={className}
          className={`absolute rounded-full blur-3xl ${className}`}
          animate={{ x, y }}
          transition={{ duration, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
      {/* A faint veil keeps text crisp on top of the colours. */}
      <div className="absolute inset-0 bg-white/30 dark:bg-slate-950/30" />
    </div>
  );
}
