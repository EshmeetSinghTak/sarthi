# F6 — Document Auto-Fill into Loan Application Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SARTHI pre-fills a loan application from the student's free-text memory, shows it for review/edit on a `/apply` page with field-level provenance, and lets them tick documents and "submit" (demo).

**Architecture:** A `app/application.py` module owns the schema, LLM extraction (free utility model, behind a monkeypatchable seam), and draft assembly with provenance + completeness. A user-scoped `app/app_store.py` persists one editable application per user. A `draft_application` agent tool kicks it off from chat; cookie-scoped REST endpoints feed the schema-driven `/apply` page.

**Tech Stack:** Python 3.14, OpenAI client (NVIDIA utility model `llama-3.1-8b`), FastAPI + Pydantic, SQLite (stdlib), pytest (sync); Next.js 16 + React 19 + Tailwind v4 + framer-motion.

## Global Constraints

- **No paid LLMs / no Claude.** Extraction uses the free NVIDIA utility model (`settings.utility_model`).
- **Never hardcode tunables.** Field/document definitions live in `backend/data/application_schema.json`; DB/schema paths in `config.py`. No field lists hardcoded in logic or the React component (the page renders from the schema in the API response).
- **Honesty:** auto-fill proposes the student's *own* stated facts; only `extractable:true` fields can be auto-filled. "Submit" is a demo (no lender API, no document storage); the reference is labeled a demo.
- **`user_id` from the signed cookie**, never the body (REST uses `auth.resolve_user` + `_with_cookie`; the tool uses `InjectedState("user_id")`).
- **Extraction must never break the flow** — on any model/parse error, `extract_fields` returns `{}`.
- Tests: plain `pytest`, no new deps; async tested via `asyncio.run` where needed. Backend: `cd backend && ./.venv/Scripts/python -m pytest -q`. Frontend: `cd sarthi-web && npx tsc --noEmit` and `npm run build`.
- Windows: scripts printing model/unicode output need `sys.stdout.reconfigure(encoding="utf-8")`.

---

## File Structure

**New:**
- `backend/data/application_schema.json` — sections/fields (key,label,type,extractable,required) + documents.
- `backend/app/application.py` — schema load, `extract_fields`, `completeness`, `build_draft`, `public_view`.
- `backend/app/app_store.py` — user-scoped SQLite persistence (one application/user).
- `backend/app/tools/application.py` — `@tool draft_application`.
- `backend/tests/test_application.py`, `test_app_store.py`, `test_application_api.py`, `test_application_tool.py`.
- `sarthi-web/src/lib/application.ts` — typed client.
- `sarthi-web/src/app/(app)/apply/page.tsx` — schema-driven review/edit page.

**Modified:**
- `backend/app/config.py` — `APPLICATION_SCHEMA_PATH`, `APPLICATION_DB_PATH`.
- `backend/app/prompts.py` — `APPLICATION_EXTRACT_PROMPT` + tool line in `SYSTEM_PROMPT`.
- `backend/app/tools/__init__.py`, `backend/app/agent.py` — register `draft_application`.
- `backend/app/server.py` — `init_db` for app_store + `/application` endpoints.
- `sarthi-web/src/lib/nav.ts`, `sarthi-web/src/components/AppShell.tsx` — `/apply` nav + `file` icon.
- `CLAUDE.md` — record F6.

---

## Task 1: Schema data file + config paths

**Files:**
- Create: `backend/data/application_schema.json`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `config.APPLICATION_SCHEMA_PATH: Path`, `config.APPLICATION_DB_PATH: str`; the schema JSON.

- [ ] **Step 1: Create the schema file**

Create `backend/data/application_schema.json`:

```json
{
  "note": "Fields SARTHI drafts from the student's own messages; verify before use.",
  "sections": [
    {
      "key": "personal",
      "title": "Personal",
      "fields": [
        {"key": "full_name", "label": "Full name", "type": "text", "extractable": true, "required": true},
        {"key": "date_of_birth", "label": "Date of birth", "type": "date", "extractable": false, "required": true},
        {"key": "city", "label": "City", "type": "text", "extractable": true, "required": false},
        {"key": "phone", "label": "Phone", "type": "tel", "extractable": false, "required": true},
        {"key": "email", "label": "Email", "type": "email", "extractable": false, "required": true}
      ]
    },
    {
      "key": "academic",
      "title": "Academic",
      "fields": [
        {"key": "current_degree", "label": "Current degree", "type": "text", "extractable": true, "required": false},
        {"key": "institution", "label": "Current institution", "type": "text", "extractable": true, "required": false},
        {"key": "cgpa", "label": "CGPA / %", "type": "text", "extractable": true, "required": false},
        {"key": "target_course", "label": "Target course", "type": "text", "extractable": true, "required": true},
        {"key": "target_country", "label": "Target country", "type": "text", "extractable": true, "required": true},
        {"key": "target_universities", "label": "Target universities", "type": "text", "extractable": true, "required": false}
      ]
    },
    {
      "key": "financial",
      "title": "Loan & co-applicant",
      "fields": [
        {"key": "loan_amount_inr_lakh", "label": "Loan amount (₹ lakh)", "type": "number", "extractable": true, "required": true},
        {"key": "co_applicant_name", "label": "Co-applicant name", "type": "text", "extractable": false, "required": true},
        {"key": "co_applicant_relation", "label": "Co-applicant relation", "type": "text", "extractable": false, "required": true},
        {"key": "co_applicant_income_inr_lakh", "label": "Co-applicant income / yr (₹ lakh)", "type": "number", "extractable": true, "required": true},
        {"key": "collateral_value_inr_lakh", "label": "Collateral value (₹ lakh)", "type": "number", "extractable": true, "required": false}
      ]
    }
  ],
  "documents": [
    {"key": "passport", "label": "Passport"},
    {"key": "marksheets", "label": "Academic marksheets"},
    {"key": "admission_letter", "label": "Admission / offer letter"},
    {"key": "income_proof", "label": "Co-applicant income proof"},
    {"key": "coapplicant_kyc", "label": "Co-applicant KYC (PAN / Aadhaar)"},
    {"key": "bank_statements", "label": "Bank statements (6 months)"}
  ]
}
```

- [ ] **Step 2: Write the failing test**

Add to `backend/tests/test_config.py`:

```python
def test_application_paths_present():
    assert config.APPLICATION_SCHEMA_PATH.exists()
    assert config.APPLICATION_DB_PATH


def test_application_schema_shape():
    import json
    schema = json.loads(config.APPLICATION_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["sections"] and schema["documents"]
    for section in schema["sections"]:
        assert section["key"] and section["title"]
        for f in section["fields"]:
            assert {"key", "label", "type", "extractable", "required"} <= set(f)
    # at least one extractable and one non-extractable field exist
    fields = [f for s in schema["sections"] for f in s["fields"]]
    assert any(f["extractable"] for f in fields)
    assert any(not f["extractable"] for f in fields)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_config.py -q`
Expected: FAIL — `AttributeError: ... 'APPLICATION_SCHEMA_PATH'`.

- [ ] **Step 4: Add config paths**

In `backend/app/config.py`, after the F5 loan block, append:

```python
# --- F6 Document Auto-Fill (application schema + draft store) ---
APPLICATION_SCHEMA_PATH = BACKEND_DIR / "data" / "application_schema.json"
APPLICATION_DB_PATH: str = os.getenv("SARTHI_APPLICATION_DB", str(BACKEND_DIR / "sarthi_application.db"))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_config.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/data/application_schema.json backend/app/config.py backend/tests/test_config.py
git commit -m "feat(apply): application schema data file + config paths"
```

---

## Task 2: Extraction + draft assembly

**Files:**
- Create: `backend/app/application.py`
- Modify: `backend/app/prompts.py`
- Test: `backend/tests/test_application.py`

**Interfaces:**
- Consumes: `config.APPLICATION_SCHEMA_PATH`; `settings.utility_model`; `memory.all_facts` (Task uses it in build_draft).
- Produces: `SCHEMA`, `FIELD_KEYS`, `EXTRACTABLE_KEYS`, `DOCUMENT_KEYS`; `completeness(fields: dict) -> dict`; `extract_fields(facts: list[str]) -> dict`; `build_draft(user_id: str) -> dict`; `public_view(stored: dict) -> dict`; internal `_call_model(prompt: str) -> str` (monkeypatchable seam).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_application.py`:

```python
import json

from app import application


def test_completeness_counts_nonempty():
    c = application.completeness({"full_name": "Priya", "city": "", "cgpa": "7.8"})
    assert c == {"filled": 2, "total": len(application.FIELD_KEYS)}


def test_extract_fields_filters_to_extractable_and_nonempty(monkeypatch):
    # Model returns an extra non-extractable key and an empty value — both dropped.
    canned = json.dumps({
        "full_name": "Priya Sharma",
        "phone": "9999999999",          # not extractable -> dropped
        "target_course": "",            # empty -> dropped
        "loan_amount_inr_lakh": "45",
    })
    monkeypatch.setattr(application, "_call_model", lambda prompt: canned)
    out = application.extract_fields(["Name is Priya Sharma", "Budget around 45 lakh"])
    assert out == {"full_name": "Priya Sharma", "loan_amount_inr_lakh": "45"}


def test_extract_fields_empty_facts_skips_model():
    assert application.extract_fields([]) == {}


def test_extract_fields_swallows_model_errors(monkeypatch):
    def boom(prompt):
        raise RuntimeError("model down")
    monkeypatch.setattr(application, "_call_model", boom)
    assert application.extract_fields(["something"]) == {}


def test_build_draft_shape(monkeypatch):
    monkeypatch.setattr(application.memory, "all_facts", lambda uid: ["Name is Priya"])
    monkeypatch.setattr(application, "extract_fields", lambda facts: {"full_name": "Priya"})
    draft = application.build_draft("u1")
    assert draft["fields"] == {"full_name": "Priya"}
    assert draft["ai_filled"] == ["full_name"]
    assert draft["status"] == "draft"
    assert draft["reference"] is None
    assert set(draft["documents"]) == set(application.DOCUMENT_KEYS)
    assert all(v is False for v in draft["documents"].values())


def test_public_view_adds_schema_and_completeness():
    stored = {
        "fields": {"full_name": "Priya"}, "ai_filled": ["full_name"],
        "documents": {k: False for k in application.DOCUMENT_KEYS},
        "status": "draft", "reference": None,
    }
    view = application.public_view(stored)
    assert view["schema"]["sections"] and view["schema"]["documents"]
    assert view["completeness"] == {"filled": 1, "total": len(application.FIELD_KEYS)}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_application.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.application'`.

- [ ] **Step 3: Add the extraction prompt**

In `backend/app/prompts.py`, append at the end:

```python
# F6 — extract structured loan-application fields from a student's stored memory
# facts, using the fast utility model. Output is a JSON object of field->value.
APPLICATION_EXTRACT_PROMPT = """You fill a study-abroad loan application from a \
student's known facts, for a mentoring app.

Return ONLY a JSON object mapping field keys to values, using ONLY these keys:
{keys}

Rules:
- Include a key ONLY if the facts clearly state it. Omit anything you must guess.
- Values are short strings. For amounts in INR lakh, give just the number (e.g. "45").
- Do not invent data. If unsure, omit the key.

Student's known facts:
{facts}

JSON object:"""
```

- [ ] **Step 4: Write `application.py`**

Create `backend/app/application.py`:

```python
"""F6 — assemble a loan application from the student's long-term memory.

extract_fields() is the only non-deterministic part (one utility-model call,
isolated behind _call_model for testing). Everything else is pure. We never
invent data: only fields the facts clearly state are filled, and only fields
marked extractable in the schema can be auto-filled at all.
"""

import json
import re

from openai import OpenAI

from . import config, memory
from .config import settings
from .prompts import APPLICATION_EXTRACT_PROMPT

SCHEMA = json.loads(config.APPLICATION_SCHEMA_PATH.read_text(encoding="utf-8"))
_FIELDS = [f for s in SCHEMA["sections"] for f in s["fields"]]
FIELD_KEYS = [f["key"] for f in _FIELDS]
EXTRACTABLE_KEYS = [f["key"] for f in _FIELDS if f["extractable"]]
DOCUMENT_KEYS = [d["key"] for d in SCHEMA["documents"]]

_client = OpenAI(api_key=settings.nvidia_api_key, base_url=settings.nvidia_base_url)


def _call_model(prompt: str) -> str:
    """One utility-model completion. Isolated so tests can monkeypatch it."""
    resp = _client.chat.completions.create(
        model=settings.utility_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=512,
    )
    return resp.choices[0].message.content or ""


def extract_fields(facts: list[str]) -> dict:
    """Map free-text memory facts -> structured fields (extractable keys only)."""
    facts = [f for f in (facts or []) if f and f.strip()]
    if not facts:
        return {}
    prompt = APPLICATION_EXTRACT_PROMPT.format(
        keys=", ".join(EXTRACTABLE_KEYS), facts="\n".join(f"- {f}" for f in facts)
    )
    try:
        text = _call_model(prompt)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        raw = json.loads(match.group(0))
    except Exception:
        return {}
    allowed = set(EXTRACTABLE_KEYS)
    return {
        k: str(v).strip()
        for k, v in raw.items()
        if k in allowed and str(v).strip()
    }


def completeness(fields: dict) -> dict:
    filled = sum(1 for k in FIELD_KEYS if str(fields.get(k, "")).strip())
    return {"filled": filled, "total": len(FIELD_KEYS)}


def build_draft(user_id: str) -> dict:
    """Build a fresh application draft from the user's memory facts."""
    fields = extract_fields(memory.all_facts(user_id))
    return {
        "fields": fields,
        "ai_filled": list(fields.keys()),
        "documents": {k: False for k in DOCUMENT_KEYS},
        "status": "draft",
        "reference": None,
    }


def public_view(stored: dict) -> dict:
    """Stored application + schema + live completeness, for the API/page."""
    return {
        **stored,
        "schema": {"sections": SCHEMA["sections"], "documents": SCHEMA["documents"]},
        "completeness": completeness(stored.get("fields", {})),
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_application.py -q`
Expected: PASS (6 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/application.py backend/app/prompts.py backend/tests/test_application.py
git commit -m "feat(apply): memory->application extraction + draft assembly"
```

---

## Task 3: Persistence store

**Files:**
- Create: `backend/app/app_store.py`
- Modify: `backend/app/server.py` (init the DB in lifespan)
- Test: `backend/tests/test_app_store.py`

**Interfaces:**
- Produces: `init_db()`; `get(user_id) -> dict | None`; `get_or_create(user_id, builder) -> dict`; `save(user_id, fields, documents) -> dict`; `submit(user_id, reference) -> dict | None`. Stored dict shape: `{fields, ai_filled, documents, status, reference, created_at, updated_at}`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_app_store.py`:

```python
from app import app_store


def _builder():
    return {
        "fields": {"full_name": "Priya"},
        "ai_filled": ["full_name"],
        "documents": {"passport": False},
        "status": "draft",
        "reference": None,
    }


def test_get_or_create_persists_then_returns_same(tmp_path, monkeypatch):
    monkeypatch.setattr(app_store.config, "APPLICATION_DB_PATH", str(tmp_path / "a.db"))
    app_store.init_db()
    first = app_store.get_or_create("u1", _builder)
    assert first["fields"]["full_name"] == "Priya"
    # second call does NOT rebuild (builder would raise if called)
    second = app_store.get_or_create("u1", lambda: (_ for _ in ()).throw(AssertionError("rebuilt")))
    assert second["fields"]["full_name"] == "Priya"


def test_save_updates_fields_and_documents(tmp_path, monkeypatch):
    monkeypatch.setattr(app_store.config, "APPLICATION_DB_PATH", str(tmp_path / "a.db"))
    app_store.init_db()
    app_store.get_or_create("u1", _builder)
    saved = app_store.save("u1", {"full_name": "Priya S", "city": "Nagpur"}, {"passport": True})
    assert saved["fields"]["city"] == "Nagpur"
    assert saved["documents"]["passport"] is True
    assert saved["ai_filled"] == ["full_name"]  # unchanged


def test_submit_sets_status_and_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(app_store.config, "APPLICATION_DB_PATH", str(tmp_path / "a.db"))
    app_store.init_db()
    app_store.get_or_create("u1", _builder)
    done = app_store.submit("u1", "SARTHI-ABC123")
    assert done["status"] == "submitted"
    assert done["reference"] == "SARTHI-ABC123"


def test_isolation_between_users(tmp_path, monkeypatch):
    monkeypatch.setattr(app_store.config, "APPLICATION_DB_PATH", str(tmp_path / "a.db"))
    app_store.init_db()
    app_store.get_or_create("u1", _builder)
    assert app_store.get("u2") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_app_store.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.app_store'`.

- [ ] **Step 3: Write `app_store.py`**

Create `backend/app/app_store.py`:

```python
"""SQLite store for the loan application draft (F6).

One row per user (one application). Synchronous stdlib sqlite3, fresh connection
per call. Every read/write is scoped by user_id. DB path from
config.APPLICATION_DB_PATH.
"""

import json
import sqlite3
from datetime import datetime, timezone

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    user_id        TEXT PRIMARY KEY,
    fields_json    TEXT NOT NULL,
    ai_filled_json TEXT NOT NULL,
    documents_json TEXT NOT NULL,
    status         TEXT NOT NULL,
    reference      TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.APPLICATION_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "fields": json.loads(row["fields_json"]),
        "ai_filled": json.loads(row["ai_filled_json"]),
        "documents": json.loads(row["documents_json"]),
        "status": row["status"],
        "reference": row["reference"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get(user_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM applications WHERE user_id = ?", (user_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_or_create(user_id: str, builder) -> dict:
    existing = get(user_id)
    if existing is not None:
        return existing
    draft = builder()
    now = _now()
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO applications
               (user_id, fields_json, ai_filled_json, documents_json, status,
                reference, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                json.dumps(draft["fields"]),
                json.dumps(draft["ai_filled"]),
                json.dumps(draft["documents"]),
                draft["status"],
                draft["reference"],
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get(user_id)


def save(user_id: str, fields: dict, documents: dict) -> dict | None:
    conn = _connect()
    try:
        cur = conn.execute(
            """UPDATE applications
               SET fields_json = ?, documents_json = ?, updated_at = ?
               WHERE user_id = ?""",
            (json.dumps(fields), json.dumps(documents), _now(), user_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return get(user_id)


def submit(user_id: str, reference: str) -> dict | None:
    conn = _connect()
    try:
        cur = conn.execute(
            "UPDATE applications SET status = 'submitted', reference = ?, updated_at = ? WHERE user_id = ?",
            (reference, _now(), user_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return get(user_id)
```

- [ ] **Step 4: Initialize the DB on startup**

In `backend/app/server.py`, the lifespan currently calls `sop_store.init_db()`. Add the app_store import and init. Change:

```python
from . import auth, memory, sop_store
```

to:

```python
from . import app_store, auth, memory, sop_store
```

and in the `lifespan` function, after `sop_store.init_db()` add:

```python
    app_store.init_db()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_app_store.py -q`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/app_store.py backend/app/server.py backend/tests/test_app_store.py
git commit -m "feat(apply): user-scoped SQLite store for the application draft"
```

---

## Task 4: The `draft_application` agent tool

**Files:**
- Create: `backend/app/tools/application.py`
- Modify: `backend/app/tools/__init__.py`, `backend/app/agent.py`, `backend/app/prompts.py`
- Test: `backend/tests/test_application_tool.py`

**Interfaces:**
- Consumes: `application.build_draft`, `application.public_view`, `application.FIELD_KEYS`; `app_store.get_or_create`.
- Produces: `draft_application` tool (returns JSON string with `completeness`, `filled`, `missing`, `apply_url`).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_application_tool.py`:

```python
import json

from app import application, app_store
from app.tools import draft_application


def test_draft_application_returns_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(app_store.config, "APPLICATION_DB_PATH", str(tmp_path / "a.db"))
    app_store.init_db()
    monkeypatch.setattr(application, "build_draft",
                        lambda uid: {"fields": {"full_name": "Priya"}, "ai_filled": ["full_name"],
                                     "documents": {}, "status": "draft", "reference": None})
    out = draft_application.invoke({"user_id": "u1"})
    data = json.loads(out)
    assert data["completeness"]["filled"] == 1
    assert "full_name" in data["filled"]
    assert "email" in data["missing"]
    assert data["apply_url"] == "/apply"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_application_tool.py -q`
Expected: FAIL — `ImportError: cannot import name 'draft_application'`.

- [ ] **Step 3: Write the tool**

Create `backend/app/tools/application.py`:

```python
"""F6 — draft_application agent tool. Assembles/loads the student's loan
application draft from memory and reports how much is pre-filled."""

import json
from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from .. import app_store, application


@tool
def draft_application(user_id: Annotated[str, InjectedState("user_id")] = "") -> str:
    """Pre-fill the student's education-loan application from what you remember.

    Call this when the student is ready to apply for the loan, or asks to start /
    fill the loan application. It reads their saved profile facts and drafts the
    application, then reports how many fields were pre-filled and what's still
    needed.

    Returns a JSON string with completeness (filled/total), the list of pre-filled
    fields, the list of still-missing fields, and the page to finish on. Tell the
    student how much you pre-filled, name a couple of the missing items, and point
    them to the application page to review and submit. The values are drafted from
    their own messages — remind them to verify before submitting.
    """
    stored = app_store.get_or_create(user_id, lambda: application.build_draft(user_id))
    view = application.public_view(stored)
    fields = view["fields"]
    filled = [k for k in application.FIELD_KEYS if str(fields.get(k, "")).strip()]
    missing = [k for k in application.FIELD_KEYS if not str(fields.get(k, "")).strip()]
    return json.dumps({
        "completeness": view["completeness"],
        "filled": filled,
        "missing": missing,
        "status": view["status"],
        "apply_url": "/apply",
    })
```

- [ ] **Step 4: Register the tool**

In `backend/app/tools/__init__.py`, add the import and `__all__` entry:

```python
from .application import draft_application
```

and add `"draft_application"` to `__all__`.

In `backend/app/agent.py`, update the tools import and `TOOLS` list. Change:

```python
from .tools import (
    estimate_roi,
    list_my_sops,
    loan_offer,
    review_sop,
    roi_breakdown,
    shortlist_universities,
)

TOOLS = [shortlist_universities, estimate_roi, roi_breakdown, review_sop, list_my_sops, loan_offer]
```

to:

```python
from .tools import (
    draft_application,
    estimate_roi,
    list_my_sops,
    loan_offer,
    review_sop,
    roi_breakdown,
    shortlist_universities,
)

TOOLS = [
    shortlist_universities,
    estimate_roi,
    roi_breakdown,
    review_sop,
    list_my_sops,
    loan_offer,
    draft_application,
]
```

- [ ] **Step 5: Describe the tool in the system prompt**

In `backend/app/prompts.py`, inside `YOUR TOOLS:`, after the `loan_offer` bullet (before `BOUNDARIES:`), add:

```python
- draft_application: call this when the student is ready to apply or asks to \
start the loan application. It pre-fills the application from what you remember \
about them. Tell them how much you filled in (e.g. "I've pre-filled 9 of 13 from \
our chats"), mention a couple of the missing items, and point them to the \
application page to review and submit. Remind them the draft is from their own \
words — they should verify before submitting.
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_application_tool.py tests/test_prompt.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/tools/application.py backend/app/tools/__init__.py backend/app/agent.py backend/app/prompts.py backend/tests/test_application_tool.py
git commit -m "feat(apply): draft_application agent tool, registered and prompted"
```

---

## Task 5: REST endpoints

**Files:**
- Modify: `backend/app/server.py`
- Test: `backend/tests/test_application_api.py`

**Interfaces:**
- Consumes: `app_store`, `application` (Tasks 2,3); `auth.resolve_user`, `_with_cookie`.
- Produces: `GET /application`, `PUT /application`, `POST /application/submit`, all returning `{"application": public_view}`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_application_api.py`:

```python
from fastapi.testclient import TestClient

from app import application
from app.server import app


def test_get_creates_and_put_saves_and_submit(monkeypatch):
    # Avoid a live model call: stub extraction.
    monkeypatch.setattr(application, "extract_fields", lambda facts: {"full_name": "Priya"})
    with TestClient(app) as client:
        got = client.get("/application")
        assert got.status_code == 200
        view = got.json()["application"]
        assert "schema" in view and "completeness" in view

        put = client.put("/application", json={"fields": {"full_name": "Priya S", "city": "Nagpur"},
                                               "documents": {"passport": True}})
        assert put.status_code == 200
        assert put.json()["application"]["fields"]["city"] == "Nagpur"

        sub = client.post("/application/submit")
        assert sub.status_code == 200
        out = sub.json()["application"]
        assert out["status"] == "submitted"
        assert out["reference"].startswith("SARTHI-")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_application_api.py -q`
Expected: FAIL — 404 (routes not defined).

- [ ] **Step 3: Add the endpoints**

In `backend/app/server.py`, add imports near the others (after `from .loan import assess_eligibility`):

```python
import uuid

from . import application
```

Add the request model after `LoanOfferRequest`:

```python
class ApplicationSaveRequest(BaseModel):
    fields: dict
    documents: dict
```

Add the routes at the end of the file:

```python
# ---------------------------------------------------------------------------
# F6 — Document auto-fill (loan application)
# ---------------------------------------------------------------------------


@app.get("/application")
def application_get(request: Request):
    user_id, is_new = auth.resolve_user(request)
    stored = app_store.get_or_create(user_id, lambda: application.build_draft(user_id))
    return _with_cookie({"application": application.public_view(stored)}, user_id, is_new)


@app.put("/application")
def application_save(req: ApplicationSaveRequest, request: Request):
    user_id, is_new = auth.resolve_user(request)
    app_store.get_or_create(user_id, lambda: application.build_draft(user_id))
    stored = app_store.save(user_id, req.fields, req.documents)
    if stored is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _with_cookie({"application": application.public_view(stored)}, user_id, is_new)


@app.post("/application/submit")
def application_submit(request: Request):
    user_id, is_new = auth.resolve_user(request)
    app_store.get_or_create(user_id, lambda: application.build_draft(user_id))
    reference = "SARTHI-" + uuid.uuid4().hex[:6].upper()
    stored = app_store.submit(user_id, reference)
    if stored is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _with_cookie({"application": application.public_view(stored)}, user_id, is_new)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./.venv/Scripts/python -m pytest tests/test_application_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/server.py backend/tests/test_application_api.py
git commit -m "feat(apply): GET/PUT/submit /application endpoints (cookie-scoped)"
```

---

## Task 6: Frontend `/apply` page

**Files:**
- Create: `sarthi-web/src/lib/application.ts`, `sarthi-web/src/app/(app)/apply/page.tsx`
- Modify: `sarthi-web/src/lib/nav.ts`, `sarthi-web/src/components/AppShell.tsx`

**Interfaces:**
- Consumes: `GET/PUT/POST /api/agent/application*`.
- Produces: `/apply` route + nav entry.

- [ ] **Step 1: Add the typed client**

Create `sarthi-web/src/lib/application.ts`:

```ts
const BASE = "/api/agent";

export type SchemaField = {
  key: string; label: string; type: string; extractable: boolean; required: boolean;
};
export type SchemaSection = { key: string; title: string; fields: SchemaField[] };
export type SchemaDoc = { key: string; label: string };

export type Application = {
  fields: Record<string, string>;
  ai_filled: string[];
  documents: Record<string, boolean>;
  status: "draft" | "submitted";
  reference: string | null;
  schema: { sections: SchemaSection[]; documents: SchemaDoc[] };
  completeness: { filled: number; total: number };
};

const j = async (res: Response): Promise<Application> => {
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()).application as Application;
};

export const getApplication = () =>
  fetch(`${BASE}/application`, { credentials: "include" }).then(j);

export const saveApplication = (fields: Record<string, string>, documents: Record<string, boolean>) =>
  fetch(`${BASE}/application`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ fields, documents }),
  }).then(j);

export const submitApplication = () =>
  fetch(`${BASE}/application/submit`, { method: "POST", credentials: "include" }).then(j);
```

- [ ] **Step 2: Add the nav item**

Replace `sarthi-web/src/lib/nav.ts` with:

```ts
export type NavItem = {
  href: "/chat" | "/sop" | "/loan" | "/apply";
  label: string;
  icon: "chat" | "doc" | "wallet" | "file";
};

export const APP_NAV: NavItem[] = [
  { href: "/chat", label: "Chat", icon: "chat" },
  { href: "/sop", label: "SOP", icon: "doc" },
  { href: "/loan", label: "Loan", icon: "wallet" },
  { href: "/apply", label: "Apply", icon: "file" },
];
```

- [ ] **Step 3: Add the icon to the shell map**

In `sarthi-web/src/components/AppShell.tsx`, change:

```tsx
import { IconChat, IconDoc, IconWallet } from "./icons";
```

to:

```tsx
import { IconChat, IconDoc, IconFile, IconWallet } from "./icons";
```

and change:

```tsx
const ICONS = { chat: IconChat, doc: IconDoc, wallet: IconWallet } as const;
```

to:

```tsx
const ICONS = { chat: IconChat, doc: IconDoc, wallet: IconWallet, file: IconFile } as const;
```

- [ ] **Step 4: Create the page**

Create `sarthi-web/src/app/(app)/apply/page.tsx`:

```tsx
"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";

import { Chakra } from "../../../components/Chakra";
import { IconCheck, IconFile } from "../../../components/icons";
import { container, item } from "../../../lib/motion";
import {
  type Application,
  getApplication,
  saveApplication,
  submitApplication,
} from "../../../lib/application";

export default function ApplyWorkspace() {
  const [app, setApp] = useState<Application | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    fetch("/api/agent/session", { credentials: "include" })
      .catch(() => {})
      .finally(() => {
        getApplication()
          .then(setApp)
          .catch(() => setError("Couldn't load your application. Is the agent running?"));
      });
  }, []);

  const setField = (key: string, value: string) =>
    setApp((a) => (a ? { ...a, fields: { ...a.fields, [key]: value } } : a));
  const toggleDoc = (key: string) =>
    setApp((a) => (a ? { ...a, documents: { ...a.documents, [key]: !a.documents[key] } } : a));

  const save = useCallback(async () => {
    if (!app || busy) return;
    setBusy(true);
    setError(null);
    try {
      const next = await saveApplication(app.fields, app.documents);
      setApp(next);
      setSavedAt(Date.now());
    } catch {
      setError("Save failed. Try again.");
    } finally {
      setBusy(false);
    }
  }, [app, busy]);

  const submit = async () => {
    if (!app || busy) return;
    setBusy(true);
    setError(null);
    try {
      await saveApplication(app.fields, app.documents);
      setApp(await submitApplication());
    } catch {
      setError("Submit failed. Try again.");
    } finally {
      setBusy(false);
    }
  };

  if (!app) {
    return (
      <div className="m-auto flex flex-col items-center gap-4 p-10 text-center">
        <Chakra size={36} />
        {error ? <p className="text-sm text-saffron-deep">{error}</p>
               : <p className="text-sm text-muted">Loading your application…</p>}
      </div>
    );
  }

  if (app.status === "submitted") {
    return (
      <div className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center px-5 py-16 text-center">
        <span className="grid size-14 place-items-center rounded-full bg-saffron/15 text-saffron">
          <IconCheck className="size-7" />
        </span>
        <h1 className="mt-6 font-display text-3xl font-semibold">Application submitted</h1>
        <p className="mt-2 text-muted">
          Reference <span className="font-mono text-cream">{app.reference}</span>
        </p>
        <p className="mt-6 max-w-md text-[11px] leading-relaxed text-muted">
          This is a demo submission (integration-ready); nothing was sent to a lender. Final
          eligibility and approval rest with the lending partner after verification.
        </p>
      </div>
    );
  }

  const required = app.schema.sections.flatMap((s) => s.fields).filter((f) => f.required);
  const missingRequired = required.filter((f) => !String(app.fields[f.key] ?? "").trim());
  const canSubmit = missingRequired.length === 0 && !busy;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-5 py-6">
      <motion.div variants={container} initial="hidden" animate="show">
        <motion.h1 variants={item} className="font-display text-3xl font-semibold">
          Your loan application
        </motion.h1>
        <motion.p variants={item} className="mt-2 text-balance text-muted">
          SARTHI pre-filled{" "}
          <span className="text-cream tabular-nums">
            {app.completeness.filled} of {app.completeness.total}
          </span>{" "}
          fields from your chats. Review every field, fill the gaps, and submit.
        </motion.p>
      </motion.div>

      {app.schema.sections.map((section) => (
        <div key={section.key} className="rounded-2xl border border-ink-3 bg-ink-2/40 p-5">
          <h2 className="font-display text-lg font-semibold">{section.title}</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {section.fields.map((f) => {
              const value = app.fields[f.key] ?? "";
              const fromChats = app.ai_filled.includes(f.key) && String(value).trim() !== "";
              return (
                <label key={f.key} className="block">
                  <span className="flex items-center justify-between text-sm text-muted">
                    <span>{f.label}{f.required && <span className="text-saffron-deep"> *</span>}</span>
                    <span className={`text-[10px] ${fromChats ? "text-saffron" : "text-muted"}`}>
                      {fromChats ? "from your chats" : "needs input"}
                    </span>
                  </span>
                  <input
                    type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}
                    value={value}
                    onChange={(e) => setField(f.key, e.target.value)}
                    className="mt-1 w-full rounded-xl border border-ink-3 bg-ink-2 px-3 py-2.5 text-cream outline-none focus:border-saffron/60"
                  />
                </label>
              );
            })}
          </div>
        </div>
      ))}

      <div className="rounded-2xl border border-ink-3 bg-ink-2/40 p-5">
        <h2 className="font-display text-lg font-semibold">Documents to keep ready</h2>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {app.schema.documents.map((d) => (
            <button
              key={d.key}
              onClick={() => toggleDoc(d.key)}
              className="flex items-center gap-2 rounded-xl border border-ink-3 px-3 py-2.5 text-left text-sm transition-colors hover:border-saffron/40"
            >
              <span className={`grid size-5 place-items-center rounded ${app.documents[d.key] ? "bg-saffron text-ink" : "bg-ink-3 text-muted"}`}>
                {app.documents[d.key] && <IconCheck className="size-3.5" />}
              </span>
              <span className={app.documents[d.key] ? "text-cream" : "text-muted"}>{d.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={save}
          disabled={busy}
          className="inline-flex min-h-11 items-center gap-2 rounded-full border border-saffron/50 px-5 py-2.5 text-sm font-medium text-saffron transition-colors hover:bg-saffron/10 disabled:opacity-60"
        >
          {busy ? <Chakra rolling size={18} /> : null}
          Save draft
        </button>
        <button
          onClick={submit}
          disabled={!canSubmit}
          className="inline-flex min-h-11 items-center gap-2 rounded-full bg-saffron px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-saffron-deep disabled:cursor-not-allowed disabled:opacity-50"
        >
          <IconFile className="size-4" />
          Submit application
        </button>
        {savedAt && !busy && <span className="text-xs text-muted">Draft saved</span>}
        {missingRequired.length > 0 && (
          <span className="text-xs text-muted">{missingRequired.length} required field(s) left</span>
        )}
      </div>

      <AnimatePresence>
        {error && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            role="alert" className="text-sm text-saffron-deep">
            {error}
          </motion.p>
        )}
      </AnimatePresence>

      <p className="border-t border-ink-3 pt-4 text-[11px] leading-relaxed text-muted">
        SARTHI drafted this from your own messages — please verify every field. This is a demo
        submission (integration-ready); nothing is sent to a lender.
      </p>
    </div>
  );
}
```

- [ ] **Step 5: Type-check and build**

Run: `cd sarthi-web && npx tsc --noEmit`
Expected: exit 0.

Run: `cd sarthi-web && npm run build`
Expected: succeeds; route `/apply` listed.

- [ ] **Step 6: Manual verification (both servers running)**

Restart the backend (new tool + endpoints + DB init):
`cd backend && ./.venv/Scripts/python -m uvicorn app.server:app --port 8000`
Frontend: `cd sarthi-web && npm run dev`
- In `/chat`, first give the agent some facts ("I'm Priya from Nagpur, final-year Mechanical, CGPA 7.8, want an MS in Robotics in the US, need about 45 lakh, dad earns 12 lakh"), then "I'm ready to apply for the loan" → agent calls `draft_application` and reports what it pre-filled.
- Visit `/apply` → fields pre-filled show "from your chats"; structural fields (DOB, phone, passport) show "needs input"; completeness reads "pre-filled N of M".
- Fill the required gaps → "Submit application" enables → submit → confirmation card with a `SARTHI-XXXXXX` reference + disclaimer.
- Reload `/apply` before submitting → edits persisted.

- [ ] **Step 7: Commit**

```bash
git add sarthi-web/src/lib/application.ts sarthi-web/src/lib/nav.ts sarthi-web/src/components/AppShell.tsx "sarthi-web/src/app/(app)/apply/page.tsx"
git commit -m "feat(apply): /apply review-and-submit page, nav entry, typed client"
```

---

## Task 7: Document F6 and verify the whole suite

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Record F6 in `CLAUDE.md`**

In `§0`, immediately before the `**Next up:**` line, add:

```markdown
- **F6 — Document Auto-Fill into Loan Application:** done. SARTHI pre-fills a loan application from the student's long-term memory facts. `backend/app/application.py` extracts structured fields via the free utility model (`llama-3.1-8b`, isolated behind a monkeypatchable `_call_model` seam; only `extractable:true` schema fields can be auto-filled, so the "pre-filled N of M" count is honest) over `backend/data/application_schema.json`; user-scoped `backend/app/app_store.py` persists one editable draft per user. Surfaces: `draft_application` agent tool (chat kickoff) + cookie-scoped `GET/PUT/POST /application` → new schema-driven `/apply` page (field-level provenance badges, document checklist, mock submit with a `SARTHI-XXXXXX` demo reference). New pytest suites (application/store/api/tool). **Honesty:** reads the student's *own* stated facts (never invents data), every field is reviewable with visible provenance, submission is an explicit demo — no lender API, no document storage.
```

Then update the `**Next up:**` line:

```markdown
**Next up:** F7 — Shareable "Study Abroad Passport" (viral growth loop).
```

- [ ] **Step 2: Run the full backend suite**

Run: `cd backend && ./.venv/Scripts/python -m pytest -q`
Expected: all pass (existing + new application/store/api/tool/config tests).

- [ ] **Step 3: Final frontend checks**

Run: `cd sarthi-web && npx tsc --noEmit && npm run build`
Expected: both clean.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: record F6 document auto-fill in CLAUDE.md"
```

---

## Self-Review Notes

- **Spec coverage:** schema data file (T1) · LLM extraction behind a seam + provenance/completeness (T2) · user-scoped persisted draft (T3) · agent kickoff tool (T4) · GET/PUT/submit endpoints (T5) · schema-driven `/apply` page with provenance badges + checklist + mock submit (T6) · honesty framing on page/confirmation (T6) + CLAUDE.md honesty note (T7) · tests for extraction/store/api/tool (T2–T5). Memory is read-only via `memory.all_facts` (no F1 change).
- **Type consistency:** stored dict shape `{fields, ai_filled, documents, status, reference, created_at, updated_at}` is identical across `build_draft` (T2), `app_store` (T3), and `public_view`; `public_view` adds `schema` + `completeness`, matching the `Application` TS type (T6) and the API tests (T5). `completeness` = `{filled, total}` everywhere. Tool returns `completeness/filled/missing/apply_url` consistent with its test (T4). Nav `icon: "file"` matches the `ICONS` map entry (T6).
- **No placeholders:** every code step shows complete code; tests stub the one model call (`_call_model` / `extract_fields`) so the suite is deterministic and offline.
