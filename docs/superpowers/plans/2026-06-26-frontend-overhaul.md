# Frontend Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn SARTHI's sparse frontend into a professional "modern AI product site" — a marketing landing page at `/` plus a polished, shared-shell app (chat at `/chat`, SOP at `/sop`).

**Architecture:** A Next.js App Router route group `(app)` wraps `/chat` and `/sop` in one `AppShell` (sidebar on desktop, top + bottom nav on mobile). The landing page lives at `/` with its own marketing nav. Duplicated bits (`Chakra`, icons, motion variants) are extracted into `src/components` and `src/lib` and imported everywhere. No backend changes.

**Tech Stack:** Next.js 16 (App Router), React 19, Tailwind CSS v4 (token-based, `@theme` in `globals.css`), framer-motion, TypeScript.

## Global Constraints

- **No backend changes.** Only `sarthi-web/` is touched. The agent, SSE contract, `/api/agent/*` rewrites, and signed-cookie identity are untouched.
- **Never hardcode tunables / repeated content.** Design values live as tokens in `globals.css` or `src/lib/motion.ts`; repeated content (nav items, features, phases, comparison rows) lives in typed arrays in `src/lib`, not duplicated JSX.
- **DRY.** `Chakra`, the icon set, and the motion variants must exist once (in `src/components` / `src/lib`) and be imported. No copied component definitions across pages.
- **Honest content only.** No fabricated testimonials, partner logos, user counts, or precision metrics. Landing copy uses genuine product framing. The advisory disclaimer ("SARTHI guides; it doesn't decide. Loan and admission outcomes rest with the institution.") stays visible.
- **"This is NOT the Next.js you know"** (`sarthi-web/AGENTS.md`): the routing/layout conventions used here are verified against `sarthi-web/node_modules/next/dist/docs/01-app/01-getting-started/03-layouts-and-pages.md` and `04-linking-and-navigating.md` — `Link` from `next/link`, `usePathname` from `next/navigation`, route groups `(folder)`, nested `layout.tsx` receiving `{ children }`. If extending beyond these, read the docs first.
- **Accessibility:** contrast ≥ 4.5:1, visible focus rings (`focus-visible:ring-2 focus-visible:ring-saffron/...`), ≥ 44px touch targets (`min-h-11`), keyboard operable, `aria-current="page"` on active nav, `prefers-reduced-motion` respected (use `MotionConfig reducedMotion="user"` + the CSS reduced-motion block), semantic headings, SVG icons (no emoji).
- **Dark theme only.** Existing tokens: `ink` `#1a1733`, `ink-2` `#241f45`, `ink-3` `#2f2956`, `cream` `#f5f0e6`, `muted` `#9b95c4`, `saffron` `#f4a02c`, `saffron-deep` `#e8842a`. Fonts: `font-display` (Fraunces), `font-body` (Inter), `font-deva` (Noto Serif Devanagari).
- **Verification is build + type + manual** (no FE test harness). Every task ends with `npx tsc --noEmit` and the dev server / build passing, plus a stated manual check. Run all commands from `sarthi-web/`.

---

## File Structure

```
sarthi-web/src/
  app/
    layout.tsx                 # MODIFY: minor (metadata fine as-is); stays root
    globals.css                # MODIFY: add tokens (radii, motion durations) + aura/gradient/section utilities
    page.tsx                   # REPLACE: chat logic leaves; becomes the landing page
    (app)/
      layout.tsx               # CREATE: wraps children in <AppShell>
      chat/page.tsx            # CREATE: moved chat (was app/page.tsx), re-skinned, shared imports
      sop/page.tsx             # MOVE from app/sop/page.tsx, re-skinned, shared imports
  components/
    Chakra.tsx                 # CREATE: extracted chariot-wheel mark
    icons.tsx                  # CREATE: extracted + extended inline stroke icons
    AppShell.tsx               # CREATE: sidebar + topbar + bottom nav, active state
    landing/
      MarketingNav.tsx         # CREATE
      Hero.tsx                 # CREATE
      AgentVsChatbot.tsx       # CREATE
      FeatureGrid.tsx          # CREATE
      HowItWorks.tsx           # CREATE
      Footer.tsx               # CREATE
  lib/
    motion.ts                  # CREATE: container, item, reveal variants + durations
    nav.ts                     # CREATE: typed app-nav items
    content.ts                 # CREATE: typed FEATURES, PHASES, AGENT_VS_CHATBOT
    sop.ts                     # UNCHANGED
```

Old `src/app/sop/page.tsx` is **deleted** after its content moves to `src/app/(app)/sop/page.tsx`.

---

## Task 1: Design-system foundation (tokens + motion)

**Files:**
- Modify: `sarthi-web/src/app/globals.css`
- Create: `sarthi-web/src/lib/motion.ts`

**Interfaces:**
- Produces (CSS): radius tokens `--radius-card`, `--radius-pill`; motion duration tokens `--dur-fast`, `--dur-base`; utility classes `.bg-dawn`, `.aura-saffron`, `.section` (used by landing + empty states).
- Produces (TS) from `src/lib/motion.ts`:
  - `container: Variants` and `item: Variants` (identical to the variants currently inlined in the pages)
  - `reveal: Variants` — fade-up for scroll reveal: `hidden {opacity:0,y:20}`, `show {opacity:1,y:0, transition spring}`.

- [ ] **Step 1: Add tokens + utilities to `globals.css`**

Add the radius + motion tokens inside the existing `@theme { … }` block (after the font tokens):

```css
  --radius-card: 1rem;
  --radius-pill: 9999px;

  --dur-fast: 150ms;
  --dur-base: 250ms;
```

Then add these utilities to the file (after the `@theme` block, near the other custom CSS):

```css
/* Dawn gradient canvas — the light the charioteer drives toward. */
.bg-dawn {
  background:
    radial-gradient(60% 50% at 50% 0%, rgb(244 160 44 / 0.10), transparent 70%),
    radial-gradient(40% 40% at 80% 10%, rgb(232 132 42 / 0.08), transparent 70%),
    var(--color-ink);
}

/* Soft saffron aura behind hero marks and empty states. */
.aura-saffron {
  position: relative;
}
.aura-saffron::before {
  content: "";
  position: absolute;
  inset: -40% -20% auto -20%;
  height: 18rem;
  background: radial-gradient(50% 50% at 50% 50%, rgb(244 160 44 / 0.16), transparent 70%);
  filter: blur(60px);
  z-index: -1;
  pointer-events: none;
}

/* Consistent vertical rhythm for landing sections. */
.section {
  padding-block: clamp(3.5rem, 8vw, 7rem);
}
```

- [ ] **Step 2: Create `src/lib/motion.ts`**

```ts
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
```

- [ ] **Step 3: Type-check**

Run: `cd sarthi-web && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add sarthi-web/src/app/globals.css sarthi-web/src/lib/motion.ts
git commit -m "feat(web): design tokens (radii, motion, aura/dawn utils) + shared motion variants"
```

---

## Task 2: Shared primitives (Chakra + icons)

**Files:**
- Create: `sarthi-web/src/components/Chakra.tsx`
- Create: `sarthi-web/src/components/icons.tsx`

**Interfaces:**
- Produces: `Chakra({ rolling?: boolean; size?: number })` — the chariot-wheel mark (identical behavior to the current inlined copies).
- Produces (icons, each `({ className?: string }) => JSX`): `IconCheck`, `IconDash`, `IconPlus`, `IconRestore`, `IconChevronDown`, `IconSend`, `IconArrowRight`, `IconChat`, `IconDoc`, `IconCompass`, `IconList`, `IconChart`, `IconPen`, `IconWallet`, `IconFile`, `IconShare`, `IconGithub`.

- [ ] **Step 1: Create `src/components/Chakra.tsx`**

```tsx
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
```

- [ ] **Step 2: Create `src/components/icons.tsx`**

```tsx
type IconProps = { className?: string };

function svg(path: React.ReactNode, sw = 2) {
  return (className: string) => (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={sw} aria-hidden>
      {path}
    </svg>
  );
}

export function IconCheck({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.4" aria-hidden><path d="M20 6 9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function IconDash({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.4" aria-hidden><path d="M5 12h14" strokeLinecap="round" /></svg>;
}
export function IconPlus({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden><path d="M12 5v14M5 12h14" strokeLinecap="round" /></svg>;
}
export function IconRestore({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden><path d="M3 12a9 9 0 1 0 2.6-6.3" strokeLinecap="round" strokeLinejoin="round" /><path d="M3 4v5h5" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function IconChevronDown({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden><path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function IconSend({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden><path d="M12 19V5M5 12l7-7 7 7" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function IconArrowRight({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden><path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function IconChat({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden><path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function IconDoc({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" strokeLinecap="round" strokeLinejoin="round" /><path d="M14 3v5h5M9 13h6M9 17h4" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function IconCompass({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden><circle cx="12" cy="12" r="9" /><path d="m15.5 8.5-2 5-5 2 2-5z" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function IconList({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function IconChart({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden><path d="M3 3v18h18" strokeLinecap="round" strokeLinejoin="round" /><path d="M7 14l4-4 3 3 4-5" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function IconPen({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden><path d="M12 20h9" strokeLinecap="round" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function IconWallet({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden><path d="M3 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v0H5" strokeLinecap="round" strokeLinejoin="round" /><path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7H5" strokeLinecap="round" strokeLinejoin="round" /><path d="M16 13h.01" strokeLinecap="round" /></svg>;
}
export function IconFile({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" strokeLinecap="round" strokeLinejoin="round" /><path d="M14 3v5h5" strokeLinecap="round" strokeLinejoin="round" /><path d="m9 15 2 2 4-4" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function IconShare({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4" strokeLinecap="round" /></svg>;
}
export function IconGithub({ className = "" }: IconProps) {
  return <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden><path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.46-1.11-1.46-.9-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.89 1.52 2.34 1.08 2.91.83.09-.65.35-1.08.63-1.33-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.99 1.03-2.69-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.5 9.5 0 0 1 5 0c1.91-1.29 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.6 1.03 2.69 0 3.84-2.34 4.69-4.57 4.94.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0 0 12 2z" /></svg>;
}

// `svg` helper kept for future icons; intentionally exported to avoid unused warnings.
export const _svg = svg;
```

> Note: the `svg`/`_svg` helper is optional scaffolding — if `tsc`/lint flags it as unused, delete both the helper and the `_svg` export rather than keeping dead code.

- [ ] **Step 3: Type-check**

Run: `cd sarthi-web && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add sarthi-web/src/components/Chakra.tsx sarthi-web/src/components/icons.tsx
git commit -m "feat(web): extract shared Chakra mark + inline icon set"
```

---

## Task 3: Nav + content data

**Files:**
- Create: `sarthi-web/src/lib/nav.ts`
- Create: `sarthi-web/src/lib/content.ts`

**Interfaces:**
- Produces: `APP_NAV: NavItem[]` where `NavItem = { href: "/chat" | "/sop"; label: string; icon: "chat" | "doc" }`.
- Produces: `FEATURES: Feature[]` where `Feature = { id: string; name: string; blurb: string; status: "live" | "soon"; icon: FeatureIcon }`, `FeatureIcon = "compass" | "list" | "chart" | "pen" | "wallet" | "file" | "share"`.
- Produces: `PHASES: Phase[]` where `Phase = { phase: string; title: string; moment: string }`.
- Produces: `AGENT_VS_CHATBOT: { chatbot: string[]; sarthi: string[] }`.

- [ ] **Step 1: Create `src/lib/nav.ts`**

```ts
export type NavItem = { href: "/chat" | "/sop"; label: string; icon: "chat" | "doc" };

export const APP_NAV: NavItem[] = [
  { href: "/chat", label: "Chat", icon: "chat" },
  { href: "/sop", label: "SOP", icon: "doc" },
];
```

- [ ] **Step 2: Create `src/lib/content.ts`**

```ts
export type FeatureIcon = "compass" | "list" | "chart" | "pen" | "wallet" | "file" | "share";
export type Feature = {
  id: string;
  name: string;
  blurb: string;
  status: "live" | "soon";
  icon: FeatureIcon;
};

/** The Hero-7. F1–F4 are live; F5–F7 are honest roadmap. */
export const FEATURES: Feature[] = [
  { id: "f1", name: "Conversational Agent Core", blurb: "A mentor with memory that remembers your story across every session.", status: "live", icon: "compass" },
  { id: "f2", name: "University Shortlister", blurb: "Your profile in, a ranked Reach / Target / Safe list out.", status: "live", icon: "list" },
  { id: "f3", name: "ROI Predictor", blurb: "Cost vs. salary vs. EMI — see whether a degree actually pays back.", status: "live", icon: "chart" },
  { id: "f4", name: "SOP Co-Pilot", blurb: "Socratic coaching that sharpens your statement — in your own words.", status: "live", icon: "pen" },
  { id: "f5", name: "Loan Eligibility & Offer", blurb: "A personalized funding offer, built from what SARTHI already knows.", status: "soon", icon: "wallet" },
  { id: "f6", name: "Document Auto-Fill", blurb: "Your loan application, filled from your conversations — not from scratch.", status: "soon", icon: "file" },
  { id: "f7", name: "Study Abroad Passport", blurb: "A shareable milestone card for the friends walking the same road.", status: "soon", icon: "share" },
];

export type Phase = { phase: string; title: string; moment: string };

/** Priya's journey with SARTHI — the four phases, plus the amplify loop. */
export const PHASES: Phase[] = [
  { phase: "Discover", title: "“Where do I even go?”", moment: "Chat in Hinglish and get a personalized timeline: IELTS → GRE → Apps → Visa." },
  { phase: "Decide", title: "“Which ten actually fit me?”", moment: "SARTHI builds your profile, then shows a shortlist with ROI for each university." },
  { phase: "Apply", title: "“Will my SOP stand out?”", moment: "Socratic coaching sharpens your statement — the words stay yours." },
  { phase: "Fund", title: "“Can I afford it?”", moment: "A personalized loan offer, auto-filled from everything SARTHI remembers." },
  { phase: "Amplify", title: "“Bring a friend.”", moment: "Share your Study Abroad Passport — the journey compounds." },
];

/** The core differentiator: not a chatbot, an agent. */
export const AGENT_VS_CHATBOT: { chatbot: string[]; sarthi: string[] } = {
  chatbot: ["Stateless — forgets you", "Answers only", "English-only"],
  sarthi: ["Remembers you across sessions", "Takes real actions with tools", "Hinglish & vernacular"],
};
```

- [ ] **Step 3: Type-check**

Run: `cd sarthi-web && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add sarthi-web/src/lib/nav.ts sarthi-web/src/lib/content.ts
git commit -m "feat(web): typed nav + landing content (Hero-7, phases, agent-vs-chatbot)"
```

---

## Task 4: AppShell + route-group layout

**Files:**
- Create: `sarthi-web/src/components/AppShell.tsx`
- Create: `sarthi-web/src/app/(app)/layout.tsx`

**Interfaces:**
- Consumes: `Chakra` (Task 2), `IconChat`/`IconDoc` (Task 2), `APP_NAV` (Task 3).
- Produces: `AppShell({ children }: { children: React.ReactNode })` — desktop left rail + mobile top/bottom nav, with `aria-current="page"` on the active route via `usePathname`.

- [ ] **Step 1: Create `src/components/AppShell.tsx`**

```tsx
"use client";

import { MotionConfig } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Chakra } from "./Chakra";
import { IconChat, IconDoc } from "./icons";
import { APP_NAV, type NavItem } from "../lib/nav";

const ICONS = { chat: IconChat, doc: IconDoc } as const;

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
```

- [ ] **Step 2: Create `src/app/(app)/layout.tsx`**

```tsx
import { AppShell } from "../../components/AppShell";

export default function AppGroupLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
```

- [ ] **Step 3: Type-check**

Run: `cd sarthi-web && npx tsc --noEmit`
Expected: no errors. (No route yet renders the shell — that arrives in Tasks 5–6.)

- [ ] **Step 4: Commit**

```bash
git add "sarthi-web/src/components/AppShell.tsx" "sarthi-web/src/app/(app)/layout.tsx"
git commit -m "feat(web): AppShell (sidebar + mobile nav) + (app) route-group layout"
```

---

## Task 5: Move + re-skin chat → `/chat`

**Files:**
- Create: `sarthi-web/src/app/(app)/chat/page.tsx`
- Modify: `sarthi-web/src/app/page.tsx` (temporary stub here; replaced fully in Task 7)

**Interfaces:**
- Consumes: `Chakra` (Task 2), `container`/`item` (Task 1), and runs inside `AppShell` (Task 4).
- Produces: the chat experience at `/chat`.

This task moves the current chat (today in `src/app/page.tsx`) into the route group, swaps inlined `Chakra` + motion variants for shared imports, and removes the page's own header (the shell provides nav). The streaming logic — session ping, `fetch("/api/agent/chat")`, the CRLF-tolerant frame parser, error handling — is preserved **verbatim**.

- [ ] **Step 1: Create `src/app/(app)/chat/page.tsx`**

```tsx
"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Chakra } from "../../../components/Chakra";
import { container, item } from "../../../lib/motion";

type Role = "user" | "sarthi";
type Message = { id: number; role: Role; content: string };

const STARTERS = [
  "Robotics mein MS karna hai — kahan apply karun?",
  "₹40L budget mein US ya Canada?",
  "IELTS pehle ya GRE?",
];

/** Three-dot "thinking" pulse shown before the first token arrives. */
function Thinking() {
  return (
    <span className="flex items-center gap-1 pt-2" aria-label="SARTHI is thinking">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="size-1.5 rounded-full bg-muted"
          animate={{ opacity: [0.25, 1, 0.25], y: [0, -2, 0] }}
          transition={{ repeat: Infinity, duration: 1.1, delay: i * 0.18, ease: "easeInOut" }}
        />
      ))}
    </span>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streamingId, setStreamingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const nextId = useRef(1);
  const reduce = useReducedMotion();

  useEffect(() => {
    fetch("/api/agent/session", { credentials: "include" }).catch(() => {});
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: reduce ? "auto" : "smooth",
    });
  }, [messages, reduce]);

  const busy = streamingId !== null;

  async function sendText(text: string) {
    if (!text.trim() || busy) return;
    setError(null);
    setInput("");
    if (taRef.current) taRef.current.style.height = "auto";

    const userMsg: Message = { id: nextId.current++, role: "user", content: text };
    const sarthiMsg: Message = { id: nextId.current++, role: "sarthi", content: "" };
    setMessages((m) => [...m, userMsg, sarthiMsg]);
    setStreamingId(sarthiMsg.id);

    const append = (token: string) =>
      setMessages((m) =>
        m.map((msg) => (msg.id === sarthiMsg.id ? { ...msg, content: msg.content + token } : msg)),
      );

    try {
      const res = await fetch("/api/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
        credentials: "include",
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // Frames separated by a blank line; tolerate CRLF (sse-starlette uses \r\n).
        const frames = buffer.split(/\r?\n\r?\n/);
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          let event = "message";
          const dataLines: string[] = [];
          for (const line of frame.split(/\r?\n/)) {
            if (line.startsWith(":")) continue;
            if (line.startsWith("event:")) event = line.slice(6).trim();
            else if (line.startsWith("data:")) {
              let v = line.slice(5);
              if (v.startsWith(" ")) v = v.slice(1);
              dataLines.push(v);
            }
          }
          const data = dataLines.join("\n");
          if (event === "token") append(data);
          else if (event === "error") setError("Something went wrong. Try again.");
        }
      }
    } catch {
      setError("Couldn't reach SARTHI. Is the agent running?");
    } finally {
      setStreamingId(null);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendText(input);
    }
  }

  function autoGrow(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  }

  const empty = messages.length === 0;

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      {/* Conversation */}
      <main ref={scrollRef} className="relative flex-1 overflow-y-auto">
        <div aria-hidden className="pointer-events-none absolute left-1/2 top-24 -z-0 h-72 w-72 -translate-x-1/2 rounded-full bg-saffron/15 blur-[100px]" />
        <div className="relative mx-auto w-full max-w-2xl px-5">
          {empty ? (
            <motion.div
              variants={container}
              initial="hidden"
              animate="show"
              className="flex min-h-[64vh] flex-col items-center justify-center text-center"
            >
              <motion.div variants={item} className="aura-saffron">
                <Chakra size={44} />
              </motion.div>
              <motion.h1 variants={item} className="mt-6 font-display text-4xl font-semibold leading-tight sm:text-5xl">
                Chalo, shuru karein?
              </motion.h1>
              <motion.p variants={item} className="mt-4 max-w-md text-balance text-muted">
                Tell me where you are in your journey — I&apos;ll help you find the way. English ya Hinglish, dono chalega.
              </motion.p>
              <motion.div variants={item} className="mt-8 flex flex-wrap justify-center gap-2">
                {STARTERS.map((s) => (
                  <button
                    key={s}
                    onClick={() => sendText(s)}
                    className="rounded-full border border-ink-3 bg-ink-2/60 px-3.5 py-1.5 text-sm text-cream/90 transition hover:border-saffron/50 hover:text-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60"
                  >
                    {s}
                  </button>
                ))}
              </motion.div>
            </motion.div>
          ) : (
            <ul className="space-y-6 py-6">
              <AnimatePresence initial={false}>
                {messages.map((m) =>
                  m.role === "user" ? (
                    <motion.li
                      key={m.id}
                      layout
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ type: "spring", stiffness: 320, damping: 28 }}
                      className="flex justify-end"
                    >
                      <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm border border-ink-3 bg-ink-2 px-4 py-2.5 text-cream">
                        {m.content}
                      </div>
                    </motion.li>
                  ) : (
                    <motion.li
                      key={m.id}
                      layout
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ type: "spring", stiffness: 320, damping: 28 }}
                      className="flex gap-3"
                    >
                      <Chakra rolling={streamingId === m.id} size={28} />
                      <div className="min-w-0 flex-1 pt-0.5">
                        {m.content === "" && streamingId === m.id ? (
                          <Thinking />
                        ) : (
                          <div className="md">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                            {streamingId === m.id && <span className="caret">▍</span>}
                          </div>
                        )}
                      </div>
                    </motion.li>
                  ),
                )}
              </AnimatePresence>
            </ul>
          )}
          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="pb-4 text-center text-sm text-saffron-deep"
                role="alert"
              >
                {error}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Composer */}
      <footer className="z-10 border-t border-ink-3 px-5 py-4">
        <div className="mx-auto flex w-full max-w-2xl items-end gap-2 rounded-2xl border border-ink-3 bg-ink-2 px-3 py-2 transition-colors focus-within:border-saffron/60">
          <textarea
            ref={taRef}
            value={input}
            onChange={autoGrow}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="Type in English or Hinglish…"
            aria-label="Message SARTHI"
            className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-cream outline-none placeholder:text-muted"
          />
          <motion.button
            onClick={() => sendText(input)}
            disabled={busy || !input.trim()}
            aria-label="Send message"
            whileTap={{ scale: 0.9 }}
            whileHover={busy || !input.trim() ? undefined : { scale: 1.06 }}
            className="grid size-9 shrink-0 place-items-center rounded-full bg-saffron text-ink transition-colors hover:bg-saffron-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/70 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 19V5M5 12l7-7 7 7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </motion.button>
        </div>
        <p className="mx-auto mt-2 max-w-2xl text-center text-[11px] text-muted">
          SARTHI guides; it doesn&apos;t decide. Loan and admission outcomes rest with the institution.
        </p>
      </footer>
    </div>
  );
}
```

- [ ] **Step 2: Replace `src/app/page.tsx` with a temporary redirect stub**

So the old chat code at `/` is gone and the app still builds before Task 7 lands the real landing page:

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/chat");
}
```

- [ ] **Step 3: Type-check and build**

Run: `cd sarthi-web && npx tsc --noEmit && npm run build`
Expected: build succeeds; `/chat` and `/` routes compile.

- [ ] **Step 4: Manual check (dev server)**

Run: `cd sarthi-web && npm run dev` (backend also running on :8000). Visit `/chat`:
- Shell sidebar shows on desktop; Chat is active; bottom nav shows on a narrow viewport.
- Empty state renders; a starter sends; tokens stream; the wheel rolls while streaming.
- With backend stopped, sending shows the "Couldn't reach SARTHI" error.
- `/` redirects to `/chat`.

- [ ] **Step 5: Commit**

```bash
git add "sarthi-web/src/app/(app)/chat/page.tsx" sarthi-web/src/app/page.tsx
git commit -m "feat(web): move chat into (app)/chat with shared shell; / redirects (temp)"
```

---

## Task 6: Move + re-skin SOP → `(app)/sop`

**Files:**
- Create: `sarthi-web/src/app/(app)/sop/page.tsx`
- Delete: `sarthi-web/src/app/sop/page.tsx`

**Interfaces:**
- Consumes: `Chakra` (Task 2), `IconCheck`/`IconDash`/`IconPlus`/`IconRestore`/`IconChevronDown` (Task 2), `container`/`item` (Task 1), the `lib/sop` client (unchanged), and runs inside `AppShell` (Task 4).
- Produces: the SOP workspace at `/sop`.

The behavior (create / open / save version / restore / history, the `Scorecard`, cookie identity) is unchanged. Changes: move under `(app)`, remove the page's own header, and import `Chakra` + icons from the shared modules instead of the local definitions.

- [ ] **Step 1: Create `src/app/(app)/sop/page.tsx`**

Copy the existing `src/app/sop/page.tsx` content with these exact edits:

1. Replace the imports block. Remove `import Link from "next/link";` only if no remaining `Link` usage stays — the "Ask SARTHI to review this" link **stays**, so keep `Link`. Replace `MotionConfig` usage (the shell now owns it). New top imports:

```tsx
"use client";

import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Chakra } from "../../../components/Chakra";
import { IconCheck, IconDash, IconPlus, IconRestore } from "../../../components/icons";
import { container, item } from "../../../lib/motion";
import {
  type Analysis,
  type SopMeta,
  createSop,
  getSop,
  getVersion,
  listSops,
  listVersions,
  saveVersion,
} from "../../../lib/sop";
```

2. **Delete** the local `Chakra`, `IconCheck`, `IconDash`, `IconPlus`, `IconRestore` function definitions and the local `container`/`item` consts (now imported). Keep `SIGNALS`, `Scorecard`, and the page component.

3. The history disclosure uses a chevron SVG inline — replace that inline `<svg>` with `<IconChevronDown className="size-4 transition-transform group-open:rotate-180" />` and add `IconChevronDown` to the icon import above.

4. Remove the page's own `<header>` (the shell provides nav). Replace the outer wrapper: drop `<MotionConfig reducedMotion="user">` and its closing tag, and change the root from `<div className="flex min-h-dvh flex-col">` to `<div className="flex min-h-0 flex-1 flex-col">`. The three-zone body (`<div className="flex min-h-0 flex-1 flex-col lg:flex-row">…`) stays as-is.

5. In the empty-state, wrap the `<Chakra size={44} />` container with the `aura-saffron` class for consistency with chat: `<motion.div variants={item} className="aura-saffron">`.

The full resulting file is the current SOP page minus the header/MotionConfig and minus the duplicated primitives — every handler, the `Scorecard`, the editor, the rails, and the history list are byte-for-byte the same otherwise.

- [ ] **Step 2: Delete the old route**

```bash
git rm sarthi-web/src/app/sop/page.tsx
```

- [ ] **Step 3: Type-check and build**

Run: `cd sarthi-web && npx tsc --noEmit && npm run build`
Expected: success; `/sop` resolves under the route group.

- [ ] **Step 4: Manual check**

Dev server + backend running. Visit `/sop`:
- Shell shows; SOP nav item active.
- Create a SOP, type, Save version → scorecard renders; History lists the version; Restore loads it back.
- Switch to Chat via the shell and back; SOP state reloads from the server (cookie identity intact).

- [ ] **Step 5: Commit**

```bash
git add "sarthi-web/src/app/(app)/sop/page.tsx" sarthi-web/src/app/sop/page.tsx
git commit -m "feat(web): move SOP workspace into (app)/sop on the shared shell"
```

---

## Task 7: Landing page

**Files:**
- Create: `sarthi-web/src/components/landing/MarketingNav.tsx`
- Create: `sarthi-web/src/components/landing/Hero.tsx`
- Create: `sarthi-web/src/components/landing/AgentVsChatbot.tsx`
- Create: `sarthi-web/src/components/landing/FeatureGrid.tsx`
- Create: `sarthi-web/src/components/landing/HowItWorks.tsx`
- Create: `sarthi-web/src/components/landing/Footer.tsx`
- Modify: `sarthi-web/src/app/page.tsx` (replace the redirect stub with the composed landing)

**Interfaces:**
- Consumes: `Chakra` (Task 2); icons (Task 2); `FEATURES`, `PHASES`, `AGENT_VS_CHATBOT` (Task 3); `reveal`, `container`, `item` (Task 1).
- Produces: the marketing landing at `/`. Primary CTA → `/chat`.

These are the design centerpiece — the code below is a complete, working, on-brand baseline. The implementer may refine spacing/visuals with the `ui-ux-pro-max` + `frontend-design` skills, but must keep: the exact copy from `content.ts` and the tagline/one-liner/disclaimer strings, the CTA target `/chat`, `reveal` + reduced-motion behavior, ≥ 44px targets, focus rings, and no fabricated logos/stats.

- [ ] **Step 1: `MarketingNav.tsx`**

```tsx
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
```

- [ ] **Step 2: `Hero.tsx`**

```tsx
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
```

- [ ] **Step 3: `AgentVsChatbot.tsx`**

```tsx
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
```

- [ ] **Step 4: `FeatureGrid.tsx`**

```tsx
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
```

- [ ] **Step 5: `HowItWorks.tsx`**

```tsx
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
```

- [ ] **Step 6: `Footer.tsx`**

```tsx
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
```

- [ ] **Step 7: Replace `src/app/page.tsx` with the composed landing**

```tsx
import { AgentVsChatbot } from "../components/landing/AgentVsChatbot";
import { FeatureGrid } from "../components/landing/FeatureGrid";
import { Footer } from "../components/landing/Footer";
import { Hero } from "../components/landing/Hero";
import { HowItWorks } from "../components/landing/HowItWorks";
import { MarketingNav } from "../components/landing/MarketingNav";

export default function Home() {
  return (
    <>
      <MarketingNav />
      <main>
        <Hero />
        <AgentVsChatbot />
        <FeatureGrid />
        <HowItWorks />
      </main>
      <Footer />
    </>
  );
}
```

- [ ] **Step 8: Type-check and build**

Run: `cd sarthi-web && npx tsc --noEmit && npm run build`
Expected: success; `/` is now the landing (no longer a redirect).

- [ ] **Step 9: Manual check**

Dev server. Visit `/`:
- Hero renders with dawn gradient + aura; "Start free" → `/chat`; "See how it works" scrolls to the How section.
- Sections reveal on scroll; with OS reduced-motion on, content is visible without animation.
- Feature cards show Live on F1–F4, Soon on F5–F7.
- Footer GitHub link opens the repo; Chat/SOP links work.
- Mobile width: nav collapses (Features/How hidden, Start free stays), no horizontal scroll.

- [ ] **Step 10: Commit**

```bash
git add sarthi-web/src/components/landing sarthi-web/src/app/page.tsx
git commit -m "feat(web): marketing landing page (hero, agent-vs-chatbot, features, journey, footer)"
```

---

## Task 8: Verify + docs

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** none (verification + documentation only).

- [ ] **Step 1: Full type-check + production build**

Run: `cd sarthi-web && npx tsc --noEmit && npm run build`
Expected: clean type-check; successful build listing routes `/`, `/chat`, `/sop`.

- [ ] **Step 2: Backend regression (confirm nothing backend changed)**

Run: `cd backend && ./.venv/Scripts/python -m pytest -q`
Expected: all existing tests pass (48+).

- [ ] **Step 3: Manual acceptance checklist**

With backend (`uvicorn` on :8000) and `npm run dev` (:3000):
- `/` landing renders; CTAs and anchors work.
- `/chat`: shell active state correct; session ping fires; streaming renders; backend-down shows the error; starters send; reduced-motion disables roll/caret.
- `/sop`: create / open / save / restore / history all work; cookie identity persists across a Chat↔SOP switch.
- Mobile (≤ 640px): bottom nav usable, 44px targets, no horizontal scroll.
- Keyboard: Tab reaches nav, composer, buttons; focus rings visible. Contrast holds (cream/muted on ink).

- [ ] **Step 4: Update `CLAUDE.md`**

In §0, under the "Built & verified" list, add a bullet:

```markdown
- **Frontend overhaul:** professional "modern AI product" redesign — marketing landing at `/` (hero, agent-vs-chatbot, Hero-7 feature grid, 4-phase journey, footer), shared `AppShell` (sidebar + mobile nav) via a `(app)` route group, chat moved to `/chat`, SOP to `/sop`. Shared `components/` (Chakra, icons, AppShell) + `lib/` (motion, nav, content) kill the prior copy-paste. Honest copy (no fabricated logos/stats).
```

In §14, update the visual-identity line to note the landing + shell are built. Add a line: `- [x] Whole-frontend UI/UX overhaul — landing page + shared app shell + re-skinned chat/SOP (frontend-overhaul branch).`

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: record frontend overhaul (landing + shared shell) in CLAUDE.md"
```

---

## Self-Review (completed)

**Spec coverage:** Architecture/files → Tasks 1–7 file map. Design system → Task 1. App shell → Task 4. Landing (all 6 sections + honest content) → Tasks 3 (data) + 7. Chat re-skin → Task 5. SOP re-skin → Task 6. Verification → Task 8. Out-of-scope items are not built. ✔

**Placeholder scan:** No "TBD/TODO/handle edge cases". Every code step has full code. The one judgment call (icon `svg` helper) has an explicit "delete if unused" instruction. ✔

**Type consistency:** `Chakra({rolling,size})`, icon `({className})` signatures, `NavItem`/`Feature`/`FeatureIcon`/`Phase` types, and `container`/`item`/`reveal` variant names are used identically across Tasks 2–7. `FeatureIcon` union ↔ `ICONS` map keys match. CTA target `/chat` consistent. ✔

## Out of Scope (YAGNI)

Multi-thread chat history UI, light/theme switching, real auth/login, i18n framework, CMS content, PWA/offline, any backend or agent change, and building features F5–F7 (landing roadmap only).
