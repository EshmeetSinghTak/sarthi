# SARTHI — Hackathon Project Memory

> **Purpose of this file:** Persistent project context for Claude Code sessions. Open this folder in any future session and Claude has the full backstory.

---

## 0. Current Build Status & Corrections (updated 2026-06-25)

> Reflects what is **actually built** and corrects the April plan below. Where this conflicts with later sections, **this wins** (per the §13b reversal protocol).

- **Repo:** public — https://github.com/EshmeetSinghTak/sarthi (GitHub handle **EshmeetSinghTak**). MIT. Monorepo: `backend/` (Python) + `sarthi-web/` (Next.js).
- **Hard constraint (user):** **NO Claude, NO paid LLMs** anywhere in the product. Free **NVIDIA Build** models only (OpenAI-compatible; one `base_url`/`api_key`).

**Built & verified end-to-end:**
- **F1 — agent core:** LangGraph graph `recall → agent ⇄ tools → remember`; per-thread history (`AsyncSqliteSaver`); cross-session long-term memory (Chroma distilled facts).
- **Web UI** (`sarthi-web/`): Next.js 16 + Tailwind v4 + framer-motion + react-markdown. Twilight-indigo/saffron, spinning chakra, Hinglish. **Anonymous signed-cookie identity** (Option A, `backend/app/auth.py`) — `user_id` never trusted from the body.
- **F2 — University Shortlister:** agent tool-calling over `backend/data/universities.json`; heuristic Reach/Target/Safe banding; rendered as a markdown table in chat.

**Model/stack reality (supersedes §7 & §13b where they differ):**
- Chat default: `deepseek-ai/deepseek-v4-flash` (reasoning model; `extra_body` `chat_template_kwargs.thinking`). Utility/distillation: `meta/llama-3.1-8b-instruct`. Verified fallback: `meta/llama-3.3-70b-instruct`.
- `z-ai/glm-5.1` — listed but **times out** on the free tier; do not use. **DeepSeek-R1 → DeepSeek-V4** (R1 gone). Nemotron-70b old id 404s (newer: `nvidia/llama-3.3-nemotron-super-49b-v1.5`).
- Embeddings: `nvidia/nv-embedqa-e5-v5` (1024-dim; needs `input_type` query/passage). **NV-Embed-v2 (D3c) is gone from the catalog — superseded.**
- Tool-calling confirmed on deepseek-v4-flash, llama-3.3-70b, nemotron-super-49b.
- **NVIDIA free tier 429-rate-limits** under heavy testing (deepseek hits it fastest). While testing, override per-run: `SARTHI_MODEL_DEFAULT=meta/llama-3.3-70b-instruct`.

**Environment & run:**
- **Python 3.14** + venv at `backend/.venv` (full stack incl. chromadb has 3.14 wheels — no 3.12 needed).
- Backend: `cd backend && ./.venv/Scripts/python -m uvicorn app.server:app --port 8000`. Secrets in `backend/.env` (git-ignored; `SARTHI_SECRET_KEY`, `NVIDIA_API_KEY`). Debug `/memory` gated behind `SARTHI_DEBUG`.
- Frontend: `cd sarthi-web && npm run dev` (:3000). `next.config` rewrites `/api/agent/*` → backend (same-origin keeps the identity cookie first-party).

**Gotchas (each cost real time — heed them):**
- Windows console is cp1252 → add `sys.stdout.reconfigure(encoding="utf-8")` to any script printing model output (Hindi/glyphs).
- `load_dotenv()` searches the **script's** dir, not cwd → `config.py` loads `.env` by explicit path.
- sse-starlette emits **CRLF** SSE frames → parse with `/\r?\n\r?\n/`, never `"\n\n"`.
- `TaskStop` doesn't kill the dev server's child node → port 3000 lingers; free it via PowerShell `Get-NetTCPConnection -LocalPort 3000 ... Stop-Process`. After installing a frontend dep, delete `.next` (stale RSC manifest).
- Commit `.gitignore` (incl. `.env`, `*.db`, `chroma_db/`) **before** the first `git add` so secrets never enter history.

**Next up:** F3 — ROI Predictor (builds on F2's cost data).

---

## 1. The Hackathon

- **Event:** CRP TenzorX 2026 National AI Hackathon
- **Host:** Poonawalla Fincorp (NBFC / lending)
- **Platform:** Unstop — https://unstop.com/competitions/crp-tenzorx-2026-national-ai-hackathon-poonawalla-fincorp-1651867
- **Format:** Round-based.
  - **Round 1 — PPT / Brief** · ✅ **SUBMITTED 2026-04-19**
  - **Round 1 results announced:** **2026-04-24** — ❌ **NOT SELECTED**
- **Status (post-2026-04-24):** Hackathon over. **SARTHI is now a personal/portfolio project.** No external deadline. Build at user's own pace. Goal shift: portfolio piece, learning, possible real launch — not winning a panel. **Build is underway — see §0 for current status.**
- **Team name:** **Rath** (रथ — *the chariot*) · chosen 2026-04-19 to complement SARTHI's charioteer metaphor
- **Team composition:** Solo human + Claude (effectively a 1-person team with AI collaborator)

## 2. Problem Chosen — Statement #2

**"Building a Unified Student Engagement Ecosystem for Education and Financing Choices."**

Core ask: Build an AI-first engagement platform that attracts, educates, nurtures Indian students planning higher education (abroad + domestic), funneling them toward education-loan awareness and application. Bonus challenge: *"Zero-human-intervention AI growth loop."*

### Why we chose it (and why it was the riskiest pick)
- **Risk:** Most-picked problem → 30+ competing teams doing chatbot + loan form.
- **Counter-strategy:** Win via a sharper *angle*, not broader scope. Be categorically different, not incrementally better.

### Problems we **rejected** (kept here for context — don't reopen)
- **PS1 — Placement Risk Modeling:** too data-heavy, visually bland.
- **PS3 — Agentic AI Video-Call Onboarding:** too many moving parts for a solo team; easy-to-break demo.
- **PS4A — Property Valuation:** needs real estate data we don't have.
- **PS4B — Healthcare Navigator:** weakest NBFC alignment.
- **PS4C — Kirana Cash-Flow Underwriting:** originally recommended as best-fit; user overrode.
- **PS4D — Gold Assessment:** physics-heavy, easy to stress-test negatively.

## 3. Product — SARTHI

- **Name:** SARTHI (सारथी) — *the charioteer who guided Arjuna through uncertainty*
- **Tagline:** **"Your AI Sarthi — from dream to degree."**
- **One-liner:** SARTHI is an agentic AI platform that guides Tier-2/3 Indian students end-to-end on their study-abroad journey — from "where should I even go?" to "my loan is disbursed" — in a single, memory-powered, vernacular conversation.
- **Secondary slogan (reserved for the viral Passport):** *"Every student deserves a Sarthi."*

### Three strategic frames to hammer across the deck
1. **"Not a chatbot. An agent."** — chatbots answer; agents act.
2. **"We turn the NBFC from a lender at the end of the journey into a companion at the start of it."**
3. **"We don't sell loans. We build a 12-month mentor relationship that ends in a loan."**

### Naming decision — why NOT "Poonawalla SARTHI"
- Product is **SARTHI** standalone, not co-branded.
- Poonawalla appears in **exactly 2 places** in the deck: the architecture slide (as "launch lending partner" API box) and the business-model slide (go-to-market).
- **Why:** Product-first framing signals "entrepreneur courting you" > sponsor-first framing which reads as pandering. Same effect, higher memorability.
- **Do NOT** re-brand SARTHI with Poonawalla prefix. User was clear on this.

### Competitive Landscape (3 categories × 3 players — use on Slide 4)

| Category | Real players Poonawalla competes with | Their gap | SARTHI's answer |
|----------|---------------------------------------|-----------|-----------------|
| **Counseling marketplaces** | Leverage Edu · Yocket · Shiksha | ₹50k–₹2L fees · inconsistent human counselors · English-only · biased toward paying universities | Free · AI-consistent · vernacular · unbiased agent |
| **Education-loan NBFCs (direct competitors to Poonawalla)** | **Credila · Avanse · Auxilo · Prodigy Finance** | Catch student at *loan stage* · commodity price war · zero pre-loan engagement | 12-month pre-loan relationship · alternative propensity data · natural conversion |
| **Generic AI chatbots** | ChatGPT · Gemini · generic LLMs | No memory · no action · no India context · no loan funnel | Memory · tool-calling · Bharat-first · loan-native |

**Positioning line:** *"Counselors charge too much. Loan NBFCs show up too late. Generic AI doesn't know India. SARTHI solves all three."*

## 4. Target Persona — "Priya Sharma from Nagpur"

- 21, Final-year Mech Eng, VNIT Nagpur, CGPA 7.8.
- Dad runs a small auto-parts business, family income ₹6L/yr.
- Dreams: MS in Robotics, US/Canada. Budget ₹40–60L, ~70% on loan.
- Speaks Marathi-Hindi at home, English in classroom.
- First-in-family to consider studying abroad.

### Her 7 real pains (persona slide)
1. "IELTS, TOEFL, GRE, GMAT — which, when, how?"
2. "500 US universities — which 10 actually fit me?"
3. "Will I even get admitted? Is ₹50L worth it?"
4. "My family can't guide me — no one's been abroad."
5. "I think in Marathi about big life decisions, not English."
6. "Dad's papers are messy — will any NBFC give me a loan?"
7. "Do I pay a counselor ₹1L who might push me to universities that pay them?"

### Why Priya = the NBFC's dream customer
- ₹45L loan × 8 years × ~10% = ~₹25L interest → high LTV.
- Engaged 12 months *before* loan need → deepest funnel capture possible.
- Lifetime cross-sell runway: personal loan post-job, home loan in 5 yrs, business loan later.

## 5. Hero-7 Features (PPT + Prototype scope)

| # | Feature | What it proves |
|---|---------|----------------|
| F1 | **Conversational Agent Core** (vernacular voice · auto-generates personalized application timeline: IELTS → GRE → Apps → Visa → Departure) | Mentor with memory — the agent itself |
| F2 | **University Shortlister** (profile → top-10 + admission prob + ROI) | AI/ML depth |
| F3 | **ROI Predictor** (cost vs salary vs EMI, interactive) | Financial intelligence |
| F4 | **SOP Co-Pilot** — AI-assisted, **student-authored**: Socratic prompts, structural feedback, authenticity checks. *Not wholesale generation* (avoids university AI-detection risk). | True agentic behavior |
| F5 | **Loan Eligibility + Personalized Offer** | NBFC conversion funnel |
| F6 | **Document Auto-Fill into loan app** (from past convos) | Zero-human-intervention bonus — the money shot |
| F7 | **Shareable "Study Abroad Passport"** | Viral growth loop |

**Vernacular (Hindi) voice** = layer across F1, not a standalone hero.

## 6. User Journey — "Priya's 4 Phases with SARTHI" (the PPT money slide)

Reframed from rigid calendar days to phases — real application cycles are 4–8 months, not 30 days. Phases hold up to any judge's follow-up question on timing.

| Phase | Priya's Moment | Feature |
|-------|----------------|---------|
| **Phase 1 · Discover** | Sees IG reel → voice chat in Hinglish: *"Robotics mein MS karna hai, kahan jaun?"* Agent generates her personalized application timeline (IELTS → GRE → Apps → Visa). | F1 |
| **Phase 2 · Decide** | Over a few sessions, agent builds profile → shows shortlist of 10 universities with admission probability + per-university ROI (cost vs salary vs EMI). | F2 + F3 |
| **Phase 3 · Apply** | Agent co-writes SOP via Socratic prompts (asking Priya, not replacing her). References her *actual* Bajaj internship because it remembers. | F4 |
| **Phase 4 · Fund** | *"Based on what I know, you qualify for ₹45L at 10.2%."* Agent auto-fills 90% of loan app from prior conversations → Priya uploads 3 docs → submitted. | F5 + F6 |
| **Amplify** | "Study Abroad Passport" generated → shared on IG → 3 friends sign up → loop closes. | F7 |

**The punchline:** *"4 phases. One agent. Zero human intervention. One ₹45L loan disbursed."*

## 7. AI Architecture

```
Frontend (Next.js + shadcn/ui + Tailwind, PWA)
    │
    ▼
Agent Orchestrator  (Claude Agent SDK / LangGraph)
    ├── Long-term memory per user (ChromaDB + Postgres)
    ├── Tool: University Shortlister (scikit-learn classifier + RAG over uni DB)
    ├── Tool: ROI Predictor (rules + LLM reasoning)
    ├── Tool: SOP Drafter (LLM + memory callback)
    ├── Tool: Loan Eligibility + Offer (rules + ML propensity)
    └── Tool: Passport Generator (Satori HTML→PNG)
    │
    ▼
Data & Integration Layer
    ├── University DB (QS/Times/scraped + synthetic for demo)
    ├── Salary priors (levels.fyi, H1B public data)
    ├── Voice: Whisper (STT) + Bhashini API (Hindi TTS)
    └── Poonawalla Loan API (mocked for demo, integration-ready)
```

### Stack cheat-sheet (locked 2026-04-29)

| Layer | Choice | Provider / Detail |
|-------|--------|--------------------|
| **Agent framework** | LangGraph (Python) | LLM-agnostic · graph-based agent loop |
| **LLM — default reasoning** | Nemotron-70B-Instruct | NVIDIA Build (free) |
| **LLM — light turns** | Llama-3.1-8B-Instruct | NVIDIA Build (free) |
| **LLM — heavy reasoning (SOP)** | DeepSeek-R1 | NVIDIA Build (free) |
| **LLM — Hindi fallback** | Gemini 2.0 Flash | Google AI Studio (free) |
| **LLM — speed / voice (later)** | Llama-3.3-70B | Groq (free) |
| **Embeddings** | NV-Embed-v2 (4096-dim) | NVIDIA Build (free) |
| **Relational store** | Postgres | Local Docker dev · Supabase free tier prod |
| **Vector store** | Chroma (local mode) | Persists to `./chroma_db/`; migrate to pgvector later |
| **Memory pattern** | Distilled facts (not raw transcripts) | Cleaner retrieval, smaller storage |
| **Frontend** | Next.js 14+ · TypeScript · Tailwind · shadcn/ui · Vercel AI SDK | Vercel (free) |
| **Backend** | Python · FastAPI · LangGraph | Railway / Render (free always-on) |
| **Frontend ↔ Backend** | HTTP + Server-Sent Events | Streaming agent responses |
| **ML (Phase 2+)** | scikit-learn + SHAP | Explainable predictions |
| **Voice (Phase 3+)** | Bhashini (Hindi TTS) + Whisper on Groq (STT) | Deferred from MVP |
| **Passport (Phase 3+)** | Satori (HTML→PNG) | Deferred from MVP |

**MVP cost target:** ₹0/month under free tier quotas across all providers.

**Why LLM-agnostic in the pitch:** NBFC judges want vendor flexibility (cost, compliance, negotiation). Naming a specific model can downscore us with any judge who prefers a different family. "LLM-agnostic orchestration" sounds more strategic than any single model name.

**Internal build choices (locked 2026-04-29):**

**Agent framework:** **LangGraph**. Reason: student-budget personal project + need to swap LLMs freely. Trade-off accepted: more glue code for memory/tools vs. Claude Agent SDK; OK for learning.

**LLM strategy:** Multi-provider via OpenAI-compatible APIs, NVIDIA Build (`build.nvidia.com`) as primary provider:

| Role | Model | Provider |
|------|-------|----------|
| Default agent reasoning | Nemotron-70B-Instruct | NVIDIA NIM (free) |
| Light turns | Llama-3.1-8B-Instruct | NVIDIA NIM (free) |
| Heavy reasoning (SOP feedback) | DeepSeek-R1 | NVIDIA NIM (free) |
| Hindi / fallback | Gemini 2.0 Flash | Google AI Studio (free) |
| Speed-critical voice | Llama-3.3-70B | Groq (free) |
| Embeddings (memory) | NV-Embed-v2 | NVIDIA NIM (free) |

**MVP cost target: ₹0/month** under free quotas. All providers expose OpenAI-compatible endpoints → LangGraph swaps models with a one-line `base_url`/`api_key` change.

### Architecture one-liner for the deck
> *"LLM-agnostic agent orchestration layer with long-term per-user memory, tool-calling, and multi-model fallback for cost/latency optimization."*

### Compliance & Trust layer (MUST appear on architecture slide)
- **Consent-first data capture** — explicit opt-in for every data class (chat, voice, documents, location).
- **DPDP Act 2023 compliant** — Indian data residency, user-right-to-delete, processing purpose disclosure.
- **RBI Digital Lending Guidelines aligned** — loan recommendations are advisory; underwriting decisions stay with the NBFC.
- **Explainability by default** — every ML-driven output (admission probability, loan eligibility) ships with a "why this result" reason chain.

**One-line to include on the architecture slide:** *"Consent-first · DPDP-compliant · RBI digital-lending-aligned · Explainable by default."*

### The "agent vs chatbot" proof slide
Side-by-side:
- **Chatbot:** stateless · answer-only · English only.
- **SARTHI agent:** memory per user · tool-calling · takes actions · vernacular.

## 8. Growth Strategy — Zero-Human-Intervention Loop

`ACQUIRE → ENGAGE → NURTURE → CONVERT → AMPLIFY → ACQUIRE` (closed loop)

- **Acquire:** AI-generated IG reels + SEO blogs (1/day/city×course).
- **Engage:** Free shortlister/ROI hook; profile built inside 5 min.
- **Nurture:** WhatsApp proactive nudges ("IELTS slots open in Pune tomorrow"); streaks; milestones.
- **Convert:** Personalized loan offer → auto-filled application.
- **Amplify:** Shareable "Study Abroad Passport" → friends scan QR → back into Acquire.

**Metric pitch:** *"Every Priya who gets a loan brings 3 friends into the top of the funnel — acquisition cost approaches zero."*

### Projected funnel numbers (PPT-grade, not fact-checked)
| Stage | Rate |
|-------|------|
| Reel → visit | 2% |
| Visit → first chat | 40% |
| First chat → profile complete (7d) | 25% |
| Profile → loan application | 15% |
| Application → disbursed | 35% |
| **CAC** | ₹800/user (vs Leverage Edu ₹5,000) |
| **LTV** | ₹2,50,000 over 30 yrs |

## 9. Business Impact (the NBFC-judge slide)

**Business impact lines to memorize:**
1. *"Top-of-funnel capture 12 months before loan need — loan becomes natural next step, not commodity price war."*
2. *"CAC of ₹800 vs ₹5,000 industry average → 5–6× more originations for same spend."*
3. *"Alternative propensity data (engagement, streaks, consistency) unavailable to any competitor."*
4. *"Every student = 30-year customer. Education loan → personal loan → home loan → business loan."*

**Killer one-liner:**
> *"SARTHI converts a ₹5,000 CAC into a ₹500 CAC and a one-time loan into a 30-year relationship."*

### Monetization — four revenue streams (not just loan interest)

| # | Stream | How it works | Revenue basis |
|---|--------|-------------|---------------|
| **1** | **Loan origination (primary)** | Revenue-share / exclusivity with Poonawalla on every disbursed loan | ~1–2% of loan value per origination |
| **2** | **University lead-gen fees** | Universities pay for qualified, intent-verified applicants | ₹500–₹2,000 per qualified lead |
| **3** | **Premium student tier** | Power-user subscription: unlimited SOP drafts, priority nudges, mock-interview coach, 1-on-1 AI sessions | ₹299–₹499 / month |
| **4** | **White-label agent (Phase 2)** | Other NBFCs / BFSI players license the agent after Poonawalla exclusivity period | ₹X per seat / annual contract |

**Why this matters for the pitch:** Most teams will pitch pure loan origination. A four-stream monetization model signals platform thinking, not a feature team thinking.

## 10. Prototype Build Plan (Apr 19 → May 3)

| Days | Milestone | Ships |
|------|-----------|-------|
| 1–2 | Scaffolding | Next.js + Tailwind/shadcn + Claude API + Postgres + Chroma |
| 3–4 | Agent core + memory | System prompt, tool defs, vector memory, basic chat UI |
| 5–6 | F2 Shortlister + F3 ROI | 50 US univs hardcoded, admission-prob regression, ROI chart |
| 7–8 | F4 SOP + F5 Loan Offer | SOP drafter with memory; rule-based eligibility + offer card |
| 9–10 | F6 Auto-fill + F7 Passport | Auto-fill animation; Satori passport |
| 11 | Vernacular voice | Whisper STT + Bhashini TTS + Hinglish prompt |
| 12–13 | Polish + demo script | Seed data, scripted Priya flow, fallback video |
| 14 | Buffer | Pitch rehearsal, bugs, Vercel deploy, GitHub README |

### Scope-cut order (if behind schedule)
1. Vernacular voice → English-only demo, voice in roadmap.
2. SOP Co-Pilot → mocked output instead of live Socratic flow.
3. **Never cut:** Agent chat + memory · Shortlister · Loan offer + Auto-fill · Passport.

## 11. PPT Structure (10 slides, Round 1 deliverable)

| # | Slide | Content |
|---|-------|---------|
| 1 | Cover | Logo + tagline + team + "Round 1 — PS2" |
| 2 | The Problem | Priya photo + 7 pains icon grid |
| 3 | Our Insight | "One-day transaction → 12-month relationship" reframe |
| 4 | Meet SARTHI | Name, tagline, one-liner, competitive 3×3 (counselors · loan NBFCs · generic AI) |
| 5 | The 4-Phase Journey (HERO) | Priya × SARTHI phased arc (Discover → Decide → Apply → Fund → Amplify) with all 7 features |
| 6 | AI Architecture | Layered diagram + stack + agent-vs-chatbot callout + compliance line (DPDP · RBI) |
| 7 | Zero-Human-Intervention Growth Loop | 5-stage funnel loop |
| 8 | Business Impact | 4 revenue streams · CAC/LTV math · Poonawalla go-to-market |
| 9 | Roadmap & Prototype | 14-day build plan |
| 10 | Closing | "Every student deserves a Sarthi." + contacts |

### Visual language
- Primary color: **deep indigo** with **saffron accent** (Indian but premium).
- Font: **Inter** or **Manrope**.
- Priya illustrated in one consistent style throughout.
- Each slide: ≤ 6 words in title, ≤ 3 bullets.

## 12. Strategic Guardrails (what NOT to do)

- **Don't rebrand as "Poonawalla SARTHI."** Product is standalone; partner mentioned twice only.
- **Don't make it a chatbot.** The agent/chatbot distinction is our whole differentiation — if pitch language drifts to "chatbot," we've lost.
- **Don't over-feature the prototype.** Ship the scripted Priya flow flawlessly; cut voice before cutting core loop.
- **Don't use English-only on the Bharat persona slide.** Vernacular must show somewhere visible even if voice gets cut.
- **Don't pitch loans as the hero.** Pitch the 12-month relationship; the loan is the outcome.
- **Don't oversell numbers.** CAC/LTV figures should pass a sniff test; don't quote precision we can't defend.
- **Don't name specific LLMs in the pitch.** "LLM-agnostic with multi-model routing" always beats "We use X." Internal build is specific; external pitch stays neutral.

## 13. Judging Criteria → How We Score on Each

| Criterion | How SARTHI scores |
|-----------|-------------------|
| Innovation & Creativity | Agent not chatbot · Passport viral loop · Vernacular voice |
| AI Integration & Execution | Memory · tools · ML · RAG · SHAP explainability |
| User Experience & Engagement | Priya's 4-phase scripted journey · streaks · nudges |
| Business Relevance & Conversion | Funnel math · CAC/LTV · 4 revenue streams · 2-slide Poonawalla integration · DPDP + RBI compliance |
| Prototype Quality | Working demo on Vercel · GitHub · 4 hero flows end-to-end |

## 13b. Tech Stack Decisions Log (2026-04-29 build planning session)

All 10 foundational decisions locked. Switching costs documented for future-you.

| # | Decision | Locked | Switching cost |
|---|----------|--------|----------------|
| D1 | Agent framework | LangGraph | 🟠 High (1–2 weeks) |
| D2 | LLM strategy | Multi-provider via NVIDIA Build | 🟢 Trivial (1 line per route) |
| D3a | Relational store | Postgres | 🟡 Medium |
| D3b | Vector store | Chroma local | 🟢 Low (pre-planned migration to pgvector) |
| D3c | Embedding model | NV-Embed-v2 | 🔴 Very High (re-embed everything) — picked carefully |
| D4 | Hosting | Vercel + Railway/Render | 🟢 Low |
| D5a | Frontend | Next.js + TS + shadcn | 🟠 High |
| D5b | Backend | Python + FastAPI | 🟡 Medium |
| D6 | Voice | Deferred to Phase 3+ | 🟢 Trivial |
| D7 | Data | Hand-curated 70-uni JSON | 🟢 Trivial |
| D8 | Scope order | F1 → F2 → F3 → F4 → F5 → F6 | 🟢 Trivial |
| D9 | Repo | Public `sarthi` · MIT | 🟡 Medium (license is sticky) |
| D10 | Cadence | Weekend Warrior (assumed) | 🟢 Trivial |

**Reversal protocol:** when reconsidering a decision, document the trigger (what evidence?), estimate switching cost from the table, compare to "tune the prompt instead," update CLAUDE.md with a "superseded by" line, then migrate.

## 14. Open Decisions / Things Still To Do

### ✅ Round 1 complete (2026-04-19)
- [x] Produce slide-by-slide PPT copy
- [x] Generate SARTHI.pptx
- [x] Fill placeholders and submit

### 🚀 Personal project mode (post-2026-04-24)
No external deadline. Build at own pace. Goal: portfolio piece + learning + possible real launch.

**Reframed scope decisions for personal project mode:**
- **No fallback demo video pressure** — we can iterate on real flows, not scripted ones.
- **Quality > velocity** — better to ship one feature really well than seven half-built.
- **Public from Day 1** — GitHub repo, public Vercel deploy, dev log on Twitter/LinkedIn for portfolio value.
- **Real users > pretend users** — recruit a few actual study-abroad aspirants from VNIT / college networks for feedback.

**Open MVP build items (see §0 for current status):**
- [x] Initialize Next.js + Tailwind project, push to GitHub (public) — built with Tailwind v4 directly (shadcn not used)
- [x] Basic chat loop with persistent memory — via **LangGraph** (not Claude Agent SDK — see no-paid-LLM constraint in §0)
- [x] Source universities seed dataset — `backend/data/universities.json` (~26 US + Canadian)
- [x] Build F1 Conversational Agent Core — done
- [x] F2 Shortlister — done · [ ] F3 ROI — next
- [ ] Source public salary priors (levels.fyi scrape, H1B LCA data) — needed for F3
- [ ] Decide: SOP Co-Pilot approach (F4) — free NVIDIA reasoning model (deepseek-v4), NOT Claude
- [x] Lock visual identity — twilight indigo + saffron, chakra signature, Fraunces/Inter/Noto Devanagari
- [ ] Confirm Bhashini API access (or ElevenLabs Hindi voice as fallback) — voice deferred
- [ ] Recruit 3–5 real study-abroad aspirants for usability feedback

## 15. References

- **Hackathon:** https://unstop.com/competitions/crp-tenzorx-2026-national-ai-hackathon-poonawalla-fincorp-1651867
- **Problem statement source:** `D:\downloads\69d73c0904439_TenzorX_Problem_Statements.zip` (extracted text confirmed)
- **Tagline source:** User-approved 2026-04-19 from 3 options (A/B/C), picked A.
- **Hero features source:** User approved Hero-7 = merge of user picks (1,2,3,8) + Claude picks (4,11,12) consolidated.

---

*Last updated: 2026-06-25 — added §0 (current build status & corrections): repo live, F1 + web UI + F2 shipped, model/embedding reality corrected, env/run + gotchas captured. Earlier sections retain the original pitch/strategy context; §0 supersedes stale build specifics.*

*(2026-04-19 — design reviewed and hardened with 5 MUST fixes: timeline generator · NBFC competitors · DPDP/RBI compliance · monetization streams · SOP Co-Pilot reframing; SHOULD #10 journey-as-phases.)*
