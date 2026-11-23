"""Latency bounds for the Ollama agent (no network)."""

from app.agent import chat_ollama_kwargs, trim_history_messages
from app.config import settings


def test_history_is_capped_and_truncated():
    long = "word " * 800
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": long} for i in range(10)]
    trimmed = trim_history_messages(history)
    assert len(trimmed) == settings.session_agent_history
    assert all(len(item["content"]) <= settings.history_message_chars + 1 for item in trimmed)
    assert trimmed[-1]["content"].endswith("…")


def test_ollama_kwargs_bound_generation():
    kwargs = chat_ollama_kwargs()
    assert kwargs["num_predict"] <= 896
    assert kwargs["num_ctx"] == 8192
    assert kwargs["keep_alive"] == "30m"
    assert kwargs["reasoning"] is False
