import type { Variants } from "framer-motion";

/** Staggered reveal for groups (hero, card grids). */
export const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};

/** A single staggered child. */
export const item: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 26 } },
};

/** Fade-up used with whileInView for scroll-revealed landing sections. */
export const reveal: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 240, damping: 28 } },
};
