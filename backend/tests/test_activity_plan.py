"""Activity plan tool — schema vs implementation."""

from app.plan_params import extract_activity_plan_params
from mcp_server.tools.activity_plan import MAX_PLAN_DAYS, create_activity_plan


def test_create_activity_plan_respects_10_days_and_30_minutes():
    plan = create_activity_plan(
        age_band="4_years",
        goal="turn_taking_during_play",
        days=10,
        available_minutes_per_day=30,
        setting="home",
    )
    assert plan["days"] == 10
    assert plan["available_minutes_per_day"] == 30
    assert len(plan["daily_plan"]) == 10
    assert all(d["duration_minutes"] == 30 for d in plan["daily_plan"])


def test_create_activity_plan_caps_at_max_days():
    plan = create_activity_plan(
        age_band="4_years",
        goal="default",
        days=99,
        available_minutes_per_day=15,
    )
    assert plan["days"] == MAX_PLAN_DAYS
    assert len(plan["daily_plan"]) == MAX_PLAN_DAYS


def test_extract_plan_params_from_message():
    p = extract_activity_plan_params("Give me a 10-day plan with 30 minutes a day for turn taking.")
    assert p.days == 10
    assert p.available_minutes_per_day == 30
