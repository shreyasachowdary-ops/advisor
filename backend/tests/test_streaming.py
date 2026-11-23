"""Streaming chat (/api/chat/stream) — fake model and tools, no Ollama, Chroma, or subprocess."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_ollama import ChatOllama

import app.agent as agent_mod
import app.main as main_mod
import app.services.advisor as advisor_mod
from app.main import app

PIECES = ["Try ", "naming ", "colours ", "during play."]
HIT = {
    "chunk_id": "kb-colours-001",
    "source_id": "kb-colours-001",
    "title": "Colours Through Play",
    "url": "",
    "text": "Children learn colours by sorting and naming everyday objects.",
}


class FakeStreamingAgent:
    """Stands in for the compiled agent: writes its reply through the token sink like the model."""

    async def ainvoke(self, payload, config=None):
        sink = agent_mod._token_sink.get()
        if sink:
            for piece in PIECES:
                await sink(piece)
        return {"messages": [AIMessage(content="".join(PIECES) + "\n\n**Sources used**\n- [1] Colours")]}


@pytest.fixture
async def client(monkeypatch):
    async def fake_fetch(request, max_results=4, query=None):
        return [], [HIT]

    async def fake_compiled(tools):
        return FakeStreamingAgent()

    async def fake_tools():
        return [SimpleNamespace(name=n) for n in agent_mod.AGENT_TOOL_NAMES]

    monkeypatch.setattr(agent_mod, "fetch_citations_via_mcp", fake_fetch)
    monkeypatch.setattr(agent_mod, "invoke_mcp_tool", AsyncMock(return_value={}))
    monkeypatch.setattr(agent_mod, "get_mcp_tools", fake_tools)
    monkeypatch.setattr(agent_mod, "_compiled_advisor_agent", fake_compiled)
    monkeypatch.setattr(advisor_mod, "check_ollama_available", AsyncMock(return_value=True))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _events(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


async def _stream(client, message: str) -> list[tuple[str, dict]]:
    resp = await client.post("/api/chat/stream", json={"message": message})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["x-accel-buffering"] == "no"
    return _events(resp.text)


async def test_stream_sends_pieces_then_full_cleaned_answer(client):
    events = await _stream(client, "How can I help my 3-year-old learn colours through play?")
    deltas = [d["text"] for e, d in events if e == "delta"]
    assert deltas == PIECES
    event, done = events[-1]
    assert event == "done"
    # The final answer is cleaned (model 'Sources used' removed) and carries citations.
    assert done["answer"] == "".join(PIECES)
    assert done["risk_level"] == "normal"
    assert [c["source_id"] for c in done["citations"]] == [HIT["source_id"]]
    assert done["session_id"] and done["message_id"]


async def test_stream_urgent_message_never_reaches_model(client):
    events = await _stream(client, "A child told me they want to kill themselves.")
    assert [e for e, _ in events] == ["done"]
    assert events[0][1]["risk_level"] == "urgent"
    assert events[0][1]["requires_confirmation"] is True


async def test_stream_failure_sends_error_event(client, monkeypatch):
    monkeypatch.setattr(main_mod, "process_chat", AsyncMock(side_effect=RuntimeError("boom")))
    events = await _stream(client, "How do I help with sharing?")
    assert events == [("error", {"detail": "The advisor could not answer right now."})]


async def test_plain_chat_endpoint_is_unchanged(client):
    resp = await client.post("/api/chat", json={"message": "How can I help my child learn colours?"})
    assert resp.status_code == 200
    assert resp.json()["answer"] == "".join(PIECES)


async def test_streaming_model_passes_text_to_sink_and_keeps_full_message(monkeypatch):
    async def fake_astream(self, messages, stop=None, run_manager=None, **kwargs):
        for piece in PIECES:
            yield ChatGenerationChunk(message=AIMessageChunk(content=piece))

    monkeypatch.setattr(agent_mod.StreamingChatOllama, "_astream", fake_astream)
    llm = agent_mod.StreamingChatOllama(model="fake")
    got: list[str] = []

    async def sink(text: str) -> None:
        got.append(text)

    token = agent_mod._token_sink.set(sink)
    try:
        result = await llm._agenerate([HumanMessage(content="hi")])
    finally:
        agent_mod._token_sink.reset(token)
    assert got == PIECES
    assert result.generations[0].message.content == "".join(PIECES)


async def test_streaming_model_without_sink_behaves_like_chat_ollama(monkeypatch):
    plain = ChatResult(generations=[])
    monkeypatch.setattr(ChatOllama, "_agenerate", AsyncMock(return_value=plain))
    llm = agent_mod.StreamingChatOllama(model="fake")
    assert await llm._agenerate([HumanMessage(content="hi")]) is plain
