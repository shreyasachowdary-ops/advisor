"""Server-side retrieval for grounding and citation provenance (always via MCP)."""

from app.citations import citations_from_hits, hits_from_search_payload
from app.mcp.client import invoke_mcp_tool
from app.models import ChatRequest, Citation


async def fetch_citations_via_mcp(
    request: ChatRequest,
    max_results: int = 4,
    query: str | None = None,
) -> tuple[list[Citation], list[dict]]:
    """Invoke search_knowledge through MCP; return citations and raw hits for validation."""
    payload = await invoke_mcp_tool(
        "search_knowledge",
        {"query": query or request.message, "max_results": max_results},
    )
    hits = hits_from_search_payload(payload)
    return citations_from_hits(hits), hits
