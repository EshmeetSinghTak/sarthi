"use client";

import { motion } from "framer-motion";

import {
  IconChart,
  IconCompass,
  IconFile,
  IconList,
  IconPen,
  IconShare,
  IconWallet,
} from "../icons";
import { container, item } from "../../lib/motion";
import { FEATURES, type FeatureIcon } from "../../lib/content";

const ICONS: Record<FeatureIcon, (p: { className?: string }) => React.JSX.Element> = {
  compass: IconCompass,
  list: IconList,
  chart: IconChart,
  pen: IconPen,
  wallet: IconWallet,
  file: IconFile,
  share: IconShare,
};

export function FeatureGrid() {
  return (
    <section id="features" className="section">
      <div className="mx-auto max-w-6xl px-5">
        <h2 className="text-center font-display text-3xl font-semibold tracking-tight sm:text-4xl">
          One agent, the whole journey.
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-balance text-center text-muted">
          Seven capabilities — four live today, three on the road ahead.
        </p>
        <motion.ul
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.15 }}
          className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {FEATURES.map((f) => {
            const Icon = ICONS[f.icon];
            return (
              <motion.li
                key={f.id}
                variants={item}
                className="rounded-2xl border border-ink-3 bg-ink-2/40 p-6 transition-colors hover:border-saffron/40"
              >
                <div className="flex items-center justify-between">
                  <span className="grid size-11 place-items-center rounded-xl bg-saffron/12 text-saffron">
                    <Icon className="size-5" />
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                      f.status === "live" ? "bg-saffron/15 text-saffron" : "bg-ink-3 text-muted"
                    }`}
                  >
                    {f.status === "live" ? "Live" : "Soon"}
                  </span>
                </div>
                <h3 className="mt-4 font-display text-lg font-semibold">{f.name}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{f.blurb}</p>
              </motion.li>
            );
          })}
        </motion.ul>
      </div>
    </section>
  );
}
