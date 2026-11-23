"""Deterministic play-based activity plan generator."""

import re
from typing import Any

MAX_PLAN_DAYS = 14
MIN_MINUTES = 5
MAX_MINUTES = 120

PLAN_TEMPLATES: dict[str, dict[str, Any]] = {
    "turn_taking_during_play": {
        "title": "Turn-Taking During Play",
        "setup": "Pair of identical toys (blocks, cars, or cups) and a sand timer or visual timer.",
        "adult_language": [
            "My turn… your turn.",
            "You waited — thank you for waiting.",
            "The timer shows when it's your turn.",
        ],
        "steps": [
            "Day 1–2: Adult models turn-taking with a 30-second timer during a favourite game.",
            "Day 3: Child and peer take turns with adult coaching; celebrate waiting.",
            "Day 4: Introduce a 'waiting mat' — child holds a card while waiting.",
            "Day 5: Short cooperative game (rolling a ball back and forth) with minimal prompts.",
            "Extension: Increase wait time slightly; fade prompts; note independent turn-taking.",
        ],
        "observation_prompt": "Note how long the child can wait before needing a prompt. Record one success each day.",
    },
    "morning_routine": {
        "title": "Gentle Morning Routine",
        "setup": "Picture schedule with 3–4 steps (wake up, wash, dress, bag).",
        "adult_language": [
            "First we… then we…",
            "You did the first step — what's next on our pictures?",
            "We have time; let's do this together.",
        ],
        "steps": [
            "Day 1: Walk through picture schedule together; child points to each step.",
            "Day 2: Child completes one step independently (e.g. putting on shoes).",
            "Day 3: Add a 'ready song' or chime when the routine starts.",
            "Day 4–5: Practise the sequence with fewer reminders; praise specific efforts.",
            "Extension: Child leads one step; adult narrates; adjust visuals if a step is hard.",
        ],
        "observation_prompt": "Which step causes the most difficulty? Note mood at drop-off after the routine.",
    },
    "sharing_toys": {
        "title": "Learning to Share",
        "setup": "Duplicate toys and a 'sharing timer' (2-minute visual timer).",
        "adult_language": [
            "When the timer rings, it's time to swap.",
            "You can ask: 'Can I have a turn when you're done?'",
            "Sharing means we both get to play.",
        ],
        "steps": [
            "Day 1: Adult models asking for a turn and waiting.",
            "Day 2: Use timer for short turns with popular toys.",
            "Day 3: Teach phrase: 'Can I play when you're finished?'",
            "Day 4–5: Peer play with timer; adult coaches conflict moments.",
            "Extension: Practise with less familiar toys; celebrate negotiated sharing.",
        ],
        "observation_prompt": "Does the child use words or physical grabbing? Note one positive sharing moment daily.",
    },
    "separation_anxiety": {
        "title": "Easing Separation at Drop-Off",
        "setup": "Small comfort object (if school allows), goodbye ritual card.",
        "adult_language": [
            "I will come back after [activity].",
            "Your teachers will keep you safe.",
            "One hug, then I'll wave from the door.",
        ],
        "steps": [
            "Day 1: Establish a consistent 3-step goodbye ritual (hug, wave, phrase).",
            "Day 2: Keep goodbye brief and confident; teacher engages child immediately.",
            "Day 3: Child holds comfort object during first activity.",
            "Day 4–5: Gradually reduce time at door; teacher sends a brief 'settled' update.",
            "Extension: Review ritual; celebrate shorter settling time.",
        ],
        "observation_prompt": "How many minutes until the child engages in an activity? Track each morning.",
    },
    "aggressive_behaviour": {
        "title": "Supporting Positive Behaviour After Aggression",
        "setup": "Calm corner materials, feeling cards, and predictable response scripts.",
        "adult_language": [
            "Hands are for helping.",
            "You were angry — let's find a safe way to show that.",
            "We'll try again when your body feels calm.",
        ],
        "steps": [
            "Day 1: Teach calm-down choices (breathing, squeeze toy, ask for help).",
            "Day 2: Practise naming feelings before escalation with picture cards.",
            "Day 3: Role-play safe alternatives when frustrated during play.",
            "Day 4–5: Reinforce repair (check-in, apology if ready, joint problem-solving).",
            "Extension: Review triggers; adjust environment; praise recovery.",
        ],
        "observation_prompt": "What happens just before aggressive behaviour? Note recovery time and what helps.",
    },
    "default": {
        "title": "Play-Based Learning Plan",
        "setup": "Simple open-ended materials (blocks, crayons, containers, natural items).",
        "adult_language": [
            "I wonder what you could make…",
            "Tell me about your idea.",
            "You worked hard on that.",
        ],
        "steps": [
            "Day 1: Free exploration with one material; adult narrates child's actions.",
            "Day 2: Introduce a simple goal (build a tower, draw a circle).",
            "Day 3: Add a social element — build together or side by side.",
            "Day 4–5: Child leads the play; adult asks open questions.",
            "Extension: Rotate materials; document one new skill observed.",
        ],
        "observation_prompt": "What does the child choose to do? Note engagement time and one new skill.",
    },
}


_DAY_PREFIX_RE = re.compile(r"^Day\s+(\d+)(?:\s*[–-]\s*(\d+))?:\s*")


def _expand_steps(steps: list[str]) -> tuple[list[str], str]:
    """Turn "Day 1–2: X", "Day 3: Y", "Extension: Z" into [X, X, Y, ...] and Z.

    Template text keeps its day ranges for readability; labels are assigned by the
    actual plan day, so day numbers in the output always match.
    """
    base: list[str] = []
    extension = ""
    for step in steps:
        match = _DAY_PREFIX_RE.match(step)
        if match:
            start = int(match.group(1))
            end = int(match.group(2) or start)
            base.extend([step[match.end():].strip()] * (end - start + 1))
        elif step.lower().startswith("extension:"):
            extension = step.split(":", 1)[1].strip()
        else:
            base.append(step.strip())
    return base, extension or (base[-1] if base else "")


def create_activity_plan(
    age_band: str,
    goal: str,
    available_minutes_per_day: int = 15,
    days: int = 5,
    setting: str = "home",
) -> dict[str, Any]:
    """Generate a deterministic, editable play-based plan (up to 14 days)."""
    days = max(1, min(int(days), MAX_PLAN_DAYS))
    available_minutes_per_day = max(MIN_MINUTES, min(int(available_minutes_per_day), MAX_MINUTES))

    template = PLAN_TEMPLATES.get(goal, PLAN_TEMPLATES["default"])
    setting_note = (
        "Adapt materials to classroom centres and group size."
        if setting == "classroom"
        else "Use everyday home materials and routines."
    )

    base, extension = _expand_steps(template["steps"])
    daily_plan = []
    for day in range(1, days + 1):
        if days < len(base):
            # Shorter plans sample the distinct steps evenly so every day is different.
            distinct = list(dict.fromkeys(base))
            activity = distinct[(day - 1) * len(distinct) // days]
        elif day <= len(base):
            activity = base[day - 1]
        else:
            activity = f"Practise again and extend: {extension}"
        daily_plan.append(
            {
                "day": day,
                "duration_minutes": available_minutes_per_day,
                "activity": activity,
            }
        )

    return {
        "plan_id": f"plan_{goal}_{age_band}_{days}d",
        "title": template["title"],
        "age_band": age_band,
        "goal": goal,
        "days": days,
        "available_minutes_per_day": available_minutes_per_day,
        "setting": setting,
        "setting_note": setting_note,
        "setup": template["setup"],
        "adult_language": template["adult_language"],
        "daily_plan": daily_plan,
        "extension": extension,
        "observation_prompt": template["observation_prompt"],
        "editable": True,
        "generated_by": "deterministic_template",
    }
