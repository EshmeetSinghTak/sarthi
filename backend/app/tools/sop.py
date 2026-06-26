"""F4 — SOP Co-Pilot.

`analyze_sop` is a deterministic, model-free analysis of an SOP draft: length,
clichés, overlong sentences, and coarse structure signals. It produces *signals*
to prompt reflection, never a grade. Agent tools (added later) load a student's
saved draft and return this analysis for Socratic coaching.

Every tunable lives in app.config / data files — nothing hardcoded here.
"""

import json
import re
from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from .. import config, sop_store

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
        "long_sentence_threshold": config.SOP_LONG_SENTENCE_WORDS,
        "structure_signals": structure_signals,
        "note": CLICHE_NOTE + " These are signals to prompt reflection, not a grade.",
    }


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
