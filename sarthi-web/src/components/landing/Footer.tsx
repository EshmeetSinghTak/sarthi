import Link from "next/link";

import { Chakra } from "../Chakra";
import { IconGithub } from "../icons";

export function Footer() {
  return (
    <footer className="border-t border-ink-3/60 bg-ink">
      <div className="mx-auto max-w-6xl px-5 py-12">
        <div className="flex flex-wrap items-center gap-3">
          <Chakra size={26} />
          <span className="font-display text-lg font-semibold tracking-tight">SARTHI</span>
          <span className="font-deva text-saffron">सारथी</span>
          <a
            href="https://github.com/EshmeetSinghTak/sarthi"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="SARTHI on GitHub"
            className="ml-auto inline-flex min-h-11 items-center gap-2 rounded-full px-3 text-sm text-muted transition-colors hover:text-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60"
          >
            <IconGithub className="size-5" /> GitHub
          </a>
        </div>
        <p className="mt-6 max-w-2xl text-sm text-muted">
          Your AI Sarthi — from dream to degree.
        </p>
        <p className="mt-2 max-w-2xl text-xs text-muted">
          SARTHI guides; it doesn&apos;t decide. Loan and admission outcomes rest with the institution.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
          <Link href="/chat" className="text-muted transition-colors hover:text-cream">Chat</Link>
          <Link href="/sop" className="text-muted transition-colors hover:text-cream">SOP Workspace</Link>
          <span className="text-xs text-muted">MIT · built with free NVIDIA models</span>
        </div>
      </div>
    </footer>
  );
}
