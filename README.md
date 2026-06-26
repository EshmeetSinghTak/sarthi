# SARTHI (सारथी)

> **Your AI Sarthi — from dream to degree.**

SARTHI is an agentic AI platform that guides Tier-2/3 Indian students end-to-end on their study-abroad journey — from *"where should I even go?"* to *"my loan is disbursed"* — in a single, memory-powered, vernacular conversation.

**Not a chatbot. An agent.** Chatbots answer; SARTHI remembers, reasons, and takes action.

---

## Why this exists

Counsellors charge ₹50k–₹2L and push universities that pay them. Education-loan NBFCs only show up at the very end. Generic AI chatbots have no memory, no India context, and no idea how an Indian student actually finances a degree abroad. SARTHI is built for **Priya from Nagpur** — first-in-family, thinks in Marathi-Hindi about big decisions, needs a guide for the full 12-month arc, not a transaction at the end.

## Status

🚧 **Active build — personal/portfolio project.** No external deadline.

- ✅ **F1 — Conversational Agent Core** working end-to-end: LangGraph agent with SARTHI persona, streaming over SSE, per-thread conversation history (SQLite checkpointer), and **cross-session long-term memory** (distilled facts in Chroma, recalled in new sessions).
- ✅ **F2 — University Shortlister**: agent tool-calling over a curated dataset; returns a Reach/Target/Safe shortlist with approximate cost, rendered as a table in chat.
- ✅ **F3 — ROI Predictor**: deterministic per-university cost vs salary vs EMI and payback math, plus a rate×tenure EMI sensitivity grid, exposed as two agent tools over a salary-priors dataset.
- ✅ **F4 — SOP Co-Pilot**: a dedicated workspace with deterministic SOP analysis (length, cliché/red-flag detection, structure signals), an append-only per-user multi-SOP version store, and a Socratic coaching agent that gives feedback without ghost-writing.
- ✅ **Web app** (`sarthi-web/`): Next.js + Tailwind. Marketing landing page, a shared app shell (sidebar + mobile nav), a streaming chat workspace, and the SOP workspace. Anonymous signed-cookie identity, markdown rendering, framer-motion, vernacular-first design (spinning chakra, Hinglish starters).
- ⏭️ Next: F5 — Loan Eligibility + Personalized Offer.

## Stack

| Layer | Choice |
|-------|--------|
| Language / runtime | Python 3.14 (backend) · TypeScript / Node (web) |
| Agent framework | LangGraph (`recall → agent ⇄ tools → remember` graph) |
| LLM access | LLM-agnostic via **NVIDIA Build** (OpenAI-compatible, free tier) — one `base_url` / `api_key`, swappable per route |
| Default chat model | `deepseek-ai/deepseek-v4-flash` (reasoning) · verified fallback `meta/llama-3.3-70b-instruct` |
| Utility model | `meta/llama-3.1-8b-instruct` (fact distillation, light turns) |
| Embeddings | `nvidia/nv-embedqa-e5-v5` (1024-dim) |
| Conversation memory | SQLite checkpointer (`langgraph-checkpoint-sqlite` / `aiosqlite`) — per-thread history |
| Long-term memory | Chroma vector store — distilled per-user facts recalled across sessions |
| Backend API | FastAPI · Uvicorn · `sse-starlette` (Server-Sent Events streaming) |
| SOP store | Append-only SQLite, user-scoped versions |
| Frontend | Next.js 16 · React 19 · Tailwind CSS v4 · framer-motion · react-markdown + remark-gfm |
| Auth | Anonymous signed-cookie identity (server-issued `user_id`, never trusted from the request body) |
| Tests | `pytest` (deterministic ROI / SOP / config suites) |

**No Claude, no paid LLMs anywhere** — the project runs end-to-end on free NVIDIA Build models. Models are reached through a single OpenAI-compatible client, so any route can be re-pointed by changing one line.

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

Then talk to the agent:

```bash
curl -N -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"priya","message":"Hi, I want an MS in Robotics abroad."}'
```

`GET /memory/{user_id}` shows the long-term facts SARTHI has learned about a user (debug-only; enable with `SARTHI_DEBUG=true`).

> ⚠️ **Security:** the API currently has **no authentication** — `user_id` is client-supplied and unverified. Run **local-only**. Real auth (verified session → `user_id`) and CORS lockdown are tracked as the Phase 2 "user identity" item, required before any deployment.

## Roadmap

`F1` Conversational Agent Core (memory) → `F2` University Shortlister → `F3` ROI Predictor → `F4` SOP Co-Pilot → `F5` Loan Eligibility + Offer → `F6` Document Auto-Fill → `F7` Study Abroad Passport.

One feature per release. Ship and use F1 before adding F2.

## License

MIT — see [LICENSE](LICENSE).

---

*Built by Team Rath (रथ — the chariot).*
