from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_model: str = "gemma4:12b"
    ollama_embed_model: str = "nomic-embed-text"
    chroma_path: str = str(BACKEND_ROOT / "data" / "chroma")
    kb_version: str = "0.1.0"
    school_id: str = "poc_test_school"
    api_host: str = "127.0.0.1"
    api_port: int = 8787
    cors_origins: str = "http://127.0.0.1:5173"
    max_agent_steps: int = 8
    mcp_python_command: str = ""
    session_max_messages: int = 12
    # Turns passed into the agent (must be <= session_max_messages).
    session_agent_history: int = 6
    session_ttl_seconds: int = 3600
    session_max_sessions: int = 500
    # Drop Chroma hits with L2 distance above this (None = keep all ranked hits).
    # 0.9 measured on nomic-embed-text: relevant hits ~0.5–0.85, off-topic ~1.1 (DEC-029).
    chroma_max_distance: float | None = 0.9
    # Cap generated tokens. Answers are short; a high cap makes slow models run for minutes.
    ollama_num_predict: int = 896
    # Context window sent to Ollama. 0 = model default (often 32k, which is slow on CPU).
    ollama_num_ctx: int = 8192
    # Keep weights in memory between ERP users. Empty string = Ollama default (~5 minutes).
    ollama_keep_alive: str = "30m"
    # False disables extended thinking on models that support it (e.g. gemma4). None = model default.
    ollama_reasoning: bool | None = False
    # Max characters of each prior turn sent back to the model.
    history_message_chars: int = 1500
    audit_dir: str = str(BACKEND_ROOT / "data" / "audit")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
