"""FastAPI application — routes and wiring only."""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import settings
from app.models import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    HealthResponse,
    ReadyResponse,
    SafeguardingConfirmRequest,
    SafeguardingConfirmResponse,
)
from app.mcp.client import start_persistent_session, stop_persistent_session
from app.observability import get_trace, start_trace
from app.services.advisor import check_ollama_available, process_chat
from app.services.feedback import record_feedback
from app.services.readiness import check_chroma, check_mcp, check_ollama
from app.services.safeguarding import confirm_safeguarding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # One long-lived MCP tool process for the whole API process (DEC-031).
    # Startup and shutdown run in the same task, which the stdio transport requires.
    await start_persistent_session()
    try:
        yield
    finally:
        await stop_persistent_session()


app = FastAPI(
    title="Parent/Teacher Agentic Advisor",
    description="PoC advisory assistant for preschool parents and teachers",
    version=settings.kb_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "request_id=%s method=%s path=%s status=%s latency_ms=%d",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Liveness: API process is running."""
    ollama_ok = await check_ollama_available()
    return HealthResponse(status="ok", ollama=ollama_ok, kb_version=settings.kb_version)


@app.get("/api/ready", response_model=ReadyResponse)
async def ready():
    """Readiness: core dependencies for advisory chat."""
    ollama_ok = await check_ollama()
    chroma_ok = await check_chroma()
    mcp_ok = await check_mcp()
    return ReadyResponse(
        ready=chroma_ok and mcp_ok,
        ollama=ollama_ok,
        chroma=chroma_ok,
        mcp=mcp_ok,
        kb_version=settings.kb_version,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    rid = getattr(http_request.state, "request_id", str(uuid.uuid4()))
    start_trace(rid)
    logger.info(
        "request_id=%s chat session=%s audience=%s age=%s msg_len=%d",
        rid,
        request.session_id or "(new)",
        request.audience,
        request.age_band,
        len(request.message),
    )
    response = await process_chat(request)
    _log_chat_complete(rid)
    return response


def _log_chat_complete(rid: str) -> None:
    tr = get_trace()
    if tr:
        logger.info(
            "CHAT_COMPLETE request_id=%s timings_ms=%s mcp_tools=%s mcp_calls=%s "
            "citations_hits=%d citation_mcp_fallback=%s ollama_chat_calls=%d",
            rid,
            tr.timings_ms,
            tr.mcp_tools_loaded,
            tr.mcp_tool_calls,
            tr.citation_hit_count,
            tr.citation_mcp_fallback,
            len(tr.ollama_chat_calls),
        )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, http_request: Request):
    """Same answer as /api/chat, sent as Server-Sent Events so text shows while it is written.

    Events: ``delta`` {"text": ...} pieces of the model's answer (may be none, e.g. safety
    replies), then one ``done`` with the full ChatResponse, or ``error`` {"detail": ...}.
    The ``done`` answer is the cleaned final text and replaces what was streamed.
    """
    rid = getattr(http_request.state, "request_id", str(uuid.uuid4()))
    start_trace(rid)
    logger.info(
        "request_id=%s chat_stream session=%s audience=%s age=%s msg_len=%d",
        rid,
        request.session_id or "(new)",
        request.audience,
        request.age_band,
        len(request.message),
    )
    queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()

    async def on_token(text: str) -> None:
        await queue.put(("delta", {"text": text}))

    async def run() -> None:
        try:
            response = await process_chat(request, on_token=on_token)
            _log_chat_complete(rid)
            await queue.put(("done", response.model_dump(mode="json")))
        except Exception:
            logger.exception("request_id=%s chat_stream failed", rid)
            await queue.put(("error", {"detail": "The advisor could not answer right now."}))

    # Created after start_trace so the task shares this request's trace context.
    task = asyncio.create_task(run())

    async def events():
        try:
            while True:
                event, data = await queue.get()
                yield _sse(event, data)
                if event in ("done", "error"):
                    return
        finally:
            if not task.done():  # client went away mid-answer
                task.cancel()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/feedback")
async def feedback(body: FeedbackRequest):
    return record_feedback(body)


@app.post("/api/safeguarding/confirm", response_model=SafeguardingConfirmResponse)
async def safeguarding_confirm(body: SafeguardingConfirmRequest):
    if not body.user_confirmed:
        raise HTTPException(
            status_code=400,
            detail="user_confirmed must be true to submit a safeguarding flag",
        )
    return await confirm_safeguarding(body)
