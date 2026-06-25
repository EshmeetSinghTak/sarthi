"""FastAPI server exposing the SARTHI agent over SSE.

Endpoints:
  GET  /health                 - liveness
  POST /chat                   - stream a reply (Server-Sent Events)
  GET  /memory/{user_id}       - inspect a user's stored long-term facts (debug)

The AsyncSqliteSaver checkpointer must stay open for the app's lifetime, so we
enter it in the lifespan and compile the graph once.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import memory
from .agent import build_graph
from .config import settings

_graph = None  # compiled LangGraph app, set in lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph
    settings.require_key()
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db) as saver:
        _graph = build_graph(saver)
        yield
    _graph = None


app = FastAPI(title="SARTHI Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    user_id: str
    message: str
    thread_id: str | None = None  # defaults to user_id (one ongoing thread)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "chat_model": settings.chat_model}


@app.post("/chat")
async def chat(req: ChatRequest):
    thread_id = req.thread_id or req.user_id
    config = {"configurable": {"thread_id": thread_id}}
    state = {"messages": [HumanMessage(content=req.message)], "user_id": req.user_id}

    async def event_stream():
        try:
            async for chunk, meta in _graph.astream(
                state, config=config, stream_mode="messages"
            ):
                # Forward only streaming token chunks from the response node.
                # (messages mode also surfaces the complete AIMessage the node
                # commits to state — skip that to avoid a duplicated reply.)
                if (
                    meta.get("langgraph_node") == "respond"
                    and isinstance(chunk, AIMessageChunk)
                    and chunk.content
                ):
                    yield {"event": "token", "data": chunk.content}
            yield {"event": "done", "data": ""}
        except Exception as e:  # surface errors to the client instead of hanging
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_stream())


@app.get("/memory/{user_id}")
async def get_memory(user_id: str) -> dict:
    return {"user_id": user_id, "facts": memory.all_facts(user_id)}
