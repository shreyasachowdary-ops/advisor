"""Integration: LangChain MCP client → stdio server → custom tools."""

import pytest

from app.mcp.client import get_mcp_tools, invoke_mcp_tool


@pytest.mark.asyncio
async def test_mcp_tool_discovery_includes_custom_tools():
    tools = await get_mcp_tools()
    names = {t.name for t in tools}
    assert "search_knowledge" in names
    assert "create_activity_plan" in names
    assert "get_school_policy" in names
    assert "submit_safeguarding_flag" in names


@pytest.mark.asyncio
async def test_mcp_search_knowledge_via_client():
    result = await invoke_mcp_tool(
        "search_knowledge",
        {"query": "morning routine preschool", "audience": "parent", "max_results": 2},
    )
    assert "results" in result
    for row in result.get("results", []):
        assert "confidence" not in row
        if row:
            assert "distance" in row or result.get("total_chunks") == 0


@pytest.mark.asyncio
async def test_mcp_activity_plan_via_client():
    result = await invoke_mcp_tool(
        "create_activity_plan",
        {
            "age_band": "4_years",
            "goal": "turn_taking_during_play",
            "days": 10,
            "available_minutes_per_day": 30,
            "setting": "home",
        },
    )
    assert result["days"] == 10
    assert result["available_minutes_per_day"] == 30
    assert len(result["daily_plan"]) == 10


@pytest.mark.asyncio
async def test_mcp_school_policy_via_client():
    result = await invoke_mcp_tool("get_school_policy", {"policy_type": "behaviour_support"})
    assert result.get("policy_type") == "behaviour_support"
    assert "text" in result


@pytest.mark.asyncio
async def test_mcp_safeguarding_rejects_without_confirm():
    result = await invoke_mcp_tool(
        "submit_safeguarding_flag",
        {
            "category": "test",
            "severity": "low",
            "user_summary": "test",
            "user_confirmed": False,
        },
    )
    assert result.get("status") == "rejected"
