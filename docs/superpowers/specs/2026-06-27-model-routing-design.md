# SARTHI — Automatic Model Routing (Design Spec)

**Date:** 2026-06-27
**Status:** Approved (design), pending implementation plan
**Author:** Rath (solo) + Claude

---

## 1. Problem & Goal

SARTHI currently runs every chat turn through a single fixed model
(`SARTHI_MODEL_DEFAULT`). That forces one compromise for all turns: a model fast
enough for "hi" is mediocre at deep SOP critique, and a model good at deep
reasoning is needlessly slow for a greeting.

**Goal:** let the agent pick the right model per turn, automatically, with **no
user interaction** — fast model for trivial turns, the standard model for normal
work, and a deep-reasoning model for genuinely hard tasks. The headline risk of
any router is *misrouting*; this design makes the agent **cheap to be wrong**
rather than betting on a perfect router.

This finishes a capability already sketched in `CLAUDE.md` §7 (multi-tier model
strategy) that was never wired up.

### Non-goals (YAGNI)
- No user-facing model picker or manual override.
- No new models beyond the three below.
- No change to memory, tools, auth, or the SOP/ROI/shortlist features.
- No LLM-based router (a model call to classify would add latency to the very
  turns we want fast). The router is pure heuristics.

---

## 2. The Three Tiers (measured 2026-06-27, free NVIDIA tier)

| Tier | Model | Latency | Tools? | Notes |
|------|-------|---------|--------|-------|
| **Light** | `meta/llama-3.1-8b-instruct` | ~0.8s | ✗ (unreliable) | Already the `utility_model`. Chit-chat only. |
| **Mid (default)** | `meta/llama-3.3-70b-instruct` | ~2s | ✓ | Fast + tool-capable. The safe default. |
| **Reasoning** | `nvidia/llama-3.3-nemotron-super-49b-v1.5` | ~27s | ✓ | Deep, high quality. Thinks in a separate `reasoning_content` channel. |

Notes that shape the design:
- `deepseek-ai/deepseek-v4-flash` is **excluded** — it times out (~183s) on the
  free tier (the bug fixed on 2026-06-27).
- Nemotron returns the answer in `.content` and its chain-of-thought in
  `reasoning_content`; with too small a token budget it spends everything
  thinking and returns empty `.content` (observed). The reasoning tier therefore
  needs a larger `max_tokens`.

---

## 3. Decisions (from brainstorming)

1. **Three tiers, both directions** (down to light, up to reasoning).
2. **Direction-aware escalation:**
   - **light → mid = REACTIVE**: let the 8B answer; if the reply is weak, retry
     on the 70B. The 8B is fast enough that an occasional double-call is cheap.
   - **mid → reasoning = PREDICTIVE**: decided *before* generating, from
     signals. Never generate a full 70B answer, judge it weak, *then* also wait
     ~27s for the reasoning model — that would double the slow latency.
3. **Reasoning tier fires on:** a deep tool (`review_sop`) having just run, **or**
   a clearly complex comparative turn (length/keyword signals).
4. **UI:** a subtle per-reply tier badge, plus a "thinking deeply…" loading
   state while the reasoning tier is working (so a ~27s wait reads as intentional,
   not a hang).
5. **Misroute strategy:** safe default (uncertain → MID, never light), tiers
   gated by high-confidence signals, one-shot escalation as the safety net.

---

## 4. Architecture

The graph topology is unchanged. Routing intelligence lives in a new pure module
and inside the existing `agent_node`.

```
recall → agent ⇄ tools → remember          (topology unchanged)
            │
            └─ on EACH entry:
                 tier = router.choose_tier(last_human, just_ran_deep_tool)
                 ├─ LIGHT: invoke llm_light; if router.is_weak_reply(reply) → retry on llm_mid   (REACTIVE)
                 ├─ MID:   invoke llm_mid
                 └─ REASONING: invoke llm_reasoning  (fallback to llm_mid on error)
```

Because the tier is recomputed on every `agent_node` entry, the post-tool
escalation works naturally: after `review_sop` runs and the graph loops back,
`just_ran_deep_tool` is true, so the *synthesis* turn jumps to reasoning.

---

## 5. Components

### 5.1 `backend/app/router.py` (new) — pure, no I/O, no LLM
- `class Tier(str, Enum)`: `LIGHT`, `MID`, `REASONING`.
- `choose_tier(user_text: str, just_ran_deep_tool: bool) -> Tier`:
  - `REASONING` if `just_ran_deep_tool`, **or** the message is complex:
    word count ≥ `ROUTER_COMPLEX_MIN_WORDS`, or contains any
    `ROUTER_COMPLEX_KEYWORDS` (e.g. "vs", "should i", "trade-off", "compare",
    "why", "explain", "pros and cons").
  - `LIGHT` only if high-confidence trivial: word count ≤
    `ROUTER_TRIVIAL_MAX_WORDS` **and** matches a `ROUTER_TRIVIAL_PATTERNS`
    entry (greeting/thanks/affirmation) **and** not a question (no "?").
  - `MID` otherwise (the safe default).
  - Order of checks: deep-tool/complex → reasoning first; then trivial → light;
    else mid. (Complexity wins over brevity, e.g. a short but loaded question.)
- `is_weak_reply(text: str) -> bool`: empty/whitespace, or
  `len(text.strip()) < ROUTER_WEAK_REPLY_MIN_CHARS`, or matches a
  `ROUTER_REFUSAL_PATTERNS` entry ("i can't", "i cannot", "as an ai", …).

All keyword/pattern lists and thresholds are imported from `config.py`. No
literals in `router.py`.

### 5.2 `backend/app/llm.py`
- Keep `distill_facts` as-is (utility model, off the chat path).
- Replace the single `chat_llm` with three builders / instances:
  - `llm_light` — `MODEL_LIGHT`, **no tools bound**, normal temperature.
  - `llm_mid` — `MODEL_MID`, tools bound (current behavior).
  - `llm_reasoning` — `MODEL_REASONING`, tools bound, `max_tokens =
    REASONING_MAX_TOKENS`, reasoning `extra_body`.
- `llm_for_tier(tier: Tier)` → returns the matching instance.
- Tools are bound here (import `TOOLS` list); `agent.py` consumes `llm_for_tier`.

### 5.3 `backend/app/config.py` — new centralized tunables
- Models: `MODEL_LIGHT` (default `meta/llama-3.1-8b-instruct`),
  `MODEL_MID` (default = existing `SARTHI_MODEL_DEFAULT`, i.e.
  `meta/llama-3.3-70b-instruct`), `MODEL_REASONING`
  (default `nvidia/llama-3.3-nemotron-super-49b-v1.5`). All env-overridable.
- Router thresholds: `ROUTER_TRIVIAL_MAX_WORDS`, `ROUTER_TRIVIAL_PATTERNS`,
  `ROUTER_COMPLEX_MIN_WORDS`, `ROUTER_COMPLEX_KEYWORDS`,
  `ROUTER_DEEP_TOOLS` (= `{"review_sop"}`), `ROUTER_WEAK_REPLY_MIN_CHARS`,
  `ROUTER_REFUSAL_PATTERNS`.
- Reasoning: `REASONING_MAX_TOKENS` (large enough that thinking doesn't starve
  the answer — start ~3072).
- Backward-compat: `chat_model` stays as an alias of `MODEL_MID` so nothing else
  breaks; `chat_extra_body` reused for the reasoning tier.

### 5.4 `backend/app/agent.py`
- `agent_node` becomes tier-aware:
  1. Determine `just_ran_deep_tool`: inspect the tail of `state["messages"]` for
     a `ToolMessage` whose tool name ∈ `ROUTER_DEEP_TOOLS` produced since the
     last `HumanMessage`.
  2. `tier = router.choose_tier(last_human, just_ran_deep_tool)`.
  3. **Emit the tier up-front** via LangGraph's custom stream writer
     (`get_stream_writer()`), so the frontend learns the tier *before* a slow
     reasoning call begins.
  4. Invoke `llm_for_tier(tier)`.
  5. If `tier == LIGHT` and `is_weak_reply(reply.content)` and the reply has no
     tool calls → re-invoke on `llm_mid`, emit updated tier (`MID`).
  6. If `tier == REASONING` and the call raises/times out → fall back to
     `llm_mid`, emit updated tier.
- `_route`, `recall_node`, `remember_node`, graph wiring: unchanged.

### 5.5 `backend/app/server.py`
- `event_stream()` consumes `stream_mode=["messages", "custom"]`.
- Custom writer payloads (`{"tier": "..."}`) are forwarded as a new SSE event:
  `{"event": "meta", "data": "<tier>"}`.
- Token forwarding (node == "agent", `AIMessageChunk`, `.content`) unchanged — so
  `reasoning_content` still never reaches the client.
- `error` / `done` events unchanged.

### 5.6 `sarthi-web/src/app/(app)/chat/page.tsx`
- Extend `Message` with `tier?: "fast" | "standard" | "deep"` (mapped from the
  `meta` event: light→fast, mid→standard, reasoning→deep).
- On `meta`, set the streaming message's tier.
- **Badge:** a small, quiet pill on each finished SARTHI reply showing the tier.
- **Deep-thinking state:** when the streaming reply's tier is `deep` and no
  tokens have arrived, render "SARTHI is thinking deeply…" instead of the plain
  three-dot `Thinking`.
- **Tier-aware stall timeout:** when tier becomes `deep`, raise the watchdog
  window to `STALL_TIMEOUT_DEEP_MS` (e.g. 90s) so a legitimate ~27s reasoning
  turn isn't aborted. Resets per token, as today.

---

## 6. Data Flow (one turn, worked example: SOP coaching)

1. `recall` loads the user's memory facts (unchanged).
2. `agent_node` entry: `choose_tier("review my SOP draft", just_ran_deep_tool=False)`
   → message names a tool need → `llm_mid` decides to call `review_sop`.
   Emits `meta: standard`.
3. `tools` runs `review_sop`, appends the analysis (unchanged tool loop).
4. `agent_node` re-entry: `just_ran_deep_tool=True` → `REASONING`.
   Emits `meta: deep` → frontend flips to "thinking deeply…".
5. `llm_reasoning` synthesizes Socratic coaching from the analysis; only
   `.content` streams to the user.
6. `remember` distills durable facts (unchanged).

Trivial turn ("thanks!"): step 2 → `LIGHT` → 8B answers in ~1s; if it returned
something weak, reactive retry on mid.

---

## 7. Error Handling

| Failure | Handling |
|---------|----------|
| Reasoning model errors / times out | Catch in `agent_node`; fall back to `llm_mid`; emit updated tier. A slow-tier failure never dead-ends a turn. |
| Light model weak/empty/refusal | Reactive retry on `llm_mid` (core path). |
| Light model unexpectedly emits a tool call | It has no tools bound, so this can't happen; if a weak/empty reply results, reactive retry to mid (which has tools) covers it. |
| Stream stalls | Tier-aware client watchdog: longer window for `deep`; resets per token. |
| `reasoning_content` leakage | Server forwards only `.content`; verified during build. |
| Custom stream writer unsupported in installed LangGraph | Fallback: emit `meta` at stream end (badge still works); drive the "thinking deeply" state from the predicted tier client-side. Decide during the first build task. |

---

## 8. Testing

- **`backend/tests/test_router.py` (new) — exhaustive, pure, no live models:**
  - trivial greeting → LIGHT; greeting-but-question → MID; "thanks" → LIGHT.
  - complex keyword ("US vs Canada, what should I do?") → REASONING.
  - long message ≥ threshold → REASONING.
  - `just_ran_deep_tool=True` → REASONING regardless of text.
  - ambiguous / ordinary turn → **MID** (the safe-default guarantee — the central
    misroute defense).
  - `is_weak_reply`: empty, too-short, refusal pattern → True; normal → False.
- **`backend/tests/test_llm.py` (extend):** `llm_for_tier` returns the right
  instance per tier; light has no tools bound, mid/reasoning do.
- **One live smoke check** (manual or marked): each tier responds; nemotron
  `.content` is non-empty with the configured token budget and reasoning text
  does not leak into the stream.
- Existing 48 backend tests must stay green (no behavior change to tools/memory).

---

## 9. Files Touched

**New:** `backend/app/router.py`, `backend/tests/test_router.py`.
**Modified:** `backend/app/config.py`, `backend/app/llm.py`, `backend/app/agent.py`,
`backend/app/server.py`, `sarthi-web/src/app/(app)/chat/page.tsx`,
`backend/tests/test_llm.py` (extend), `CLAUDE.md` (record the feature).

---

## 10. Open Risk to Verify First

LangGraph custom stream writer (`get_stream_writer()` + `stream_mode=["messages",
"custom"]`) in the installed version. First implementation task verifies it; if
absent, use the end-of-stream `meta` fallback (§7). Everything else is standard.
