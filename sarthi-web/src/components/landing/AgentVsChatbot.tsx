"use client";

import { motion } from "framer-motion";

import { IconCheck, IconDash } from "../icons";
import { reveal } from "../../lib/motion";
import { AGENT_VS_CHATBOT } from "../../lib/content";

export function AgentVsChatbot() {
  return (
    <section className="section border-y border-ink-3/60">
      <motion.div
        variants={reveal}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.3 }}
        className="mx-auto max-w-4xl px-5"
      >
        <h2 className="text-center font-display text-3xl font-semibold tracking-tight sm:text-4xl">
          Not a chatbot. An agent.
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-balance text-center text-muted">
          Chatbots answer and forget. SARTHI remembers you, uses tools, and takes action.
        </p>
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-ink-3 bg-ink-2/40 p-6">
            <p className="text-sm font-medium uppercase tracking-wide text-muted">A generic chatbot</p>
            <ul className="mt-4 space-y-3">
              {AGENT_VS_CHATBOT.chatbot.map((t) => (
                <li key={t} className="flex items-center gap-3 text-sm text-muted">
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-ink-3 text-muted">
                    <IconDash className="size-3.5" />
                  </span>
                  {t}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-saffron/30 bg-saffron/5 p-6">
            <p className="text-sm font-medium uppercase tracking-wide text-saffron">SARTHI</p>
            <ul className="mt-4 space-y-3">
              {AGENT_VS_CHATBOT.sarthi.map((t) => (
                <li key={t} className="flex items-center gap-3 text-sm text-cream">
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-saffron/15 text-saffron">
                    <IconCheck className="size-3.5" />
                  </span>
                  {t}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
