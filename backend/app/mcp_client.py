"""Backward-compatible re-export — prefer app.mcp.client."""

from app.mcp.client import (
    get_mcp_client,
    get_mcp_tools,
    invoke_mcp_tool,
    start_persistent_session,
    stop_persistent_session,
)

__all__ = [
    "get_mcp_client",
    "get_mcp_tools",
    "invoke_mcp_tool",
    "start_persistent_session",
    "stop_persistent_session",
]
