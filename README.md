# SARTHI (सारथी)

> **Your AI Sarthi — from dream to degree.**

SARTHI is an agentic AI platform that guides Tier-2/3 Indian students end-to-end on their study-abroad journey — from *"where should I even go?"* to *"my loan is disbursed"* — in a single, memory-powered, vernacular conversation.

**Not a chatbot. An agent.** Chatbots answer; SARTHI remembers, reasons, and takes action.

---

## Why this exists

Counsellors charge ₹50k–₹2L and push universities that pay them. Education-loan NBFCs only show up at the very end. Generic AI chatbots have no memory, no India context, and no idea how an Indian student actually finances a degree abroad. SARTHI is built for **Priya from Nagpur** — first-in-family, thinks in Marathi-Hindi about big decisions, needs a guide for the full 12-month arc, not a transaction at the end.

## Status

🚧 **Early build — personal/portfolio project.** No external deadline.

- ✅ **F1 — Conversational Agent Core** working end-to-end: LangGraph agent with SARTHI persona, streaming over SSE, per-thread conversation history, and **cross-session long-term memory** (distilled facts in Chroma, recalled in new sessions).
- ⏭️ Next: frontend chat UI, then F2 University Shortlister.

## Stack

| Layer | Choice |
|-------|--------|
| Agent framework | LangGraph (Python) |
| LLMs | LLM-agnostic via NVIDIA Build (OpenAI-compatible) — free tier |
| Default model | `meta/llama-3.3-70b-instruct` (free) |
| Memory | Postgres (relational) + Chroma (vector), distilled facts |
| Backend | Python · FastAPI · LangGraph |
| Frontend | Next.js · TypeScript · Tailwind · shadcn/ui |
| Hosting | Vercel (web) · Railway/Render (agent) |

No Claude or paid LLMs — the project runs entirely on free providers.

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

`GET /memory/{user_id}` shows the long-term facts SARTHI has learned about a user.

## Roadmap

`F1` Conversational Agent Core (memory) → `F2` University Shortlister → `F3` ROI Predictor → `F4` SOP Co-Pilot → `F5` Loan Eligibility + Offer → `F6` Document Auto-Fill → `F7` Study Abroad Passport.

One feature per release. Ship and use F1 before adding F2.

## License

MIT — see [LICENSE](LICENSE).

---

*Built by Team Rath (रथ — the chariot).*
