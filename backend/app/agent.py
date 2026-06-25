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

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from . import memory
from .llm import chat_llm, distill_facts
from .prompts import SYSTEM_PROMPT
from .tools import shortlist_universities

TOOLS = [shortlist_universities]
_llm_with_tools = chat_llm.bind_tools(TOOLS)


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
    reply = await _llm_with_tools.ainvoke(prompt)
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
