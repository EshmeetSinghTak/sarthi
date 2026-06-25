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

# Chat model — DeepSeek reasoning content stays in additional_kwargs; only
# .content (the answer) streams to the user.
chat_llm = ChatOpenAI(
    model=settings.chat_model,
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key,
    temperature=0.7,
    top_p=0.95,
    max_tokens=2048,
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
