"""MCP stdio server exposing advisor tools."""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Ensure backend root is on path when run as subprocess
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import ValidationError

from mcp_server.tool_inputs import (
    CreateActivityPlanInput,
    GetSchoolPolicyInput,
    SearchKnowledgeInput,
    SubmitSafeguardingFlagInput,
)
from mcp_server.tools.activity_plan import create_activity_plan
from mcp_server.tools.safeguarding import submit_safeguarding_flag
from mcp_server.tools.school_policy import get_school_policy
from mcp_server.tools.search_knowledge import search_knowledge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

server = Server("advisor-tools")

TOOL_INPUT_MODELS: dict[str, type] = {
    "search_knowledge": SearchKnowledgeInput,
    "create_activity_plan": CreateActivityPlanInput,
    "get_school_policy": GetSchoolPolicyInput,
    "submit_safeguarding_flag": SubmitSafeguardingFlagInput,
}

TOOL_HANDLERS = {
    "search_knowledge": lambda args: search_knowledge(**args),
    "create_activity_plan": lambda args: create_activity_plan(**args),
    "get_school_policy": lambda args: get_school_policy(**args),
    "submit_safeguarding_flag": lambda args: submit_safeguarding_flag(**args),
}

TOOL_DESCRIPTIONS = {
    "search_knowledge": (
        "Read-only vector retrieval from the curated early-childhood knowledge base (Chroma). "
        "Returns snippets with distance scores (lower = closer match)."
    ),
    "create_activity_plan": (
        "Generate a deterministic, editable, play-based multi-day activity plan. "
        "Use only when the user explicitly requests a structured plan."
    ),
    "get_school_policy": (
        "Read-only lookup of school policy for the trusted server-configured school. "
        "Argument: policy_type only (e.g. bullying, behaviour). School identity is not passed by the model."
    ),
    "submit_safeguarding_flag": (
        "Submit a safeguarding concern to the PoC audit log. Requires user_confirmed=true. "
        "Never call without explicit user confirmation."
    ),
}


def _validate_arguments(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    model = TOOL_INPUT_MODELS.get(name)
    if not model:
        raise ValueError(f"Unknown tool: {name}")
    return model.model_validate(arguments).model_dump()


@server.list_tools()
async def list_tools() -> list[Tool]:
    tools: list[Tool] = []
    for name, model in TOOL_INPUT_MODELS.items():
        tools.append(
            Tool(
                name=name,
                description=TOOL_DESCRIPTIONS[name],
                inputSchema=model.model_json_schema(),
            )
        )
    return tools


def _log_tool_result_meta(name: str, result: dict[str, Any]) -> None:
    if name == "search_knowledge":
        logger.info(
            "MCP_SERVER_TOOL_DONE tool=%s results=%s total_chunks=%s",
            name,
            len(result.get("results") or []),
            result.get("total_chunks"),
        )
    else:
        logger.info("MCP_SERVER_TOOL_DONE tool=%s keys=%s", name, list(result.keys())[:6])


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    logger.info("MCP_SERVER_TOOL_CALL tool=%s", name)
    try:
        args = _validate_arguments(name, arguments or {})
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            result = {"error": f"Unknown tool: {name}"}
        else:
            result = handler(args)
            if isinstance(result, dict) and "error" not in result:
                _log_tool_result_meta(name, result)
    except ValidationError as exc:
        logger.warning("Validation failed for tool %s: %s", name, exc)
        result = {"error": "invalid_arguments", "details": exc.errors()}
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        result = {"error": str(exc)}

    return [TextContent(type="text", text=json.dumps(result, separators=(",", ":")))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
