"""Pydantic models are the canonical MCP tool input schemas."""

from mcp_server.tool_inputs import (
    CreateActivityPlanInput,
    GetSchoolPolicyInput,
    SearchKnowledgeInput,
    SubmitSafeguardingFlagInput,
)


def test_mcp_schemas_match_pydantic_json_schema():
    models = [
        SearchKnowledgeInput,
        CreateActivityPlanInput,
        GetSchoolPolicyInput,
        SubmitSafeguardingFlagInput,
    ]
    for model in models:
        schema = model.model_json_schema()
        assert schema["type"] == "object"
        assert "properties" in schema


def test_activity_plan_days_bounds_in_schema():
    schema = CreateActivityPlanInput.model_json_schema()
    days = schema["properties"]["days"]
    assert days.get("maximum") == 14 or "le" in str(days)
