"""Per-request Ollama / tool timing (no message content logged)."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGeneration, LLMResult

logger = logging.getLogger(__name__)

_THINK_MARKERS = ("redacted_thinking", "thinking", "reasoning_content")


def _message_char_estimate(messages: list[list[BaseMessage]] | Any) -> int:
    total = 0
    batches = messages if isinstance(messages, list) else []
    for batch in batches:
        if not isinstance(batch, list):
            continue
        for msg in batch:
            content = getattr(msg, "content", "") or ""
            if isinstance(content, str):
                total += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        total += len(str(block.get("text", "")))
                    else:
                        total += len(str(block))
            tool_calls = getattr(msg, "tool_calls", None) or []
            total += sum(len(str(tc)) for tc in tool_calls)
    return total


def _thinking_char_estimate(message: BaseMessage) -> int:
    extra = getattr(message, "additional_kwargs", {}) or {}
    reasoning = extra.get("reasoning_content") or ""
    n = len(reasoning) if isinstance(reasoning, str) else len(str(reasoning))
    content = getattr(message, "content", "") or ""
    if isinstance(content, str):
        lower = content.lower()
        if any(m in lower for m in _THINK_MARKERS):
            n += len(content)
    return n


class OllamaProfileHandler(AsyncCallbackHandler):
    """Collects chat-model and tool timings for one agent invocation."""

    def __init__(self, request_id: str = "-") -> None:
        self.request_id = request_id
        self.chat_calls: list[dict[str, Any]] = []
        self.tool_calls: list[dict[str, Any]] = []
        self._chat_start: dict[str, float] = {}
        self._tool_start: dict[str, float] = {}
        self._chat_index = 0
        self._tool_index = 0
        self._pending_context_chars = 0

    async def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        self._chat_start[str(run_id)] = perf_counter()
        self._pending_context_chars = _message_char_estimate(messages)

    async def on_chat_model_end(
        self,
        response: LLMResult,
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        start = self._chat_start.pop(str(run_id), None)
        elapsed_ms = int((perf_counter() - start) * 1000) if start else -1
        self._chat_index += 1
        idx = self._chat_index

        input_tokens: int | None = None
        output_tokens: int | None = None
        done_reason: str | None = None
        model_name: str | None = None
        total_duration_ns: int | None = None
        prompt_eval_duration_ns: int | None = None
        eval_duration_ns: int | None = None
        tool_call_count = 0
        thinking_chars = 0
        answer_chars = 0

        if response.generations:
            gen = response.generations[0][0]
            if isinstance(gen, ChatGeneration):
                msg = gen.message
                usage = getattr(msg, "usage_metadata", None)
                if usage:
                    input_tokens = usage.get("input_tokens")
                    output_tokens = usage.get("output_tokens")
                meta = getattr(msg, "response_metadata", None) or {}
                done_reason = meta.get("done_reason")
                model_name = meta.get("model")
                total_duration_ns = meta.get("total_duration")
                prompt_eval_duration_ns = meta.get("prompt_eval_duration")
                eval_duration_ns = meta.get("eval_duration")
                tool_call_count = len(getattr(msg, "tool_calls", None) or [])
                thinking_chars = _thinking_char_estimate(msg)
                content = getattr(msg, "content", "") or ""
                if isinstance(content, str):
                    answer_chars = len(content.strip())

        record = {
            "index": idx,
            "elapsed_ms": elapsed_ms,
            "context_chars_est": self._pending_context_chars,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "done_reason": done_reason,
            "model": model_name,
            "total_duration_ms": (
                int(total_duration_ns / 1_000_000) if total_duration_ns else None
            ),
            "prompt_eval_ms": (
                int(prompt_eval_duration_ns / 1_000_000) if prompt_eval_duration_ns else None
            ),
            "eval_ms": int(eval_duration_ns / 1_000_000) if eval_duration_ns else None,
            "tool_calls": tool_call_count,
            "thinking_chars": thinking_chars,
            "answer_chars": answer_chars,
        }
        self.chat_calls.append(record)
        logger.info(
            "OLLAMA_CHAT_CALL request_id=%s call=%d elapsed_ms=%d input_tokens=%s "
            "output_tokens=%s done_reason=%s tool_calls=%d thinking_chars=%d "
            "context_chars_est=%d prompt_eval_ms=%s eval_ms=%s",
            self.request_id,
            idx,
            elapsed_ms,
            input_tokens,
            output_tokens,
            done_reason,
            tool_call_count,
            thinking_chars,
            record["context_chars_est"],
            record["prompt_eval_ms"],
            record["eval_ms"],
        )

    async def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        self._tool_start[str(run_id)] = perf_counter()

    async def on_tool_end(
        self,
        output: str,
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        start = self._tool_start.pop(str(run_id), None)
        elapsed_ms = int((perf_counter() - start) * 1000) if start else -1
        self._tool_index += 1
        serialized = kwargs.get("serialized") or {}
        name = kwargs.get("name")
        if not name and isinstance(serialized, dict):
            name = serialized.get("name", "unknown")
        name = name or "unknown"
        self.tool_calls.append(
            {"index": self._tool_index, "tool_name": name, "elapsed_ms": elapsed_ms}
        )
        logger.info(
            "AGENT_TOOL_EXEC request_id=%s tool_name=%s elapsed_ms=%d",
            self.request_id,
            name,
            elapsed_ms,
        )


def profile_from_agent_messages(messages: list[Any]) -> list[dict[str, Any]]:
    """Build per-AIMessage Ollama stats from LangChain message history."""
    records: list[dict[str, Any]] = []
    idx = 0
    for msg in messages:
        if msg.__class__.__name__ != "AIMessage":
            continue
        idx += 1
        meta = getattr(msg, "response_metadata", None) or {}
        usage = getattr(msg, "usage_metadata", None) or {}
        input_tokens = usage.get("input_tokens") if usage else meta.get("prompt_eval_count")
        output_tokens = usage.get("output_tokens") if usage else meta.get("eval_count")
        total_duration_ns = meta.get("total_duration")
        prompt_eval_duration_ns = meta.get("prompt_eval_duration")
        eval_duration_ns = meta.get("eval_duration")
        content = getattr(msg, "content", "") or ""
        answer_chars = len(content.strip()) if isinstance(content, str) else 0
        records.append(
            {
                "index": idx,
                "elapsed_ms": (
                    int(total_duration_ns / 1_000_000) if total_duration_ns else None
                ),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "done_reason": meta.get("done_reason"),
                "model": meta.get("model"),
                "prompt_eval_ms": (
                    int(prompt_eval_duration_ns / 1_000_000)
                    if prompt_eval_duration_ns
                    else None
                ),
                "eval_ms": (
                    int(eval_duration_ns / 1_000_000) if eval_duration_ns else None
                ),
                "tool_calls": len(getattr(msg, "tool_calls", None) or []),
                "thinking_chars": _thinking_char_estimate(msg),
                "answer_chars": answer_chars,
            }
        )
    return records


def log_ollama_profile_summary(
    request_id: str,
    handler: OllamaProfileHandler,
    chat_calls: list[dict[str, Any]] | None = None,
) -> None:
    """chat_calls overrides the handler's list. On Python 3.10 LangChain callbacks do not reach
    the model call, so the handler sees none; pass profile_from_agent_messages(...) instead."""
    calls = chat_calls if chat_calls is not None else handler.chat_calls
    total_chat_ms = sum((c.get("elapsed_ms") or 0) for c in calls if (c.get("elapsed_ms") or 0) >= 0)
    total_tool_ms = sum(
        t.get("elapsed_ms", 0) for t in handler.tool_calls if t.get("elapsed_ms", 0) >= 0
    )
    total_out = sum(c.get("output_tokens") or 0 for c in calls)
    total_in = sum(c.get("input_tokens") or 0 for c in calls)
    total_think = sum(c.get("thinking_chars") or 0 for c in calls)
    logger.info(
        "OLLAMA_PROFILE_SUMMARY request_id=%s chat_calls=%d chat_ms=%d tool_calls=%d "
        "tool_ms=%d input_tokens=%d output_tokens=%d thinking_chars=%d",
        request_id,
        len(calls),
        total_chat_ms,
        len(handler.tool_calls),
        total_tool_ms,
        total_in,
        total_out,
        total_think,
    )
