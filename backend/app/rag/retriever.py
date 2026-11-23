"""RAG documentation module.

Live retrieval runs inside the custom MCP tool ``search_knowledge`` (Chroma + Ollama
embeddings via ``app.embeddings``). The LangChain agent reaches it only through MCP —
not via direct imports from the agent path.

Unit tests may call ``mcp_server.tools.search_knowledge`` to validate business logic.
"""
