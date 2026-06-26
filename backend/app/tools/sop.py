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
