"""API endpoint tests (contract only — no Ollama/Chroma needed; DEC-034).

The model is reported down and context preparation is stubbed, so normal chats take
the degraded template path. The live path is covered by tests/integration/.
"""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

import app.services.advisor as advisor_mod
from app.agent import TurnContext
from app.main import app


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setattr(advisor_mod, "check_ollama_available", AsyncMock(return_value=False))
    monkeypatch.setattr(advisor_mod, "prepare_context", AsyncMock(return_value=TurnContext()))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "kb_version" in data


@pytest.mark.asyncio
async def test_chat_normal(client):
    resp = await client.post(
        "/api/chat",
        json={
            "message": "My 4-year-old is upset at preschool drop-off.",
            "audience": "parent",
            "age_band": "4_years",
            "language": "en",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "normal"
    assert len(data["answer"]) > 0
    assert data["message_id"]
    assert data["session_id"]


@pytest.mark.asyncio
async def test_chat_urgent_escalation(client):
    resp = await client.post(
        "/api/chat",
        json={
            "message": "A child told me they want to kill themselves.",
            "audience": "teacher",
            "age_band": "5_years",
            "language": "en",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "urgent"
    assert data["requires_human_review"] is True
    assert data["requires_confirmation"] is True
    assert data["safeguarding_event_id"] is None


@pytest.mark.asyncio
async def test_feedback_requires_message_id(client):
    chat = await client.post(
        "/api/chat",
        json={
            "message": "How do I help with sharing?",
            "audience": "parent",
            "age_band": "4_years",
            "language": "en",
        },
    )
    mid = chat.json()["message_id"]
    sid = chat.json()["session_id"]
    resp = await client.post(
        "/api/feedback",
        json={"rating": "helpful", "message_id": mid, "session_id": sid},
    )
    assert resp.status_code == 200
    assert resp.json()["message_id"] == mid


@pytest.mark.asyncio
async def test_safeguarding_rejects_unconfirmed(client):
    resp = await client.post(
        "/api/safeguarding/confirm",
        json={
            "message_id": "00000000-0000-0000-0000-000000000001",
            "category": "abuse",
            "severity": "high",
            "user_summary": "test",
            "user_confirmed": False,
        },
    )
    assert resp.status_code == 400
