"""Parse activity-plan duration hints from user text (for agent / tool arguments)."""

import re
from dataclasses import dataclass


@dataclass
class ActivityPlanParams:
    days: int | None = None
    available_minutes_per_day: int | None = None


_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "twenty": 20, "thirty": 30,
}
_NUMBER_WORD_RE = re.compile(r"\b(" + "|".join(_NUMBER_WORDS) + r")\b")


def extract_activity_plan_params(message: str) -> ActivityPlanParams:
    # "Five-day plan, ten minutes a day" -> "5-day plan, 10 minutes a day"
    lower = _NUMBER_WORD_RE.sub(lambda m: str(_NUMBER_WORDS[m.group(1)]), message.lower())
    days: int | None = None
    minutes: int | None = None

    day_match = re.search(
        r"\b(\d{1,2})\s*[- ]?\s*day\b|\b(?:for|over)\s+(\d{1,2})\s+days?\b",
        lower,
    )
    if day_match:
        days = int(next(g for g in day_match.groups() if g))
    else:
        week_match = re.search(r"\b(?:for|over)\s+(?:a|1)\s+week\b|\b(1|2)[- ]?weeks?\b", lower)
        if week_match:
            days = 7 * int(week_match.group(1) or 1)

    min_match = re.search(
        r"\b(\d{1,3})\s*minutes?\s*(?:a|per|each)\s*day\b|\b(\d{1,3})\s*min(?:/day)?\b",
        lower,
    )
    if min_match:
        minutes = int(next(g for g in min_match.groups() if g))

    if days is not None:
        days = max(1, min(days, 14))
    if minutes is not None:
        minutes = max(5, min(minutes, 120))

    return ActivityPlanParams(days=days, available_minutes_per_day=minutes)
