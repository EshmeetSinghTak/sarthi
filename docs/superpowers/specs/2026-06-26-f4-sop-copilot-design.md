# F4 — SOP Co-Pilot (full workspace): Design

**Date:** 2026-06-26
**Status:** Approved (revisable during implementation)
**Builds on:** F1 agent core + memory, the anonymous-cookie identity (`backend/app/auth.py`), and the F2/F3 testable-tool pattern.

## Goal

Help a Tier-2/3 Indian student **author their own** Statement of Purpose with AI coaching — Socratic questions, deterministic structural feedback, and authenticity checks — **never wholesale generation** (universities run AI-detectors; a machine-written SOP is a liability). Includes a persistent multi-SOP workspace (one per university/program) with append-only version history. Implements CLAUDE.md §5 F4 and §6 Phase 3.

## Constraints (Global)

- **No Claude / no paid LLMs.** The Socratic coaching rides the existing free NVIDIA chat model (`deepseek-ai/deepseek-v4-flash`, reasoning); the deterministic analyzer uses **no model at all**. Test with `SARTHI_MODEL_DEFAULT=meta/llama-3.3-70b-instruct` to dodge deepseek rate limits.
- **NEVER hardcode tunables.** Cliché/red-flag phrases live in `backend/data/sop_cliches.json`; target word range, long-sentence threshold, and the SOP DB path live in `config.py`. No literals in analyzer logic.
- **Never generate the SOP for the student.** This is a hard rule baked into the prompt; the agent coaches and critiques, the student writes.
- **Identity from the signed cookie, never the request body** (same trust model as `/chat`). The LLM never supplies `user_id` to tools — it is injected via LangGraph `InjectedState`.
- **Follow existing patterns:** pure functions under thin tool/API wrappers; data in `backend/data/`; SQLite for storage; Next.js App Router + Tailwind v4 (twilight-indigo/saffron) for UI.

## Decisions (from brainstorming)

1. **Shape:** deterministic analyzer tool + Socratic coaching behavior + **full persistence workspace**.
2. **UI:** a dedicated `/sop` workspace (editor + analysis readout + version history) plus chat coaching.
3. **Count:** multiple named SOPs per student (one per university/program).
4. **Versioning:** append-only — each save is a new immutable version; "current" = latest; restore = save an old version's content as a new latest.
5. **Frontend verification:** manual (no FE test harness in the repo); automated tests cover the backend.

## Architecture & Units

### `backend/app/tools/sop.py`
- Pure `analyze_sop(text: str) -> dict` (deterministic; see §Analyzer).
- Agent tool wrappers `review_sop` and `list_my_sops` (see §Agent).

### `backend/app/sop_store.py`
A small synchronous SQLite repository (stdlib `sqlite3`, a fresh connection per call — safe and trivially unit-testable). The DB path comes from `config.SOP_DB_PATH`. Functions:
- `init_db(path=None)` — create tables if absent (idempotent; called at startup).
- `create_sop(user_id, title) -> dict` — returns `{id, user_id, title, created_at}`.
- `list_sops(user_id) -> list[dict]` — the user's SOPs, each with `latest_version_id` and `updated_at` (newest first).
- `get_sop(user_id, sop_id) -> dict | None` — ownership-checked (returns None if not owned).
- `add_version(user_id, sop_id, content, analysis) -> dict` — append a version; returns `{id, sop_id, created_at}`. Ownership-checked.
- `list_versions(user_id, sop_id) -> list[dict]` — version metadata (id, created_at, word_count), newest first.
- `get_version(user_id, sop_id, version_id) -> dict | None` — full content + analysis.
- `get_latest_version(user_id, sop_id) -> dict | None`.

All reads/writes are scoped by `user_id` so one anonymous user can never touch another's data.

### `backend/data/sop_cliches.json`
```jsonc
{
  "note": "Common SOP clichés / red-flag openers and filler that weaken authenticity. Curated, guidance-only.",
  "cliches": ["since childhood", "from a young age", "i have always been passionate",
              "burning desire", "dream since", "renowned university", "esteemed faculty",
              "leaps and bounds", "tireless efforts", "ever since i can remember",
              "i was fascinated", "world-class", "cutting-edge", "plethora", "in today's world"]
}
```

### `config.py` additions (named constants — no hardcoding)
- `SOP_DB_PATH` (default `BACKEND_DIR / "sarthi_sop.db"`, env-overridable `SARTHI_SOP_DB`).
- `SOP_TARGET_WORDS_MIN` (700), `SOP_TARGET_WORDS_MAX` (1000) — typical SOP length band.
- `SOP_LONG_SENTENCE_WORDS` (40) — sentences longer than this are flagged.

## Analyzer — `analyze_sop(text)` (deterministic, no LLM)

Returns a dict:
- `word_count: int`, `paragraph_count: int` (blank-line-separated blocks).
- `length_flag: "short" | "ok" | "long"` vs the config word band.
- `cliche_hits: list[{phrase, count}]` — case-insensitive matches from `sop_cliches.json`.
- `long_sentences: list[{text_preview, word_count}]` — sentences over `SOP_LONG_SENTENCE_WORDS` (split on `.?!`).
- `structure_signals: {mentions_program: bool, mentions_goal: bool, gives_reasons: bool}` — heuristic keyword presence (e.g. program/degree words; goal/career/future words; "because/why/motivat" rationale words). Labelled as *signals*, not verdicts.
- `note`: a one-line "these are signals to prompt reflection, not a grade" disclaimer.

Pure, side-effect-free, fully unit-testable. The cliché list and thresholds are injected from data/config, so tests assert behavior against known inputs.

## Agent — Socratic coaching (LLM)

Each tool is a thin wrapper over a plain inner function (`_review_sop(user_id, title)`, `_list_my_sops(user_id)`) that holds the logic — so tests call the inner function directly with a seeded temp DB, never needing graph state. The `@tool` only adds `InjectedState` extraction + `json.dumps`.

Two tools in `sop.py`, registered in `agent.py`'s `TOOLS` (and `ToolNode`):

- `review_sop(title: str | None = None, *, user_id: Annotated[str, InjectedState("user_id")]) -> str`
  Loads the latest version of the student's SOP (matched by `title`; if `title` omitted and the user has exactly one SOP, use it; if several, return a short "which one?" payload listing titles). Runs `analyze_sop` on the content and returns the analysis as a JSON string. The LLM only ever supplies `title` — `user_id` is injected by `ToolNode` from graph state, never from the model.
- `list_my_sops(*, user_id: Annotated[str, InjectedState("user_id")]) -> str`
  Returns the user's SOP titles + last-updated, as JSON. Lets the agent orient before reviewing.

**Prompt** (`prompts.py`, new "SOP COACH" block in the YOUR TOOLS / behavior area):
- When the student wants SOP help, call `review_sop` (or `list_my_sops` first if unsure which).
- Coach **Socratically**: ask pointed questions that make the student supply specifics; tie feedback to the analysis (clichés, length, missing "why this program") **and to remembered facts** (their real internship, CGPA, target country) so it feels personal.
- **Never write or rewrite the SOP for them.** Offer structural guidance, examples of *questions to answer*, and line-level critique — but the words stay the student's. Say plainly that universities detect AI-written SOPs and authenticity matters.
- Keep the existing "figures approximate / advisory" and boundary norms.

## REST API (`server.py`) — cookie identity, never body

All endpoints derive `user_id` via `auth.resolve_user(request)`. Reached from the frontend through the existing rewrite at `/api/agent/<path>`.

- `GET  /sops` → `{sops: [...]}` (the user's SOPs).
- `POST /sops` body `{title}` → created SOP. (Mint identity cookie if new, like `/session`.)
- `GET  /sops/{sop_id}` → SOP meta + latest version (content + analysis), 404 if not owned.
- `POST /sops/{sop_id}/versions` body `{content}` → runs `analyze_sop` server-side, stores `{content, analysis}`, returns the new version meta + analysis. 404 if not owned.
- `GET  /sops/{sop_id}/versions` → version history (metadata).
- `GET  /sops/{sop_id}/versions/{version_id}` → full version (content + analysis).

`sop_store.init_db()` is called in the FastAPI lifespan alongside the existing checkpointer setup.

## Frontend — `/sop` workspace (`sarthi-web`)

A new App Router route `src/app/sop/page.tsx` plus small components and an API client `src/lib/sop.ts`. Layout:
- **Left:** SOP list/switcher + "New SOP" (title prompt).
- **Center:** draft editor (`<textarea>`), "Save version" button (POST version), live structural readout (word count, length flag, cliché chips, long-sentence/structure signals) from the saved analysis.
- **Right/below:** version history list with view/restore.
- Simple nav between chat (`/`) and SOP (`/sop`), consistent twilight-indigo/saffron styling, framer-motion in keeping with the existing page. All fetches use `credentials: "include"`.
- Coaching stays in the chat tab; the SOP page links the student there ("Ask SARTHI to review this").

## Testing

Backend (pytest, extends the F3 suite):
- `tests/test_sop_analyze.py` — word/paragraph counts; length flags at band edges; cliché detection (case-insensitive, multiple hits); long-sentence detection at the threshold; structure signals true/false on crafted inputs; empty-string safety.
- `tests/test_sop_store.py` — temp DB via `SOP_DB_PATH` override: create/list/get; append-only versions; latest resolution; restore-as-new-version; **ownership isolation** (user B cannot read/write user A's SOP).
- `tests/test_sop_api.py` — FastAPI `TestClient`: full CRUD happy paths, identity from cookie, 404 on cross-user access, analysis present on save.
- `tests/test_sop_tools.py` — `review_sop` / `list_my_sops` with an injected `user_id` (call the underlying functions directly with a seeded temp DB); JSON shape; the "which SOP?" disambiguation path.
- `tests/test_prompt.py` — extend to assert the SOP tools/coach guidance appear in `SYSTEM_PROMPT`.

Frontend: manual verification against the running stack (documented checklist in the final task).

## Build Sequence (units → tasks)

1. `config.py` constants + `sop_cliches.json` (data) + pytest data-integrity test.
2. `analyze_sop` pure function + tests.
3. `sop_store` SQLite repository + tests (incl. ownership isolation).
4. REST API endpoints + lifespan `init_db` + API tests.
5. Agent tools (`review_sop`, `list_my_sops`) with `InjectedState` + registration + tool tests.
6. Prompt "SOP COACH" block + prompt test.
7. Frontend `/sop` workspace + nav + API client (manual verification).
8. End-to-end check (agent calls `review_sop`, coaches Socratically, refuses to write the SOP) + CLAUDE.md update.

## Out of Scope (YAGNI)

Real-time collaborative editing, rich-text/PDF export/import, AI-generated full drafts (forbidden), a grammar/spell-check engine, per-version textual diff visualization (history + restore only), and sharing SOPs between users.
