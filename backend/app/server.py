"""FastAPI server exposing the SARTHI agent over SSE.

Endpoints:
  GET  /health     - liveness
  GET  /session    - ensure an anonymous identity cookie exists
  POST /chat       - stream a reply (Server-Sent Events)
  GET  /memory     - inspect the current user's stored facts (debug-only)

Identity: user_id is derived from a server-signed httpOnly cookie (see auth.py),
never from the request body — so it cannot be spoofed. Anonymous, no login.
CORS is restricted and credentialed. Still pre-account; add real login before
storing anything more sensitive than study-abroad preferences.

The AsyncSqliteSaver checkpointer must stay open for the app's lifetime, so we
enter it in the lifespan and compile the graph once.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import auth, memory, sop_store
from .agent import build_graph
from .config import settings
from .tools.sop import analyze_sop

log = logging.getLogger("sarthi")
_graph = None  # compiled LangGraph app, set in lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph
    settings.require_key()
    sop_store.init_db()
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
    allow_credentials=True,  # required so identity cookies cross origins
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    message: str
    # Identity comes from the cookie, never the body.


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "chat_model": settings.chat_model}


@app.get("/session")
async def session(request: Request):
    """Ensure the caller has an identity cookie; mint one if absent."""
    user_id, is_new = auth.resolve_user(request)
    from fastapi.responses import JSONResponse

    resp = JSONResponse({"ok": True})
    if is_new:
        auth.set_cookie(resp, user_id)
    return resp


@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    user_id, is_new = auth.resolve_user(request)
    thread_id = user_id  # one ongoing thread per anonymous user
    config = {"configurable": {"thread_id": thread_id}}
    state = {"messages": [HumanMessage(content=req.message)], "user_id": user_id}

    async def event_stream():
        try:
            async for chunk, meta in _graph.astream(
                state, config=config, stream_mode="messages"
            ):
                # Forward only streaming token chunks from the response node.
                # (messages mode also surfaces the complete AIMessage the node
                # commits to state — skip that to avoid a duplicated reply.)
                if (
                    meta.get("langgraph_node") == "agent"
                    and isinstance(chunk, AIMessageChunk)
                    and chunk.content
                ):
                    yield {"event": "token", "data": chunk.content}
            yield {"event": "done", "data": ""}
        except Exception:
            # Log details server-side; don't leak internals to the client.
            log.exception("chat stream failed for thread %s", thread_id)
            yield {"event": "error", "data": "internal error"}

    resp = EventSourceResponse(event_stream())
    if is_new:
        auth.set_cookie(resp, user_id)
    return resp


@app.get("/memory")
async def get_memory(request: Request) -> dict:
    # Debug-only inspection of the CURRENT user's own facts (from the cookie).
    # Disabled unless SARTHI_DEBUG=true.
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    user_id, _ = auth.resolve_user(request)
    return {"user_id": user_id, "facts": memory.all_facts(user_id)}


# ---------------------------------------------------------------------------
# F4 — SOP Co-Pilot endpoints
# ---------------------------------------------------------------------------


class CreateSopRequest(BaseModel):
    title: str


class SaveVersionRequest(BaseModel):
    content: str


def _with_cookie(payload: dict, user_id: str, is_new: bool, status_code: int = 200) -> JSONResponse:
    resp = JSONResponse(payload, status_code=status_code)
    if is_new:
        auth.set_cookie(resp, user_id)
    return resp


@app.get("/sops")
def sop_list(request: Request):
    user_id, is_new = auth.resolve_user(request)
    return _with_cookie({"sops": sop_store.list_sops(user_id)}, user_id, is_new)


@app.post("/sops")
def sop_create(req: CreateSopRequest, request: Request):
    user_id, is_new = auth.resolve_user(request)
    title = req.title.strip() or "Untitled SOP"
    sop = sop_store.create_sop(user_id, title)
    return _with_cookie(sop, user_id, is_new, status_code=201)


@app.get("/sops/{sop_id}")
def sop_get(sop_id: int, request: Request):
    user_id, is_new = auth.resolve_user(request)
    sop = sop_store.get_sop(user_id, sop_id)
    if sop is None:
        raise HTTPException(status_code=404, detail="Not found")
    latest = sop_store.get_latest_version(user_id, sop_id)
    return _with_cookie({"sop": sop, "latest": latest}, user_id, is_new)


@app.post("/sops/{sop_id}/versions")
def sop_add_version(sop_id: int, req: SaveVersionRequest, request: Request):
    user_id, is_new = auth.resolve_user(request)
    analysis = analyze_sop(req.content)
    version = sop_store.add_version(user_id, sop_id, req.content, analysis)
    if version is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _with_cookie({"version": version, "analysis": analysis}, user_id, is_new, status_code=201)


@app.get("/sops/{sop_id}/versions")
def sop_list_versions(sop_id: int, request: Request):
    user_id, is_new = auth.resolve_user(request)
    if sop_store.get_sop(user_id, sop_id) is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _with_cookie({"versions": sop_store.list_versions(user_id, sop_id)}, user_id, is_new)


@app.get("/sops/{sop_id}/versions/{version_id}")
def sop_get_version(sop_id: int, version_id: int, request: Request):
    user_id, is_new = auth.resolve_user(request)
    version = sop_store.get_version(user_id, sop_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _with_cookie({"version": version}, user_id, is_new)
