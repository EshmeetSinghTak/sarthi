"""FastAPI server exposing the SARTHI agent over SSE.

Endpoints:
  GET  /health                 - liveness
  POST /chat                   - stream a reply (Server-Sent Events)
  GET  /memory/{user_id}       - inspect stored facts (debug-only, off by default)

The AsyncSqliteSaver checkpointer must stay open for the app's lifetime, so we
enter it in the lifespan and compile the graph once.

⚠️  SECURITY — NOT PRODUCTION READY. This API has NO authentication: user_id is
client-supplied and unverified. That means any caller can impersonate a user
(read their recalled memory, pollute their facts) and — when SARTHI_DEBUG is on
— read any user's stored PII. Before any deployment, add real auth (derive
user_id from a verified session/token, not the request body) and restrict CORS.
Tracked as the Phase 2 "user identity" item. Run local-only until then.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import memory
from .agent import build_graph
from .config import settings

log = logging.getLogger("sarthi")
_graph = None  # compiled LangGraph app, set in lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph
    settings.require_key()
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db) as saver:
        _graph = build_graph(saver)
        yield
    _graph = None


# Comma-separated allowed origins; defaults to local dev only. Set
# SARTHI_CORS_ORIGINS for other environments (never use "*" with credentials).
_origins = [
    o.strip()
    for o in os.getenv(
        "SARTHI_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]

app = FastAPI(title="SARTHI Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
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
        except Exception:
            # Log details server-side; don't leak internals to the client.
            log.exception("chat stream failed for thread %s", thread_id)
            yield {"event": "error", "data": "internal error"}

    return EventSourceResponse(event_stream())


@app.get("/memory/{user_id}")
async def get_memory(user_id: str) -> dict:
    # Debug-only: returns a user's PII with no auth, so it's an IDOR risk.
    # Disabled unless SARTHI_DEBUG=true (intended for local development only).
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    return {"user_id": user_id, "facts": memory.all_facts(user_id)}
