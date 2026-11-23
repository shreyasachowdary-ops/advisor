# Parent/Teacher Agentic Advisor (PoC)

A local, private AI advisor for parents and teachers of preschool children (ages 2–5). Provides practical, evidence-aligned guidance on play-based learning, behaviour, routines, and parent–teacher communication.

**Not** a counsellor, diagnostician, or child-protection case system.

## Architecture

```
ERP UI (or reference_frontend for local dev)
        |
        v
FastAPI (/api/chat)
        |
        v
Deterministic safety (urgent / referral / normal)
        |
        v  NORMAL path only
Context in code (via MCP): search_knowledge always;
get_school_policy / create_activity_plan when clearly requested
        |
        v
LangChain agent (ChatOllama) with the passages/policy/plan in its prompt
(may call read-only tools for more; never submit_safeguarding_flag)
        |
        v
langchain-mcp-adapters --> ONE long-lived MCP stdio server (mcp_server/server.py)
        |
        +-- search_knowledge --> Chroma + Ollama embeddings (distance cutoff 0.9)
        +-- create_activity_plan (templates)
        +-- get_school_policy
        `-- submit_safeguarding_flag (only via POST /api/safeguarding/confirm)
```

If the model is down or fails, the API still answers from templates and sets
`degraded: true` in the response. See `DECISIONS.md` for the reasoning behind each part.

## Prerequisites

- Python 3.10+ (3.11+ recommended)
- Node.js 18+
- Ollama running locally with a chat model (default `gemma4:12b`)

```bash
ollama serve
ollama pull gemma4:12b
ollama pull nomic-embed-text   # must match OLLAMA_EMBED_MODEL in .env
```

## Setup

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # edit if needed

# First-time or after embedding/seed changes only:
python -m ingestion.ingest
# Deliberate rebuild:
python -m ingestion.ingest --reset
```

Do **not** run `--reset` on every `git pull`. Reuse `backend/data/chroma` unless embeddings, seed data, or schema changed.

### Frontend (local dev UI)

The production UI is the ERP page in `erp-integration/` (see below). For local
development, `reference_frontend/` is a standalone copy of the same ChildConnect UI.
Its Vite dev server proxies `/api` to the backend on port 8787.

```bash
cd reference_frontend
npm install
```

## Run

**Terminal 1 — Backend:**
```bash
cd backend
.venv\Scripts\activate   # or source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload
```

**Terminal 2 — Dev UI:**
```bash
cd reference_frontend
npm run dev
```

Open: http://127.0.0.1:5173

## Networking (browser vs server)

| Who runs the browser | What `advisor_base_url` / API URL should be |
|----------------------|---------------------------------------------|
| Same machine as FastAPI | `http://127.0.0.1:8787` |
| Another PC on the school LAN | `http://<server-ip-or-hostname>:8787` |
| Production | Your configured HTTPS hostname |

`127.0.0.1` in **browser** JavaScript always means the user's device, not your SSH server. ERP `config_web.json` must use an address clients can reach.

Run uvicorn with `--host 0.0.0.0` when serving the API to other machines on the network.

## Sessions, feedback, and safeguarding

- `POST /api/chat` accepts optional `session_id` and returns `message_id` + `session_id`.
- `POST /api/feedback` requires `message_id` (links feedback to a specific assistant reply).
- Urgent messages return `requires_confirmation: true` and **do not** auto-submit safeguarding logs.
- `POST /api/safeguarding/confirm` runs only after explicit user confirmation (via MCP `submit_safeguarding_flag`).

Or use the helper script (Linux/macOS): `bash scripts/run_dev.sh`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Liveness (API up; Ollama status reported) |
| `/api/ready` | GET | Readiness (Chroma + MCP tool discovery) |
| `/api/chat` | POST | Main chat endpoint |
| `/api/chat/stream` | POST | Same answer as `/api/chat`, sent as Server-Sent Events: `delta` pieces while Gemma writes, then one `done` with the full response (or `error`) |
| `/api/feedback` | POST | Submit feedback rating |
| `/api/safeguarding/confirm` | POST | Submit safeguarding flag (requires confirmation) |

## Tests

```bash
cd backend
.venv\Scripts\activate
pytest tests --ignore=tests/integration -v   # fast; no Ollama needed (fake model)
pytest tests/integration -v                  # live: MCP subprocess + Chroma + Ollama
```

Tests write audit events to a temporary folder (`tests/conftest.py`), never to
`backend/data/audit/`.

Safety metrics are reported against `backend/eval/prompts.json` only — not real-world recall.

Optional LangSmith: set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` in the environment; app works without them.

## Demo Script

1. **Morning routine** — "My 4-year-old is upset at preschool drop-off" → cited retrieval + small steps
2. **Positive intervention** — "A child keeps pushing during play" → positive strategies
3. **Activity plan** — "Create a 5-day turn-taking activity plan" → deterministic plan
4. **Safety escalation** — "A child said they want to kill themselves" → immediate escalation
5. **No student data** — works without names, admission numbers, or history

## Configuration

See `backend/.env.example` for all environment variables.

## ERP Integration (lnpl_erp_dev_v1)

To integrate the advisor into the school ERP (same pattern as Notice Agent / `GenerateNotice.js`):

```powershell
cd erp-integration
.\apply-to-erp.ps1 -ErpRoot "C:\path\to\lnpl_erp_dev_v1"
# Optional explicit roles: -AdvisorRoles @("applicant","teacher")
```

Canonical page: `erp-integration/src/components/Communication/AdvisorPage.js`

See [erp-integration/COPY_INSTRUCTIONS.md](erp-integration/COPY_INSTRUCTIONS.md) for manual steps.

## Licence

PoC — internal use only. Knowledge sources retain their original licences.
