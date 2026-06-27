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
