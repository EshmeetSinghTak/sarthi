"""The SARTHI agent graph.

Flow:  recall  ->  agent  ⇄  tools  ->  remember

- recall:   pull the user's relevant long-term facts (Chroma) for this turn.
- agent:    the chat model, bound to tools (F2: university shortlister). It may
            answer directly, or emit tool calls.
- tools:    execute any tool calls, append results, loop back to the agent.
- remember: distill durable facts from the user's message and store them.

Long-term facts (cross-session, per user) live in Chroma. Conversation history
(per thread) lives in the LangGraph checkpointer.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from . import config, memory, router
from .llm import distill_facts, llm_light, llm_mid, llm_reasoning
from .prompts import SYSTEM_PROMPT
from .router import Tier
from .tools import estimate_roi, list_my_sops, review_sop, roi_breakdown, shortlist_universities

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


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    recalled: list[str]


def _last_human(messages: list[BaseMessage]) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return str(m.content)
    return ""


def recall_node(state: AgentState) -> dict:
    query = _last_human(state["messages"])
    facts = memory.recall(state["user_id"], query, k=5) if query else []
    return {"recalled": facts}


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


def remember_node(state: AgentState) -> dict:
    msg = _last_human(state["messages"])
    if msg:
        facts = distill_facts(msg)
        if facts:
            memory.remember(state["user_id"], facts)
    return {}


def _route(state: AgentState) -> str:
    """After the agent: run tools if it asked for them, else finish up."""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "remember"


def build_graph(checkpointer):
    g = StateGraph(AgentState)
    g.add_node("recall", recall_node)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(TOOLS))
    g.add_node("remember", remember_node)

    g.add_edge(START, "recall")
    g.add_edge("recall", "agent")
    g.add_conditional_edges("agent", _route, {"tools": "tools", "remember": "remember"})
    g.add_edge("tools", "agent")
    g.add_edge("remember", END)
    return g.compile(checkpointer=checkpointer)
