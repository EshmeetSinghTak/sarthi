"use client";

import { motion } from "framer-motion";
import Link from "next/link";

import { Chakra } from "../Chakra";
import { IconArrowRight } from "../icons";
import { container, item } from "../../lib/motion";

export function Hero() {
  return (
    <section className="bg-dawn">
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="mx-auto flex max-w-3xl flex-col items-center px-5 pb-10 pt-20 text-center sm:pt-28"
      >
        <motion.div variants={item} className="aura-saffron">
          <Chakra size={56} />
        </motion.div>
        <motion.p variants={item} className="mt-6 font-deva text-lg text-saffron">
          सारथी
        </motion.p>
        <motion.h1 variants={item} className="mt-3 font-display text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">
          Your AI Sarthi — from dream to degree.
        </motion.h1>
        <motion.p variants={item} className="mt-5 max-w-xl text-balance text-base text-muted sm:text-lg">
          An agentic AI mentor that guides Indian students through studying abroad — from
          &ldquo;where do I even go?&rdquo; to a funded degree — in one memory-powered, vernacular
          conversation.
        </motion.p>
        <motion.div variants={item} className="mt-9 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/chat"
            className="inline-flex min-h-11 items-center gap-1.5 rounded-full bg-saffron px-6 py-3 text-sm font-medium text-ink transition-colors hover:bg-saffron-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/70"
          >
            Start free <IconArrowRight className="size-4" />
          </Link>
          <a
            href="#how"
            className="inline-flex min-h-11 items-center rounded-full border border-ink-3 px-6 py-3 text-sm text-cream transition-colors hover:border-saffron/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60"
          >
            See how it works
          </a>
        </motion.div>
      </motion.div>
    </section>
  );
}
