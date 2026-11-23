"""Local Ollama embeddings (LangChain) — shared by ingestion and retrieval."""

from functools import lru_cache

from langchain_ollama import OllamaEmbeddings

from app.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    return get_embedding_model().embed_documents(texts)


def embed_query(text: str) -> list[float]:
    import logging

    logging.getLogger(__name__).info(
        "EMBED_QUERY model=%s dimensions_request=1",
        settings.ollama_embed_model,
    )
    return get_embedding_model().embed_query(text)
