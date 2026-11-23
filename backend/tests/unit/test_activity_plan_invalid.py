"""Activity plan validation edge cases."""

import pytest
from pydantic import ValidationError

from mcp_server.tool_inputs import CreateActivityPlanInput
from mcp_server.tools.activity_plan import create_activity_plan


def test_pydantic_rejects_days_over_14():
    with pytest.raises(ValidationError):
        CreateActivityPlanInput(age_band="4_years", goal="default", days=20)


def test_implementation_clamps_extreme_minutes():
    plan = create_activity_plan(
        age_band="4_years",
        goal="default",
        days=3,
        available_minutes_per_day=999,
    )
    assert plan["available_minutes_per_day"] <= 120
