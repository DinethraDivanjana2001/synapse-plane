# CLAUDE.md — SynapsePlane Instructions for Claude Code

> This file is read by Claude Code (claude.ai/code or claude CLI) at session start.
> Antigravity reads AGENTS.md. Both tools share the same project documents under docs/.

---

## Session start — mandatory

Before touching any code, read:

1. `AGENTS.md` — shared AI context, design principles, hard scope rules
2. `docs/PROJECT_SCOPE.md` — full scope and priority levels
3. `docs/REQUIREMENTS.md` — structured FR/NFR list
4. `docs/ARCHITECTURE.md` — layer design and data flows
5. `docs/ROADMAP.md` — day plan and exit criteria
6. `docs/PROGRESS.md` — what is done, what is next
7. `docs/DECISIONS.md` — all architecture decisions so far

Summarize the current state and the next approved task before proposing changes.

---

## Claude Code's primary responsibilities

Claude Code handles bounded, well-defined backend tasks where deep context matters:

- Domain model implementation (`src/synapse_plane/domain/`)
- Planning and validation logic (`src/synapse_plane/planning/`)
- Orchestration scheduler and executor (`src/synapse_plane/orchestration/`)
- Policy enforcement (`src/synapse_plane/policies/`)
- Agent implementations (`src/synapse_plane/agents/`)
- Tool/provider adapters (`src/synapse_plane/tools/`)
- Persistence repositories (`src/synapse_plane/persistence/`)
- FastAPI routes and middleware (`apps/api/`)
- Pytest test suites (`tests/`)
- Difficult debugging and refactoring

---

## Technology constraints

| Component | Choice | Notes |
|-----------|--------|-------|
| Language | Python 3.12 | Type hints everywhere |
| API framework | FastAPI | Async where appropriate |
| Validation | Pydantic v2 | All schemas use Pydantic models |
| ORM | SQLAlchemy 2.x | Async sessions with PostgreSQL |
| Migrations | Alembic | Every schema change needs a migration |
| Testing | Pytest + pytest-asyncio | No live LLM or external calls in unit/integration |
| Linting | Ruff | `ruff check .` must pass clean |
| Type checking | Mypy or Pyright | Strict mode for domain layer |
| Frontend | React + TypeScript | Vite build; restrained professional UI |
| Containers | Docker + Compose | `docker compose up --build` must work |

---

## Coding rules

1. **Type hints on every function.** Return types included. No `Any` in domain layer.
2. **Pydantic models for all inter-layer data.** No raw dicts crossing layer boundaries.
3. **No secrets in code.** Config comes from environment via `python-dotenv` or similar.
4. **Tests are not optional.** Every new module needs at least one test before it is done.
5. **State transitions are deterministic.** No LLM decides execution or task state.
6. **Approval gate cannot be bypassed.** `CONSEQUENTIAL_WRITE` tasks always stop.
7. **Idempotency key on all external writes.** Calendar events use `execution_id:task_id:proposal_version`.
8. **Errors are classified.** Transient vs fatal vs policy vs schema. See `docs/REQUIREMENTS.md`.
9. **Never expand scope silently.** If a task touches something not in the current plan,
   stop and report before proceeding.
10. **Update `docs/PROGRESS.md` at end of session.** This is how other tools stay in sync.

---

## Database transaction discipline

- State transitions (e.g., `RUNNING → SUCCEEDED`) update inside a transaction.
- Task output is stored atomically with the state update.
- The "durable checkpoint" behaviour means the orchestrator must be able to
  reconstruct ready tasks purely from DB state — no in-memory call stack required.

---

## LLM call discipline

- LLM calls happen only in `src/synapse_plane/planning/` and optionally in
  `src/synapse_plane/agents/` for explanation generation.
- LLM output is always a *proposal*. It must be validated against a Pydantic schema
  before any further action.
- Never pass the full agent catalogue or full event history to the model. Pass only
  what the current task requires.
- Count or log every LLM call (model name, token estimate, execution/task context).

---

## Test categories

| Category | Location | Constraints |
|----------|----------|-------------|
| Unit | `tests/unit/` | No DB, no LLM, no external I/O |
| Integration | `tests/integration/` | Real DB (SQLite or test PG), fake agents |
| Scenario | `tests/scenarios/` | Full stack with mock providers; no live LLM |

Scenario tests must cover exactly:
1. Successful restaurant → calendar workflow (reaches COMPLETED after approval)
2. Primary venue agent failure → fallback → COMPLETED
3. Unsupported intent (flight + payment) → stops at UNSUPPORTED_CAPABILITY

---

## Git discipline

- Commit messages: `type(scope): short description` (conventional commits)
- Example: `feat(orchestration): implement dependency-aware task scheduler`
- Do not commit generated files, `*.db`, `.env`, or any secret
- Feature work goes on `feature/xxx` branches; merge via PR

---

*Claude Code is a powerful but bounded assistant here. Its output must be reviewed,
tested, and committed by the human developer before it is considered accepted.*
