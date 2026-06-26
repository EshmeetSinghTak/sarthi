"use client";

import { motion } from "framer-motion";

import { container, item } from "../../lib/motion";
import { PHASES } from "../../lib/content";

export function HowItWorks() {
  return (
    <section id="how" className="section border-t border-ink-3/60">
      <div className="mx-auto max-w-3xl px-5">
        <h2 className="text-center font-display text-3xl font-semibold tracking-tight sm:text-4xl">
          Four phases. One agent.
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-balance text-center text-muted">
          Priya&apos;s path with SARTHI — from first question to a funded seat, and a friend brought along.
        </p>
        <motion.ol
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.15 }}
          className="mt-12 space-y-4"
        >
          {PHASES.map((p, i) => (
            <motion.li
              key={p.phase}
              variants={item}
              className="flex gap-4 rounded-2xl border border-ink-3 bg-ink-2/40 p-5"
            >
              <span className="grid size-9 shrink-0 place-items-center rounded-full bg-saffron/12 font-display text-sm font-semibold text-saffron tabular-nums">
                {i + 1}
              </span>
              <div>
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <span className="text-xs font-medium uppercase tracking-wide text-saffron">{p.phase}</span>
                  <h3 className="font-display text-lg font-semibold">{p.title}</h3>
                </div>
                <p className="mt-1 text-sm leading-relaxed text-muted">{p.moment}</p>
              </div>
            </motion.li>
          ))}
        </motion.ol>
      </div>
    </section>
  );
}
