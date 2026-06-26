"use client";

import { motion } from "framer-motion";

/** SARTHI's mark: a chariot wheel (chakra). Rolls while she is working. */
export function Chakra({ rolling = false, size = 28 }: { rolling?: boolean; size?: number }) {
  const spokes = Array.from({ length: 8 }, (_, i) => (i * 360) / 8);
  return (
    <motion.span
      className="grid shrink-0 place-items-center rounded-full bg-saffron/12"
      style={{ width: size, height: size }}
      animate={rolling ? { rotate: 360 } : { rotate: 0 }}
      transition={rolling ? { repeat: Infinity, ease: "linear", duration: 3.5 } : { duration: 0.2 }}
      aria-hidden
    >
      <svg viewBox="0 0 24 24" style={{ width: size * 0.7, height: size * 0.7 }} className="text-saffron">
        <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <circle cx="12" cy="12" r="2.2" fill="currentColor" />
        {spokes.map((deg) => (
          <line
            key={deg}
            x1="12"
            y1="12"
            x2="12"
            y2="3.5"
            stroke="currentColor"
            strokeWidth="1"
            transform={`rotate(${deg} 12 12)`}
          />
        ))}
      </svg>
    </motion.span>
  );
}
