"""Feedback audit log linked to assistant message_id."""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.models import FeedbackRequest


def record_feedback(body: FeedbackRequest) -> dict[str, str]:
    log_path = Path(settings.audit_dir) / "feedback.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message_id": body.message_id,
        "session_id": body.session_id,
        "rating": body.rating,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    return {"status": "recorded", "message_id": body.message_id}
