"""Retrieval filtering behavior (deterministic)."""

from mcp_server.tool_inputs import SearchKnowledgeInput
from mcp_server.tools.search_knowledge import _build_where_clause, search_knowledge


def test_age_and_audience_are_not_filters():
    """DEC-025 / DEC-033: only topics filter; stray age_band/audience args are ignored."""
    inp = SearchKnowledgeInput.model_validate(
        {"query": "counting", "audience": "parent", "age_band": "5_years"}
    )
    assert _build_where_clause(inp) is None
    assert _build_where_clause(SearchKnowledgeInput(query="x", topics=["play"])) == {
        "topic": {"$in": ["play"]}
    }


def test_search_returns_list_for_query():
    result = search_knowledge(query="morning drop-off routine", max_results=4)
    assert "results" in result
    assert isinstance(result["results"], list)
    for row in result["results"]:
        assert "distance" in row or result.get("total_chunks") == 0
        assert "confidence" not in row


def test_parent_can_find_teacher_tagged_passage():
    """DEC-033: the numeracy passage is tagged teacher-only but answers a parent's question."""
    result = search_knowledge(query="How can I teach counting at home?", max_results=4)
    if not result.get("total_chunks"):
        return
    assert "kb-ncert-numeracy-010" in [r["chunk_id"] for r in result["results"]]


def test_off_topic_query_is_dropped_by_cutoff():
    """DEC-029: unrelated questions retrieve nothing instead of 4 weak matches."""
    result = search_knowledge(query="How do I fix my car's brakes?", max_results=4)
    assert result["results"] == []


def test_search_with_topic_filter():
    result = search_knowledge(query="sharing toys", topics=["behaviour"], max_results=4)
    assert all(r["topic"] == "behaviour" for r in result["results"])


def test_search_no_results_still_structured():
    result = search_knowledge(query="xyznonexistenttopic999", max_results=4)
    assert isinstance(result["results"], list)
