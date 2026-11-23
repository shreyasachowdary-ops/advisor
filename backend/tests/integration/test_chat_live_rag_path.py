"""Live /api/chat RAG path: agent → MCP → search_knowledge → citations (no direct tool imports in API)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.citations import validate_citations_subset_of_hits
from app.main import app
from app.mcp.client import invoke_mcp_tool
from app.safety import classify_safety
from app.models import RiskLevel


ROUTINE_QUERY = "How can I create a predictable daily routine for my child?"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=600.0) as ac:
        yield ac


@pytest.mark.asyncio
async def test_live_chat_rag_routine_query_end_to_end(client):
    safety = classify_safety(ROUTINE_QUERY)
    assert safety.risk_level == RiskLevel.NORMAL

    mcp_payload = await invoke_mcp_tool(
        "search_knowledge",
        {
            "query": ROUTINE_QUERY,
            "audience": "parent",
            "age_band": "4_years",
            "max_results": 4,
        },
    )
    assert "results" in mcp_payload
    if not mcp_payload.get("results"):
        pytest.skip("Chroma KB empty — cannot verify live RAG citations")

    for row in mcp_payload["results"]:
        assert row.get("chunk_id")
        assert row.get("title")

    resp = await client.post(
        "/api/chat",
        json={
            "message": ROUTINE_QUERY,
            "audience": "parent",
            "age_band": "4_years",
            "language": "en",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "normal"
    assert data["citations"], "ChatResponse.citations must come from MCP retrieval, not LLM text"
    assert data["sources"] == data["citations"]

    # After chat, MCP may return a slightly different top-k than the pre-call snapshot;
    # every structured citation must still exist in a fresh MCP retrieval for this query.
    post_mcp = await invoke_mcp_tool(
        "search_knowledge",
        {
            "query": ROUTINE_QUERY,
            "audience": "parent",
            "age_band": "4_years",
            "max_results": 8,
        },
    )
    allowed = {
        (r.get("chunk_id") or r.get("source_id")) for r in post_mcp.get("results", [])
    }
    from app.models import Citation

    structured = [Citation(**c) for c in data["citations"]]
    assert validate_citations_subset_of_hits(structured, post_mcp.get("results", []))
    for c in data["citations"]:
        assert c["chunk_id"] in allowed or c["source_id"] in allowed

    assert "sources used" not in data["answer"].lower()
