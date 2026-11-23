"""Explicit safeguarding confirmation — never auto-submit on classifier alone."""

from app.mcp.client import invoke_mcp_tool
from app.models import SafeguardingConfirmRequest, SafeguardingConfirmResponse


async def confirm_safeguarding(body: SafeguardingConfirmRequest) -> SafeguardingConfirmResponse:
    if not body.user_confirmed:
        return SafeguardingConfirmResponse(
            status="rejected",
            message="user_confirmed must be true to submit a safeguarding flag",
            safeguarding_event_id=None,
            message_id=body.message_id,
        )

    result = await invoke_mcp_tool(
        "submit_safeguarding_flag",
        {
            "category": body.category,
            "severity": body.severity,
            "user_summary": body.user_summary,
            "user_confirmed": True,
        },
    )
    event_id = result.get("event_id") if isinstance(result, dict) else None
    return SafeguardingConfirmResponse(
        status=result.get("status", "recorded") if isinstance(result, dict) else "error",
        message=result.get("message", "") if isinstance(result, dict) else str(result),
        safeguarding_event_id=event_id,
        message_id=body.message_id,
    )
