# SARTHI (सारथी)

> **Your AI Sarthi — from dream to degree.**

SARTHI is an agentic AI platform that guides Tier-2/3 Indian students end-to-end on their study-abroad journey — from *"where should I even go?"* to *"my loan is disbursed"* — in a single, memory-powered, vernacular conversation.

**Not a chatbot. An agent.** Chatbots answer; SARTHI remembers, reasons, and takes action.

---

## Why this exists

Counsellors charge ₹50k–₹2L and push universities that pay them. Education-loan NBFCs only show up at the very end. Generic AI chatbots have no memory, no India context, and no idea how an Indian student actually finances a degree abroad. SARTHI is built for **Priya from Nagpur** — first-in-family, thinks in Marathi-Hindi about big decisions, needs a guide for the full 12-month arc, not a transaction at the end.

## Status

🚧 **Active build — personal/portfolio project.** No external deadline. Six capabilities live end-to-end.

- ✅ **F1 — Conversational Agent Core**: LangGraph agent with SARTHI persona, streaming over SSE, per-thread conversation history (SQLite checkpointer), and **cross-session long-term memory** (distilled facts in Chroma, recalled in new sessions).
- ✅ **F2 — University Shortlister**: agent tool-calling over a curated dataset; returns a Reach/Target/Safe shortlist with approximate cost, rendered as a table in chat.
- ✅ **F3 — ROI Predictor**: deterministic per-university cost vs salary vs EMI and payback math, plus a rate×tenure EMI sensitivity grid, exposed as two agent tools over a salary-priors dataset.
- ✅ **F4 — SOP Co-Pilot**: a dedicated workspace with deterministic SOP analysis (length, cliché/red-flag detection, structure signals), an append-only per-user multi-SOP version store, and a Socratic coaching agent that gives feedback without ghost-writing.
- ✅ **F5 — Loan Eligibility + Personalized Offer**: an indicative education-loan engine over real, sourced lender policy data (caps, LTV, FOIR, rate bands) — eligible amount, indicative rate band, EMI, a qualitative strength rating with an explainable reason chain, and RBI-aligned disclaimers. Surfaced as a chat offer card and a live `/loan` page with sliders. Transparent rules engine (no fabricated ML), ML-ready seam.
- ✅ **F6 — Document Auto-Fill**: SARTHI pre-fills a loan application from the student's own long-term memory facts (schema-driven extraction via the free utility model), persists one editable draft per user, and exposes a schema-driven `/apply` page with field-level provenance ("from your chats" / "needs input"), a document checklist, and an explicit demo submission. Reads only the student's stated facts — never invents data.
- ✅ **Model routing**: automatic per-turn tier selection — a light model for chit-chat, a mid/default model for tool use, and a reasoning model for deep turns (SOP critique, complex comparisons), with direction-aware escalation. The chosen tier is streamed to the UI as a per-reply badge.
- ✅ **Web app** (`sarthi-web/`): Next.js + Tailwind. Marketing landing page, a shared app shell (sidebar + mobile nav), a streaming chat workspace, and the SOP, Loan, and Apply workspaces. Anonymous signed-cookie identity, markdown rendering, framer-motion, vernacular-first design (spinning chakra, Hinglish starters).

## Stack

| Layer | Choice |
|-------|--------|
| Language / runtime | Python 3.14 (backend) · TypeScript / Node (web) |
| Agent framework | LangGraph (`recall → agent ⇄ tools → remember` graph) |
| LLM access | LLM-agnostic via **NVIDIA Build** (OpenAI-compatible) — one `base_url` / `api_key`, swappable per route |
| Model routing | Automatic per-turn tier: light `meta/llama-3.1-8b-instruct` (chit-chat) · default `meta/llama-3.3-70b-instruct` (tools) · reasoning `nvidia/llama-3.3-nemotron-super-49b-v1.5` (deep turns) |
| Utility model | `meta/llama-3.1-8b-instruct` (fact distillation, document extraction) |
| Embeddings | `nvidia/nv-embedqa-e5-v5` (1024-dim) |
| Conversation memory | SQLite checkpointer (`langgraph-checkpoint-sqlite` / `aiosqlite`) — per-thread history |
| Long-term memory | Chroma vector store — distilled per-user facts recalled across sessions |
| Backend API | FastAPI · Uvicorn · `sse-starlette` (Server-Sent Events streaming) |
| Domain data | Sourced JSON — universities, salary priors, lender loan policy, application schema |
| Persistence | User-scoped SQLite stores (SOP versions, loan application draft) |
| Frontend | Next.js 16 · React 19 · Tailwind CSS v4 · framer-motion · react-markdown + remark-gfm |
| Auth | Anonymous signed-cookie identity (server-issued `user_id`, never trusted from the request body) |
| Tests | `pytest` — deterministic finance / loan / ROI / SOP / application / router / API suites |

## Setup (backend)

Requires Python 3.14 (3.11+ should work).

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows: .venv\Scripts\activate
cp .env.example .env               # then paste your NVIDIA_API_KEY
pip install -r requirements.txt

python smoke_test.py               # 1-shot: streams a SARTHI reply
uvicorn app.server:app --port 8000 # run the agent API
```

Then talk to the agent. Identity comes from a server-signed cookie, so use a cookie jar (a first request mints an anonymous `user_id`):

```bash
curl -N -c jar.txt -b jar.txt -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hi, I want an MS in Robotics abroad."}'
```

For the full experience, run the web app (`cd sarthi-web && npm run dev`) — it proxies the API same-origin so the identity cookie stays first-party.

`GET /memory` shows the long-term facts SARTHI has learned about the current user (debug-only; enable with `SARTHI_DEBUG=true`).

> ⚠️ **Security:** identity is an **anonymous signed httpOnly cookie** — `user_id` is derived server-side and never trusted from the request body, so it cannot be spoofed. There is still no *account* login, so run **local-only** for now; real user accounts and production CORS lockdown are required before any deployment.

## Roadmap

Shipped, one feature per release:

`F1` Conversational Agent Core (memory) → `F2` University Shortlister → `F3` ROI Predictor → `F4` SOP Co-Pilot → `F5` Loan Eligibility + Offer → `F6` Document Auto-Fill.

Plus automatic model routing across light / default / reasoning tiers. Further work (voice, richer datasets, real user accounts) is exploratory and unscheduled.

## License

MIT — see [LICENSE](LICENSE).

---

*Built by Team Rath (रथ — the chariot).*
