"""Canonical Pydantic input models for MCP tools (validation + JSON schema)."""

from typing import Literal

from pydantic import BaseModel, Field

# Template keys in mcp_server/tools/activity_plan.py (enum so the model sees valid values).
ActivityGoal = Literal[
    "turn_taking_during_play",
    "morning_routine",
    "sharing_toys",
    "separation_anxiety",
    "aggressive_behaviour",
    "default",
]

# Policy keys in data/policies/<school_id>.json for the PoC school.
PolicyType = Literal["bullying", "wellbeing", "pickup_safety", "behaviour_support"]


class SearchKnowledgeInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    # No age_band or audience filter: the whole KB applies to parents and teachers of
    # 2–5 year olds (DECISIONS.md DEC-025, DEC-033). Extra fields are ignored.
    topics: list[str] | None = None
    max_results: int = Field(default=4, ge=1, le=10)


class CreateActivityPlanInput(BaseModel):
    age_band: Literal["2_years", "3_years", "4_years", "5_years"]
    goal: ActivityGoal = Field(..., description="Template to use; 'default' for anything else.")
    available_minutes_per_day: int = Field(default=15, ge=5, le=120)
    days: int = Field(default=5, ge=1, le=14)
    setting: Literal["home", "classroom"] = "home"


class GetSchoolPolicyInput(BaseModel):
    """School/tenant identity is server-side only (settings.school_id), not from the model."""

    policy_type: PolicyType


class SubmitSafeguardingFlagInput(BaseModel):
    category: str = Field(..., min_length=1, max_length=100)
    severity: Literal["low", "medium", "high", "critical"]
    user_summary: str = Field(..., min_length=1, max_length=2000)
    user_confirmed: bool = False
