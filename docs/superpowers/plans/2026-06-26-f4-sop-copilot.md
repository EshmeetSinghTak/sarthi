# F4 — SOP Co-Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an SOP Co-Pilot to SARTHI — a deterministic SOP analyzer, a persistent multi-SOP workspace (append-only versions), cookie-scoped REST API, Socratic chat-coaching tools, and a `/sop` frontend.

**Architecture:** Mirrors F2/F3's testable-core pattern. Pure `analyze_sop(text)` + a synchronous SQLite repository (`sop_store.py`) under thin REST and LangChain-tool wrappers. The chat agent reaches a user's draft via tools that receive `user_id` through LangGraph `InjectedState` (never from the model). A new Next.js `/sop` route is the authoring surface.

**Tech Stack:** Python 3.14, FastAPI, LangGraph/LangChain, stdlib `sqlite3`, pytest; Next.js 16 + Tailwind v4 + framer-motion.

## Global Constraints

- **No Claude / no paid LLMs.** Coaching rides the existing free NVIDIA chat model; the analyzer uses no model. Test the live agent with `SARTHI_MODEL_DEFAULT=meta/llama-3.3-70b-instruct`.
- **NEVER hardcode tunables.** Clichés → `backend/data/sop_cliches.json`; word band + sentence threshold + DB path → `backend/app/config.py`. No literals in analyzer logic.
- **Never auto-generate the SOP.** The prompt forbids writing/rewriting the student's SOP; the agent coaches only.
- **Identity from the signed cookie, never the body.** API endpoints use `auth.resolve_user(request)`; agent tools get `user_id` via `InjectedState`. All store reads/writes are scoped by `user_id`.
- **Run commands** from `backend/` with `./.venv/Scripts/python`. Windows + Git Bash.
- **Frontend:** Next.js 16 has breaking changes — consult `sarthi-web/node_modules/next/dist/docs/` before writing FE code (per `sarthi-web/AGENTS.md`). Reuse existing Tailwind tokens (`ink-2`, `ink-3`, `cream`, `muted`, `saffron`, `saffron-deep`, `font-display`, `font-deva`). FE is verified manually.

---

### Task 1: Config constants + cliché data

**Files:**
- Modify: `backend/app/config.py` (append constants)
- Create: `backend/data/sop_cliches.json`
- Test: `backend/tests/test_sop_data.py`

**Interfaces:**
- Produces: `config.SOP_DB_PATH: str`, `config.SOP_TARGET_WORDS_MIN: int` (700), `config.SOP_TARGET_WORDS_MAX: int` (1000), `config.SOP_LONG_SENTENCE_WORDS: int` (40); `sop_cliches.json` with `note` + `cliches: list[str]` (all lowercase).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_sop_data.py`:
```python
import json

from app import config


def test_sop_config_constants():
    assert config.SOP_TARGET_WORDS_MIN == 700
    assert config.SOP_TARGET_WORDS_MAX == 1000
    assert config.SOP_LONG_SENTENCE_WORDS == 40
    assert config.SOP_DB_PATH


def test_sop_cliches_data():
    data = json.loads(
        (config.BACKEND_DIR / "data" / "sop_cliches.json").read_text(encoding="utf-8")
    )
    assert data["note"].strip()
    assert isinstance(data["cliches"], list) and len(data["cliches"]) >= 5
    # stored lowercase so case-insensitive matching is a simple substring test
    assert all(c == c.lower() for c in data["cliches"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_sop_data.py -v`
Expected: FAIL — `AttributeError: module 'app.config' has no attribute 'SOP_TARGET_WORDS_MIN'`

- [ ] **Step 3: Add config constants**

Append to the end of `backend/app/config.py`:
```python

# --- F4 SOP Co-Pilot (tunables centralized; never hardcode in logic) ---
SOP_DB_PATH: str = os.getenv("SARTHI_SOP_DB", str(BACKEND_DIR / "sarthi_sop.db"))
SOP_TARGET_WORDS_MIN: int = 700   # typical SOP lower bound
SOP_TARGET_WORDS_MAX: int = 1000  # typical SOP upper bound
SOP_LONG_SENTENCE_WORDS: int = 40  # sentences longer than this are flagged
```

- [ ] **Step 4: Create the cliché data file**

Create `backend/data/sop_cliches.json`:
```json
{
  "note": "Common SOP clichés / red-flag openers and filler that weaken authenticity. Curated, guidance-only — flagging a phrase invites the student to rewrite it in their own specifics.",
  "cliches": [
    "since childhood",
    "from a young age",
    "i have always been passionate",
    "burning desire",
    "dream since",
    "ever since i can remember",
    "i was always fascinated",
    "renowned university",
    "esteemed faculty",
    "world-class",
    "cutting-edge",
    "state-of-the-art",
    "leaps and bounds",
    "tireless efforts",
    "plethora",
    "in today's world"
  ]
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_sop_data.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/data/sop_cliches.json backend/tests/test_sop_data.py
git commit -m "F4: add SOP config constants + cliché data"
```

---

### Task 2: `analyze_sop` pure function

**Files:**
- Create: `backend/app/tools/sop.py`
- Test: `backend/tests/test_sop_analyze.py`

**Interfaces:**
- Consumes: `config.SOP_TARGET_WORDS_MIN/MAX`, `config.SOP_LONG_SENTENCE_WORDS`, `config.BACKEND_DIR`, `sop_cliches.json` (Task 1).
- Produces: `analyze_sop(text: str) -> dict` with keys `word_count, paragraph_count, length_flag ("short"|"ok"|"long"), target_words ([min,max]), cliche_hits ([{phrase,count}]), long_sentences ([{text_preview,word_count}]), structure_signals ({mentions_program,mentions_goal,gives_reasons}), note`. Also module constants `CLICHES`, `CLICHE_NOTE`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_sop_analyze.py`:
```python
from app.tools.sop import analyze_sop


def test_empty_string_is_safe():
    out = analyze_sop("")
    assert out["word_count"] == 0
    assert out["paragraph_count"] == 0
    assert out["length_flag"] == "short"
    assert out["cliche_hits"] == []
    assert out["long_sentences"] == []


def test_length_flag_bands():
    assert analyze_sop("word " * 500)["length_flag"] == "short"
    assert analyze_sop("word " * 800)["length_flag"] == "ok"
    assert analyze_sop("word " * 1200)["length_flag"] == "long"


def test_word_and_paragraph_counts():
    out = analyze_sop("one two three\n\nfour five")
    assert out["word_count"] == 5
    assert out["paragraph_count"] == 2


def test_cliche_detection_case_insensitive_and_counts():
    out = analyze_sop("Since Childhood I loved robots. Since childhood, again.")
    hits = {h["phrase"]: h["count"] for h in out["cliche_hits"]}
    assert hits.get("since childhood") == 2


def test_long_sentence_flagged():
    long_one = "I " + "really " * 45 + "want this."
    assert len(analyze_sop(long_one)["long_sentences"]) == 1
    assert analyze_sop("I want this. It is short.")["long_sentences"] == []


def test_structure_signals():
    text = "I want to join this Master's program because my goal is a research career."
    sig = analyze_sop(text)["structure_signals"]
    assert sig["mentions_program"] and sig["mentions_goal"] and sig["gives_reasons"]
    assert not any(analyze_sop("Hello there.")["structure_signals"].values())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_sop_analyze.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.tools.sop'`

- [ ] **Step 3: Implement the analyzer**

Create `backend/app/tools/sop.py`:
```python
"""F4 — SOP Co-Pilot.

`analyze_sop` is a deterministic, model-free analysis of an SOP draft: length,
clichés, overlong sentences, and coarse structure signals. It produces *signals*
to prompt reflection, never a grade. Agent tools (added later) load a student's
saved draft and return this analysis for Socratic coaching.

Every tunable lives in app.config / data files — nothing hardcoded here.
"""

import json
import re

from .. import config

_CLICHES = json.loads(
    (config.BACKEND_DIR / "data" / "sop_cliches.json").read_text(encoding="utf-8")
)
CLICHE_NOTE = _CLICHES["note"]
CLICHES = _CLICHES["cliches"]

_WORD_RE = re.compile(r"\b\w+\b")
_PARA_SPLIT = re.compile(r"\n\s*\n")
_SENT_SPLIT = re.compile(r"[.?!]+")

_PROGRAM_WORDS = ("program", "master", "phd", "degree", "university", "graduate", "course")
_GOAL_WORDS = ("goal", "career", "aspire", "future", "ambition", "after graduation", "long-term")
_REASON_WORDS = ("because", "why", "motivat", "reason", "drawn to", "interested in", "led me")


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def analyze_sop(text: str) -> dict:
    """Deterministic structural + authenticity signals for an SOP draft."""
    text = text or ""
    lower = text.lower()
    words = _word_count(text)
    paragraphs = [p for p in _PARA_SPLIT.split(text.strip()) if p.strip()]

    if words < config.SOP_TARGET_WORDS_MIN:
        length_flag = "short"
    elif words > config.SOP_TARGET_WORDS_MAX:
        length_flag = "long"
    else:
        length_flag = "ok"

    cliche_hits = [
        {"phrase": phrase, "count": lower.count(phrase)}
        for phrase in CLICHES
        if lower.count(phrase)
    ]

    long_sentences = []
    for raw in _SENT_SPLIT.split(text):
        s = raw.strip()
        wc = _word_count(s)
        if wc > config.SOP_LONG_SENTENCE_WORDS:
            long_sentences.append(
                {"text_preview": " ".join(s.split()[:12]) + "…", "word_count": wc}
            )

    structure_signals = {
        "mentions_program": any(w in lower for w in _PROGRAM_WORDS),
        "mentions_goal": any(w in lower for w in _GOAL_WORDS),
        "gives_reasons": any(w in lower for w in _REASON_WORDS),
    }

    return {
        "word_count": words,
        "paragraph_count": len(paragraphs),
        "length_flag": length_flag,
        "target_words": [config.SOP_TARGET_WORDS_MIN, config.SOP_TARGET_WORDS_MAX],
        "cliche_hits": cliche_hits,
        "long_sentences": long_sentences,
        "structure_signals": structure_signals,
        "note": CLICHE_NOTE + " These are signals to prompt reflection, not a grade.",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_sop_analyze.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/tools/sop.py backend/tests/test_sop_analyze.py
git commit -m "F4: deterministic analyze_sop + tests"
```

---

### Task 3: SQLite SOP repository

**Files:**
- Create: `backend/app/sop_store.py`
- Test: `backend/tests/test_sop_store.py`

**Interfaces:**
- Consumes: `config.SOP_DB_PATH`.
- Produces:
  - `init_db() -> None`
  - `create_sop(user_id, title) -> dict` → `{id, user_id, title, created_at}`
  - `list_sops(user_id) -> list[dict]` → each `{id, title, created_at, latest_version_id, updated_at, word_count}` newest-updated first
  - `get_sop(user_id, sop_id) -> dict | None` (ownership-checked)
  - `add_version(user_id, sop_id, content, analysis: dict) -> dict | None` → `{id, sop_id, created_at}`; None if not owned
  - `list_versions(user_id, sop_id) -> list[dict]` → `{id, created_at, word_count}` newest first
  - `get_version(user_id, sop_id, version_id) -> dict | None` → `{id, content, analysis, created_at, word_count}`
  - `get_latest_version(user_id, sop_id) -> dict | None` (same shape as get_version)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_sop_store.py`:
```python
import pytest

from app import config, sop_store


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SOP_DB_PATH", str(tmp_path / "sop.db"))
    sop_store.init_db()


def test_create_and_list(db):
    s = sop_store.create_sop("u1", "CMU Robotics")
    assert s["title"] == "CMU Robotics" and s["user_id"] == "u1"
    sops = sop_store.list_sops("u1")
    assert len(sops) == 1 and sops[0]["id"] == s["id"]
    assert sops[0]["latest_version_id"] is None


def test_append_only_versions_and_latest(db):
    s = sop_store.create_sop("u1", "X")
    sop_store.add_version("u1", s["id"], "draft one", {"word_count": 2})
    sop_store.add_version("u1", s["id"], "draft two longer", {"word_count": 3})
    latest = sop_store.get_latest_version("u1", s["id"])
    assert latest["content"] == "draft two longer"
    assert latest["analysis"] == {"word_count": 3}
    assert len(sop_store.list_versions("u1", s["id"])) == 2


def test_restore_as_new_version(db):
    s = sop_store.create_sop("u1", "X")
    v1 = sop_store.add_version("u1", s["id"], "original", {"word_count": 1})
    sop_store.add_version("u1", s["id"], "edited", {"word_count": 1})
    old = sop_store.get_version("u1", s["id"], v1["id"])
    sop_store.add_version("u1", s["id"], old["content"], {"word_count": 1})
    assert sop_store.get_latest_version("u1", s["id"])["content"] == "original"
    assert len(sop_store.list_versions("u1", s["id"])) == 3


def test_ownership_isolation(db):
    s = sop_store.create_sop("u1", "Private")
    sop_store.add_version("u1", s["id"], "secret", {"word_count": 1})
    assert sop_store.get_sop("u2", s["id"]) is None
    assert sop_store.get_latest_version("u2", s["id"]) is None
    assert sop_store.get_version("u2", s["id"], 1) is None
    assert sop_store.add_version("u2", s["id"], "hack", {"word_count": 1}) is None
    assert sop_store.list_sops("u2") == []
    assert sop_store.list_versions("u2", s["id"]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_sop_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.sop_store'`

- [ ] **Step 3: Implement the repository**

Create `backend/app/sop_store.py`:
```python
"""SQLite repository for SOP drafts (F4).

Synchronous stdlib sqlite3 — a fresh connection per call (cheap, thread-safe,
trivially testable). Append-only versions: each save is a new immutable row;
"current" = latest. Every read/write is scoped by user_id, so one anonymous
user can never touch another's SOPs. DB path comes from config.SOP_DB_PATH.
"""

import json
import sqlite3
from datetime import datetime, timezone

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sops (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    TEXT NOT NULL,
    title      TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sop_versions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sop_id        INTEGER NOT NULL REFERENCES sops(id),
    content       TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    word_count    INTEGER NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sops_user ON sops(user_id);
CREATE INDEX IF NOT EXISTS idx_versions_sop ON sop_versions(sop_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.SOP_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _owns(conn: sqlite3.Connection, user_id: str, sop_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sops WHERE id = ? AND user_id = ?", (sop_id, user_id)
    ).fetchone()
    return row is not None


def create_sop(user_id: str, title: str) -> dict:
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO sops (user_id, title, created_at) VALUES (?, ?, ?)",
            (user_id, title, _now()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM sops WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def list_sops(user_id: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.created_at,
                   v.id         AS latest_version_id,
                   v.created_at AS updated_at,
                   v.word_count AS word_count
            FROM sops s
            LEFT JOIN sop_versions v
              ON v.id = (SELECT id FROM sop_versions
                         WHERE sop_id = s.id ORDER BY id DESC LIMIT 1)
            WHERE s.user_id = ?
            ORDER BY COALESCE(v.created_at, s.created_at) DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_sop(user_id: str, sop_id: int) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM sops WHERE id = ? AND user_id = ?", (sop_id, user_id)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_version(user_id: str, sop_id: int, content: str, analysis: dict) -> dict | None:
    conn = _connect()
    try:
        if not _owns(conn, user_id, sop_id):
            return None
        cur = conn.execute(
            """INSERT INTO sop_versions (sop_id, content, analysis_json, word_count, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (sop_id, content, json.dumps(analysis), int(analysis.get("word_count", 0)), _now()),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, sop_id, created_at FROM sop_versions WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def list_versions(user_id: str, sop_id: int) -> list[dict]:
    conn = _connect()
    try:
        if not _owns(conn, user_id, sop_id):
            return []
        rows = conn.execute(
            "SELECT id, created_at, word_count FROM sop_versions WHERE sop_id = ? ORDER BY id DESC",
            (sop_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _version_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "content": row["content"],
        "analysis": json.loads(row["analysis_json"]),
        "word_count": row["word_count"],
        "created_at": row["created_at"],
    }


def get_version(user_id: str, sop_id: int, version_id: int) -> dict | None:
    conn = _connect()
    try:
        if not _owns(conn, user_id, sop_id):
            return None
        row = conn.execute(
            "SELECT * FROM sop_versions WHERE id = ? AND sop_id = ?", (version_id, sop_id)
        ).fetchone()
        return _version_row_to_dict(row) if row else None
    finally:
        conn.close()


def get_latest_version(user_id: str, sop_id: int) -> dict | None:
    conn = _connect()
    try:
        if not _owns(conn, user_id, sop_id):
            return None
        row = conn.execute(
            "SELECT * FROM sop_versions WHERE sop_id = ? ORDER BY id DESC LIMIT 1", (sop_id,)
        ).fetchone()
        return _version_row_to_dict(row) if row else None
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_sop_store.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/sop_store.py backend/tests/test_sop_store.py
git commit -m "F4: append-only SQLite SOP repository (user-scoped) + tests"
```

---

### Task 4: REST API + lifespan init

**Files:**
- Modify: `backend/app/server.py` (add models, endpoints, lifespan `init_db`)
- Test: `backend/tests/test_sop_api.py`

**Interfaces:**
- Consumes: `sop_store.*` (Task 3), `analyze_sop` (Task 2), `auth.resolve_user`/`set_cookie`.
- Produces endpoints: `GET /sops`, `POST /sops`, `GET /sops/{sop_id}`, `POST /sops/{sop_id}/versions`, `GET /sops/{sop_id}/versions`, `GET /sops/{sop_id}/versions/{version_id}`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_sop_api.py`:
```python
import pytest
from fastapi.testclient import TestClient

from app import config


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SOP_DB_PATH", str(tmp_path / "sop_api.db"))
    from app.server import app

    with TestClient(app) as c:
        yield c


def test_create_and_get_sop(client):
    r = client.post("/sops", json={"title": "CMU"})
    assert r.status_code == 201
    sid = r.json()["id"]
    g = client.get(f"/sops/{sid}")
    assert g.status_code == 200
    assert g.json()["sop"]["title"] == "CMU"
    assert g.json()["latest"] is None


def test_save_version_returns_analysis(client):
    sid = client.post("/sops", json={"title": "X"}).json()["id"]
    r = client.post(f"/sops/{sid}/versions", json={"content": "word " * 800})
    assert r.status_code == 201
    body = r.json()
    assert body["analysis"]["length_flag"] == "ok"
    assert body["analysis"]["word_count"] == 800
    assert client.get(f"/sops/{sid}/versions").json()["versions"][0]["id"] == body["version"]["id"]


def test_list_sops_scoped_to_user(client):
    client.post("/sops", json={"title": "A"})
    assert len(client.get("/sops").json()["sops"]) == 1


def test_cross_user_access_is_404(client):
    sid = client.post("/sops", json={"title": "Private"}).json()["id"]
    from app.server import app

    with TestClient(app) as other:  # fresh cookie jar = different anonymous user
        assert other.get(f"/sops/{sid}").status_code == 404
        assert other.post(f"/sops/{sid}/versions", json={"content": "x"}).status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_sop_api.py -v`
Expected: FAIL — 404/405 on `/sops` (routes not defined yet)

- [ ] **Step 3: Wire `init_db` into the lifespan**

In `backend/app/server.py`, update the imports near the top — add to the existing `from . import auth, memory` line so it reads:
```python
from . import auth, memory, sop_store
from .agent import build_graph
from .config import settings
from .tools.sop import analyze_sop
```
Then in the `lifespan` function, add the SOP DB init right after `settings.require_key()`:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph
    settings.require_key()
    sop_store.init_db()
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db) as saver:
        _graph = build_graph(saver)
        yield
    _graph = None
```

- [ ] **Step 4: Add request models and endpoints**

In `backend/app/server.py`, add a `JSONResponse` import to the FastAPI responses (there is already a local `from fastapi.responses import JSONResponse` inside `/session`; add a module-level one near the other imports):
```python
from fastapi.responses import JSONResponse
```
Then append the SOP endpoints at the end of the file:
```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_sop_api.py -v`
Expected: PASS (4 passed). (Requires `NVIDIA_API_KEY` in `backend/.env` — the lifespan calls `settings.require_key()`; it is present.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/server.py backend/tests/test_sop_api.py
git commit -m "F4: cookie-scoped SOP REST API + lifespan init + tests"
```

---

### Task 5: Agent tools (`review_sop`, `list_my_sops`)

**Files:**
- Modify: `backend/app/tools/sop.py` (add inner functions + `@tool` wrappers)
- Modify: `backend/app/tools/__init__.py` (export)
- Modify: `backend/app/agent.py` (import + `TOOLS`)
- Test: `backend/tests/test_sop_tools.py`

**Interfaces:**
- Consumes: `sop_store.*`, `analyze_sop`, `langgraph.prebuilt.InjectedState`.
- Produces: inner `_review_sop(user_id, title=None) -> dict`, `_list_my_sops(user_id) -> dict`; tools `review_sop`, `list_my_sops` (return JSON strings); both exported from `app.tools`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_sop_tools.py`:
```python
import pytest

from app import config, sop_store
from app.tools import sop as sop_mod


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SOP_DB_PATH", str(tmp_path / "t.db"))
    sop_store.init_db()


def _add(user, title, content):
    s = sop_store.create_sop(user, title)
    sop_store.add_version(user, s["id"], content, sop_mod.analyze_sop(content))
    return s


def test_review_sop_no_sop(seeded):
    assert "error" in sop_mod._review_sop("u1")


def test_review_sop_single(seeded):
    _add("u1", "CMU", "I want this program because my goal is research. " * 5)
    out = sop_mod._review_sop("u1")
    assert out["sop_title"] == "CMU"
    assert "analysis" in out and "draft" in out


def test_review_sop_needs_title_when_multiple(seeded):
    _add("u1", "CMU", "x")
    _add("u1", "MIT", "y")
    out = sop_mod._review_sop("u1")
    assert out.get("need_title") is True
    assert set(out["available"]) == {"CMU", "MIT"}


def test_review_sop_by_title_substring(seeded):
    _add("u1", "CMU Robotics", "x")
    _add("u1", "MIT EECS", "y")
    assert sop_mod._review_sop("u1", "mit")["sop_title"] == "MIT EECS"


def test_list_my_sops(seeded):
    _add("u1", "CMU", "x")
    out = sop_mod._list_my_sops("u1")
    assert [s["title"] for s in out["sops"]] == ["CMU"]


def test_tool_names():
    assert sop_mod.review_sop.name == "review_sop"
    assert sop_mod.list_my_sops.name == "list_my_sops"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_sop_tools.py -v`
Expected: FAIL — `AttributeError: module 'app.tools.sop' has no attribute '_review_sop'`

- [ ] **Step 3: Add inner functions + tool wrappers**

First add these imports to `backend/app/tools/sop.py` — the `from typing import Annotated` goes at the very top, and the three import lines join the existing import group (after `from .. import config`; note `json` and `re` are already imported there):
```python
from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from .. import config, sop_store
```
(Replace the existing `from .. import config` line with `from .. import config, sop_store`.)

Then append the functions to the end of `backend/app/tools/sop.py`:
```python
def _list_my_sops(user_id: str) -> dict:
    return {"sops": sop_store.list_sops(user_id)}


def _review_sop(user_id: str, title: str | None = None) -> dict:
    sops = sop_store.list_sops(user_id)
    if not sops:
        return {"error": "No SOP found. Ask the student to start one in the SOP workspace."}

    if title:
        t = title.strip().lower()
        chosen = next((s for s in sops if s["title"].strip().lower() == t), None)
        if chosen is None:
            chosen = next((s for s in sops if t in s["title"].strip().lower()), None)
        if chosen is None:
            return {"error": f"No SOP titled '{title}'.", "available": [s["title"] for s in sops]}
    elif len(sops) == 1:
        chosen = sops[0]
    else:
        return {"need_title": True, "available": [s["title"] for s in sops]}

    latest = sop_store.get_latest_version(user_id, chosen["id"])
    if latest is None:
        return {"error": f"'{chosen['title']}' has no saved draft yet.", "sop_title": chosen["title"]}
    return {
        "sop_title": chosen["title"],
        "analysis": analyze_sop(latest["content"]),
        "draft": latest["content"],
    }


@tool
def review_sop(
    title: str | None = None,
    user_id: Annotated[str, InjectedState("user_id")] = "",
) -> str:
    """Review the student's own saved SOP draft and return analysis to coach from.

    Call this when the student wants feedback on their Statement of Purpose. If
    they have one SOP, omit `title`. If they have several and you're unsure which,
    call list_my_sops first or pass the `title`.

    Args:
        title: Which SOP to review (by its title), e.g. "CMU Robotics". Omit if
            the student has only one.

    Returns a JSON string with the SOP title, the deterministic analysis
    (length, clichés, long sentences, structure signals) and the draft text.
    Use it to ask Socratic questions and give grounded feedback — NEVER rewrite
    the SOP for the student.
    """
    return json.dumps(_review_sop(user_id, title))


@tool
def list_my_sops(user_id: Annotated[str, InjectedState("user_id")] = "") -> str:
    """List the student's saved SOPs (titles + last-updated). Use to orient
    before reviewing when the student has more than one SOP."""
    return json.dumps(_list_my_sops(user_id))
```

- [ ] **Step 4: Export the tools**

Replace `backend/app/tools/__init__.py` with:
```python
"""Agent tools (F2+)."""

from .roi import estimate_roi, roi_breakdown
from .shortlist import shortlist_universities
from .sop import list_my_sops, review_sop

__all__ = [
    "shortlist_universities",
    "estimate_roi",
    "roi_breakdown",
    "review_sop",
    "list_my_sops",
]
```

- [ ] **Step 5: Register the tools in the agent**

In `backend/app/agent.py`, change the tools import:
```python
from .tools import estimate_roi, list_my_sops, review_sop, roi_breakdown, shortlist_universities
```
and the `TOOLS` list:
```python
TOOLS = [shortlist_universities, estimate_roi, roi_breakdown, review_sop, list_my_sops]
```

- [ ] **Step 6: Run the suite and verify tool registration**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_sop_tools.py -v`
Expected: PASS (6 passed)

Run: `cd backend && ./.venv/Scripts/python -c "import sys; sys.path.insert(0,'.'); from app.agent import TOOLS; print([t.name for t in TOOLS])"`
Expected: `['shortlist_universities', 'estimate_roi', 'roi_breakdown', 'review_sop', 'list_my_sops']`

- [ ] **Step 7: Commit**

```bash
git add backend/app/tools/sop.py backend/app/tools/__init__.py backend/app/agent.py backend/tests/test_sop_tools.py
git commit -m "F4: review_sop + list_my_sops agent tools (InjectedState) + register"
```

---

### Task 6: System-prompt "SOP COACH" block

**Files:**
- Modify: `backend/app/prompts.py`
- Test: `backend/tests/test_prompt.py` (extend)

**Interfaces:** Produces an updated `SYSTEM_PROMPT` that documents `review_sop`/`list_my_sops` and the never-write-it coaching rule.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_prompt.py`:
```python
def test_prompt_mentions_sop_tools():
    assert "review_sop" in SYSTEM_PROMPT
    assert "list_my_sops" in SYSTEM_PROMPT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_prompt.py -v`
Expected: FAIL — `assert 'review_sop' in SYSTEM_PROMPT`

- [ ] **Step 3: Add the coaching block to the prompt**

In `backend/app/prompts.py`, the ROI tools paragraph ends with the line:
```python
sensitivity grid as a small markdown table (tenure rows x rate columns).
```
Directly **after** that line and **before** the blank line preceding `BOUNDARIES:`, paste these lines *inside the same triple-quoted string* (match the existing `\`-continuation style; do not add quotes):
```python
- review_sop / list_my_sops: the student writes their Statement of Purpose in \
the SOP workspace; these tools read their saved draft. Call review_sop when the \
student wants SOP feedback (call list_my_sops first if they have several and \
you're unsure which). Coach SOCRATICALLY: use the analysis (clichés, length, \
missing "why this program") AND what you remember about them (their real \
internship, CGPA, target) to ask pointed questions that make THEM write better. \
NEVER write or rewrite the SOP for them — universities detect AI-written SOPs, \
and the words must be the student's own. Critique and question; do not author.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_prompt.py -v`
Expected: PASS

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && ./.venv/Scripts/python -m pytest -q`
Expected: PASS (all F2/F3/F4 backend tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/prompts.py backend/tests/test_prompt.py
git commit -m "F4: teach the agent the SOP coaching tools + never-write rule"
```

---

### Task 7: Frontend `/sop` workspace

**Files:**
- Create: `sarthi-web/src/lib/sop.ts`
- Create: `sarthi-web/src/app/sop/page.tsx`
- Modify: `sarthi-web/src/app/page.tsx` (add a nav link to `/sop`)

**Interfaces:** Consumes the REST API from Task 4 via `/api/agent/sops` (the existing rewrite). Verified manually.

- [ ] **Step 1: Read the Next.js 16 docs first**

This repo runs Next.js 16 with breaking changes (`sarthi-web/AGENTS.md`). Before writing components, skim the App Router client-component and routing docs under `sarthi-web/node_modules/next/dist/docs/`. Heed any deprecation notices. Use `"use client"` (these are interactive client components).

- [ ] **Step 2: Create the API client**

Create `sarthi-web/src/lib/sop.ts`:
```ts
const BASE = "/api/agent";

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export type SopMeta = {
  id: number;
  title: string;
  created_at: string;
  latest_version_id: number | null;
  updated_at: string | null;
  word_count: number | null;
};

export type Analysis = {
  word_count: number;
  paragraph_count: number;
  length_flag: "short" | "ok" | "long";
  target_words: [number, number];
  cliche_hits: { phrase: string; count: number }[];
  long_sentences: { text_preview: string; word_count: number }[];
  structure_signals: { mentions_program: boolean; mentions_goal: boolean; gives_reasons: boolean };
  note: string;
};

export type Version = {
  id: number;
  content: string;
  analysis: Analysis;
  created_at: string;
  word_count: number;
};

export const listSops = () =>
  fetch(`${BASE}/sops`, { credentials: "include" }).then(j<{ sops: SopMeta[] }>).then((d) => d.sops);

export const createSop = (title: string) =>
  fetch(`${BASE}/sops`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ title }),
  }).then(j<SopMeta>);

export const getSop = (id: number) =>
  fetch(`${BASE}/sops/${id}`, { credentials: "include" }).then(
    j<{ sop: SopMeta; latest: Version | null }>,
  );

export const saveVersion = (id: number, content: string) =>
  fetch(`${BASE}/sops/${id}/versions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ content }),
  }).then(j<{ version: { id: number; created_at: string }; analysis: Analysis }>);

export const listVersions = (id: number) =>
  fetch(`${BASE}/sops/${id}/versions`, { credentials: "include" })
    .then(j<{ versions: { id: number; created_at: string; word_count: number }[] }>)
    .then((d) => d.versions);

export const getVersion = (sopId: number, vId: number) =>
  fetch(`${BASE}/sops/${sopId}/versions/${vId}`, { credentials: "include" })
    .then(j<{ version: Version }>)
    .then((d) => d.version);
```

- [ ] **Step 3: Create the workspace page**

Create `sarthi-web/src/app/sop/page.tsx`:
```tsx
"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  type Analysis,
  type SopMeta,
  createSop,
  getSop,
  getVersion,
  listSops,
  listVersions,
  saveVersion,
} from "../../lib/sop";

type VersionMeta = { id: number; created_at: string; word_count: number };

function Flag({ flag }: { flag: Analysis["length_flag"] }) {
  const label = flag === "ok" ? "On target" : flag === "short" ? "Too short" : "Too long";
  const tone = flag === "ok" ? "text-saffron" : "text-saffron-deep";
  return <span className={`text-xs font-medium ${tone}`}>{label}</span>;
}

function Readout({ a }: { a: Analysis }) {
  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center gap-3">
        <span className="text-cream">{a.word_count} words</span>
        <span className="text-muted">·</span>
        <span className="text-muted">
          target {a.target_words[0]}–{a.target_words[1]}
        </span>
        <Flag flag={a.length_flag} />
      </div>
      <div className="flex flex-wrap gap-2">
        {(["mentions_program", "mentions_goal", "gives_reasons"] as const).map((k) => (
          <span
            key={k}
            className={`rounded-full border px-2 py-0.5 text-xs ${
              a.structure_signals[k]
                ? "border-saffron/50 text-cream"
                : "border-ink-3 text-muted line-through"
            }`}
          >
            {k.replace("mentions_", "").replace("gives_", "")}
          </span>
        ))}
      </div>
      {a.cliche_hits.length > 0 && (
        <div>
          <p className="text-muted">Clichés to rewrite in your own words:</p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {a.cliche_hits.map((c) => (
              <span key={c.phrase} className="rounded bg-saffron/12 px-2 py-0.5 text-xs text-saffron">
                “{c.phrase}”{c.count > 1 ? ` ×${c.count}` : ""}
              </span>
            ))}
          </div>
        </div>
      )}
      {a.long_sentences.length > 0 && (
        <div>
          <p className="text-muted">{a.long_sentences.length} long sentence(s) (&gt;40 words):</p>
          <ul className="mt-1 space-y-1">
            {a.long_sentences.map((s, i) => (
              <li key={i} className="text-xs text-cream/80">
                {s.text_preview} <span className="text-muted">({s.word_count}w)</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-[11px] text-muted">{a.note}</p>
    </div>
  );
}

export default function SopWorkspace() {
  const [sops, setSops] = useState<SopMeta[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [content, setContent] = useState("");
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [versions, setVersions] = useState<VersionMeta[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshSops = useCallback(async () => {
    try {
      setSops(await listSops());
    } catch {
      setError("Couldn't load your SOPs. Is the agent running?");
    }
  }, []);

  useEffect(() => {
    fetch("/api/agent/session", { credentials: "include" })
      .catch(() => {})
      .finally(refreshSops);
  }, [refreshSops]);

  const open = useCallback(async (id: number) => {
    setActiveId(id);
    setError(null);
    const [{ latest }, vs] = await Promise.all([getSop(id), listVersions(id)]);
    setContent(latest?.content ?? "");
    setAnalysis(latest?.analysis ?? null);
    setVersions(vs);
  }, []);

  async function onNew() {
    const title = window.prompt("Name this SOP (e.g. 'CMU Robotics'):")?.trim();
    if (!title) return;
    const sop = await createSop(title);
    await refreshSops();
    await open(sop.id);
  }

  async function onSave() {
    if (activeId === null) return;
    setSaving(true);
    setError(null);
    try {
      const { analysis: a } = await saveVersion(activeId, content);
      setAnalysis(a);
      setVersions(await listVersions(activeId));
      await refreshSops();
    } catch {
      setError("Save failed. Try again.");
    } finally {
      setSaving(false);
    }
  }

  async function onRestore(vId: number) {
    if (activeId === null) return;
    const v = await getVersion(activeId, vId);
    setContent(v.content);
  }

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex items-center gap-3 border-b border-ink-3 px-5 py-3">
        <span className="font-display text-lg font-semibold tracking-tight">SOP Workspace</span>
        <span className="font-deva text-saffron">सारथी</span>
        <Link href="/" className="ml-auto text-sm text-muted hover:text-cream">
          ← Back to chat
        </Link>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* SOP list */}
        <aside className="w-56 shrink-0 overflow-y-auto border-r border-ink-3 p-3">
          <button
            onClick={onNew}
            className="mb-3 w-full rounded-lg border border-saffron/50 px-3 py-1.5 text-sm text-saffron hover:bg-saffron/10"
          >
            + New SOP
          </button>
          <ul className="space-y-1">
            {sops.map((s) => (
              <li key={s.id}>
                <button
                  onClick={() => open(s.id)}
                  className={`w-full truncate rounded-lg px-3 py-2 text-left text-sm ${
                    s.id === activeId ? "bg-ink-2 text-cream" : "text-muted hover:bg-ink-2/60"
                  }`}
                >
                  {s.title}
                  <span className="block text-[11px] text-muted">
                    {s.word_count != null ? `${s.word_count} words` : "no draft yet"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        {/* Editor + analysis */}
        <main className="flex min-w-0 flex-1 flex-col p-5">
          {activeId === null ? (
            <div className="m-auto max-w-sm text-center text-muted">
              <p className="font-display text-2xl text-cream">Your SOP, your words.</p>
              <p className="mt-3 text-sm">
                Create an SOP, draft it here, and ask SARTHI in chat to coach you — she questions and
                critiques, but never writes it for you.
              </p>
            </div>
          ) : (
            <>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Write your Statement of Purpose here…"
                className="min-h-0 flex-1 resize-none rounded-xl border border-ink-3 bg-ink-2 p-4 text-cream outline-none focus:border-saffron/60"
              />
              <div className="mt-3 flex items-center gap-3">
                <button
                  onClick={onSave}
                  disabled={saving}
                  className="rounded-lg bg-saffron px-4 py-1.5 text-sm font-medium text-ink hover:bg-saffron-deep disabled:opacity-50"
                >
                  {saving ? "Saving…" : "Save version"}
                </button>
                <Link href="/" className="text-sm text-muted hover:text-cream">
                  Ask SARTHI to review this →
                </Link>
              </div>
              {error && <p className="mt-2 text-sm text-saffron-deep">{error}</p>}
              {analysis && (
                <div className="mt-4 rounded-xl border border-ink-3 bg-ink-2/50 p-4">
                  <Readout a={analysis} />
                </div>
              )}
            </>
          )}
        </main>

        {/* Version history */}
        <aside className="w-52 shrink-0 overflow-y-auto border-l border-ink-3 p-3">
          <p className="mb-2 text-xs uppercase tracking-wide text-muted">History</p>
          <ul className="space-y-1">
            {versions.map((v) => (
              <li key={v.id} className="flex items-center justify-between gap-2 text-sm">
                <span className="text-muted">{new Date(v.created_at).toLocaleString()}</span>
                <button onClick={() => onRestore(v.id)} className="text-saffron hover:underline">
                  restore
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Add a nav link from chat to the SOP workspace**

In `sarthi-web/src/app/page.tsx`, add the import at the top (after the existing imports):
```tsx
import Link from "next/link";
```
Then in the header, replace this line:
```tsx
          <span className="ml-auto hidden text-xs text-muted sm:block">from dream to degree</span>
```
with:
```tsx
          <Link href="/sop" className="ml-auto text-sm text-muted hover:text-cream">
            SOP Workspace →
          </Link>
```

- [ ] **Step 5: Manual verification**

Start backend and frontend (two terminals):
```bash
cd backend && SARTHI_MODEL_DEFAULT=meta/llama-3.3-70b-instruct ./.venv/Scripts/python -m uvicorn app.server:app --port 8000
```
```bash
cd sarthi-web && npm run dev
```
In the browser at `http://localhost:3000`:
- Click "SOP Workspace →"; create a New SOP ("CMU Robotics").
- Paste/type a draft; click "Save version"; confirm the analysis readout shows word count, length flag, cliché chips (try including "since childhood"), and structure signals.
- Save again; confirm a second entry appears in History and "restore" repopulates the editor.
- Reload the page; confirm the SOP list and latest draft persist (cookie identity).
- Confirm cross-navigation between `/` and `/sop` works.

If a frontend dep was added, delete `.next` before restarting (stale RSC manifest — see CLAUDE.md). To free port 3000 if it lingers: PowerShell `Get-NetTCPConnection -LocalPort 3000 | ... Stop-Process`.

- [ ] **Step 6: Commit**

```bash
git add sarthi-web/src/lib/sop.ts sarthi-web/src/app/sop/page.tsx sarthi-web/src/app/page.tsx
git commit -m "F4: /sop workspace UI (editor, analysis readout, version history)"
```

---

### Task 8: End-to-end coaching check + docs

**Files:**
- Create: (scratch) an e2e script under the scratchpad — not committed
- Modify: `CLAUDE.md` (§0 + §14)

**Interfaces:** none new. Verifies the agent calls `review_sop` and coaches without rewriting.

- [ ] **Step 1: Write the e2e script (scratchpad)**

Create `<scratchpad>/e2e_sop.py` (use the session scratchpad dir):
```python
"""Live e2e for F4: does the agent review a seeded SOP and coach (not write it)?"""
import asyncio
import os
import sys

os.environ.setdefault("SARTHI_MODEL_DEFAULT", "meta/llama-3.3-70b-instruct")
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from app import sop_store  # noqa: E402
from app.agent import build_graph  # noqa: E402
from app.tools.sop import analyze_sop  # noqa: E402


async def main():
    sop_store.init_db()
    uid = "e2e-sop-user"
    s = sop_store.create_sop(uid, "CMU Robotics")
    draft = (
        "Since childhood I have always been passionate about robots. "
        "I want to join your renowned university. " * 8
    )
    sop_store.add_version(uid, s["id"], draft, analyze_sop(draft))

    graph = build_graph(MemorySaver())
    cfg = {"configurable": {"thread_id": uid}}
    state = {
        "messages": [HumanMessage(content="Can you review my SOP and tell me what to fix?")],
        "user_id": uid,
    }
    result = await graph.ainvoke(state, config=cfg)
    calls = [tc["name"] for m in result["messages"] if isinstance(m, AIMessage) for tc in (m.tool_calls or [])]
    final = next((m.content for m in reversed(result["messages"]) if isinstance(m, AIMessage) and m.content and not m.tool_calls), "")
    print("TOOL CALLS:", calls)
    print("REPLY (first 700 chars):\n", final[:700])


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run it and confirm behavior**

Run: `cd backend && ./.venv/Scripts/python <scratchpad>/e2e_sop.py`
Expected: `TOOL CALLS` includes `review_sop`; the reply asks Socratic questions / flags the clichés ("since childhood", "renowned university") and does NOT output a rewritten SOP. (If the model rewrites it wholesale, strengthen the prompt's never-write rule and re-run.)

- [ ] **Step 3: Update CLAUDE.md**

In `CLAUDE.md`, update the §0 "Next up" line (currently F4) to mark F4 done and point to F5, and in §14 change `[ ] F4 SOP — next` to `[x] F4 SOP — done · [ ] F5 Loan — next`. Note the new `sarthi_sop.db` (git-ignored via `*.db`) and the `/sop` route.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "F4: SOP Co-Pilot done; update CLAUDE.md (next: F5)"
```

---

## Post-implementation
- Full backend suite green (`./.venv/Scripts/python -m pytest -q`).
- Frontend manually verified per Task 7 Step 5.
- Consider merging `f4-sop-copilot` → `main` (superpowers:finishing-a-development-branch).
