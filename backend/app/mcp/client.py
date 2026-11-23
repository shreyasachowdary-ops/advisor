"""LangChain MCP client — live path to advisor MCP stdio server.

Two modes (DECISIONS.md DEC-031):
- Persistent: ``start_persistent_session()`` (called from the FastAPI lifespan) starts
  ONE MCP server subprocess and keeps its session open. Tools are bound to it, so a
  tool call costs a JSON message, not a new Python process.
- Per-call (fallback): when no persistent session is running (scripts, tests without
  lifespan) or it has failed, tools from ``client.get_tools()`` start a fresh
  subprocess for every call, as before.
"""

import asyncio
import logging
import sys
from contextlib import AsyncExitStack
from functools import lru_cache
from time import perf_counter
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from app.config import BACKEND_ROOT, settings
from app.observability import get_request_id, get_trace
from app.tool_payload import parse_tool_payload

logger = logging.getLogger(__name__)

SERVER_NAME = "advisor"
MCP_SERVER_SCRIPT = BACKEND_ROOT / "mcp_server" / "server.py"

EXPECTED_TOOLS = frozenset(
    {
        "search_knowledge",
        "create_activity_plan",
        "get_school_policy",
        "submit_safeguarding_flag",
    }
)

_per_call_tools: list[BaseTool] | None = None
_per_call_lock = asyncio.Lock()

_persistent_stack: AsyncExitStack | None = None
_persistent_tools: list[BaseTool] | None = None


@lru_cache(maxsize=1)
def get_mcp_client() -> MultiServerMCPClient:
    command = settings.mcp_python_command or sys.executable
    return MultiServerMCPClient(
        {
            SERVER_NAME: {
                "transport": "stdio",
                "command": command,
                "args": [str(MCP_SERVER_SCRIPT)],
            }
        }
    )


async def start_persistent_session() -> bool:
    """Open one long-lived MCP session. Must be closed by ``stop_persistent_session``
    in the same task (the FastAPI lifespan does both)."""
    global _persistent_stack, _persistent_tools
    if _persistent_tools is not None:
        return True
    stack = AsyncExitStack()
    start = perf_counter()
    try:
        session = await stack.enter_async_context(get_mcp_client().session(SERVER_NAME))
        tools = await load_mcp_tools(session, server_name=SERVER_NAME)
    except Exception:
        logger.exception("MCP persistent session failed to start; using per-call mode")
        await stack.aclose()
        return False
    _persistent_stack, _persistent_tools = stack, tools
    logger.info(
        "MCP_PERSISTENT_SESSION started tools=%s elapsed_ms=%d",
        sorted(t.name for t in tools),
        int((perf_counter() - start) * 1000),
    )
    return True


async def stop_persistent_session() -> None:
    global _persistent_stack, _persistent_tools
    stack, _persistent_stack, _persistent_tools = _persistent_stack, None, None
    if stack is not None:
        try:
            await stack.aclose()
        except Exception:
            logger.warning("MCP persistent session did not close cleanly", exc_info=True)
        logger.info("MCP_PERSISTENT_SESSION stopped")


def _disable_persistent_tools(reason: str) -> None:
    """Stop routing calls to a broken session. The stack is closed at shutdown, in
    the task that opened it."""
    global _persistent_tools
    if _persistent_tools is not None:
        logger.error("MCP persistent session disabled (%s); switching to per-call mode", reason)
        _persistent_tools = None


def using_persistent_session() -> bool:
    return _persistent_tools is not None


def _result_metadata(tool_name: str, payload: dict[str, Any]) -> str:
    if tool_name == "search_knowledge":
        n = len(payload.get("results") or [])
        total = payload.get("total_chunks", "?")
        return f"results={n} total_chunks={total}"
    if tool_name == "create_activity_plan":
        return f"days={payload.get('days', '?')}"
    if tool_name == "get_school_policy":
        return f"policy_type={payload.get('policy_type', 'missing')}"
    if tool_name == "submit_safeguarding_flag":
        return f"status={payload.get('status', '?')}"
    if "error" in payload:
        return "error=1"
    return "ok=1"


async def _get_per_call_tools() -> list[BaseTool]:
    global _per_call_tools
    async with _per_call_lock:
        if _per_call_tools is None:
            _per_call_tools = await get_mcp_client().get_tools(server_name=SERVER_NAME)
        return _per_call_tools


async def get_mcp_tools() -> list[BaseTool]:
    start = perf_counter()
    tools = _persistent_tools if _persistent_tools is not None else await _get_per_call_tools()
    names = sorted(t.name for t in tools)
    tr = get_trace()
    load_ms = int((perf_counter() - start) * 1000)
    if tr:
        tr.mcp_tools_loaded = names
        tr.timings_ms["mcp_tools_load"] = load_ms
    logger.debug(
        "MCP_TOOLS request_id=%s tools=%s persistent=%s elapsed_ms=%d",
        get_request_id(),
        names,
        using_persistent_session(),
        load_ms,
    )
    missing = EXPECTED_TOOLS - set(names)
    if missing:
        logger.warning("MCP_TOOLS_MISSING request_id=%s missing=%s", get_request_id(), sorted(missing))
    return tools


async def _call(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    tool_map = {t.name: t for t in await get_mcp_tools()}
    if tool_name not in tool_map:
        return {"error": f"Unknown tool: {tool_name}"}
    return parse_tool_payload(await tool_map[tool_name].ainvoke(arguments))


async def invoke_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    rid = get_request_id()
    tr = get_trace()
    if tr:
        tr.mcp_tool_calls.append(tool_name)
    start = perf_counter()
    persistent = using_persistent_session()
    try:
        payload = await _call(tool_name, arguments)
    except Exception as exc:
        if not persistent:
            logger.exception("MCP tool %s failed request_id=%s", tool_name, rid)
            return {"error": str(exc)}
        # Transport/session failures raise; retry once without the persistent session.
        _disable_persistent_tools(f"{tool_name} raised {type(exc).__name__}")
        try:
            payload = await _call(tool_name, arguments)
        except Exception as retry_exc:
            logger.exception("MCP tool %s failed after retry request_id=%s", tool_name, rid)
            return {"error": str(retry_exc)}
    logger.info(
        "MCP_TOOL_RESULT request_id=%s tool_name=%s persistent=%s elapsed_ms=%d %s",
        rid,
        tool_name,
        persistent,
        int((perf_counter() - start) * 1000),
        _result_metadata(tool_name, payload),
    )
    return payload
