"""Unit tests for citation extraction from tool payloads."""

from langchain_core.messages import AIMessage, ToolMessage

from app.citations import (
    citations_from_hits,
    collect_search_hits_from_agent_messages,
    strip_model_sources_section,
)
from app.tool_payload import parse_tool_payload


def test_parse_mcp_style_text_block():
    raw = [
        {
            "type": "text",
            "text": '{"results": [{"chunk_id": "kb-1", "source_id": "kb-1", "title": "T", "url": "http://x"}]}',
        }
    ]
    payload = parse_tool_payload(raw)
    assert len(payload["results"]) == 1


def test_collect_hits_from_tool_message():
    msg = ToolMessage(
        content='{"results": [{"chunk_id": "kb-2", "source_id": "kb-2", "title": "CDC", "url": "https://cdc.gov"}]}',
        tool_call_id="1",
        name="search_knowledge",
    )
    hits = collect_search_hits_from_agent_messages([msg])
    assert len(hits) == 1
    cites = citations_from_hits(hits)
    assert cites[0].chunk_id == "kb-2"


def test_strip_model_sources_section():
    text = "Advice here.\n\n**Sources used:**\n- CDC (https://cdc.gov)\n"
    assert "Sources used" not in strip_model_sources_section(text)
    assert text.startswith("Advice here.")


def test_llm_prose_json_is_not_treated_as_retrieval():
    fake = AIMessage(
        content='{"results": [{"chunk_id": "invented", "source_id": "invented", "title": "Fake", "url": "https://evil.example"}]}'
    )
    hits = collect_search_hits_from_agent_messages([fake])
    assert hits == []
