"""Citations = pre-retrieval hits + agent search_knowledge hits (DEC-026), never prose."""

from langchain_core.messages import AIMessage, ToolMessage

from app.agent import _resolve_citations


def _search_msg(*ids: str) -> ToolMessage:
    rows = ",".join(f'{{"chunk_id": "{i}", "source_id": "{i}", "title": "T{i}", "url": ""}}' for i in ids)
    return ToolMessage(content=f'{{"results": [{rows}]}}', tool_call_id="1", name="search_knowledge")


def test_context_hits_become_citations_without_agent_search():
    ctx_hits = [{"chunk_id": "kb-1", "source_id": "kb-1", "title": "CDC", "url": ""}]
    citations, hits = _resolve_citations(ctx_hits, [AIMessage(content="Advice.")])
    assert [c.chunk_id for c in citations] == ["kb-1"]
    assert len(hits) == 1


def test_agent_search_hits_are_merged_and_deduped():
    ctx_hits = [{"chunk_id": "kb-1", "source_id": "kb-1", "title": "CDC", "url": ""}]
    citations, _ = _resolve_citations(ctx_hits, [_search_msg("kb-1", "kb-2")])
    assert [c.chunk_id for c in citations] == ["kb-1", "kb-2"]


def test_policy_tool_output_never_becomes_a_citation():
    msg = ToolMessage(
        content='{"policy_type": "bullying", "text": "Restorative approaches."}',
        tool_call_id="1",
        name="get_school_policy",
    )
    citations, hits = _resolve_citations([], [msg])
    assert citations == []
    assert hits == []


def test_model_prose_sources_are_ignored():
    prose = AIMessage(content='Sources: {"results": [{"chunk_id": "kb-fake", "title": "Fake"}]}')
    citations, _ = _resolve_citations([], [prose])
    assert citations == []
