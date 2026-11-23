"""Rule-based safety classifier — targets 100% recall on urgent categories."""

import re
from dataclasses import dataclass

from app.models import RiskLevel


@dataclass
class SafetyResult:
    risk_level: RiskLevel
    escalation_message: str | None
    requires_human_review: bool
    matched_category: str | None = None


# Urgent patterns — immediate escalation, no normal advice
URGENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        # Stems like "suicid" end with \w* so "suicide"/"suicidal" match;
        # verbs allow -s/-ing/-ed so "wants to die"/"hurting himself" match.
        "self_harm",
        re.compile(
            r"\b(suicid\w*|self[- ]?harm\w*|"
            r"kill(s|ing|ed)?\s+(myself|themselves|himself|herself|themself)\b|"
            r"want(s|ed|ing)?\s+to\s+(die|be\s+dead|kill)\b|"
            r"(do|does|did)(n'?t|\s+not)\s+want\s+to\s+(live|be\s+alive)\b|"
            r"better\s+off\s+dead\b|"
            r"cut(s|ting)?\s+(myself|themselves|himself|herself|themself)\b|"
            r"end(s|ing)?\s+(my|his|her|their)\s+(own\s+)?life\b|"
            r"(hurt|harm)(s|ing|ed)?\s+(myself|themselves|himself|herself|themself)\b)",
            re.I,
        ),
    ),
    (
        "harm_others",
        re.compile(
            r"\b(kill(s|ing)?\s+(him|her|them|the\s+child)\b|"
            r"hurt(s|ing)?\s+(someone|others|other\s+children|children)\b|"
            r"planning\s+to\s+attack|bring(s|ing)?\s+a\s+weapon|threaten(s|ed)?\s+to\s+kill)\b",
            re.I,
        ),
    ),
    (
        "abuse_neglect",
        re.compile(
            r"\b(sexual\s+abuse|sexually\s+abused|molest\w*|rape|incest|"
            r"(physical|emotional)\s+abuse|beat(s|ing|en)?\s+(the\s+)?child|being\s+beaten|"
            # Feeling left out by peers or a new sibling is not neglect.
            r"(?<!feels\s)(?<!feel\s)(?<!felt\s)neglect(s|ed|ing)?\b"
            r"(?!\s+by\s+(peers|friends|classmates|other\s+(children|kids)))|"
            r"starv(ing|ed)\s+(the\s+)?child|"
            r"locked\s+in\s+(a\s+)?closet|unsafe\s+home|exploit(ed|ation)|"
            r"abus(e|es|ed|ing|ive)\b(?!\s+(of\s+power|the\s+word)))",
            re.I,
        ),
    ),
    (
        "sexual_content_minor",
        re.compile(
            r"\b(child\s+porn|sexual\s+(photos?|images?|videos?)\s+of\s+(a\s+)?child|"
            r"inappropriate\s+touch(ing)?\s+(by\s+an?\s+adult|of\s+(a\s+)?child))\b",
            re.I,
        ),
    ),
    (
        # Weapon words stay urgent unless clearly a toy, utensil, or sport.
        "violence_weapons",
        re.compile(
            r"(?<!toy\s)(?<!water\s)(?<!nerf\s)(?<!glue\s)(?<!bubble\s)(?<!squirt\s)"
            r"(?<!finger\s)(?<!pretend\s)\bguns?\b|"
            r"(?<!butter\s)(?<!plastic\s)(?<!play\s)(?<!toy\s)(?<!table\s)"
            r"\bkni(fe|ves)\b(?!\s+(safety|skills|and\s+fork))|"
            r"\b(weapons?|stab(s|bed|bing)?|immediate\s+danger|active\s+shooter)\b|"
            r"\bshoot(s|ing)?\b(?!\s+(hoops?|baskets?|(the|a)\s+ball|goals?|"
            r"photos?|pictures?|videos?|bubbles))",
            re.I,
        ),
    ),
    (
        "severe_bullying",
        re.compile(
            r"\b(severe\s+bullying|bullied\s+so\s+badly|"
            r"threaten(ed)?\s+(to\s+)?hurt|cyberbully.*suicid)\b",
            re.I,
        ),
    ),
    (
        "missing_child",
        re.compile(
            r"\b(missing\s+child|child\s+(is\s+)?missing|abduct(ed|ion)|"
            r"ran\s+away\s+and\s+(we\s+)?can'?t\s+find)\b",
            re.I,
        ),
    ),
    (
        "medical_emergency",
        re.compile(
            # A known condition ("seizure disorder/plan") is not an emergency in progress.
            r"\b(not\s+breathing|unconscious|seizures?\b(?!\s+(disorder|plan|medication|history))|"
            r"severe\s+allergic|"
            r"overdose|poison(ed|ing)|serious\s+injury|emergency\s+room\s+now|"
            r"mental\s+health\s+emergency|psychotic\s+episode)\b",
            re.I,
        ),
    ),
]

# Non-urgent referral patterns
REFERRAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "persistent_distress",
        re.compile(
            r"\b(persistent(ly)?\s+(anxious|depressed|withdrawn)|"
            r"won'?t\s+stop\s+crying\s+for\s+weeks|functional\s+decline|"
            r"significant\s+behavio(u)?r\s+change)\b",
            re.I,
        ),
    ),
    (
        "learning_difficulties",
        re.compile(
            r"\b(suspect\w*\s+.*(adhd|autism|dyslexia|learning\s+disabilit\w*)|"
            r"has\s+(a\s+)?(autism|adhd|dyslexia|learning\s+disabilit\w*)|"
            r"learning\s+disabilit\w*|developmental\s+delay|"
            r"speech\s+not\s+developing)\b",
            re.I,
        ),
    ),
    (
        "repeated_bullying",
        re.compile(
            r"\b(repeated(ly)?\s+bullied|ongoing\s+bullying|bullying\s+for\s+months)\b",
            re.I,
        ),
    ),
    (
        "professional_support",
        re.compile(
            r"\b(need\s+a\s+(counsell|therap|psycholog|psychiatr)|"
            r"refer\s+to\s+(special\s+educator|occupational\s+therap))\b",
            re.I,
        ),
    ),
]

URGENT_ESCALATION_MESSAGE = """Thank you for sharing this — it sounds very serious, and the child's safety comes first.

**Please contact your school's safeguarding lead, counsellor, or a trusted adult immediately.** If anyone is in immediate danger, call your local emergency number right now.

This advisor cannot investigate, assess, or handle safeguarding concerns. A trained professional needs to support you and the child directly.

**Helpful contacts (PoC placeholders — replace with your school's real contacts):**
- School safeguarding lead: contact your school office
- Child helpline: check NCPCR / local child helpline for your region
- Emergency services: dial your local emergency number if there is immediate danger

You are not alone, and reaching out for help is the right step."""

REFERRAL_MESSAGE = """It sounds like this has been going on for a while and may need more specialised support than general guidance can offer.

**Consider speaking with:**
- Your child's teacher or school counsellor
- A paediatrician or child health professional
- A special educator, if learning or development concerns persist

This is a suggestion to seek support — not a diagnosis. Early conversations with professionals often help families and teachers plan next steps together.

Would you like some general ideas for supporting the child while you arrange that conversation?"""


def classify_safety(message: str) -> SafetyResult:
    """Classify message risk level. Urgent checks run first for maximum recall."""
    text = message.strip()
    if not text:
        return SafetyResult(
            risk_level=RiskLevel.NORMAL,
            escalation_message=None,
            requires_human_review=False,
        )

    for category, pattern in URGENT_PATTERNS:
        if pattern.search(text):
            return SafetyResult(
                risk_level=RiskLevel.URGENT,
                escalation_message=URGENT_ESCALATION_MESSAGE,
                requires_human_review=True,
                matched_category=category,
            )

    for category, pattern in REFERRAL_PATTERNS:
        if pattern.search(text):
            return SafetyResult(
                risk_level=RiskLevel.REFERRAL,
                escalation_message=REFERRAL_MESSAGE,
                requires_human_review=True,
                matched_category=category,
            )

    return SafetyResult(
        risk_level=RiskLevel.NORMAL,
        escalation_message=None,
        requires_human_review=False,
    )
