# SynapsePlane

**From intent to trusted execution.**

SynapsePlane is a stateful, human-governed execution plane for multi-agent AI workflows. It transforms natural-language user intentions into validated task graphs, selects trusted agents from a capability catalogue, coordinates sequential and parallel execution, pauses before consequential external actions to get human approval, and recovers safely from failures.

Built as a technical interview submission for [Efimind](https://efimind.ai), this prototype demonstrates the core architecture of an agentic execution plane — the governance and orchestration layer that controls how AI intent becomes real-world action.

---

## What it does

Submit a natural-language intent like:

> "Find a good Italian restaurant near me for dinner tomorrow and put it in my calendar."

SynapsePlane will:

1. Load your profile (location, cuisine preferences, calendar provider, approval policy)
2. Decompose the intent into a validated task graph
3. Select trusted agents from its catalogue based on capabilities
4. Execute `search_restaurants` and `check_calendar_availability` in parallel
5. Rank restaurants using a deterministic score (distance, rating, cuisine match, price)
6. **Pause and ask for your approval** before creating the calendar event
7. After approval, create the calendar event through the selected provider
8. Record the full execution timeline — every decision, agent selection, and tool call

---

## Quick start

### Prerequisites

- Docker and Docker Compose
- An OpenAI API key (or leave blank — a deterministic fake planner works without one)

### Run locally

```bash
git clone https://github.com/DinethraDivanjana2001/synapse-plane.git
cd synapse-plane
cp .env.example .env
# Edit .env — add OPENAI_API_KEY if you have one (optional for demo)
docker compose up --build
```

- API: `http://localhost:8000`
- Web UI: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`

### Run without Docker

```bash
# Backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn apps.api.main:app --reload

# Frontend (separate terminal)
cd apps/web
npm install
npm run dev
```

---

## Demonstration scenarios

The UI provides clearly labelled scenario controls:

| Scenario | How to trigger | What it shows |
|----------|---------------|---------------|
| **Normal run** | Submit the restaurant intent (default) | Full success flow: planning → parallel execution → approval → calendar event |
| **Primary agent failure** | Enable "Inject failure" toggle before submitting | Retry → fallback agent → recovery → completion |
| **Unsupported intent** | Try: *"Book me a flight to Singapore"* | Plan validation stops before any tool call; `UNSUPPORTED_CAPABILITY` response |

---

## Architecture overview

```
User Intent
    │
    ▼
Intent Planner (LLM or deterministic)
    │  proposes WorkflowDefinition
    ▼
Plan Validator (deterministic — checks capabilities, DAG, schemas)
    │  validated plan
    ▼
Dependency Scheduler
    │  dispatches ready tasks (concurrent where possible)
    ▼
Agent Router (filters catalogue → scores → selects → records reason)
    │  selected agent
    ▼
Agent Executor → [local agents / real API provider adapters — no MCP gateway runs]
    │  typed output
    ▼
Approval Gate (CONSEQUENTIAL_WRITE tasks pause here)
    │  user approves/rejects
    ▼
Resume → Calendar Provider → External Action Record
    │
    ▼
Execution Complete (full event timeline in DB)
```

**Core principle:** LLMs interpret, propose, rank, and explain. Deterministic code validates, authorizes, schedules, persists, and commits. No LLM output causes an external write without passing policy checks.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full layer diagram and data flows.

---

## Project structure

```
synapse-plane/
├── apps/
│   ├── api/              FastAPI application (routes, middleware, dependency injection)
│   └── web/              React + TypeScript frontend (Vite)
├── src/
│   └── synapse_plane/
│       ├── domain/       Pydantic schemas, state enums, event types
│       ├── planning/     Intent planner, plan validator
│       ├── registry/     Agent catalogue, capability router
│       ├── orchestration/ Scheduler, executor, dependency resolver
│       ├── policies/     Approval policy, retry policy, risk classifier
│       ├── agents/       Local agent implementations
│       ├── tools/        Provider interfaces (real APIs, no MCP layer), mock providers
│       ├── persistence/  SQLAlchemy ORM models, repositories, Alembic config
│       └── observability/ Event emitter, structured logging
├── tests/
│   ├── unit/             No external dependencies; fast
│   ├── integration/      Real DB (SQLite), fake agents; no live APIs
│   └── scenarios/        End-to-end: success, failure/recovery, unsupported intent
├── docs/                 Architecture, scope, requirements, roadmap, decisions, progress
├── demo/                 Fixtures, seed data, scenario scripts
├── AGENTS.md             AI coding assistant context (Cursor, Antigravity, Claude Code)
├── CLAUDE.md             Claude Code specific instructions
├── AI_USAGE.md           Transparent AI methodology for evaluators
├── docker-compose.yml
├── .env.example
└── pyproject.toml
```

---

## Running tests

```bash
# All tests (requires DB — uses SQLite by default for tests)
pytest

# Unit tests only (no DB needed)
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Scenario tests (full stack with mock providers)
pytest tests/scenarios/

# With coverage
pytest --cov=src/synapse_plane --cov-report=term-missing
```

All tests run without live LLM or external API credentials.

---

## Agent catalogue

| Agent | Capability | Status |
|-------|-----------|--------|
| `venue-search-primary` | `places.search.restaurant` | Implemented (supports failure injection) |
| `venue-search-fallback` | `places.search.restaurant` | Implemented (deterministic mock) |
| `venue-recommender` | `places.rank.restaurant` | Implemented (hybrid deterministic scoring) |
| `calendar-scheduler` | `calendar.read_availability`, `calendar.create_event` | Implemented (mock; P1: Google adapter) |
| `weather-context` | `weather.read_forecast` | P1 / disabled |
| `city-itinerary` | `itinerary.compose` | Catalogue-only (not implemented) |
| `external-concierge` | remote capability example | Catalogue-only |

---

## Environment variables

Copy `.env.example` to `.env` and configure:

```bash
# Required
DATABASE_URL=postgresql+asyncpg://synapse:synapse@localhost:5432/synapse_plane

# Optional — system runs with fake planner if absent
OPENAI_API_KEY=

# Optional — P1 feature
GOOGLE_CALENDAR_CLIENT_ID=
GOOGLE_CALENDAR_CLIENT_SECRET=
GOOGLE_CALENDAR_REDIRECT_URI=

# Demo controls
DEMO_MODE=true          # Enables scenario toggle controls in UI
LOG_LEVEL=INFO
```

---

## Known limitations

- **Single demo user** — Multi-user authentication is out of scope for this prototype.
- **Mock providers by default** — Real Google Calendar requires OAuth setup; mock fallback always available.
- **Restaurant data is mocked** — A realistic fixture of Colombo venues is used. A real Places API adapter is a P1 target.
- **No payment, booking, or financial operations** — These are explicitly out of scope and refused by the system.
- **Prototype throughput** — The current scheduler uses in-process asyncio. For production, this becomes a queue-based distributed worker system.

---

## Scale path

The current modular monolith would evolve into distributed services by:
- Extracting the agent catalogue into a **Registry Service** with semantic search
- Replacing the in-process scheduler with a **Durable Workflow Engine** (e.g., Temporal)
- Running agents as isolated **Worker Services** consuming from a task queue
- Adding a **Policy Service** for tenant-scoped trust and approval rules
- Routing external agents through a **Sandboxed Adapter Gateway** with auth and timeouts

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) section 11 for the full scale-path explanation.

---


## Architecture

See the full architecture design, layer responsibilities, data flows, and scale story in the project documentation under `docs/`.

---

*SynapsePlane — From intent to trusted execution.*
