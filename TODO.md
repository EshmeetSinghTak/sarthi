# SARTHI — Build To-Do List

> **Status:** Personal project mode (post-hackathon). No external deadline. Build sustainably.
> **Approach:** Decide before building. Don't ship code until Phase 0 questions are answered.

---

## Phase 0 · Decisions to Discuss (BEFORE writing any code)

These are the choices that lock everything downstream. Each needs a real conversation, not a guess.

- [x] **D1. Agent SDK / framework** — ✅ **LOCKED 2026-04-29: LangGraph**
   - Reason: student-budget personal project; need to swap LLMs freely (Claude · Gemini · GPT · open-source). Cost flexibility > DX speed.
   - Trade-off accepted: more glue code for memory/tools than Claude Agent SDK; OK for learning.
   - Adjacent: LangSmith for graph-level observability is a free bonus.
- [x] **D2. Foundation LLM** — ✅ **LOCKED 2026-04-29: Multi-provider via NVIDIA Build (primary)**
   - Default reasoning: **Nemotron-70B-Instruct** (NVIDIA NIM, free)
   - Light turns: Llama-3.1-8B-Instruct (NVIDIA NIM, free)
   - Heavy reasoning / SOP: DeepSeek-R1 (NVIDIA NIM, free)
   - Hindi fallback: Gemini 2.0 Flash (Google AI Studio, free)
   - Voice / speed: Llama-3.3-70B (Groq, free)
   - Embeddings: NV-Embed-v2 (NVIDIA NIM, free) — also feeds into D3
   - Reason: NVIDIA Build offers frontier-class models (Nemotron, DeepSeek) on a generous free tier with OpenAI-compatible APIs. Cost target ₹0/month for MVP.
   - Sub-tasks before code: sign up for NVIDIA Build · Google AI Studio · Groq accounts; get API keys.
- [x] **D3. Memory architecture** — ✅ **LOCKED 2026-04-29**
   - Relational: **Postgres** (local Docker dev · Supabase free tier prod)
   - Vector: **Chroma** (local mode, persists to `./chroma_db/`)
   - Embeddings: **NV-Embed-v2** via NVIDIA NIM (already chosen in D2)
   - Memory pattern: **distilled facts** (not raw transcripts) — clean retrieval
   - Migration path: Chroma → pgvector when we outgrow single-instance, no rewrite
   - Schemas: `users`, `conversations`, `messages`, `loan_applications` in Postgres; `user_memories` collection in Chroma
- [x] **D4. Hosting / deploy target** — ✅ **LOCKED 2026-04-29**
   - Frontend: **Vercel** (Next.js native, free tier)
   - Python agent backend: **Railway** or **Render** (free tier, always-on for long agent loops)
   - Reason: Vercel serverless timeouts don't fit multi-tool agent loops; split keeps both free.

- [x] **D5. Frontend stack** — ✅ **LOCKED 2026-04-29**
   - Frontend: **Next.js 14+ App Router · TypeScript · Tailwind · shadcn/ui · Vercel AI SDK** (streaming)
   - Backend: **Python + FastAPI** hosting LangGraph agent server
   - Boundary: HTTP / Server-Sent Events between TS frontend and Python backend.

- [x] **D6. Voice / vernacular plan** — ✅ **LOCKED 2026-04-29**
   - **MVP: text-only English + Hinglish (mixed Roman + Devanagari).**
   - Voice deferred to Phase 3+ (after F1–F5 are working).
   - Future stack: **Bhashini** (Hindi TTS, free, Govt of India) + **Whisper on Groq** (STT, free).

- [x] **D7. Data sourcing** — ✅ **LOCKED 2026-04-29**
   - **Hand-curated JSON** of ~50 US + ~20 Canadian universities (version-controlled in repo).
   - Salary priors: fork **levels.fyi public scrape** + **H1B LCA disclosure data** from existing GitHub projects.
   - Currency: hardcode INR/USD ≈ 84 for MVP; switch to Exchangerate-API if needed.

- [x] **D8. Scope ordering** — ✅ **LOCKED 2026-04-29**
   - MVP-0: **F1 alone** — agent + memory (the foundation)
   - MVP-1: + F2 University Shortlister
   - MVP-2: + F3 ROI Predictor
   - MVP-3: + F4 SOP Co-Pilot
   - MVP-4: + F5 Loan Eligibility + Offer
   - MVP-5: + F6 Document Auto-Fill
   - Future: F7 Passport · voice · viral mechanics
   - **Rule:** one tool per release. Ship and use F1 alone before adding F2.

- [x] **D9. Repo + identity** — ✅ **MOSTLY LOCKED 2026-04-29**
   - Repo name: **`sarthi`**
   - Visibility: **public from Day 1** (build-in-public for portfolio value)
   - License: **MIT**
   - README sections: tagline · live demo link · screenshots · stack · "why this exists" · setup · roadmap
   - ⏳ **Pending: GitHub username/handle** — will fill when user provides

- [x] **D10. Build cadence** — ✅ **PARTIALLY LOCKED 2026-04-29**
   - Working assumption: **Weekend Warrior** (6–10 hrs/weekend, weekday touches optional → MVP-3 in ~8 weeks)
   - ⏳ **Pending: user confirmation** — adjust if Steady Evening or Sprint Mode preferred

---

## Phase 1 · Foundation (Phase 0 ✅ complete · ready to start)

**Pre-flight homework (do these first, no coding required):**
- [ ] Sign up at `build.nvidia.com` → save `NVIDIA_API_KEY`
- [ ] Sign up at `aistudio.google.com` → save `GOOGLE_API_KEY`
- [ ] Sign up at `console.groq.com` → save `GROQ_API_KEY`
- [ ] Sign up at `supabase.com` (we'll use later for prod Postgres)
- [ ] Confirm GitHub username/handle
- [ ] Confirm build cadence (Weekend Warrior assumed)

**Repo setup:**
- [ ] Create public GitHub repo `sarthi` with MIT license
- [ ] `git init` locally · push initial commit (CLAUDE.md, TODO.md, PPT-SLIDES.md, build_deck.py, SARTHI.pptx)
- [ ] Add `.gitignore` (Python, Node, .env, .chroma_db, etc.)
- [ ] Write README v1: tagline · stack · "why this exists" · setup · roadmap

**Backend scaffold (Python + LangGraph):**
- [ ] Create `backend/` folder · `pyproject.toml` (Python 3.11+) or `requirements.txt`
- [ ] Install: `langgraph`, `langchain-openai`, `chromadb`, `fastapi`, `uvicorn`, `python-dotenv`, `psycopg[binary]`
- [ ] Set up `.env.example` · real `.env` git-ignored
- [ ] Write **smoke test**: a one-node LangGraph that calls Nemotron-70B with a "Hello, Priya" prompt
- [ ] Add second node: NV-Embed-v2 embedding test (embed "Priya wants MS Robotics" and print vector dim)
- [ ] Set up Postgres locally via Docker · run a basic migration (users, conversations, messages)
- [ ] Set up Chroma local-mode persistent collection `user_memories`

**Frontend scaffold (Next.js + TS):**
- [ ] `npx create-next-app sarthi-web --typescript --tailwind --app --src-dir --import-alias "@/*"`
- [ ] Install shadcn/ui CLI · init · add `button`, `card`, `input`, `chat` components
- [ ] Install Vercel AI SDK (`ai`, `@ai-sdk/openai`-equivalent for our backend)
- [ ] Build placeholder homepage with SARTHI branding (deep indigo + saffron from PPT)
- [ ] Build basic chat page (input + scrolling messages, no agent wired yet)

**Wire it up:**
- [ ] FastAPI endpoint `/chat` that streams agent responses (SSE)
- [ ] Frontend chat page calls `/chat` and renders streaming text
- [ ] First end-to-end test: type "Hi, I'm Priya" in browser → agent replies via Nemotron → response streams to UI

**Deploy:**
- [ ] Deploy frontend to Vercel (link to repo)
- [ ] Deploy backend to Railway · point to Supabase Postgres + Chroma volume
- [ ] Public URL works · share with one friend for first sanity test

**Phase 1 done = a stranger can visit a public URL, type a message, and SARTHI replies via Nemotron-70B with a SARTHI-flavored persona.**

## Phase 2 · F1 — Conversational Agent Core (the foundation of everything)

- [ ] Design agent system prompt (persona, tone, India-context, vernacular)
- [ ] Implement long-term memory store (chosen vector DB)
- [ ] Implement conversation history retrieval per user
- [ ] Build basic chat UI (streaming responses)
- [ ] Implement user identity (anonymous user ID via cookie or simple email auth)
- [ ] Test memory: agent recalls facts from prior session for the same user
- [ ] Deploy and try with 1 real user (you, then a friend)

## Phase 3 · Tools (one at a time, never parallel)

Build, test, ship, get feedback. THEN move to next tool.

- [ ] **F2. University Shortlister** — needs uni dataset + scoring logic
- [ ] **F3. ROI Predictor** — needs salary priors + EMI math
- [ ] **F4. SOP Co-Pilot** — Socratic prompts, not generation
- [ ] **F5. Loan Eligibility + Offer** — rule-based for MVP
- [ ] **F6. Document Auto-Fill** — extracts from prior conversations
- [ ] **F7. Study Abroad Passport** — image generation + share flow
- [ ] **F1.5. Vernacular voice layer** — only after text feels solid

## Phase 4 · Polish & Real-User Validation

- [ ] Recruit 3–5 real study-abroad aspirants (VNIT / Nagpur / college networks)
- [ ] Onboard them, give honest feedback prompts, watch them use it
- [ ] Iterate on what breaks for real users (always > what you imagined)
- [ ] Add basic analytics (Plausible / PostHog) to see actual user behavior
- [ ] Public dev log on Twitter / LinkedIn (build-in-public for portfolio value)

## Phase 5 · Optional / Stretch

- [ ] Mobile PWA polish
- [ ] Domestic students (CAT/GATE/IIM track) — second persona
- [ ] Multi-language beyond Hindi (Tamil / Marathi / Bengali)
- [ ] Pitch to a real NBFC partner once 50+ users have used it

---

## What we're explicitly NOT doing in MVP

- ❌ No "zero human intervention" growth loop yet — that's a Phase 4+ flex
- ❌ No viral mechanics until the core agent is good
- ❌ No mobile app — PWA is enough
- ❌ No premium tier / monetization plumbing — free for users until 100+ DAU
- ❌ No fancy ML for admission probability — heuristic scoring + LLM reasoning is enough for MVP

---

*Next step: walk through Phase 0 questions one at a time, starting with D1 (Agent SDK) and D2 (LLM choice).*
