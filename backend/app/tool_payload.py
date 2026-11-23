"""Parse MCP / LangChain tool return payloads into JSON dicts."""

import json
from typing import Any


def parse_tool_payload(value: Any) -> dict[str, Any]:
    """Normalize tool output (str JSON, MCP text blocks, nested result) to a dict."""
    if isinstance(value, dict) and "results" in value:
        return value
    if isinstance(value, dict) and "status" in value:
        return value
    if isinstance(value, dict) and "daily_plan" in value:
        return value
    if isinstance(value, dict) and "policy_type" in value:
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"result": value}
    if isinstance(value, list) and value:
        for item in value:
            if isinstance(item, dict) and item.get("type") == "text":
                return parse_tool_payload(item.get("text", ""))
        return {}
    if isinstance(value, dict) and "result" in value:
        inner = value["result"]
        if isinstance(inner, list):
            return parse_tool_payload(inner)
        if isinstance(inner, dict):
            return inner
    return value if isinstance(value, dict) else {"result": value}
