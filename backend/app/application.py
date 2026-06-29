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
