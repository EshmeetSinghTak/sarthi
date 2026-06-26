"use client";

import Link from "next/link";

import { Chakra } from "../Chakra";
import { IconArrowRight } from "../icons";

export function MarketingNav() {
  return (
    <header className="sticky top-0 z-20 border-b border-ink-3/60 bg-ink/70 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center gap-4 px-5 py-3" aria-label="Marketing">
        <Link href="/" className="flex items-center gap-2 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60">
          <Chakra size={28} />
          <span className="font-display text-xl font-semibold tracking-tight">SARTHI</span>
          <span className="font-deva text-saffron">सारथी</span>
        </Link>
        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <a href="#features" className="hidden min-h-11 items-center rounded-full px-3 text-sm text-muted transition-colors hover:text-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60 sm:inline-flex">
            Features
          </a>
          <a href="#how" className="hidden min-h-11 items-center rounded-full px-3 text-sm text-muted transition-colors hover:text-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60 sm:inline-flex">
            How it works
          </a>
          <Link
            href="/chat"
            className="inline-flex min-h-11 items-center gap-1.5 rounded-full bg-saffron px-4 text-sm font-medium text-ink transition-colors hover:bg-saffron-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/70"
          >
            Start free <IconArrowRight className="size-4" />
          </Link>
        </div>
      </nav>
    </header>
  );
}
