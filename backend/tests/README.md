# Test layout

| Directory | Purpose |
|-----------|---------|
| `tests/` (root) | Unit tests (safety, citations, activity plan, retrieval logic) |
| `tests/unit/` | Additional unit tests (schema sync, validation) |
| `tests/integration/` | MCP client → server → tool boundaries (slower) |
| `eval/prompts.json` | Safety evaluation dataset (not pytest) |

Run fast unit tests:

```bash
pytest tests/unit tests/test_safety.py tests/test_citations.py tests/test_activity_plan.py tests/test_retrieval.py -q
```

Run integration (spawns MCP subprocess):

```bash
pytest tests/integration -q
```
