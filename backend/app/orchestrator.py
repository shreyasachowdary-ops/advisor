"""Backward-compatible re-export — prefer app.services.advisor."""

from app.services.advisor import check_ollama_available, process_chat

__all__ = ["check_ollama_available", "process_chat"]
