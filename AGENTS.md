# AGENTS.md — SynapsePlane AI Coding Context (v3)

> **Read `PROJECT_CONTEXT.md` first.** That is the canonical source of truth.
> This file summarizes the most critical rules for AI coding agents.

---

## Mandatory reading before any session

| File | Why |
|------|-----|
| `PROJECT_CONTEXT.md` | **Canonical source of truth — read this first** |
| `docs/SCOPE_CORRECTION.md` | What v1 got wrong and why |
| `docs/ARCHITECTURE.md` | Full system design |
| `docs/MEMORY_AND_RAG.md` | Persistent memory, hybrid RAG, knowledge graph |
| `docs/AGENT_CATALOGUE.md` | 5 real agents, tools, feasibility checklist |
| `docs/PROGRESS.md` | What is done, what is next |

### Session-start prompt
```
Read PROJECT_CONTEXT.md, docs/AGENT_CATALOGUE.md, docs/MEMORY_AND_RAG.md,
and docs/PROGRESS.md before writing any code.
Tell me: what has been completed, what the next task is, and flag any
conflict between the requested work and the 3-tier architecture.
```

---

## The single most important rule

> SynapsePlane orchestrates genuine goal-directed agents. Agents reason and use tools. APIs, calendar operations, database operations, vector search and graph queries are TOOLS — not agents. Persistent memory and hybrid RAG provide grounded context. Deterministic orchestration controls execution, safety, approval and recovery.

---

## The 3-Tier Architecture (NEVER violate)

1. **Orchestrator (Execution Plane):** Deterministic. Plans, validates, routes, tracks state, enforces approval.
2. **Agents:** Goal-directed. Reason, choose tools, observe results, adapt.
3. **Tools:** Deterministic. One operation each (pgvector_search, calendar_read, etc.)

---

## The 5 Real Agents

1. `internal-context-intelligence` — Hybrid RAG retrieval, entity graph, grounded context package
2. `internal-planning-decision` — LLM-proposed DAG + recommendation synthesis + replanning
3. `external-browser-use` — Live browser agent for restaurant/venue discovery
4. `external-open-deep-research` — Multi-step research for travel use case
5. `external-openclaw-personal` — Personal assistant for calendar actions (MCP)

---

## Two Use Cases (both must work)

- **Use Case 1:** "Arrange dinner with Maya" → context + browser-use + openclaw + approval
- **Use Case 2:** "Compare Kandy vs Galle trip" → context + open-deep-research + browser-use (no approval)

Different intents MUST produce different agent selections.

---

## Hard stops

Never implement: `payment.execute`, `flight.book`, `hotel.book`, `restaurant.reserve`, `message.send_external`

Never do silently:
- Send user's full memory to any LLM or external agent
- Bypass approval gate for CONSEQUENTIAL_WRITE
- Label a single API call as an "agent"
- Mix memories between users

---

## Key paths

```
src/synapse_plane/agents/internal/    context_intelligence.py, planning_decision.py
src/synapse_plane/agents/external/    browser_use_adapter.py, open_deep_research_adapter.py, openclaw_adapter.py
src/synapse_plane/tools/              All deterministic tool implementations
src/synapse_plane/memory/             Ingestion pipeline, embedding service
src/synapse_plane/retrieval/          Hybrid RAG retriever, context package builder
src/synapse_plane/planning/           Plan validator (deterministic)
src/synapse_plane/registry/           Agent catalogue, capability router
src/synapse_plane/orchestration/      Scheduler, executor, dependency resolver
src/synapse_plane/policies/           Approval policy, retry policy, risk classifier
src/synapse_plane/persistence/        SQLAlchemy ORM, repositories, Alembic
apps/api/                             FastAPI application
apps/web/                             React frontend
demo/                                 50+ seed memories, agent manifests
```
