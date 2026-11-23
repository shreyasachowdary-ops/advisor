"""Integration: /api/chat citations must come from MCP search_knowledge hits only."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.citations import citations_from_hits, validate_citations_subset_of_hits
from app.main import app
from app.mcp.client import invoke_mcp_tool
from app.services.retrieval import fetch_citations_via_mcp
from app.models import ChatRequest, Audience, AgeBand


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=300.0) as ac:
        yield ac


@pytest.mark.asyncio
async def test_mcp_search_returns_provenance_metadata():
    payload = await invoke_mcp_tool(
        "search_knowledge",
        {
            "query": "preschool drop-off morning routine",
            "audience": "parent",
            "age_band": "4_years",
            "max_results": 4,
        },
    )
    assert "results" in payload
    if payload["results"]:
        row = payload["results"][0]
        assert row.get("chunk_id")
        assert row.get("source_id")
        assert row.get("title")
        assert "confidence" not in row


@pytest.mark.asyncio
async def test_citations_extracted_from_mcp_hits():
    request = ChatRequest(
        message="My 4-year-old is upset at preschool drop-off.",
        audience=Audience.PARENT,
        age_band=AgeBand.FOUR_YEARS,
    )
    citations, hits = await fetch_citations_via_mcp(request)
    if not hits:
        pytest.skip("Chroma KB empty on this environment")
    assert citations
    assert validate_citations_subset_of_hits(citations, hits)
    for c in citations:
        assert c.chunk_id
        assert c.source_id


@pytest.mark.asyncio
async def test_chat_response_citations_match_mcp_retrieval(client):
    request_body = {
        "message": "My 4-year-old is upset at preschool drop-off.",
        "audience": "parent",
        "age_band": "4_years",
        "language": "en",
    }
    mcp_payload = await invoke_mcp_tool(
        "search_knowledge",
        {
            "query": request_body["message"],
            "audience": request_body["audience"],
            "age_band": request_body["age_band"],
            "max_results": 4,
        },
    )
    if not mcp_payload.get("results"):
        pytest.skip("Chroma KB empty on this environment")

    allowed_ids = {
        (r.get("chunk_id") or r.get("source_id"))
        for r in mcp_payload["results"]
    }

    resp = await client.post("/api/chat", json=request_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "normal"
    assert data["citations"], "citations must be populated from MCP retrieval"
    for c in data["citations"]:
        assert c["chunk_id"] in allowed_ids or c["source_id"] in allowed_ids
    assert data["sources"] == data["citations"]
    answer_lower = data["answer"].lower()
    assert "sources used" not in answer_lower, "LLM sources section must be stripped; use citations field"


@pytest.mark.asyncio
async def test_fabricated_citation_not_in_api_response(client):
    """Structured citations cannot include ids outside the MCP retrieval set for this query."""
    query = "turn taking during play with peers"
    mcp_payload = await invoke_mcp_tool(
        "search_knowledge",
        {"query": query, "audience": "teacher", "max_results": 4},
    )
    allowed = {(r.get("chunk_id") or r.get("source_id")) for r in mcp_payload.get("results", [])}
    if not allowed:
        pytest.skip("Chroma KB empty")

    resp = await client.post(
        "/api/chat",
        json={
            "message": query,
            "audience": "teacher",
            "age_band": "4_years",
            "language": "en",
        },
    )
    data = resp.json()
    for c in data.get("citations", []):
        assert c["chunk_id"] in allowed
        assert c["source_id"] in allowed
    fake = citations_from_hits(
        [{"chunk_id": "kb-fake-not-in-kb", "source_id": "kb-fake-not-in-kb", "title": "Fake"}]
    )
    assert not validate_citations_subset_of_hits(fake, mcp_payload.get("results", []))
