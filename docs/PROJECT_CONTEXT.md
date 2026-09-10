# SynapsePlane — Project Context

**Status:** Active prototype  
**Delivery deadline:** Four focused development days  
**Primary evaluator:** Technical interview panel  
**Repository:** `DinethraDivanjana2001/synapse-plane`

---

## What this project is

SynapsePlane is a technical interview submission for an AI engineering role.
The assignment asks for an agentic execution plane: a system that takes a user intent,
decomposes it into tasks, selects agents from a trusted catalogue, executes tasks
sequentially or in parallel, passes typed outputs between agents, tracks state durably,
handles failures and replanning, and pauses before consequential actions to get human
approval.

The project demonstrates these capabilities through a restaurant discovery and calendar
scheduling workflow. The workflow is not the product — the execution plane is. The
restaurant use case is a concrete, bounded demonstration of platform capabilities.

---

## Why this architecture

The assessment explicitly asks:

> *"Which parts should be handled by LLMs versus deterministic logic?"*

The answer embodied in SynapsePlane:

- **LLMs** interpret natural language, propose task graphs, rank options with explanation,
  and summarize results. Their output is always a *proposal*.
- **Deterministic code** validates plans, filters agents, enforces policy, manages state
  transitions, stores checkpoints, enforces approval gates, and commits external actions.

This separation is not just a design choice — it is the central correctness guarantee.
No LLM output causes an external write without passing deterministic policy checks.

---

## How to use the documentation set

| Document | Purpose |
|----------|---------|
| `AGENTS.md` | AI-tool instructions; read first every session |
| `CLAUDE.md` | Claude Code specific instructions |
| `AI_USAGE.md` | Honest disclosure of AI tool usage for evaluators |
| `docs/PROJECT_CONTEXT.md` | This file — background and orientation |
| `docs/PROJECT_SCOPE.md` | Full scope, priorities, FR/NFR, delivery plan |
| `docs/REQUIREMENTS.md` | Structured requirements ready to implement |
| `docs/ARCHITECTURE.md` | Architecture design, data flows, technology choices |
| `docs/ROADMAP.md` | Day-by-day plan with exit criteria |
| `docs/PROGRESS.md` | Live completion tracker — updated every session |
| `docs/DECISIONS.md` | Architecture decision records |

---

## Demo user

The prototype uses a single seeded demo user named **Dinethra**, located in Colombo,
Sri Lanka. The profile captures food preferences, calendar provider, approval policy,
and other fields that materially affect workflow execution. The profile can be edited
through the UI to demonstrate that preferences change system behaviour.

---

## Primary demonstration scenarios

1. **Success scenario:** `Find a good Italian restaurant near me for dinner tomorrow and put it in my calendar.` → full workflow through approval → calendar event created.

2. **Failure/recovery scenario:** Same intent with primary venue agent injected failure → retry → fallback agent → recovery → calendar event created.

3. **Unsupported-intent scenario:** `Buy me the cheapest flight to Singapore.` → stopped at plan validation with `UNSUPPORTED_CAPABILITY`.

---

## Target domain context

The target product is a cognitive augmentation AI system: persistent context from a
user's thoughts, goals, relationships, and decisions, turned into insights and proactive
assistance through AI, knowledge graphs, semantic retrieval, and agentic workflows.

SynapsePlane is directly relevant to that domain because it implements the agentic
workflow layer such a product needs, with proper governance over when AI acts.
