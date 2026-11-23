"""
Profile /api/chat latency by scenario (requires Ollama + Chroma + MCP).

Usage (from backend/):
  python scripts/profile_chat_latency.py
  python scripts/profile_chat_latency.py --scenario rag
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.models import Audience, AgeBand, ChatRequest
from app.observability import start_trace
from app.services.advisor import process_chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("profile_chat_latency")

SCENARIOS: dict[str, str] = {
    "simple": "What is a good way to praise a 4-year-old for small efforts?",
    "rag": "How can I create a predictable daily routine for my child?",
    "activity_plan": (
        "Create a 5-day turn-taking activity plan for my 4-year-old, 15 minutes per day."
    ),
    "school_policy": "What is our school policy on bullying?",
    "multi_tool": (
        "How can I help my child with morning routines, and what does our bullying policy say?"
    ),
}


async def run_scenario(name: str, message: str) -> dict:
    rid = str(uuid.uuid4())
    start_trace(rid)
    request = ChatRequest(
        message=message,
        audience=Audience.PARENT,
        age_band=AgeBand.FOUR_YEARS,
        language="en",
    )
    from time import perf_counter

    t0 = perf_counter()
    resp = await process_chat(request)
    total_ms = int((perf_counter() - t0) * 1000)
    from app.observability import get_trace

    tr = get_trace()
    row = {
        "scenario": name,
        "request_id": rid,
        "total_ms": total_ms,
        "timings_ms": tr.timings_ms if tr else {},
        "mcp_tool_calls": tr.mcp_tool_calls if tr else [],
        "citation_mcp_fallback": tr.citation_mcp_fallback if tr else None,
        "ollama_chat_calls": tr.ollama_chat_calls if tr else [],
        "citations": len(resp.citations),
        "risk_level": resp.risk_level.value,
    }
    logger.info("PROFILE_RESULT %s", json.dumps(row, default=str))
    return row


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()) + ["all"],
        default="all",
    )
    args = parser.parse_args()
    names = list(SCENARIOS.keys()) if args.scenario == "all" else [args.scenario]
    results = []
    for name in names:
        results.append(await run_scenario(name, SCENARIOS[name]))
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
