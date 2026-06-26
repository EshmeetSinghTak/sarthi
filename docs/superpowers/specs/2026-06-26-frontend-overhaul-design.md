# Frontend Overhaul — "Modern AI product site": Design

**Date:** 2026-06-26
**Status:** Approved (revisable during implementation)
**Builds on:** the existing Next.js 16 app (`sarthi-web/`), Tailwind v4 tokens in `globals.css`, framer-motion, and the chat (`/`) + SOP (`/sop`) pages.

## Goal

Make SARTHI's frontend look like a real, professional AI product — not a sparse chat box. Add a marketing **landing page** that sells the product, then route into a **polished app** (chat + SOP) that shares one cohesive shell, type system, component set, and motion language. Keep the twilight-indigo/saffron/chakra brand; raise the execution to "modern AI product site" quality (ChatGPT / Perplexity / Linear / Vercel bar).

## Constraints (Global)

- **No backend changes.** This is purely `sarthi-web/`. The agent, SSE contract, `/api/agent/*` rewrites, and the anonymous signed-cookie identity are untouched. Backend tests must stay green by virtue of not being touched.
- **NEVER hardcode tunables** (standing user rule). Shared design values (type scale, spacing, radii, colors, motion durations) live as tokens in `globals.css` / a motion module — not as scattered magic literals in components. Repeated content (nav items, feature list, journey phases) lives in small typed data arrays, not duplicated JSX.
- **DRY the duplication that exists today.** `Chakra`, the icon set, and the motion variants (`container`/`item`) are currently copy-pasted across `page.tsx` and `sop/page.tsx`. Extract them to shared modules; both pages import them.
- **Honest content only.** No fabricated testimonials, partner logos, user counts, or precision metrics. Landing copy uses the genuine product framing from `CLAUDE.md` (tagline, one-liner, Hero-7, the 4-phase journey, agent-vs-chatbot). The advisory disclaimer ("SARTHI guides; it doesn't decide") stays visible.
- **"This is NOT the Next.js you know"** (`sarthi-web/AGENTS.md`): before writing routing/layout code, read the relevant guide under `sarthi-web/node_modules/next/dist/docs/` (route groups, layouts, `Link`, metadata). Do not assume training-data conventions.
- **Accessibility is non-negotiable** (matches the bar already met by `/sop`): contrast ≥ 4.5:1, visible focus rings, ≥ 44px touch targets, keyboard operability, `aria-current` on active nav, `prefers-reduced-motion` respected on every animation, semantic headings, SVG icons (no emoji).
- **Dark theme only.** No light mode in this pass.

## Decisions (from brainstorming)

1. **Direction:** "Modern AI product site" — dark polished landing page (bold hero, feature sections, gradients/depth) → clean app.
2. **Routing:** landing at `/`; chat moves to `/chat`; SOP stays at `/sop`. Landing's primary CTA → `/chat`.
3. **Landing scope:** full marketing page — Hero · Agent≠Chatbot · Feature grid (Hero-7) · How-it-works (4 phases) · Footer.
4. **Shell:** Approach A — a shared `AppShell` (left sidebar nav rail on desktop; top bar + bottom nav on mobile) wrapping `/chat` and `/sop` via a Next.js route group. Landing is **not** inside the shell; it has its own marketing nav.

## Architecture & File Structure

Next.js App Router with a **route group** for the authenticated-style app surface:

```
src/app/
  layout.tsx              # root: fonts, <body>, metadata (unchanged structurally)
  globals.css             # design system (expanded)
  page.tsx                # NEW landing page (replaces the old chat page here)
  (app)/
    layout.tsx            # NEW — wraps children in <AppShell>
    chat/page.tsx         # the old page.tsx chat logic, moved + re-skinned
    sop/page.tsx          # the existing SOP workspace, re-skinned
src/components/
  Chakra.tsx              # shared chariot-wheel mark (extracted)
  icons.tsx               # shared inline stroke icons (extracted + extended)
  AppShell.tsx            # sidebar/topbar/bottom-nav shell + active state
  landing/
    MarketingNav.tsx      # landing-only top nav (logo + section links + "Start free")
    Hero.tsx
    AgentVsChatbot.tsx
    FeatureGrid.tsx
    HowItWorks.tsx
    Footer.tsx
src/lib/
  motion.ts               # shared variants: container, item, reveal (+ durations)
  nav.ts                  # typed nav-item list (app rail) — single source
  content.ts              # typed landing content: features (Hero-7), phases (4), agent-vs-chatbot rows
  sop.ts                  # unchanged API client
```

**Route move:** the current `src/app/page.tsx` (chat) becomes `src/app/(app)/chat/page.tsx`. Its internal `Chakra`, icons, and motion variants are replaced by imports from `components/` and `lib/motion`. `src/app/sop/page.tsx` → `src/app/(app)/sop/page.tsx`, same import swap. A route group `(app)` does not affect URLs, so `/sop` stays `/sop` and chat becomes `/chat`.

**Why this structure:** files that change together live together; the shell and its nav are one unit; landing sections are small, individually understandable components driven by data arrays; the app pages shrink to their actual logic once boilerplate is shared.

## Design System (`globals.css`)

Keep existing color tokens; **add** a documented, reusable layer so components stop inventing values:

- **Type scale** (CSS custom props, e.g. `--text-display`, `--text-h1`…`--text-h3`, `--text-body`, `--text-caption`) with Fraunces for display/headings, Inter for body/UI, Noto Serif Devanagari for Hindi. Body base 16px, line-height 1.5–1.65.
- **Spacing & radii:** standardize on the 4/8 rhythm already in use; define radius tokens (e.g. `--radius-card`, `--radius-pill`) so cards/pills are consistent.
- **Elevation for dark:** depth via layered surfaces (`ink` → `ink-2` → `ink-3`) + hairline rings + soft **saffron glow auras** (radial-gradient utilities), not heavy drop shadows. Add 1–2 gradient/aura utility classes (e.g. `.aura-saffron`, a dawn-gradient background) reused by hero and empty states.
- **Motion tokens:** standard durations/easings (e.g. `--dur-fast` 150ms, `--dur-base` 250ms) referenced by `lib/motion.ts` so timing is uniform.
- Existing `.md` markdown styles, chakra-roll/caret keyframes, scrollbar, and reduced-motion block are kept (and the reduced-motion block extended to cover any new always-on animation).

`lib/motion.ts` exports `container`, `item` (the current variants), and a new `reveal` (fade-up on scroll via `whileInView`, `viewport={{ once: true }}`) used by landing sections. All respect `MotionConfig reducedMotion="user"`.

## App Shell (`components/AppShell.tsx`)

A client component wrapping `(app)` children.

- **Desktop (≥ lg):** fixed left rail (~64–72px or a slim labeled column) — Chakra logo (links to `/`), then nav items from `lib/nav.ts` (Chat, SOP), each an icon + label, with `aria-current="page"` + saffron active treatment on the matching route (via `usePathname`). Bottom of rail: a quiet link to the landing/about.
- **Mobile:** a top bar (Chakra + section title) and a bottom nav bar (same items, ≥ 44px targets) — no horizontal scroll, safe-area aware.
- Content area renders `children`; pages control their own scroll. Active route detection uses the App Router `usePathname` hook.
- Focus rings, 44px targets, keyboard order. Single source of nav items so adding F5 later is one array entry.

## Landing Page (`/`)

Server-friendly composition of section components (sections may be client components only where motion needs it; content arrays live in `lib/content.ts`). Dark canvas, dawn gradient + chakra aura.

1. **MarketingNav:** Chakra + "SARTHI सारथी", anchor links (Features · How it works), and a `Start free →` button → `/chat`. Collapses gracefully on mobile.
2. **Hero:** display headline built on the tagline **"Your AI Sarthi — from dream to degree."**, the one-liner subhead, primary CTA `Start free →` (`/chat`) + secondary "See how it works" (anchor). Chakra mark, aura/gradient, entrance stagger.
3. **Agent ≠ Chatbot:** a compact comparison (chatbot: stateless · answer-only · English-only vs SARTHI: memory · tool-calling · acts · vernacular) — the core differentiator, from `CLAUDE.md` §7.
4. **FeatureGrid:** the **Hero-7** as cards (icon + name + one line), data-driven from `content.ts`: Conversational Agent Core, University Shortlister, ROI Predictor, SOP Co-Pilot, Loan Eligibility + Offer, Document Auto-Fill, Study Abroad Passport. Cards for already-built features (F1–F4) may carry a subtle "live" tag; the rest read as the roadmap — honest framing.
5. **HowItWorks:** the **4-phase Priya journey** (Discover → Decide → Apply → Fund, + Amplify) as a stepped sequence, scroll-revealed.
6. **Footer:** tagline, GitHub link (`https://github.com/EshmeetSinghTak/sarthi`), the advisory disclaimer, "MIT · built with free NVIDIA models", and quiet links to Chat/SOP.

All sections use `reveal` motion with reduced-motion fallback. No fabricated logos/stats/testimonials.

## Chat Page (`/chat`)

Same engine and SSE parsing as today (unchanged logic: session ping, streaming, CRLF frame split, error states). Re-skin only:
- Lives inside `AppShell`; its own per-page header is removed (the shell provides nav). A slim in-page title/affordance may remain if needed for the empty state.
- Imports `Chakra`, icons, motion from shared modules (no local copies).
- Polished message rows (student vs SARTHI), refined composer, a warmer welcome/empty state consistent with the new system. STARTERS retained.
- Disclaimer line retained.

## SOP Page (`/sop`)

Functionality unchanged (the F4 store/API/coaching are untouched). Re-skin only:
- Moves under `(app)`, rendered inside `AppShell`; its bespoke header is replaced by the shell.
- Swaps local `Chakra`/icons/motion for the shared modules.
- Scorecard, editor, history, restore keep their behavior; visuals align to the expanded token set.

## Testing & Verification

The repo has **no frontend test harness** (per the F4 spec); verification is build + type + manual, while backend tests remain green.

- **Type/build gates (must pass):** `npx tsc --noEmit` and `npm run build` in `sarthi-web/`.
- **Backend regression:** `pytest` in `backend/` stays green (no backend files change) — run once at the end to confirm nothing was touched inadvertently.
- **Manual checklist (documented in the final task):**
  - Routes resolve: `/` (landing), `/chat`, `/sop`; old `/` no longer shows chat.
  - Landing CTAs and anchors work; nav between Chat/SOP via the shell works; active state correct.
  - Chat: session ping fires, streaming renders, error state on backend down, starters send, reduced-motion disables the roll/caret.
  - SOP: create / open / save version / restore / history all still work (cookie identity intact through the route move).
  - Mobile: no horizontal scroll, bottom nav usable, 44px targets; keyboard tab order and focus rings visible; contrast holds.

## Build Sequence (units → tasks)

1. **Design-system foundation:** expand `globals.css` (type scale, spacing/radii, elevation/aura/gradient utilities, motion tokens, extend reduced-motion) + create `lib/motion.ts` (`container`, `item`, `reveal`).
2. **Shared primitives:** `components/Chakra.tsx` + `components/icons.tsx` (extract from current pages, extend icon set for nav/landing).
3. **Nav + content data:** `lib/nav.ts` (app rail items) + `lib/content.ts` (Hero-7 features, 4 phases, agent-vs-chatbot rows) — typed, single-source.
4. **AppShell:** `components/AppShell.tsx` + `(app)/layout.tsx` (sidebar/topbar/bottom-nav, active state, a11y).
5. **Move + re-skin chat:** relocate to `(app)/chat/page.tsx`, swap to shared modules, polish; verify streaming end-to-end.
6. **Move + re-skin SOP:** relocate to `(app)/sop/page.tsx`, swap to shared modules, align visuals; verify CRUD.
7. **Landing page:** `MarketingNav`, `Hero`, `AgentVsChatbot`, `FeatureGrid`, `HowItWorks`, `Footer` + new `app/page.tsx` composing them.
8. **Verify + docs:** `tsc` + `build` clean, backend `pytest` green, run the manual checklist, update `CLAUDE.md` (§0 + §14 frontend status).

## Out of Scope (YAGNI)

Multi-thread chat history UI, light/theme switching, real authentication/login, i18n framework, CMS-driven content, PWA/offline, any backend or agent change, and building the not-yet-implemented features (F5–F7) — they appear on the landing as honest roadmap only.
