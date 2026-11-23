"""Deterministic routing for policy and activity-plan requests (DEC-027)."""

import pytest

from app.models import AgeBand, Audience, ChatRequest
from app.routing import detect_intent, detect_policy, is_plan_request, plan_goal
from mcp_server.tools.activity_plan import create_activity_plan


def _req(message: str, audience: Audience = Audience.PARENT) -> ChatRequest:
    return ChatRequest(message=message, audience=audience, age_band=AgeBand.FOUR_YEARS)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("What is our school policy on bullying?", (True, "bullying")),
        ("What does the pickup policy say about authorised adults?", (True, "pickup_safety")),
        ("Do we have a wellbeing policy?", (True, "wellbeing")),
        ("What are the school rules about behaviour?", (True, "behaviour_support")),
        ("Do we have a policy on screen time?", (True, None)),
        ("My child is being bullied at playtime", (False, None)),
    ],
)
def test_detect_policy(message, expected):
    assert detect_policy(message) == expected


@pytest.mark.parametrize(
    "message",
    [
        "Create a 5-day turn-taking activity plan for my 4-year-old.",
        "I need a weekly plan for morning routines at home.",
        "Five-day activity plan for sharing toys in the classroom.",
        "Can you make a separation anxiety plan for drop-off?",
        "Activity plan for turn-taking during play, 15 minutes a day.",
    ],
)
def test_eval_activity_prompts_are_plan_requests(message):
    assert is_plan_request(message)


def test_plain_question_is_not_a_plan_request():
    assert not is_plan_request("We had no plan for bedtime and it went badly.")
    assert not is_plan_request("How do I help my child share toys?")


@pytest.mark.parametrize(
    ("message", "goal"),
    [
        ("turn-taking plan", "turn_taking_during_play"),
        ("plan for sharing toys", "sharing_toys"),
        ("separation anxiety plan for drop-off", "separation_anxiety"),
        ("plan for a child who keeps hitting", "aggressive_behaviour"),
        ("weekly plan for morning routines", "morning_routine"),
        ("plan for learning colours", "default"),
    ],
)
def test_plan_goal(message, goal):
    assert plan_goal(message) == goal


def test_plan_args_use_parsed_days_minutes_and_setting():
    intent = detect_intent(_req("Make a ten-day sharing plan, 20 minutes a day", Audience.TEACHER))
    assert intent.plan_args == {
        "age_band": "4_years",
        "goal": "sharing_toys",
        "days": 10,
        "available_minutes_per_day": 20,
        "setting": "classroom",
    }


@pytest.mark.parametrize("days", [3, 5, 10, 14])
def test_plan_days_are_distinct_or_progressing(days):
    plan = create_activity_plan("4_years", "turn_taking_during_play", days=days)
    activities = [d["activity"] for d in plan["daily_plan"]]
    assert len(activities) == days
    assert not any(a.startswith("Day ") for a in activities), "stale template day labels leaked"
    if days <= 3:
        assert len(set(activities)) == days
