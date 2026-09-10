# SynapsePlane

**From intent to trusted execution.**

[![CI](https://github.com/DinethraDivanjana2001/synapse-plane/actions/workflows/ci.yml/badge.svg)](https://github.com/DinethraDivanjana2001/synapse-plane/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/frontend-React%20%2B%20TypeScript-61DAFB?logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL%20%2B%20pgvector-4169E1?logo=postgresql&logoColor=white)

SynapsePlane is a persistent-context-aware **agentic execution plane**: it takes a
plain-English request, retrieves the relevant personal context, decomposes the intent
into a validated task graph, routes each task to a real agent from a capability
catalogue, executes tasks sequentially or in parallel, pauses for human approval before
anything consequential happens, and recovers from failure without ever inventing a fake
success.

Built as a technical interview submission for **[Efimind](https://efimind.ai)**, this
project demonstrates the governance and orchestration layer that sits between an AI's
intent and a real-world action — the part of an agentic system that decides *whether*
and *how* that action is allowed to happen, not just whether an LLM can produce a plan.

> **New here?** The [Evaluator Guide](https://claude.ai/code/artifact/0041d886-976b-4f7e-acc8-e4c228ebdd21)
> is a single page covering architecture, all 6 agents, failure handling, a walkthrough
> of the dashboard, the seeded demo data, and every test case with its expected result.

---

## What it does

Two real use cases, both working end to end:

**1. Context-aware dinner planning** — the primary demo:

> "Find a nice restaurant for dinner with Rebecca tonight and add it to my calendar."

SynapsePlane retrieves what it actually knows about Rebecca specifically (fast food,
casual, lively — not the user's own general taste), searches for real matching
restaurants, checks real calendar availability, ranks the candidates, and **pauses for
approval** before creating anything. Ask the same thing about Maya instead, and the
retrieved preferences — and the restaurant category recommended — genuinely change,
because the memory retrieved is person-specific, not a fixed script.

**2. Travel research and comparison** — the secondary demo:

> "Should I go to Kandy or Galle next month? Compare them and check the weather."

Real research on both destinations, real weather for each, and a written recommendation
that references both. Nothing is booked — a comparison question never needs approval.

---

## Why this is the interesting part

A single API call is not an agent. The design here rests on one rule, enforced in three
layers:

```
┌────────────────────────────────────────────────────────┐
│  ORCHESTRATOR — decomposes intent, validates the task   │
│  graph, routes to agents, tracks state, enforces        │
│  approval. 100% deterministic. No LLM decides execution.│
└────────────────────────┬───────────────────────────────┘
                          │ selects & coordinates
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌────────────────────────────────────────────────────────┐
│  AGENTS — receive a goal, reason about how to pursue    │
│  it, choose tools, observe results, adapt.              │
└────────────────────────┬───────────────────────────────┘
                          │ uses
                          ▼
┌────────────────────────────────────────────────────────┐
│  TOOLS — one specific, deterministic operation each.    │
│  pgvector_search, calendar_read, graph_query, forecast. │
└────────────────────────────────────────────────────────┘
```

LLMs interpret, propose, rank, and explain. Deterministic code validates, authorizes,
schedules, persists, and commits. No LLM output ever causes an external write without
passing a policy check first.

---

## Quick start

### Recommended: real mode

This is the only mode that shows the actual agent behavior — live web search, real
person-specific memory retrieval, a real calendar write.

```bash
git clone https://github.com/DinethraDivanjana2001/synapse-plane.git
cd synapse-plane
cp .env.example .env
# edit .env: set DEMO_MODE=false, add a free Gemini API key and a free Tavily API key
docker compose up --build
```

- Web UI: `http://localhost:3000`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

`docker compose up --build` also starts Postgres (with pgvector) as its own container —
there's nothing to configure by hand. On every start, `demo/seed.py` clears and
re-seeds one demo profile (66 memories, 26 entities, 34 relationships) automatically, so
the state described in this README is exactly what you'll have once the stack is up.

Google Calendar needs one extra one-time step to actually create events:

```bash
python scripts/setup_google_calendar_auth.py   # interactive, needs a real browser
```

Everything else — planning, restaurant search, travel research, weather — works
immediately with just the two API keys above. Weather needs no key at all in either
mode.

### Fallback: demo mode

```bash
cp .env.example .env
# leave DEMO_MODE=true (the default) — no API keys needed
docker compose up --build
```

Fully deterministic, zero cost, zero network calls — useful for reviewing the task
graph, the approval gate, and failure-recovery behavior on their own, but it does not
exercise the real agents. See the Evaluator Guide's test-case table for exactly which
results differ between the two modes.

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

## The agent catalogue

Six agents. Two are internal (pure reasoning, no external calls); four are external,
backed by real APIs.

| Agent | Capabilities | What it actually calls |
|---|---|---|
| **Context Intelligence** | `context.retrieve`, `memory.resolve_entities` | Real pgvector semantic search (`gemini-embedding-001`) + real entity/relationship graph traversal |
| **Planning & Decision** | `workflow.plan`, `recommendation.synthesize`, `alternatives.compare` | Real Gemini for the plan and for written recommendations; deterministic scoring for ranking |
| **Browser Use (web)** | `web.discover_places`, `web.verify_information` | Real Tavily search + Gemini extraction |
| **Open Deep Research** | `research.deep`, `travel.destination_research` | Real Tavily search + Gemini synthesis, including named attractions |
| **OpenClaw (calendar)** | `personal.calendar_availability`, `personal.calendar_create` | Real Google Calendar API via OAuth |
| **Weather** | `weather.check` | Real Open-Meteo API — no key required |

Three of these were originally scoped around specific third-party projects — a
browser-automation package, a hosted LangGraph research server, a self-hosted MCP
gateway. None of that infrastructure was ever stood up (each needs something this
environment doesn't have: a local Chromium install, a separately-hosted server process,
a self-hosted gateway), so each was rebuilt on a real external API that accomplishes the
same goal a different way — real search instead of a real browser, a direct API call
instead of a hosted server, a direct Google Calendar integration instead of a gateway.
Every one of them still makes a genuine network call and returns real data; the table
above states exactly which is which rather than leaving it implied.

---

## Retrieval — real RAG, not a keyword match

Every plan is written with the top-scoring relevant memories already attached, retrieved
*before* the planner runs — this is why the same phrasing produces a different
restaurant category depending on who's named in it. The retrieval score combines five
signals:

```
score = 0.35×semantic_similarity + 0.20×entity_match + 0.20×confidence
        + 0.15×recency + 0.10×explicit_boost − 0.30 if stale
```

In real mode, semantic similarity comes from `gemini-embedding-001` (3072-dim) compared
via pgvector cosine distance, and entity matching comes from a real relationship graph
built at seed time — so a query naming a specific person retrieves that person's
memories over a merely-similar one. Demo mode keeps a deterministic hash in place of the
embedding model, by design, so it stays network-free and reproducible for CI.

---

## Reliability

- **Every failure is classified** before deciding what to do about it: transient
  (retry with capped exponential backoff), agent-unavailable (route to a different
  eligible agent), or terminal (fail, no retry).
- **Fallback routing excludes the failed agent** — the replacement is a genuinely
  different implementation, not the same agent retried under another name.
- **Out-of-scope requests refuse cleanly.** Anything outside dining/travel fails
  immediately with `UNSUPPORTED_CAPABILITY` and zero tasks run — never a wrong action
  dressed up as success.
- **Every consequential write is idempotent.** Calendar events carry a key of
  `execution_id:task_id:1`; approving the same proposal twice returns the first result,
  never a duplicate.
- **The approval gate cannot be bypassed.** Any `CONSEQUENTIAL_WRITE` task always stops
  and waits for an explicit human decision.

---

## Project structure

```
synapse-plane/
├── apps/
│   ├── api/                         FastAPI application (routes, middleware, DI)
│   └── web/                         React + TypeScript frontend (Vite)
├── src/synapse_plane/
│   ├── domain/                      Pydantic schemas, state enums, event types
│   ├── memory/                      Memory ingestion, entity extraction, embedding
│   ├── retrieval/                   Hybrid context retrieval, context package builder
│   ├── planning/                    Intent planner (LLM), plan validator (deterministic)
│   ├── registry/                    Agent catalogue, capability router
│   ├── orchestration/               Scheduler, executor, dependency resolver
│   ├── policies/                    Approval policy, retry policy, risk classifier
│   ├── agents/internal/             Context Intelligence, Planning & Decision
│   ├── agents/external/             Browser Use, Open Deep Research, OpenClaw adapters
│   ├── tools/                       Deterministic tool implementations
│   ├── persistence/                 SQLAlchemy ORM, repositories, Alembic
│   └── observability/               Event emitter, structured logging
├── tests/
│   ├── unit/                        No DB, no LLM, no external I/O
│   ├── integration/                 Real DB, fake agents
│   └── scenarios/                   End-to-end: success, failure/recovery, unsupported
├── demo/                            seed.py — the demo profile and all fixture data
├── alembic/                         Database migrations
├── scripts/                         setup_google_calendar_auth.py, one-time OAuth
├── AGENTS.md                        Shared AI coding-assistant context
├── CLAUDE.md                        Claude Code specific instructions
├── PROJECT_CONTEXT.md               Canonical architecture reference
├── docker-compose.yml
├── .env.example
└── pyproject.toml
```

---

## Running tests

```bash
pytest                                                    # everything
pytest tests/unit/                                        # no DB needed
pytest tests/integration/                                 # real DB, fake agents
pytest tests/scenarios/                                   # full stack, mock providers
pytest --cov=src/synapse_plane --cov-report=term-missing  # with coverage
```

All 84 tests run without live LLM or external API credentials — CI runs this same suite
against a real Postgres service container on every push.

---

## Environment variables

Copy `.env.example` to `.env`. The two that matter most:

```bash
# Set to false for real agent behavior; true (default) needs no keys at all
DEMO_MODE=true

# The field is named OPENAI_API_KEY for historical reasons — it points at
# Gemini's OpenAI-compatible endpoint, not OpenAI. Leave blank to keep DEMO_MODE.
OPENAI_API_KEY=
OPENAI_MODEL=gemini-3.5-flash-lite
EMBEDDING_MODEL=gemini-embedding-001

# Real web search for Browser Use and Open Deep Research
TAVILY_API_KEY=

# Real Google Calendar (needs the one-time OAuth step above first)
CALENDAR_PROVIDER=mock   # mock | google
```

`DATABASE_URL` and CORS settings are also in `.env.example`, with sensible Docker
Compose defaults that don't need to change for local evaluation.

---

## Known limitations

- **No re-planning after failure.** Failure recovery is retry (same agent, backoff) and
  fallback (a different agent) — not regenerating the plan mid-execution.
- **Fault injection only works in demo mode.** The real search agent has no
  fault-injection hook yet, so the "Inject Failure" toggle has no visible effect once
  `DEMO_MODE=false`.
- **Web-search restaurant extraction isn't a perfect dietary filter.** It's read by an
  LLM from real search results, not a structured database query — an occasional
  mismatched candidate for a strict dietary constraint is a known, separate limitation
  from the retrieval layer itself.
- **Single demo user.** Multi-user authentication is out of scope for this prototype.
- **No payment, booking, or financial operations.** These are explicitly prohibited
  capabilities, hardcoded in the plan validator and refused unconditionally.

---

## Scale path

The current modular monolith would evolve into distributed services by:

- Extracting the agent catalogue into a **Registry Service** with semantic search
- Replacing the in-process scheduler with a **durable workflow engine** (e.g. Temporal)
- Running agents as isolated **worker services** consuming from a task queue
- Adding a **policy service** for tenant-scoped trust and approval rules
- Routing external agents through a **sandboxed adapter gateway** with auth and timeouts

---

*SynapsePlane — From intent to trusted execution.*
