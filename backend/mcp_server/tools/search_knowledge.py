"""Vector retrieval against local Chroma knowledge base."""

import logging
import threading
import time
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.embeddings import embed_query
from mcp_server.tool_inputs import SearchKnowledgeInput

logger = logging.getLogger(__name__)

COLLECTION_NAME = "advisor_kb"

_collection = None
_collection_lock = threading.Lock()
_count_cache: tuple[float, int] | None = None
_COUNT_TTL_SECONDS = 30.0


def _get_collection():
    """Reuse one PersistentClient/collection per process (read-heavy path)."""
    global _collection
    with _collection_lock:
        if _collection is None:
            client = chromadb.PersistentClient(
                path=settings.chroma_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            _collection = client.get_or_create_collection(name=COLLECTION_NAME)
        return _collection


def reset_collection_cache() -> None:
    """Used after ingestion in-process or in tests."""
    global _collection, _count_cache
    with _collection_lock:
        _collection = None
        _count_cache = None


def _collection_count(collection: Any) -> int:
    """Chroma count() hits disk; the KB only changes on ingest."""
    global _count_cache
    now = time.monotonic()
    if _count_cache and now - _count_cache[0] < _COUNT_TTL_SECONDS:
        return _count_cache[1]
    count = int(collection.count())
    _count_cache = (now, count)
    return count


def _build_where_clause(inp: SearchKnowledgeInput) -> dict[str, Any] | None:
    if inp.topics:
        return {"topic": {"$in": inp.topics}}
    return None


def search_knowledge(
    query: str,
    topics: list[str] | None = None,
    max_results: int = 4,
) -> dict[str, Any]:
    """Search the curated knowledge base; optional topic filter only.

    Age band and audience are deliberately not filters: the whole KB applies to
    parents and teachers of 2–5 year olds (DECISIONS.md DEC-025, DEC-033). Hits with
    a distance above ``settings.chroma_max_distance`` are dropped (DEC-029).

    ``distance`` in each result is the vector distance from Chroma (lower = closer in
    embedding space). It is **not** a calibrated probability or answer correctness score.
    Query embeddings always use ``settings.ollama_embed_model`` (same as ingestion).
    """
    inp = SearchKnowledgeInput(query=query, topics=topics, max_results=max_results)
    collection = _get_collection()
    count = _collection_count(collection)
    if count == 0:
        logger.warning("Knowledge base is empty — run ingestion first")
        return {"results": [], "kb_version": settings.kb_version, "total_chunks": 0}

    where_filter = _build_where_clause(inp)
    n_results = min(inp.max_results, count)

    try:
        query_embedding = embed_query(inp.query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
        )
    except Exception as exc:
        logger.error("Chroma/embed query failed (not falling back to a different embedder): %s", exc)
        return {"results": [], "kb_version": settings.kb_version, "error": str(exc)}

    snippets: list[dict[str, Any]] = []
    max_distance = settings.chroma_max_distance
    if results and results.get("documents"):
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        ids = results["ids"][0] if results.get("ids") else [""] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [None] * len(docs)

        for doc, meta, chunk_id, dist in zip(docs, metas, ids, distances):
            if max_distance is not None and dist is not None and float(dist) > max_distance:
                continue
            source_id = meta.get("source_id") or chunk_id
            snippets.append(
                {
                    "chunk_id": chunk_id,
                    "source_id": source_id,
                    "text": doc,
                    "title": meta.get("title", "Unknown"),
                    "url": meta.get("source_url", ""),
                    "section": meta.get("section") or meta.get("topic") or None,
                    "publication_date": meta.get("publication_date"),
                    "reviewed_at": meta.get("reviewed_at"),
                    "topic": meta.get("topic", ""),
                    "audience": meta.get("audience", "both"),
                    "age_band": meta.get("age_band", "all"),
                    "source": meta.get("source", ""),
                    "distance": dist,
                }
            )

    return {
        "results": snippets[: inp.max_results],
        "kb_version": settings.kb_version,
        "total_chunks": count,
    }
