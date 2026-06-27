# Automatic Model Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the SARTHI agent automatically pick a light / mid / reasoning model per turn, with no user interaction, and make misrouting cheap to recover from.

**Architecture:** A pure heuristic router (`router.py`) decides the tier on every `agent_node` entry. The graph topology is unchanged; `agent_node` picks the bound model, emits the tier up-front via LangGraph's custom stream writer, and does reactive light→mid retry / reasoning→mid fallback. The server forwards the tier as an SSE `meta` event; the chat UI shows a per-reply badge, a "thinking deeply" state, and a tier-aware stall timeout.

**Tech Stack:** Python 3.14, LangGraph, LangChain (`langchain_openai.ChatOpenAI`), FastAPI + sse-starlette, pytest (sync tests, `asyncio.run` for async); Next.js 16 + React 19 + Tailwind v4 + framer-motion.

## Global Constraints

- **No paid LLMs / no Claude.** Free NVIDIA Build models only (OpenAI-compatible).
- **Never hardcode tunables.** All thresholds, keyword lists, and model ids live in `backend/app/config.py`.
- **`user_id` comes from the signed cookie**, never the request body. This plan does not touch identity.
- **Excluded model:** `deepseek-ai/deepseek-v4-flash` (times out ~183s on free tier).
- **Tier models (defaults, env-overridable):** light `meta/llama-3.1-8b-instruct`; mid `meta/llama-3.3-70b-instruct`; reasoning `nvidia/llama-3.3-nemotron-super-49b-v1.5`.
- **Reasoning model** returns its answer in `.content` and chain-of-thought in `reasoning_content`; needs a large `max_tokens` (~3072) or `.content` comes back empty. Only `.content` is ever streamed to the client.
- **Misroute rule:** when uncertain, route to MID — never light. LIGHT fires only on high-confidence trivial turns; REASONING only on explicit signals.
- Tests use the existing pattern: plain `pytest`, no new dependencies; async functions tested via `asyncio.run(...)`.
- Backend run: `cd backend && ./.venv/Scripts/python -m pytest -q`. Frontend checks: `cd sarthi-web && npx tsc --noEmit` and `npm run build`.
- Windows: scripts printing model output need `sys.stdout.reconfigure(encoding="utf-8")`.

---

## File Structure

**New files:**
- `backend/app/router.py` — pure tier-selection heuristics (`Tier`, `choose_tier`, `is_weak_reply`).
- `backend/tests/test_router.py` — exhaustive unit tests for the router.
- `backend/tests/test_agent_routing.py` — tests for deep-tool detection + escalation paths.
- `backend/tests/test_server_stream.py` — SSE event-generation tests with a fake graph.

**Modified files:**
- `backend/app/config.py` — tier model ids + router tunables.
- `backend/app/llm.py` — three model instances (`llm_light`, `llm_mid`, `llm_reasoning`); keep `distill_facts`.
- `backend/app/agent.py` — tier-aware `agent_node`, `llm_for_tier`, `_just_ran_deep_tool`, tier emission, escalation.
- `backend/app/server.py` — extract `_stream_chat`; forward `meta` events; consume combined stream modes.
- `backend/tests/test_config.py` — assert new config values (extend).
- `sarthi-web/src/app/(app)/chat/page.tsx` — meta parsing, tier badge, deep-thinking state, tier-aware stall timeout.
- `CLAUDE.md` — record the feature.

---

## Task 1: Config tunables for routing

**Files:**
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `settings.model_light`, `settings.model_mid`, `settings.model_reasoning`, `settings.reasoning_max_tokens` (all `str`/`int`); module-level `config.ROUTER_TRIVIAL_MAX_WORDS: int`, `config.ROUTER_TRIVIAL_PATTERNS: tuple[str,...]`, `config.ROUTER_COMPLEX_MIN_WORDS: int`, `config.ROUTER_COMPLEX_KEYWORDS: tuple[str,...]`, `config.ROUTER_DEEP_TOOLS: frozenset[str]`, `config.ROUTER_WEAK_REPLY_MIN_CHARS: int`, `config.ROUTER_REFUSAL_PATTERNS: tuple[str,...]`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_config.py`:

```python
def test_tier_models_present():
    assert config.settings.model_light == "meta/llama-3.1-8b-instruct"
    assert config.settings.model_mid  # defaults to the standard chat model
    assert config.settings.model_reasoning == "nvidia/llama-3.3-nemotron-super-49b-v1.5"
    assert config.settings.reasoning_max_tokens >= 2048


def test_router_tunables_present():
    assert config.ROUTER_TRIVIAL_MAX_WORDS > 0
    assert isinstance(config.ROUTER_TRIVIAL_PATTERNS, tuple) and config.ROUTER_TRIVIAL_PATTERNS
    assert config.ROUTER_COMPLEX_MIN_WORDS > config.ROUTER_TRIVIAL_MAX_WORDS
    assert "vs" in config.ROUTER_COMPLEX_KEYWORDS
    assert "review_sop" in config.ROUTER_DEEP_TOOLS
    assert config.ROUTER_WEAK_REPLY_MIN_CHARS > 0
    assert any("can't" in p or "cannot" in p for p in config.ROUTER_REFUSAL_PATTERNS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_config.py -q`
Expected: FAIL — `AttributeError: ... 'model_light'` / `module 'app.config' has no attribute 'ROUTER_TRIVIAL_MAX_WORDS'`.

- [ ] **Step 3: Add the model fields to `Settings`**

In `backend/app/config.py`, inside `class Settings`, in the `# --- Models ---` block, after the `chat_model` line add:

```python
    # Tiered chat models for automatic routing (see router.py / agent.py).
    model_light: str = os.getenv("SARTHI_MODEL_LIGHT", "meta/llama-3.1-8b-instruct")
    model_mid: str = os.getenv(
        "SARTHI_MODEL_MID", os.getenv("SARTHI_MODEL_DEFAULT", "meta/llama-3.3-70b-instruct")
    )
    model_reasoning: str = os.getenv(
        "SARTHI_MODEL_REASONING", "nvidia/llama-3.3-nemotron-super-49b-v1.5"
    )
    # Reasoning models spend tokens "thinking"; give the answer room to land.
    reasoning_max_tokens: int = int(os.getenv("SARTHI_REASONING_MAX_TOKENS", "3072"))
```

Then change the existing `chat_model` line so `/health` reports the mid (default) tier — replace:

```python
    chat_model: str = os.getenv("SARTHI_MODEL_DEFAULT", "deepseek-ai/deepseek-v4-flash")
```

with (place it **after** the `model_mid` line so the name resolves):

```python
    chat_model: str = model_mid  # the user-facing default tier; shown by /health
```

- [ ] **Step 4: Add the router tunables (module level)**

In `backend/app/config.py`, after the existing `# --- F4 SOP Co-Pilot ...` constants block (end of file), append:

```python
# --- Model routing (automatic tier selection; tunables centralized) ---
# A turn is "trivial" (-> light 8B) only if it is short AND matches a pattern
# below AND is not a question. Keep this conservative: misrouting up to MID is
# safe, misrouting a real question down to the 8B is not.
ROUTER_TRIVIAL_MAX_WORDS: int = 4
ROUTER_TRIVIAL_PATTERNS: tuple[str, ...] = (
    "hi", "hello", "hey", "namaste", "thanks", "thank you", "thx", "ty",
    "ok", "okay", "cool", "great", "got it", "nice", "good morning",
    "good evening", "good night", "bye", "shukriya", "theek hai",
)
# A turn is "complex" (-> reasoning 49B) if it is long OR contains a clearly
# comparative/decision keyword. Kept narrow on purpose (reasoning is ~27s).
ROUTER_COMPLEX_MIN_WORDS: int = 40
ROUTER_COMPLEX_KEYWORDS: tuple[str, ...] = (
    "vs", "versus", "should i", "trade-off", "tradeoff", "trade off",
    "compare", "comparison", "pros and cons", "which is better",
    "better option", "worth it",
)
# Tools whose output warrants a deep-reasoning synthesis turn after they run.
ROUTER_DEEP_TOOLS: frozenset[str] = frozenset({"review_sop"})
# A light-tier reply this short, empty, or matching a refusal is "weak" and
# triggers a one-shot retry on the mid tier.
ROUTER_WEAK_REPLY_MIN_CHARS: int = 12
ROUTER_REFUSAL_PATTERNS: tuple[str, ...] = (
    "i can't", "i cannot", "i'm unable", "i am unable",
    "as an ai", "i'm sorry, but", "i am sorry, but",
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_config.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat(routing): add tier model ids and router tunables to config"
```

---

## Task 2: The pure router

**Files:**
- Create: `backend/app/router.py`
- Test: `backend/tests/test_router.py`

**Interfaces:**
- Consumes: `config.ROUTER_*` from Task 1.
- Produces: `Tier` (Enum: `LIGHT`, `MID`, `REASONING`, str-valued `"light"/"mid"/"reasoning"`); `choose_tier(user_text: str, just_ran_deep_tool: bool = False) -> Tier`; `is_weak_reply(text: str) -> bool`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_router.py`:

```python
from app.router import Tier, choose_tier, is_weak_reply


def test_trivial_greeting_is_light():
    assert choose_tier("hi") is Tier.LIGHT
    assert choose_tier("thanks!") is Tier.LIGHT
    assert choose_tier("ok cool") is Tier.LIGHT


def test_greeting_with_question_is_not_light():
    # A question is never trivial — fall back to the safe default.
    assert choose_tier("hello, which university?") is Tier.MID


def test_comparative_keywords_are_reasoning():
    assert choose_tier("US vs Canada for robotics?") is Tier.REASONING
    assert choose_tier("should I do an MS or an MBA") is Tier.REASONING
    assert choose_tier("compare CMU and MIT for me") is Tier.REASONING


def test_long_message_is_reasoning():
    long_msg = " ".join(["word"] * 45)
    assert choose_tier(long_msg) is Tier.REASONING


def test_deep_tool_forces_reasoning_regardless_of_text():
    assert choose_tier("hi", just_ran_deep_tool=True) is Tier.REASONING


def test_ordinary_turn_is_mid_safe_default():
    # The central misroute defense: uncertain -> MID, never light.
    assert choose_tier("what's the deadline for fall intake") is Tier.MID
    assert choose_tier("tell me about the GRE") is Tier.MID
    assert choose_tier("") is Tier.MID


def test_is_weak_reply():
    assert is_weak_reply("") is True
    assert is_weak_reply("   ") is True
    assert is_weak_reply("ok") is True  # below min chars
    assert is_weak_reply("I can't help with that.") is True  # refusal
    assert is_weak_reply("Here is a detailed, useful answer for you.") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_router.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.router'`.

- [ ] **Step 3: Write the router**

Create `backend/app/router.py`:

```python
"""Automatic model-tier routing — pure heuristics, no I/O, no LLM calls.

choose_tier() runs on every agent turn:
  LIGHT     — high-confidence trivial chit-chat (fast 8B)
  MID       — the safe default for normal work (70B, tool-capable)
  REASONING — deep tasks: after a deep tool, or clearly complex turns (slow 49B)

Misroute strategy: when uncertain, return MID. LIGHT fires only on
high-confidence trivial turns; REASONING only on explicit signals. All
thresholds and word lists live in config.py.
"""

from enum import Enum

from . import config


class Tier(str, Enum):
    LIGHT = "light"
    MID = "mid"
    REASONING = "reasoning"


def _word_count(text: str) -> int:
    return len(text.split())


def _is_trivial(text: str) -> bool:
    t = text.strip().lower()
    if not t or "?" in t:
        return False
    if _word_count(t) > config.ROUTER_TRIVIAL_MAX_WORDS:
        return False
    stripped = t.strip(".!,… ")
    return any(
        stripped == p or stripped.startswith(p + " ")
        for p in config.ROUTER_TRIVIAL_PATTERNS
    )


def _is_complex(text: str) -> bool:
    t = text.strip().lower()
    if not t:
        return False
    if _word_count(t) >= config.ROUTER_COMPLEX_MIN_WORDS:
        return True
    return any(kw in t for kw in config.ROUTER_COMPLEX_KEYWORDS)


def choose_tier(user_text: str, just_ran_deep_tool: bool = False) -> Tier:
    # Order matters: complexity wins over brevity (a short but loaded question
    # should still reason), and the safe default is MID.
    if just_ran_deep_tool or _is_complex(user_text):
        return Tier.REASONING
    if _is_trivial(user_text):
        return Tier.LIGHT
    return Tier.MID


def is_weak_reply(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < config.ROUTER_WEAK_REPLY_MIN_CHARS:
        return True
    low = t.lower()
    return any(p in low for p in config.ROUTER_REFUSAL_PATTERNS)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_router.py -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/router.py backend/tests/test_router.py
git commit -m "feat(routing): pure heuristic tier router (choose_tier, is_weak_reply)"
```

---

## Task 3: Three model instances in llm.py

**Files:**
- Modify: `backend/app/llm.py`
- Test: `backend/tests/test_llm.py` (new)

**Interfaces:**
- Consumes: `settings.model_light/model_mid/model_reasoning/reasoning_max_tokens` (Task 1).
- Produces: module-level `llm_light`, `llm_mid`, `llm_reasoning` (all `ChatOpenAI`, no tools bound); `distill_facts` unchanged.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_llm.py`:

```python
from app import llm
from app.config import settings


def test_three_tier_instances_have_correct_models():
    assert llm.llm_light.model_name == settings.model_light
    assert llm.llm_mid.model_name == settings.model_mid
    assert llm.llm_reasoning.model_name == settings.model_reasoning


def test_reasoning_has_larger_token_budget_than_light():
    assert llm.llm_reasoning.max_tokens > llm.llm_light.max_tokens


def test_distill_facts_still_exported():
    assert callable(llm.distill_facts)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_llm.py -q`
Expected: FAIL — `AttributeError: module 'app.llm' has no attribute 'llm_light'`.

- [ ] **Step 3: Rewrite the model wiring in `llm.py`**

In `backend/app/llm.py`, replace the single `chat_llm = ChatOpenAI(...)` block (the lines from the `# Chat model —` comment through the closing `)` of `chat_llm`) with:

```python
def _make_chat(model: str, max_tokens: int, *, extra_body: dict | None = None) -> ChatOpenAI:
    """Build a ChatOpenAI for one tier. Tools are bound later in agent.py."""
    return ChatOpenAI(
        model=model,
        base_url=settings.nvidia_base_url,
        api_key=settings.nvidia_api_key,
        temperature=0.7,
        top_p=0.95,
        max_tokens=max_tokens,
        extra_body=extra_body,
    )


# Three tiers selected per-turn by the router. None has tools bound here;
# agent.py binds tools to the mid/reasoning tiers (the light 8B can't call
# tools reliably and only handles trivial chit-chat).
llm_light = _make_chat(settings.model_light, max_tokens=1024)
llm_mid = _make_chat(settings.model_mid, max_tokens=2048, extra_body=settings.chat_extra_body)
llm_reasoning = _make_chat(
    settings.model_reasoning,
    max_tokens=settings.reasoning_max_tokens,
    extra_body=settings.chat_extra_body,
)
```

Keep the `_raw = OpenAI(...)` line and the entire `distill_facts` function unchanged. Update the module docstring's first paragraph to mention three tiers if you like (optional, no behavior change).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_llm.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm.py backend/tests/test_llm.py
git commit -m "feat(routing): build light/mid/reasoning ChatOpenAI tiers in llm.py"
```

---

## Task 4: Tier-aware agent node + escalation

**Files:**
- Modify: `backend/app/agent.py`
- Test: `backend/tests/test_agent_routing.py` (new)

**Interfaces:**
- Consumes: `llm_light/llm_mid/llm_reasoning` (Task 3); `Tier`, `choose_tier`, `is_weak_reply` (Task 2); `config.ROUTER_DEEP_TOOLS` (Task 1); `get_stream_writer` from `langgraph.config`.
- Produces: `llm_for_tier(tier) -> Runnable`; `_just_ran_deep_tool(messages) -> bool`; `agent_node` (now tier-aware). `build_graph`, `recall_node`, `remember_node`, `_route`, `TOOLS` unchanged.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_agent_routing.py`:

```python
import asyncio

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app import agent
from app.router import Tier


def test_just_ran_deep_tool_detects_review_sop():
    msgs = [
        HumanMessage(content="review my sop"),
        AIMessage(content="", tool_calls=[{"name": "review_sop", "args": {}, "id": "1"}]),
        ToolMessage(content="{}", name="review_sop", tool_call_id="1"),
    ]
    assert agent._just_ran_deep_tool(msgs) is True


def test_just_ran_deep_tool_ignores_shallow_tool():
    msgs = [
        HumanMessage(content="roi please"),
        ToolMessage(content="{}", name="estimate_roi", tool_call_id="1"),
    ]
    assert agent._just_ran_deep_tool(msgs) is False


def test_just_ran_deep_tool_false_with_only_human():
    assert agent._just_ran_deep_tool([HumanMessage(content="hi")]) is False


def test_llm_for_tier_mapping():
    assert agent.llm_for_tier(Tier.LIGHT) is agent.llm_light
    assert agent.llm_for_tier(Tier.MID) is agent._mid_tools
    assert agent.llm_for_tier(Tier.REASONING) is agent._reasoning_tools


class _FakeLLM:
    def __init__(self, msg):
        self.msg = msg

    async def ainvoke(self, prompt):
        return self.msg


class _RaisingLLM:
    async def ainvoke(self, prompt):
        raise RuntimeError("model down")


def _run_agent(state):
    return asyncio.run(agent.agent_node(state))


def test_weak_light_reply_escalates_to_mid(monkeypatch):
    monkeypatch.setattr(agent, "llm_light", _FakeLLM(AIMessage(content="ok")))
    monkeypatch.setattr(agent, "_mid_tools", _FakeLLM(AIMessage(content="A full, helpful answer.")))
    state = {"messages": [HumanMessage(content="hi")], "user_id": "u", "recalled": []}
    out = _run_agent(state)
    assert out["messages"][0].content == "A full, helpful answer."


def test_reasoning_failure_falls_back_to_mid(monkeypatch):
    monkeypatch.setattr(agent, "_reasoning_tools", _RaisingLLM())
    monkeypatch.setattr(agent, "_mid_tools", _FakeLLM(AIMessage(content="Mid handled it.")))
    state = {
        "messages": [HumanMessage(content="US vs Canada for robotics?")],
        "user_id": "u",
        "recalled": [],
    }
    out = _run_agent(state)
    assert out["messages"][0].content == "Mid handled it."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_agent_routing.py -q`
Expected: FAIL — `AttributeError: module 'app.agent' has no attribute '_just_ran_deep_tool'`.

- [ ] **Step 3: Rewrite the routing parts of `agent.py`**

In `backend/app/agent.py`:

(a) Update imports. Replace:

```python
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
```

with:

```python
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.config import get_stream_writer
```

Replace:

```python
from . import memory
from .llm import chat_llm, distill_facts
```

with:

```python
from . import config, memory, router
from .llm import distill_facts, llm_light, llm_mid, llm_reasoning
from .router import Tier
```

(b) Replace the tool-binding line:

```python
TOOLS = [shortlist_universities, estimate_roi, roi_breakdown, review_sop, list_my_sops]
_llm_with_tools = chat_llm.bind_tools(TOOLS)
```

with:

```python
TOOLS = [shortlist_universities, estimate_roi, roi_breakdown, review_sop, list_my_sops]
# Tools bound to the tiers that can use them. Light (8B) stays tool-less.
_mid_tools = llm_mid.bind_tools(TOOLS)
_reasoning_tools = llm_reasoning.bind_tools(TOOLS)

# Tier -> the label the frontend shows on each reply.
_TIER_LABEL = {Tier.LIGHT: "fast", Tier.MID: "standard", Tier.REASONING: "deep"}


def llm_for_tier(tier: Tier):
    if tier is Tier.LIGHT:
        return llm_light
    if tier is Tier.REASONING:
        return _reasoning_tools
    return _mid_tools


def _just_ran_deep_tool(messages: list[BaseMessage]) -> bool:
    """True if a deep tool produced output since the last user message."""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return False
        if isinstance(m, ToolMessage) and getattr(m, "name", None) in config.ROUTER_DEEP_TOOLS:
            return True
    return False


def _emit_tier(tier: Tier) -> None:
    """Tell the client which tier is answering (best-effort; no-op off-stream)."""
    try:
        get_stream_writer()({"tier": _TIER_LABEL[tier]})
    except Exception:
        pass
```

(c) Replace the whole `agent_node` function with:

```python
async def agent_node(state: AgentState) -> dict:
    system = SYSTEM_PROMPT
    if state.get("recalled"):
        known = "\n".join(f"- {f}" for f in state["recalled"])
        system += (
            "\n\nWHAT YOU ALREADY KNOW ABOUT THIS STUDENT (from past "
            f"conversations):\n{known}\n\nUse this naturally; don't recite it back."
        )
    prompt = [SystemMessage(content=system), *state["messages"]]

    tier = router.choose_tier(
        _last_human(state["messages"]), _just_ran_deep_tool(state["messages"])
    )
    _emit_tier(tier)

    try:
        reply = await llm_for_tier(tier).ainvoke(prompt)
    except Exception:
        # A slow-tier failure must never dead-end a turn — fall back to mid.
        if tier is Tier.REASONING:
            tier = Tier.MID
            _emit_tier(tier)
            reply = await _mid_tools.ainvoke(prompt)
        else:
            raise

    # Reactive light -> mid: the 8B answered something weak, retry on the 70B.
    if (
        tier is Tier.LIGHT
        and not getattr(reply, "tool_calls", None)
        and router.is_weak_reply(str(reply.content))
    ):
        _emit_tier(Tier.MID)
        reply = await _mid_tools.ainvoke(prompt)

    return {"messages": [reply]}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_agent_routing.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Confirm nothing else imported the old symbol**

Run: `cd backend && grep -rn "chat_llm\|_llm_with_tools" app/ ; echo "exit $?"`
Expected: no matches (grep exit 1). If anything matches, update it to use `llm_for_tier` / `_mid_tools`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/agent.py backend/tests/test_agent_routing.py
git commit -m "feat(routing): tier-aware agent_node with escalation and tier emission"
```

---

## Task 5: SSE meta event in server.py

**Files:**
- Modify: `backend/app/server.py`
- Test: `backend/tests/test_server_stream.py` (new)

**Interfaces:**
- Consumes: a graph object exposing `astream(state, config=..., stream_mode=[...])` yielding `(mode, payload)`.
- Produces: `_stream_chat(graph, state, config) -> async generator` of SSE dicts with events `meta` / `token` / `done` / `error`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_server_stream.py`:

```python
import asyncio

from langchain_core.messages import AIMessageChunk

from app import server


class _FakeGraph:
    async def astream(self, state, config=None, stream_mode=None):
        yield ("custom", {"tier": "deep"})
        yield ("messages", (AIMessageChunk(content="Hello"), {"langgraph_node": "agent"}))
        yield ("messages", (AIMessageChunk(content=""), {"langgraph_node": "agent"}))  # skipped
        yield ("messages", (AIMessageChunk(content="x"), {"langgraph_node": "tools"}))  # skipped


def _collect(graph):
    async def run():
        return [e async for e in server._stream_chat(graph, {}, {})]
    return asyncio.run(run())


def test_stream_emits_meta_then_token_then_done():
    events = _collect(_FakeGraph())
    assert {"event": "meta", "data": "deep"} in events
    assert {"event": "token", "data": "Hello"} in events
    assert events[-1] == {"event": "done", "data": ""}
    # empty content and non-agent nodes are not forwarded as tokens
    assert sum(1 for e in events if e["event"] == "token") == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_server_stream.py -q`
Expected: FAIL — `AttributeError: module 'app.server' has no attribute '_stream_chat'`.

- [ ] **Step 3: Extract and extend the stream generator**

In `backend/app/server.py`, add this module-level async generator (e.g. just above the `@app.post("/chat")` decorator):

```python
async def _stream_chat(graph, state, config):
    """Yield SSE events: meta (tier) + token (reply text) + done/error."""
    try:
        async for mode, payload in graph.astream(
            state, config=config, stream_mode=["messages", "custom"]
        ):
            if mode == "custom":
                tier = payload.get("tier") if isinstance(payload, dict) else None
                if tier:
                    yield {"event": "meta", "data": tier}
            elif mode == "messages":
                chunk, meta = payload
                if (
                    meta.get("langgraph_node") == "agent"
                    and isinstance(chunk, AIMessageChunk)
                    and chunk.content
                ):
                    yield {"event": "token", "data": chunk.content}
        yield {"event": "done", "data": ""}
    except Exception:
        log.exception("chat stream failed")
        yield {"event": "error", "data": "internal error"}
```

Then in the `chat` endpoint, replace the inner `async def event_stream(): ...` definition and the `resp = EventSourceResponse(event_stream())` line with a single call that reuses the extracted generator:

```python
    resp = EventSourceResponse(_stream_chat(_graph, state, config))
```

(Delete the now-unused local `event_stream` function entirely. Keep the `user_id`, `thread_id`, `config`, `state`, and the `if is_new: auth.set_cookie(...)` lines exactly as they are.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_server_stream.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/server.py backend/tests/test_server_stream.py
git commit -m "feat(routing): forward tier as SSE meta event from /chat"
```

---

## Task 6: Frontend — badge, deep-thinking state, tier-aware timeout

**Files:**
- Modify: `sarthi-web/src/app/(app)/chat/page.tsx`

**Interfaces:**
- Consumes: SSE `meta` event carrying `"fast" | "standard" | "deep"`.
- Produces: per-reply tier badge; "thinking deeply…" empty state; longer stall window for deep turns. (No automated tests — verified via `tsc` + `build` + manual.)

- [ ] **Step 1: Add the tier type, labels, and deep timeout constant**

Near the top of `page.tsx`, replace:

```tsx
type Role = "user" | "sarthi";
type Message = { id: number; role: Role; content: string };

// Abort the stream if SARTHI sends nothing for this long (model hang / rate-limit).
const STALL_TIMEOUT_MS = 45_000;
```

with:

```tsx
type Role = "user" | "sarthi";
type TierLabel = "fast" | "standard" | "deep";
type Message = { id: number; role: Role; content: string; tier?: TierLabel };

// Abort the stream if SARTHI sends nothing for this long (model hang / rate-limit).
const STALL_TIMEOUT_MS = 45_000;
// Deep-reasoning turns stay silent while thinking (~27s) — give them more room.
const STALL_TIMEOUT_DEEP_MS = 90_000;

const TIER_LABEL: Record<TierLabel, string> = {
  fast: "Fast",
  standard: "Standard",
  deep: "Deep thinking",
};
```

- [ ] **Step 2: Add a DeepThinking component**

Just after the existing `function Thinking() { ... }` block, add:

```tsx
/** Shown while the slow reasoning tier is composing (stays silent ~27s). */
function DeepThinking() {
  return (
    <span className="flex items-center gap-2 pt-2 text-sm text-muted" aria-label="SARTHI is thinking deeply">
      SARTHI is thinking deeply
      <span className="flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="size-1.5 rounded-full bg-saffron/70"
            animate={{ opacity: [0.25, 1, 0.25] }}
            transition={{ repeat: Infinity, duration: 1.1, delay: i * 0.18, ease: "easeInOut" }}
          />
        ))}
      </span>
    </span>
  );
}
```

- [ ] **Step 3: Parse the meta event and make the stall window tier-aware**

In `sendText`, the watchdog block currently reads:

```tsx
    const controller = new AbortController();
    let timedOut = false;
    let stall: ReturnType<typeof setTimeout> | undefined;
    const resetStall = () => {
      if (stall) clearTimeout(stall);
      stall = setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, STALL_TIMEOUT_MS);
    };
```

Replace it with a version that uses a mutable window:

```tsx
    const controller = new AbortController();
    let timedOut = false;
    let stallWindow = STALL_TIMEOUT_MS;
    let stall: ReturnType<typeof setTimeout> | undefined;
    const resetStall = () => {
      if (stall) clearTimeout(stall);
      stall = setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, stallWindow);
    };

    const setTier = (tier: TierLabel) =>
      setMessages((m) =>
        m.map((msg) => (msg.id === sarthiMsg.id ? { ...msg, tier } : msg)),
      );
```

Then in the SSE event dispatch, currently:

```tsx
          if (event === "token") append(data);
          else if (event === "error") setError("Something went wrong. Try again.");
```

replace with:

```tsx
          if (event === "token") append(data);
          else if (event === "meta") {
            const tier = data as TierLabel;
            setTier(tier);
            if (tier === "deep") {
              stallWindow = STALL_TIMEOUT_DEEP_MS;
              resetStall();
            }
          } else if (event === "error") setError("Something went wrong. Try again.");
```

- [ ] **Step 4: Render the deep-thinking state and the badge**

In the SARTHI message branch, replace:

```tsx
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
```

with:

```tsx
                      <div className="min-w-0 flex-1 pt-0.5">
                        {m.content === "" && streamingId === m.id ? (
                          m.tier === "deep" ? <DeepThinking /> : <Thinking />
                        ) : (
                          <div className="md">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                            {streamingId === m.id && <span className="caret">▍</span>}
                          </div>
                        )}
                        {m.tier && streamingId !== m.id && m.content !== "" && (
                          <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-muted">
                            <span className="size-1.5 rounded-full bg-saffron/60" />
                            {TIER_LABEL[m.tier]}
                          </div>
                        )}
                      </div>
```

- [ ] **Step 5: Type-check and build**

Run: `cd sarthi-web && npx tsc --noEmit`
Expected: exit 0, no errors.

Run: `cd sarthi-web && npm run build`
Expected: build succeeds; route `/chat` compiles.

- [ ] **Step 6: Manual verification (with both servers running)**

Backend: `cd backend && ./.venv/Scripts/python -m uvicorn app.server:app --port 8000`
Frontend: `cd sarthi-web && npm run dev`
- "hi" → reply tagged **Fast** (or Standard if it escalated).
- "tell me about the GRE" → **Standard**.
- "US vs Canada for robotics, what should I do?" → shows **SARTHI is thinking deeply…**, then a reply tagged **Deep thinking** (allow ~30s; should not abort).

- [ ] **Step 7: Commit**

```bash
git add sarthi-web/src/app/\(app\)/chat/page.tsx
git commit -m "feat(routing): chat tier badge, deep-thinking state, tier-aware timeout"
```

---

## Task 7: Document the feature and verify the whole suite

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Record the feature in `CLAUDE.md`**

In `§0`, immediately before the `**Next up:** F5 ...` line, add:

```markdown
- **Model routing:** done. Automatic per-turn tier selection — light (`llama-3.1-8b`, chit-chat), mid/default (`llama-3.3-70b`, tools), reasoning (`nemotron-super-49b`, deep). Pure heuristic router (`backend/app/router.py`, all tunables in `config.py`); direction-aware escalation (light→mid reactive on weak replies, mid→reasoning predictive on deep tool / complex turns) with reasoning→mid fallback. Tier streamed to the UI via a custom-stream `meta` SSE event → per-reply badge + "thinking deeply" state + tier-aware stall timeout. New pytest suites (router/agent/server-stream). **Gotcha:** the reasoning model returns its answer in `.content` and thoughts in `reasoning_content` (only `.content` is streamed); too small a `max_tokens` starves the answer.
```

- [ ] **Step 2: Run the full backend suite**

Run: `cd backend && ./.venv/Scripts/python -m pytest -q`
Expected: all tests pass (existing 48 + new: test_config additions, 8 router, 3 llm, 6 agent_routing, 1 server_stream).

- [ ] **Step 3: Final frontend checks**

Run: `cd sarthi-web && npx tsc --noEmit && npm run build`
Expected: both clean.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: record automatic model routing in CLAUDE.md"
```

---

## Self-Review Notes

- **Spec coverage:** tiers/models (Task 1,3) · heuristic router + misroute safe-default (Task 2) · direction-aware escalation + post-tool reasoning + reasoning fallback (Task 4) · up-front tier via custom stream writer + `meta` SSE (Task 4,5) · badge + deep-thinking + tier-aware timeout (Task 6) · tests for router/agent/server (Task 2,4,5) · docs (Task 7). Custom-stream-writer risk (spec §10) is resolved — verified available; no fallback path needed.
- **Type consistency:** `Tier` (`LIGHT/MID/REASONING`), `choose_tier(user_text, just_ran_deep_tool)`, `is_weak_reply(text)`, `llm_for_tier`, `_just_ran_deep_tool`, `_stream_chat`, `TierLabel` (`fast/standard/deep`), and SSE event names (`meta/token/done/error`) are used identically across tasks.
- **No placeholders:** every code step shows complete code; every run step shows the command and expected result.
