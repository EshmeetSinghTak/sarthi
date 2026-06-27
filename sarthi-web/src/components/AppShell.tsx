"use client";

import { MotionConfig } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Chakra } from "./Chakra";
import { IconChat, IconDoc, IconWallet } from "./icons";
import { APP_NAV, type NavItem } from "../lib/nav";

const ICONS = { chat: IconChat, doc: IconDoc, wallet: IconWallet } as const;

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(href + "/");
}

function RailLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = ICONS[item.icon];
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={`group flex min-h-11 items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60 ${
        active ? "bg-ink-2 text-cream" : "text-muted hover:bg-ink-2/60 hover:text-cream"
      }`}
    >
      <Icon className={`size-5 shrink-0 ${active ? "text-saffron" : ""}`} />
      <span className="hidden lg:inline">{item.label}</span>
    </Link>
  );
}

function BottomLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = ICONS[item.icon];
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={`flex min-h-11 flex-1 flex-col items-center justify-center gap-0.5 rounded-lg py-1.5 text-[11px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60 ${
        active ? "text-saffron" : "text-muted"
      }`}
    >
      <Icon className="size-5" />
      {item.label}
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <MotionConfig reducedMotion="user">
      <div className="flex h-dvh flex-col lg:flex-row">
        {/* Mobile top bar */}
        <header className="flex items-center gap-3 border-b border-ink-3 px-4 py-3 lg:hidden">
          <Link href="/" className="flex items-center gap-2 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60">
            <Chakra size={24} />
            <span className="font-display text-lg font-semibold tracking-tight">SARTHI</span>
            <span className="font-deva text-saffron">सारथी</span>
          </Link>
        </header>

        {/* Desktop left rail */}
        <aside className="hidden shrink-0 flex-col border-r border-ink-3 p-3 lg:flex lg:w-56">
          <Link
            href="/"
            className="mb-6 flex items-center gap-2 rounded-lg px-2 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60"
          >
            <Chakra size={28} />
            <span className="font-display text-xl font-semibold tracking-tight">SARTHI</span>
            <span className="font-deva text-saffron">सारथी</span>
          </Link>
          <nav className="flex flex-col gap-1" aria-label="Primary">
            {APP_NAV.map((item) => (
              <RailLink key={item.href} item={item} active={isActive(pathname, item.href)} />
            ))}
          </nav>
          <Link
            href="/"
            className="mt-auto rounded-lg px-3 py-2 text-xs text-muted transition-colors hover:text-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60"
          >
            ← Back to home
          </Link>
        </aside>

        {/* Page content */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">{children}</div>

        {/* Mobile bottom nav */}
        <nav
          className="flex items-stretch gap-1 border-t border-ink-3 px-2 py-1 lg:hidden"
          aria-label="Primary"
          style={{ paddingBottom: "max(0.25rem, env(safe-area-inset-bottom))" }}
        >
          {APP_NAV.map((item) => (
            <BottomLink key={item.href} item={item} active={isActive(pathname, item.href)} />
          ))}
        </nav>
      </div>
    </MotionConfig>
  );
}
