"""Automatic model-tier routing — pure heuristics, no I/O, no LLM calls.

choose_tier() runs on every agent turn:
  LIGHT     — high-confidence trivial chit-chat (fast 8B)
  MID       — the safe default for normal work (70B, tool-capable)
  REASONING — deep tasks: after a deep tool, or clearly complex turns (slow 49B)

Misroute strategy: when uncertain, return MID. LIGHT fires only on
high-confidence trivial turns; REASONING only on explicit signals. All
thresholds and word lists live in config.py.
"""

from enum import Enum

from . import config


class Tier(str, Enum):
    LIGHT = "light"
    MID = "mid"
    REASONING = "reasoning"


def _word_count(text: str) -> int:
    return len(text.split())


def _is_trivial(text: str) -> bool:
    t = text.strip().lower()
    if not t or "?" in t:
        return False
    if _word_count(t) > config.ROUTER_TRIVIAL_MAX_WORDS:
        return False
    stripped = t.strip(".!,… ")
    return any(
        stripped == p or stripped.startswith(p + " ")
        for p in config.ROUTER_TRIVIAL_PATTERNS
    )


def _is_complex(text: str) -> bool:
    t = text.strip().lower()
    if not t:
        return False
    if _word_count(t) >= config.ROUTER_COMPLEX_MIN_WORDS:
        return True
    return any(kw in t for kw in config.ROUTER_COMPLEX_KEYWORDS)


def choose_tier(user_text: str, just_ran_deep_tool: bool = False) -> Tier:
    # Order matters: complexity wins over brevity (a short but loaded question
    # should still reason), and the safe default is MID.
    if just_ran_deep_tool or _is_complex(user_text):
        return Tier.REASONING
    if _is_trivial(user_text):
        return Tier.LIGHT
    return Tier.MID


def is_weak_reply(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < config.ROUTER_WEAK_REPLY_MIN_CHARS:
        return True
    low = t.lower()
    return any(p in low for p in config.ROUTER_REFUSAL_PATTERNS)
