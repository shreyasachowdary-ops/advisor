"""Chat flow with a fake model and fake MCP tools — no Ollama, Chroma, or subprocess.

Covers DEC-026 (retrieval first), DEC-027 (policy/plan routing), DEC-028 (no
safeguarding tool for the model), DEC-029 (off-topic), DEC-030 (degraded flag).
"""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

import app.agent as agent_mod
import app.services.advisor as advisor_mod
from app.config import settings
from app.models import AgeBand, Audience, ChatRequest

HIT = {
    "chunk_id": "kb-manodarpan-routines-015",
    "source_id": "kb-manodarpan-routines-015",
    "title": "Manodarpan — Morning Routines",
    "url": "https://manodarpan.education.gov.in/",
    "text": "A consistent morning routine reduces preschool drop-off stress.",
}
POLICY = {
    "school_id": "poc_test_school",
    "school_name": "PoC Test Preschool",
    "policy_type": "bullying",
    "title": "Anti-Bullying Policy",
    "text": "Restorative conversations are preferred over punishment.",
    "contacts": {},
    "last_reviewed": "2025-08-01",
}
PLAN = {"plan_id": "plan_x", "title": "Turn-Taking During Play", "days": 5,
        "available_minutes_per_day": 15, "setting": "home", "daily_plan": [{"day": 1}]}

ALL_TOOLS = ["search_knowledge", "create_activity_plan", "get_school_policy", "submit_safeguarding_flag"]


class FakeAgent:
    def __init__(self, reply: str = "Here is some practical advice.", error: Exception | None = None):
        self.reply, self.error, self.prompt = reply, error, ""

    async def ainvoke(self, payload, config=None):
        if self.error:
            raise self.error
        self.prompt = payload["messages"][-1]["content"]
        return {"messages": [AIMessage(content=self.reply)]}


@pytest.fixture
def fake_stack(monkeypatch):
    """Fake MCP tools + fake compiled agent; records what the model was given."""
    state = SimpleNamespace(agent=FakeAgent(), tools_given=None, hits=[HIT], tool_calls=[])

    async def fake_fetch(request, max_results=4, query=None):
        return [], list(state.hits)

    async def fake_invoke(name, args):
        state.tool_calls.append(name)
        return POLICY if name == "get_school_policy" else PLAN if name == "create_activity_plan" else {}

    async def fake_tools():
        return [SimpleNamespace(name=n) for n in ALL_TOOLS]

    async def fake_compiled(tools):
        state.tools_given = [t.name for t in tools]
        return state.agent

    monkeypatch.setattr(agent_mod, "fetch_citations_via_mcp", fake_fetch)
    monkeypatch.setattr(agent_mod, "invoke_mcp_tool", fake_invoke)
    monkeypatch.setattr(agent_mod, "get_mcp_tools", fake_tools)
    monkeypatch.setattr(agent_mod, "_compiled_advisor_agent", fake_compiled)
    monkeypatch.setattr(advisor_mod, "check_ollama_available", AsyncMock(return_value=True))
    return state


def _req(message: str) -> ChatRequest:
    return ChatRequest(message=message, audience=Audience.PARENT, age_band=AgeBand.FOUR_YEARS)


async def test_retrieved_passages_reach_the_model_and_become_citations(fake_stack):
    resp = await advisor_mod.process_chat(_req("My 4-year-old cries at drop-off"))
    assert HIT["text"] in fake_stack.agent.prompt
    assert [c.source_id for c in resp.citations] == [HIT["source_id"]]
    assert resp.degraded is False
    assert resp.suggested_follow_up


async def test_model_never_gets_the_safeguarding_tool(fake_stack):
    await advisor_mod.process_chat(_req("How do I help with sharing?"))
    assert "submit_safeguarding_flag" not in fake_stack.tools_given
    assert set(fake_stack.tools_given) == set(agent_mod.AGENT_TOOL_NAMES)


async def test_policy_question_injects_real_policy_text(fake_stack):
    await advisor_mod.process_chat(_req("What is our school policy on bullying?"))
    assert "get_school_policy" in fake_stack.tool_calls
    assert POLICY["text"] in fake_stack.agent.prompt
    assert "ONLY this text" in fake_stack.agent.prompt


async def test_plan_request_returns_structured_plan(fake_stack):
    resp = await advisor_mod.process_chat(_req("Create a 5-day turn-taking activity plan"))
    assert "create_activity_plan" in fake_stack.tool_calls
    assert resp.activity_plan == PLAN
    assert "Do NOT write your own day-by-day plan" in fake_stack.agent.prompt


async def test_off_topic_question_has_no_citations_or_follow_up(fake_stack):
    fake_stack.hits = []
    resp = await advisor_mod.process_chat(_req("How do I fix my car's brakes?"))
    assert resp.citations == []
    assert resp.suggested_follow_up is None
    assert "outside what you can help with" in fake_stack.agent.prompt


async def test_model_down_gives_degraded_answer_with_policy(fake_stack, monkeypatch):
    monkeypatch.setattr(advisor_mod, "check_ollama_available", AsyncMock(return_value=False))
    resp = await advisor_mod.process_chat(_req("What is our school policy on bullying?"))
    assert resp.degraded is True
    assert resp.answer.startswith("The AI advisor is unavailable")
    assert POLICY["text"] in resp.answer
    assert resp.citations


async def test_agent_error_gives_degraded_answer(fake_stack):
    fake_stack.agent = FakeAgent(error=RuntimeError("model crashed"))
    resp = await advisor_mod.process_chat(_req("Create a 5-day turn-taking activity plan"))
    assert resp.degraded is True
    assert resp.activity_plan == PLAN


def test_tests_never_write_to_the_real_audit_folder():
    assert settings.audit_dir == os.environ["AUDIT_DIR"]
    assert "advisor-test-audit-" in settings.audit_dir
