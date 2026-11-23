"""Readiness checks for optional dependencies."""

import logging

from app.mcp.client import get_mcp_tools

logger = logging.getLogger(__name__)


async def check_ollama() -> bool:
    from app.services.advisor import check_ollama_available

    return await check_ollama_available()


async def check_chroma() -> bool:
    try:
        from mcp_server.tools.search_knowledge import _get_collection

        _get_collection().count()
        return True
    except Exception as exc:
        logger.debug("Chroma readiness check failed: %s", exc)
        return False


async def check_mcp() -> bool:
    try:
        tools = await get_mcp_tools()
        names = {t.name for t in tools}
        required = {
            "search_knowledge",
            "create_activity_plan",
            "get_school_policy",
            "submit_safeguarding_flag",
        }
        return required.issubset(names)
    except Exception as exc:
        logger.warning("MCP readiness check failed: %s", exc)
        return False
