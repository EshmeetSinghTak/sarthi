"""LLM wiring: the chat model (LangChain) and a utility distillation call.

Chat uses LangChain's ChatOpenAI so LangGraph can stream tokens via
stream_mode="messages". Distillation uses the raw OpenAI client with the fast
utility model — kept off the chat path so it never adds latency to replies.
"""

import json
import re

from langchain_openai import ChatOpenAI
from openai import OpenAI

from .config import settings
from .prompts import DISTILL_PROMPT

def _make_chat(model: str, max_tokens: int, *, extra_body: dict | None = None) -> ChatOpenAI:
    """Build a ChatOpenAI for one tier. Tools are bound later in agent.py."""
    return ChatOpenAI(
        model=model,
        base_url=settings.nvidia_base_url,
        api_key=settings.nvidia_api_key,
        temperature=0.7,
        top_p=0.95,
        max_tokens=max_tokens,
        extra_body=extra_body,
    )


# Three tiers selected per-turn by the router. None has tools bound here;
# agent.py binds tools to the mid/reasoning tiers (the light 8B can't call
# tools reliably and only handles trivial chit-chat). Reasoning content stays
# in additional_kwargs; only .content (the answer) streams to the user.
llm_light = _make_chat(settings.model_light, max_tokens=1024)
llm_mid = _make_chat(settings.model_mid, max_tokens=2048, extra_body=settings.chat_extra_body)
llm_reasoning = _make_chat(
    settings.model_reasoning,
    max_tokens=settings.reasoning_max_tokens,
    extra_body=settings.chat_extra_body,
)

_raw = OpenAI(api_key=settings.nvidia_api_key, base_url=settings.nvidia_base_url)


def distill_facts(message: str) -> list[str]:
    """Extract durable facts from a user message using the fast utility model."""
    try:
        resp = _raw.chat.completions.create(
            model=settings.utility_model,
            messages=[{"role": "user", "content": DISTILL_PROMPT.format(message=message)}],
            temperature=0,
            max_tokens=512,
        )
        text = (resp.choices[0].message.content or "").strip()
        # Be forgiving: pull the first JSON array out of the response.
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return []
        facts = json.loads(match.group(0))
        return [str(f) for f in facts if isinstance(f, (str, int, float)) and str(f).strip()]
    except Exception:
        # Memory distillation must never break a chat turn.
        return []
