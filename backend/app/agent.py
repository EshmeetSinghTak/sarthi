"""The SARTHI agent graph (F1).

Flow:  recall  ->  respond  ->  remember

- recall:   pull the user's relevant long-term facts (Chroma) for this turn.
- respond:  call the chat model with [system + recalled facts + history].
            Conversation history persists per thread_id via the checkpointer.
- remember: distill durable facts from the user's message and store them.

Long-term facts (cross-session, per user) live in Chroma. Conversation history
(per thread) lives in the LangGraph checkpointer. The two are deliberately
separate: facts are distilled and reusable; history is verbatim and threaded.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from . import memory
from .llm import chat_llm, distill_facts
from .prompts import SYSTEM_PROMPT


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


async def respond_node(state: AgentState) -> dict:
    system = SYSTEM_PROMPT
    if state.get("recalled"):
        known = "\n".join(f"- {f}" for f in state["recalled"])
        system += (
            "\n\nWHAT YOU ALREADY KNOW ABOUT THIS STUDENT (from past "
            f"conversations):\n{known}\n\nUse this naturally; don't recite it back."
        )
    prompt = [SystemMessage(content=system), *state["messages"]]
    reply = await chat_llm.ainvoke(prompt)
    return {"messages": [AIMessage(content=reply.content)]}


def remember_node(state: AgentState) -> dict:
    msg = _last_human(state["messages"])
    if msg:
        facts = distill_facts(msg)
        if facts:
            memory.remember(state["user_id"], facts)
    return {}


def build_graph(checkpointer):
    g = StateGraph(AgentState)
    g.add_node("recall", recall_node)
    g.add_node("respond", respond_node)
    g.add_node("remember", remember_node)
    g.add_edge(START, "recall")
    g.add_edge("recall", "respond")
    g.add_edge("respond", "remember")
    g.add_edge("remember", END)
    return g.compile(checkpointer=checkpointer)
