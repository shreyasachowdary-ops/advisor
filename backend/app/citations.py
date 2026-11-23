"""Citation provenance — only from retrieved knowledge, never LLM-invented."""

import re
from typing import Any

from app.models import Citation
from app.tool_payload import parse_tool_payload

_SOURCES_SECTION_RE = re.compile(
    r"\n(?:\*\*Sources used\*\*|(?:\*\*)?Sources used(?:\*\*)?|##\s*Sources)[^\n]*\n.*",
    re.IGNORECASE | re.DOTALL,
)


def citation_from_retrieval_hit(hit: dict[str, Any]) -> Citation:
    """Build a stable citation from a search_knowledge result row."""
    chunk_id = hit.get("chunk_id") or hit.get("source_id") or ""
    source_id = hit.get("source_id") or chunk_id
    if not chunk_id and not source_id:
        raise ValueError("Retrieval hit missing chunk_id/source_id")
    return Citation(
        source_id=source_id,
        chunk_id=chunk_id,
        title=hit.get("title", "Unknown"),
        url=hit.get("url", ""),
        section=hit.get("section"),
        publication_date=hit.get("publication_date"),
        reviewed_at=hit.get("reviewed_at"),
    )


def dedupe_citations(citations: list[Citation]) -> list[Citation]:
    seen: set[str] = set()
    out: list[Citation] = []
    for c in citations:
        key = c.source_id or c.chunk_id
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def hits_from_search_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    return [r for r in results if isinstance(r, dict) and (r.get("chunk_id") or r.get("source_id"))]


def merge_retrieval_hits(*hit_lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge hits from agent tool messages and server MCP retrieval (dedupe by chunk_id)."""
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for hits in hit_lists:
        for h in hits:
            key = h.get("chunk_id") or h.get("source_id")
            if not key or key in seen:
                continue
            seen.add(str(key))
            merged.append(h)
    return merged


def collect_search_hits_from_agent_messages(messages: list[Any]) -> list[dict[str, Any]]:
    """Extract search_knowledge rows from LangChain agent message history."""
    hits: list[dict[str, Any]] = []
    for msg in messages:
        tool_name = getattr(msg, "name", None)
        class_name = msg.__class__.__name__
        if class_name == "ToolMessage" and tool_name and tool_name != "search_knowledge":
            continue
        if class_name == "ToolMessage" and tool_name == "search_knowledge":
            content = getattr(msg, "content", None)
            payload = parse_tool_payload(content)
            if not payload.get("results") and hasattr(msg, "artifact"):
                payload = parse_tool_payload(getattr(msg, "artifact", None))
            hits.extend(hits_from_search_payload(payload))
    return hits


def citations_from_hits(hits: list[dict[str, Any]]) -> list[Citation]:
    out: list[Citation] = []
    for h in hits:
        try:
            out.append(citation_from_retrieval_hit(h))
        except ValueError:
            continue
    return dedupe_citations(out)


def strip_model_sources_section(answer: str) -> str:
    """Remove LLM-authored 'Sources used' blocks; structured citations are attached separately."""
    cleaned = _SOURCES_SECTION_RE.sub("", answer).rstrip()
    return cleaned


def allowed_chunk_keys(hits: list[dict[str, Any]]) -> set[str]:
    """All chunk/source ids that may appear on structured citations for these hits."""
    allowed: set[str] = set()
    for h in hits:
        for key in ("chunk_id", "source_id"):
            val = h.get(key)
            if val:
                allowed.add(str(val))
    return allowed


def validate_citations_subset_of_hits(citations: list[Citation], hits: list[dict[str, Any]]) -> bool:
    if not citations:
        return True
    if not hits:
        return False
    allowed = allowed_chunk_keys(hits)
    for c in citations:
        if c.chunk_id not in allowed and c.source_id not in allowed:
            return False
    return True
