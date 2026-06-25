"""Long-term, per-user memory backed by Chroma.

Stores *distilled facts* (not raw transcripts) so retrieval stays clean and
storage stays small. One persistent collection, partitioned by user_id via
metadata filtering. Embeddings come from NVIDIA (see embeddings.py); we pass
vectors to Chroma directly and never use its built-in embedder.
"""

import hashlib

import chromadb

from .config import settings
from .embeddings import embed_passages, embed_query

_client = chromadb.PersistentClient(path=settings.chroma_dir)
_collection = _client.get_or_create_collection(
    name="user_memories",
    # No embedding_function: we supply vectors ourselves.
    metadata={"hnsw:space": "cosine"},
)


def _fact_id(user_id: str, fact: str) -> str:
    """Stable id so re-storing the same fact for a user is idempotent."""
    digest = hashlib.sha1(f"{user_id}::{fact.lower().strip()}".encode()).hexdigest()
    return f"{user_id}:{digest[:16]}"


def remember(user_id: str, facts: list[str]) -> int:
    """Store durable facts for a user. Returns count stored. Idempotent."""
    facts = [f.strip() for f in facts if f and f.strip()]
    if not facts:
        return 0
    vectors = embed_passages(facts)
    _collection.upsert(
        ids=[_fact_id(user_id, f) for f in facts],
        documents=facts,
        embeddings=vectors,
        metadatas=[{"user_id": user_id} for _ in facts],
    )
    return len(facts)


def recall(user_id: str, query: str, k: int = 5) -> list[str]:
    """Return up to k facts for this user most relevant to the query."""
    if _collection.count() == 0 or not query.strip():
        return []
    res = _collection.query(
        query_embeddings=[embed_query(query)],
        n_results=k,
        where={"user_id": user_id},
    )
    docs = res.get("documents") or [[]]
    return docs[0] if docs else []


def all_facts(user_id: str) -> list[str]:
    """Every stored fact for a user (debug / inspection)."""
    res = _collection.get(where={"user_id": user_id})
    return res.get("documents") or []
