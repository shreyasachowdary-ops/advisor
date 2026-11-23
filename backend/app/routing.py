"""Deterministic intent routing for school-policy and activity-plan requests.

These tools are called in code when the message clearly asks for them, so a small
model cannot skip them or invent a policy/plan (DECISIONS.md DEC-027).
"""

import re
from dataclasses import dataclass
from typing import get_args

from app.models import Audience, ChatRequest
from app.plan_params import extract_activity_plan_params
from mcp_server.tool_inputs import ActivityGoal, PolicyType

POLICY_TYPES: tuple[str, ...] = get_args(PolicyType)

_POLICY_RE = re.compile(r"\bpolic(y|ies)\b|\bschool'?s?\s+rules?\b", re.I)

# Order matters: first match wins.
_POLICY_TYPE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("bullying", re.compile(r"\bbull(y|ied|ies|ying)\b", re.I)),
    ("pickup_safety", re.compile(r"\bpick[- ]?up|\bdrop[- ]?off|\bcollect(ion|ing)?\b|authori[sz]ed\s+adult", re.I)),
    ("wellbeing", re.compile(r"well[- ]?being|mental\s+health|emotional\s+health|wellness", re.I)),
    ("behaviour_support", re.compile(r"\bbehaviou?r|\bdiscipline|\bconduct\b", re.I)),
]

_PLAN_WORD_RE = re.compile(r"\bplans?\b", re.I)
_PLAN_CONTEXT_RE = re.compile(
    r"\b(activit\w*|days?|weeks?|weekly|daily|create|make|give|build|design|write|prepare)\b", re.I
)

_GOAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("turn_taking_during_play", re.compile(r"turn[- ]?taking|take\s+turns|taking\s+turns|wait(ing)?\s+(for\s+)?(a|their|his|her)\s+turn", re.I)),
    ("sharing_toys", re.compile(r"\bshar(e|es|ing)\b", re.I)),
    ("separation_anxiety", re.compile(r"separation|drop[- ]?off|goodbye|clingy|cries\s+when\s+(i|we)\s+leave", re.I)),
    ("aggressive_behaviour", re.compile(r"aggress\w*|\bhit(s|ting)?\b|\bpush(es|ing)?\b|\bbit(e|es|ing)\b|\bkick(s|ing)?\b|\banger\b|\bangry\b", re.I)),
    ("morning_routine", re.compile(r"\bmorning|\broutines?\b|getting\s+ready", re.I)),
]

_CLASSROOM_RE = re.compile(r"\b(class|classroom|students|pupils|circle\s+time)\b", re.I)


@dataclass
class Intent:
    policy_requested: bool = False
    policy_type: str | None = None
    plan_requested: bool = False
    plan_args: dict | None = None


def detect_policy(message: str) -> tuple[bool, str | None]:
    if not _POLICY_RE.search(message):
        return False, None
    for policy_type, pattern in _POLICY_TYPE_PATTERNS:
        if pattern.search(message):
            return True, policy_type
    return True, None


def is_plan_request(message: str) -> bool:
    return bool(_PLAN_WORD_RE.search(message) and _PLAN_CONTEXT_RE.search(message))


def plan_goal(message: str) -> str:
    for goal, pattern in _GOAL_PATTERNS:
        if pattern.search(message):
            return goal
    return "default"


def build_plan_args(request: ChatRequest) -> dict:
    hints = extract_activity_plan_params(request.message)
    classroom = request.audience == Audience.TEACHER or bool(_CLASSROOM_RE.search(request.message))
    return {
        "age_band": request.age_band.value,
        "goal": plan_goal(request.message),
        "days": hints.days or 5,
        "available_minutes_per_day": hints.available_minutes_per_day or 15,
        "setting": "classroom" if classroom else "home",
    }


def detect_intent(request: ChatRequest) -> Intent:
    policy_requested, policy_type = detect_policy(request.message)
    plan_requested = is_plan_request(request.message)
    return Intent(
        policy_requested=policy_requested,
        policy_type=policy_type,
        plan_requested=plan_requested,
        plan_args=build_plan_args(request) if plan_requested else None,
    )


# Keep ActivityGoal importable from here for callers that only need routing.
__all__ = ["ActivityGoal", "Intent", "POLICY_TYPES", "detect_intent", "detect_policy", "is_plan_request", "plan_goal"]
