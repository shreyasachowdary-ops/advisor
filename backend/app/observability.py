"""Request-scoped tracing (no message content)."""

from contextvars import ContextVar
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


@dataclass
class RequestTrace:
    request_id: str
    mcp_tool_calls: list[str] = field(default_factory=list)
    timings_ms: dict[str, int] = field(default_factory=dict)
    mcp_tools_loaded: list[str] = field(default_factory=list)
    citation_hit_count: int = 0
    ollama_chat_calls_estimate: int = 0
    citation_mcp_fallback: bool = False
    ollama_chat_calls: list[dict[str, Any]] = field(default_factory=list)
    agent_tool_exec_ms: list[dict[str, Any]] = field(default_factory=list)

    def mark(self, key: str, start: float) -> None:
        self.timings_ms[key] = int((perf_counter() - start) * 1000)


trace_var: ContextVar[RequestTrace | None] = ContextVar("trace", default=None)


def get_request_id() -> str:
    return request_id_var.get() or "-"


def get_trace() -> RequestTrace | None:
    return trace_var.get()


def start_trace(request_id: str) -> RequestTrace:
    request_id_var.set(request_id)
    tr = RequestTrace(request_id=request_id)
    trace_var.set(tr)
    return tr
