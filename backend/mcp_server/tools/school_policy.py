"""Load mock school policy data."""

import json
import logging
from pathlib import Path
from typing import Any

from app.config import BACKEND_ROOT
from app.tenant import trusted_school_id

logger = logging.getLogger(__name__)

POLICIES_DIR = BACKEND_ROOT / "data" / "policies"

_policy_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _load_policy_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    cached = _policy_cache.get(str(path))
    if cached and cached[0] == mtime:
        return cached[1]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _policy_cache[str(path)] = (mtime, data)
    return data


def get_school_policy(policy_type: str, school_id: str | None = None) -> dict[str, Any]:
    """Return approved policy text and contacts from mock JSON.

    ``school_id`` is ignored if supplied by an untrusted caller (e.g. LLM).
    PoC uses trusted ``settings.school_id`` from server configuration only.
    """
    sid = trusted_school_id()
    if school_id and school_id != sid:
        logger.warning("Ignoring client-supplied school_id=%s; using trusted %s", school_id, sid)
    policy_file = POLICIES_DIR / f"{sid}.json"
    data = _load_policy_file(policy_file)

    if data is None:
        return {
            "school_id": sid,
            "error": "Policy file not found",
            "available_types": [],
        }

    policies = data.get("policies", {})
    if policy_type not in policies:
        return {
            "school_id": sid,
            "error": f"Policy type '{policy_type}' not found",
            "available_types": list(policies.keys()),
        }

    policy = policies[policy_type]
    return {
        "school_id": sid,
        "school_name": data.get("school_name", sid),
        "policy_type": policy_type,
        "title": policy.get("title", policy_type),
        "text": policy.get("text", ""),
        "contacts": data.get("contacts", {}),
        "last_reviewed": policy.get("last_reviewed", ""),
    }
