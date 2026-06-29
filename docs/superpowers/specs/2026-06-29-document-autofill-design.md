# SARTHI F6 — Document Auto-Fill into Loan Application (Design Spec)

**Date:** 2026-06-29
**Status:** Approved (design), pending implementation plan
**Author:** Rath (solo) + Claude

---

## 1. Problem & Goal

F6 is the "zero-human-intervention" money shot (Phase 4 "Fund"): SARTHI reads
what it already knows about a student from past conversations and **pre-fills a
loan application**, so the student only reviews, fills the gaps, ticks a few
documents, and submits.

**Goal:** assemble a structured loan application from the student's free-text
long-term memory, present it for review/edit on a dedicated page, and let them
"submit" — with honest provenance (what SARTHI filled vs what needs input) and a
clearly-labeled demo submission.

### Non-goals (YAGNI)
- **No real lender API / KYC** — "submit" is a demo (integration-ready), nothing
  is sent anywhere.
- **No real document upload/storage** — a checklist only (storing real
  passports/income proofs is a PII/DPDP liability).
- **No re-architecture of memory** — we extract from the existing free-text
  facts; we do not change how facts are stored (F1).
- **No multiple applications** — one loan application per user.

---

## 2. Decisions (from brainstorming)

1. **Surface:** a dedicated `/apply` page **plus** an agent kickoff in chat (the
   full money-shot).
2. **Extraction:** LLM extraction with the free NVIDIA **utility model**
   (`llama-3.1-8b`) over the student's stored memory facts → structured fields.
3. **Documents & submit:** a document **checklist** (tick as ready) + a **mock
   submit** that returns a demo reference number; no file upload/storage.
4. **Provenance + completeness** (baked in): every field tagged "from your chats"
   vs "needs input"; a headline "SARTHI pre-filled N of M fields" — a real count,
   not a fabricated percentage.
5. **Honesty framing** (baked in): values are SARTHI's suggestions from the
   student's own words, to verify; submission is a labeled demo.

---

## 3. Architecture

```
memory facts (free-text) -> app/application.py
                              |- extract_fields(facts)  -> LLM (utility model) -> {field: value}
                              \- build_draft(user_id)    -> extract + provenance + completeness
                                         |
                              app/app_store.py  (user-scoped SQLite: one application/user, editable)
                                         |
        |-- tool: draft_application (chat kickoff) --|
        \-- REST: GET/PUT /application, POST /application/submit --> /apply page
```

Extraction is isolated in one module; the editable draft persists; the agent tool
and the page both read/write the same store. Follows the existing
store -> tool -> endpoint -> page pattern (F4 SOP, F5 loan).

---

## 4. Application schema — `backend/data/application_schema.json`

Field definitions live in data, never hardcoded in logic. Each field has `key`,
`label`, `type`, and `extractable` (can it plausibly come from a chat?).

- **personal:** full_name (ext), date_of_birth, city (ext), phone, email
- **academic:** current_degree (ext), institution (ext), cgpa (ext),
  target_course (ext), target_country (ext), target_universities (ext)
- **financial:** loan_amount_inr_lakh (ext), co_applicant_name,
  co_applicant_relation, co_applicant_income_inr_lakh (ext),
  collateral_value_inr_lakh (ext)
- **documents** (checklist, not fields): passport, marksheets, admission_letter,
  income_proof, coapplicant_kyc, bank_statements

`extractable: false` fields (DOB, phone, email, passport, co-applicant name/PAN)
structurally cannot come from chat — they remain "needs input", which keeps the
auto-fill stat honest.

File shape:
```json
{
  "note": "Fields SARTHI drafts from the student's own messages; verify before use.",
  "sections": [
    {"key": "personal", "title": "Personal", "fields": [
      {"key": "full_name", "label": "Full name", "type": "text", "extractable": true},
      {"key": "date_of_birth", "label": "Date of birth", "type": "date", "extractable": false}
    ]}
  ],
  "documents": [
    {"key": "passport", "label": "Passport"}
  ]
}
```

---

## 5. Extraction — `backend/app/application.py`

- `SCHEMA` loaded from the JSON file; `FIELD_KEYS`, `EXTRACTABLE_KEYS`,
  `DOCUMENT_KEYS` derived once.
- `extract_fields(facts: list[str]) -> dict[str, str]` — one call to the utility
  model with `APPLICATION_EXTRACT_PROMPT` (lists the extractable keys + the
  facts); forgiving JSON parse (mirrors `llm.distill_facts`). On any error -> `{}`
  (extraction must never break the flow). Result filtered to `EXTRACTABLE_KEYS`
  and to non-empty string values.
- `completeness(fields: dict) -> dict` — pure: `{"filled": int, "total": int}`
  counting non-empty values across all `FIELD_KEYS`.
- `build_draft(user_id: str) -> dict` — `memory.all_facts(user_id)` ->
  `extract_fields` -> returns
  `{"fields": {...}, "ai_filled": [keys], "documents": {key: false, ...},
    "completeness": {...}, "status": "draft", "reference": None}`.
  `ai_filled` is the set of keys SARTHI populated (drives the provenance badges).

The only non-deterministic part is the single `extract_fields` model call; every
other function is pure and unit-tested.

---

## 6. Persistence — `backend/app/app_store.py`

User-scoped SQLite at `config.APPLICATION_DB_PATH`, one row per user:

```
applications(
  user_id     TEXT PRIMARY KEY,
  fields_json TEXT NOT NULL,
  ai_filled_json TEXT NOT NULL,
  documents_json TEXT NOT NULL,
  status      TEXT NOT NULL,     -- 'draft' | 'submitted'
  reference   TEXT,              -- demo reference once submitted
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
)
```

Functions (all scoped by `user_id`):
- `init_db()`
- `get(user_id) -> dict | None`
- `get_or_create(user_id, builder) -> dict` — if absent, persist `builder()`
  (i.e. `build_draft`); else return stored.
- `save(user_id, fields, documents) -> dict` — update field values + checklist,
  bump `updated_at`. (Keeps existing `ai_filled`/status.)
- `submit(user_id, reference) -> dict | None` — set `status='submitted'`,
  store `reference`.

One application per user means no cross-row IDOR surface, but every query still
filters on `user_id` (defense-in-depth).

---

## 7. Agent tool + REST

### `backend/app/tools/application.py` — `@tool draft_application`
`user_id` via `InjectedState`. Ensures a draft exists (`get_or_create` with
`build_draft`), returns JSON: `completeness`, `filled` (field keys), `missing`
(field keys), and a pointer to the `/apply` page. Docstring tells the agent to
call it when the student is ready to apply / asks to start the loan application,
and to report how much was pre-filled and what's still needed — and that the
student completes and submits on the application page. Registered in
`agent.TOOLS` and named in `SYSTEM_PROMPT`.

### `backend/app/server.py` (cookie-scoped, `_with_cookie`)
- `GET /application` -> `get_or_create` -> `{"application": {...}}`.
- `PUT /application` (body: `fields`, `documents`) -> `save` ->
  `{"application": {...}}`.
- `POST /application/submit` -> generate a demo reference
  (`"SARTHI-" + uuid4().hex[:6].upper()`), `submit`, return
  `{"application": {...}}`. Reached via `/api/agent/application`.

---

## 8. Frontend — `/apply` page

- New route `sarthi-web/src/app/(app)/apply/page.tsx`; nav entry in `lib/nav.ts`
  (`{href: "/apply", label: "Apply", icon: "file"}`); `IconFile` exists, extend
  the shell icon map.
- On load: `GET /application`. Render sections as field groups; each input shows
  a **provenance badge** — "from your chats" if the key is in `ai_filled` and
  non-empty, else "needs input".
- **Completeness meter** at the top: "SARTHI pre-filled {filled} of {total}".
- **Document checklist** (checkboxes from schema `documents`).
- **Save** (PUT, debounced or explicit) and **Submit** (POST). Submit ->
  confirmation card with the demo reference + disclaimer. Submit disabled until
  required fields are non-empty (required = all `extractable:false` + the core
  financial fields; exact required set listed in the schema via a per-field
  `required` flag).
- `lib/application.ts` typed client. Twilight theme, framer-motion, a11y —
  matching chat/SOP/loan.

(Add `"required": true|false` to each schema field so the page knows what blocks
submission; keep it in the data file, not the component.)

---

## 9. Honesty / compliance (baked in)

Standing banner on the page and on the confirmation:
*"SARTHI drafted this from your own messages — please verify every field. This is
a demo submission (integration-ready); nothing is sent to a lender."*
Provenance badges make every auto-filled value auditable; the reference is
labeled a demo. Aligns with the project's RBI/advisory + no-fabrication
guardrails.

---

## 10. Testing

- **`backend/tests/test_application.py`** — pure parts: `completeness` counts
  correctly; `extract_fields` filters to extractable keys and drops empties (raw
  model call monkeypatched to return a canned JSON string); `build_draft` shape +
  `ai_filled` correct (with `extract_fields`/`memory.all_facts` monkeypatched).
- **`backend/tests/test_app_store.py`** — get_or_create persists a built draft;
  save updates fields/documents; submit sets status+reference; a second user
  can't see the first's application (isolation).
- **`backend/tests/test_application_api.py`** — GET creates, PUT saves, POST
  submit returns a reference (TestClient, cookie-scoped, like `test_sop_api`).
- **`backend/tests/test_application_tool.py`** — `draft_application` returns JSON
  with `completeness` + `missing` (monkeypatch `build_draft`).
- **Schema file shape test** (in `test_config.py` or `test_application.py`):
  sections/fields/documents present, every field has the required keys.
- **Frontend:** `tsc --noEmit` + `next build` clean; manual browser pass.
- Existing suite stays green.

---

## 11. Files

**New:** `backend/app/application.py`, `backend/app/app_store.py`,
`backend/data/application_schema.json`, `backend/app/tools/application.py`,
`backend/tests/test_application.py`, `test_app_store.py`,
`test_application_api.py`, `test_application_tool.py`,
`sarthi-web/src/lib/application.ts`,
`sarthi-web/src/app/(app)/apply/page.tsx`.
**Modified:** `backend/app/config.py` (`APPLICATION_DB_PATH`,
`APPLICATION_SCHEMA_PATH`), `backend/app/prompts.py`
(`APPLICATION_EXTRACT_PROMPT` + tool line), `backend/app/tools/__init__.py`,
`backend/app/agent.py`, `backend/app/server.py`,
`sarthi-web/src/lib/nav.ts`, `sarthi-web/src/components/AppShell.tsx`,
`CLAUDE.md`.

---

## 12. Honesty Note (for CLAUDE.md on completion)

The auto-fill reads the student's *own* stated facts from memory and proposes
them as a draft; it does not invent data. Extraction can mis-map, so every field
is reviewable with visible provenance, and submission is an explicit demo —
no lender integration, no document storage.
