# SynapsePlane — Canonical Project Context

> **This is the single source of truth.** All AI coding agents (Antigravity, Cursor, Claude Code) must read this file before touching any code. All other docs are supplementary detail.

---

## What SynapsePlane is

SynapsePlane is a **persistent-context-aware agentic execution plane** built for Efimind's technical challenge.

It receives a natural-language user intent, retrieves relevant historical personal context, decomposes the intent into a typed task graph (DAG), selects suitable agents from a catalogue, executes tasks sequentially or concurrently, passes structured outputs between agents, tracks durable execution state, recovers from failures with retry/fallback/replanning, pauses before consequential actions for human approval, resumes after approval, and records outcomes back into long-term memory.

---

## The 3-Tier Architecture (MANDATORY — never violate)

```
┌────────────────────────────────────────────────────────┐
│            TIER 1: EXECUTION PLANE (Orchestrator)       │
│  Decomposes intent, validates DAG, routes to agents,   │
│  manages state, enforces approval, records outcomes.   │
│  100% DETERMINISTIC — no LLM here.                     │
└────────────────────────┬───────────────────────────────┘
                         │ Selects & coordinates
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌────────────────────────────────────────────────────────┐
│              TIER 2: AGENTS (Goal-Directed)             │
│  Receive a goal, reason, choose tools, adapt.          │
│  Each agent is a mini problem-solver, not a wrapper.   │
└────────────────────────┬───────────────────────────────┘
                         │ Uses
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌────────────────────────────────────────────────────────┐
│           TIER 3: TOOLS & SERVICES (Deterministic)      │
│  One specific operation each.                          │
│  pgvector_search, calendar_read, graph_query, etc.     │
└────────────────────────────────────────────────────────┘
```

---

## The 5-Agent Catalogue

| Agent ID | Type | Status | Role |
|----------|------|--------|------|
| `internal-context-intelligence` | Internal | Implemented | Hybrid RAG retrieval — interprets intent, retrieves relevant memories, traverses entity graph, builds grounded context package |
| `internal-planning-decision` | Internal | Implemented | Proposes task DAG, compares alternatives, generates grounded recommendations, re-plans on failure |
| `external-browser-use` | External (browser-use/browser-use) | Live External | Live browser agent — discovers restaurants, verifies venue details on real websites |
| `external-open-deep-research` | External (langchain-ai/open_deep_research) | Registered | Multi-step research agent — investigates destinations, compares evidence from multiple sources |
| `external-openclaw-personal` | External (openclaw/openclaw) | Registered | Personal assistant agent — checks calendar availability, creates approved events via MCP |

---

## What are Tools (NOT agents)

These are deterministic utilities invoked by agents:

- `pgvector_search_tool` — cosine similarity search over memory embeddings
- `graph_query_tool` — entity/relationship traversal in PostgreSQL
- `places_primary_tool` — restaurant search API call (used by Browser Use)
- `places_fallback_tool` — secondary restaurant search (used as fallback)
- `calendar_read_tool` — read availability
- `calendar_write_tool` — create event (requires approval + idempotency key)
- `memory_store_tool` — write new memory records
- `embedding_tool` — generate text embeddings

**Rule:** A single API call is NEVER an agent. An agent receives a goal, reasons, chooses tools, observes results, and adapts.

---

## The Two Use Cases (both must work)

### Use Case 1 (Primary Demo): Context-Aware Dinner Planning
> "Arrange dinner with Maya tomorrow after work and add it to my calendar."

Agents selected: `context-intelligence` → `planning-decision` → `browser-use` (parallel with `openclaw`) → `planning-decision` (ranking) → `openclaw` (action, approval required)

### Use Case 2 (Secondary Demo): Travel Research
> "Compare a two-day trip to Kandy and Galle next month using my interests and budget."

Agents selected: `context-intelligence` → `planning-decision` → `open-deep-research` (parallel with `browser-use`) → `planning-decision` (compare/recommend)
No consequential action — no approval needed.

**Key point:** Different intents → different agents selected → this is what makes it genuinely agentic.

---

## State Machine

```
RECEIVED → CONTEXT_RETRIEVAL → PLANNING → PLAN_VALIDATION → RUNNING
RUNNING → WAITING_FOR_APPROVAL → RESUMING → RUNNING → COMPLETED
RUNNING → RETRYING → RUNNING
RUNNING → REPLANNING → PLAN_VALIDATION → RUNNING
Any → FAILED | CANCELLED | REJECTED
```

---

## Core Architecture Rules (never break these)

1. **Never send the user's full history to an LLM.** Use hybrid RAG to retrieve only relevant context.
2. **LLM proposes plans; deterministic code validates and executes them.**
3. **Every CONSEQUENTIAL_WRITE task requires a stored, signed ApprovalProposal in DB before any tool is called.**
4. **External agents receive only the minimum context needed for their task — never the full memory DB.**
5. **Prohibited capabilities** (`payment.execute`, `flight.book`, `restaurant.reserve`, `message.send_external`) are hardcoded in the validator and can never be bypassed.
6. **One action = one idempotency key** — duplicate external writes are impossible.
7. **Outcomes are recorded back into memory** — the feedback loop is not optional.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL + pgvector extension |
| ORM | SQLAlchemy 2.x async + Alembic |
| Schemas | Pydantic v2 |
| LLM | OpenAI gpt-4o-mini (via API key) OR Gemini free tier |
| Embeddings | OpenAI text-embedding-3-small (1536 dimensions) |
| Vector Search | pgvector (cosine similarity) |
| External Agent 1 | browser-use (pip install browser-use) |
| External Agent 2 | open_deep_research (LangGraph server) |
| External Agent 3 | OpenClaw (self-hosted, MCP) |
| Agent Protocol | MCP (tools) + A2A-style adapters (agents) |
| Frontend | React + TypeScript (Vite) |
| Container | Docker Compose |
| Tests | Pytest (FakePlanner + FakeEmbedding in tests) |

---

## Key File Paths

```
src/synapse_plane/memory/          Memory ingestion, entity extraction, embedding
src/synapse_plane/retrieval/       Hybrid context retrieval, context package builder
src/synapse_plane/domain/          Pydantic schemas, state enums, events
src/synapse_plane/planning/        Intent planner (LLM), plan validator (deterministic)
src/synapse_plane/registry/        Agent catalogue, capability router
src/synapse_plane/orchestration/   Scheduler, executor, dependency resolver
src/synapse_plane/policies/        Approval policy, retry policy, risk classifier
src/synapse_plane/agents/internal/ Context Intelligence + Planning Decision agents
src/synapse_plane/agents/external/ Browser Use, Open Deep Research, OpenClaw adapters
src/synapse_plane/tools/           Deterministic tool implementations and MCP layer
src/synapse_plane/persistence/     SQLAlchemy ORM, repositories, Alembic
src/synapse_plane/observability/   Event emitter, structured logging
apps/api/                          FastAPI application
apps/web/                          React frontend
tests/unit/                        No external deps, FakePlanner + FakeEmbedding
tests/integration/                 Real DB, fake agents
tests/scenarios/                   End-to-end: success, failure/recovery, unsupported, travel
demo/                              Seed: 50+ realistic memories, entities, relationships
```

---

## Stretch Features (if time permits)

- Real Google Calendar via OAuth2 (swap in `google_calendar_provider.py`)
- Voice-to-text intent input (OpenAI Whisper / Web Speech API)
- Interactive D3.js knowledge graph visualization
- Real-time WebSocket execution streaming
