"""NVIDIA hosted embeddings for long-term memory.

nv-embedqa-e5-v5 is an *asymmetric* retrieval embedder: documents must be
embedded with input_type="passage" and search queries with input_type="query".
We manage this explicitly rather than using Chroma's default embedder, so we
never download a local ONNX model and we get correct query/passage handling.
"""

from openai import OpenAI

from .config import settings

_client = OpenAI(api_key=settings.nvidia_api_key, base_url=settings.nvidia_base_url)


def _embed(texts: list[str], input_type: str) -> list[list[float]]:
    if not texts:
        return []
    resp = _client.embeddings.create(
        model=settings.embed_model,
        input=texts,
        extra_body={"input_type": input_type, "truncate": "END"},
    )
    # Preserve input order.
    return [item.embedding for item in sorted(resp.data, key=lambda d: d.index)]


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embed documents/facts for storage."""
    return _embed(texts, "passage")


def embed_query(text: str) -> list[float]:
    """Embed a single search query."""
    return _embed([text], "query")[0]
