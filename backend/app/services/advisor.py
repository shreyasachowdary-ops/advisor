"""Advisor chat service — safety gate, sessions, LangChain agent."""

import logging
import time
import uuid

import httpx

from app.agent import (
    TokenCallback,
    TurnContext,
    prepare_context,
    run_advisor_agent,
    run_fallback_via_mcp,
)
from app.citations import strip_model_sources_section
from app.observability import get_trace
from app.config import settings
from app.models import ChatRequest, ChatResponse, RiskLevel
from app.safety import classify_safety
from app.sessions.store import session_store

logger = logging.getLogger(__name__)

_OLLAMA_CACHE_TTL = 15.0
_ollama_cache: tuple[float, bool] | None = None
_ollama_http: httpx.AsyncClient | None = None


def _ollama_client() -> httpx.AsyncClient:
    global _ollama_http
    if _ollama_http is None or _ollama_http.is_closed:
        _ollama_http = httpx.AsyncClient(timeout=5.0)
    return _ollama_http


async def check_ollama_available() -> bool:
    global _ollama_cache
    now = time.monotonic()
    if _ollama_cache and now - _ollama_cache[0] < _OLLAMA_CACHE_TTL:
        return _ollama_cache[1]
    ok = False
    try:
        resp = await _ollama_client().get(f"{settings.ollama_base_url}/api/tags")
        ok = resp.status_code == 200
    except Exception:
        ok = False
    _ollama_cache = (now, ok)
    return ok


def _escalation_response(
    request: ChatRequest,
    session_id: str,
    risk_level: RiskLevel,
    answer: str,
    *,
    category: str | None = None,
) -> ChatResponse:
    return ChatResponse(
        message_id=str(uuid.uuid4()),
        session_id=session_id,
        answer=answer,
        risk_level=risk_level,
        citations=[],
        requires_human_review=True,
        requires_confirmation=risk_level == RiskLevel.URGENT,
        safeguarding_event_id=None,
        safeguarding_category=category if risk_level == RiskLevel.URGENT else None,
        suggested_follow_up=(
            "Would you like general support ideas while you arrange a professional conversation?"
            if risk_level == RiskLevel.REFERRAL
            else None
        ),
    )


async def process_chat(
    request: ChatRequest,
    use_ollama: bool = True,
    on_token: TokenCallback | None = None,
) -> ChatResponse:
    """Answer one chat turn. on_token, if given, receives the model's text as it is written;
    the returned response is still the complete, cleaned answer."""
    session = session_store.resolve(request.session_id)
    session_id = session.session_id
    session_store.append(session_id, "user", request.message)

    safety = classify_safety(request.message)

    if safety.risk_level == RiskLevel.URGENT:
        resp = _escalation_response(
            request,
            session_id,
            RiskLevel.URGENT,
            safety.escalation_message or "",
            category=safety.matched_category,
        )
        session_store.append(session_id, "assistant", resp.answer)
        return resp

    if safety.risk_level == RiskLevel.REFERRAL:
        resp = _escalation_response(
            request,
            session_id,
            RiskLevel.REFERRAL,
            safety.escalation_message or "",
        )
        session_store.append(session_id, "assistant", resp.answer)
        return resp

    ollama_ok = use_ollama and await check_ollama_available()
    history = session.as_langchain_turns()[:-1]

    # Retrieval and clearly requested policy/plan tools run in code first, so both the
    # agent and the template fallback get them (DEC-026, DEC-027).
    context: TurnContext | None = None
    try:
        context = await prepare_context(request, history)
    except Exception as exc:
        logger.exception("Context preparation failed: %s", exc)

    try:
        if ollama_ok and context is not None:
            result = await run_advisor_agent(
                request, history_messages=history, context=context, on_token=on_token
            )
        else:
            logger.warning("Ollama or context unavailable — template fallback (degraded)")
            result = await run_fallback_via_mcp(request, context)
    except Exception as exc:
        logger.exception("Agent pipeline failed, using template fallback (degraded): %s", exc)
        result = await run_fallback_via_mcp(request, context)

    answer = strip_model_sources_section(result.answer)

    resp = ChatResponse(
        message_id=str(uuid.uuid4()),
        session_id=session_id,
        answer=answer,
        risk_level=RiskLevel.NORMAL,
        citations=result.citations,
        sources=result.citations,
        suggested_follow_up=result.follow_up,
        requires_human_review=False,
        requires_confirmation=False,
        activity_plan=result.activity_plan,
        degraded=result.degraded,
    )
    session_store.append(session_id, "assistant", answer)
    tr = get_trace()
    if tr:
        logger.info(
            "request_id=%s chat done degraded=%s citations=%d tools=%s",
            tr.request_id,
            result.degraded,
            len(result.citations),
            tr.mcp_tool_calls,
        )
    return resp
