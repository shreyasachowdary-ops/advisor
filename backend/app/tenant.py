"""Trusted tenant/school context (PoC: settings; later: authenticated user)."""

from app.config import settings


def trusted_school_id() -> str:
    """Server-side school id — do not use LLM/browser-supplied values for authorization."""
    return settings.school_id
