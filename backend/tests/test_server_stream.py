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
