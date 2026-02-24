# CoAgent Studio

![Stack](https://img.shields.io/badge/stack-Vue3%20%2B%20FastAPI-brightgreen)
![Database](https://img.shields.io/badge/db-PostgreSQL%2016%20%7C%20Neo4j%205%20%7C%20Qdrant-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-yellow)

**CoAgent Studio** is a full-stack **AI Agent Orchestration Platform (PaaS)**. It provides a visual workflow designer, an autonomous trigger engine, and a real-time multi-agent execution runtime — all decoupled from any single application context.

Agents, Workflows, and Triggers are **first-class, top-level resources** that can be attached to collaborative rooms, invoked via API/Webhook, or activated automatically by event-driven rules.

A built-in **GraphRAG (Graph Retrieval-Augmented Generation)** engine powers knowledge graph construction from conversations, enabling deep cross-session reasoning by any agent.

---

## Architecture Overview

```
Browser (Vue 3 SPA)
      │  HTTP + WebSocket
      ▼
FastAPI Backend (Python async)
  ├── PostgreSQL  — users, courses, rooms, agents, workflows, triggers, artifacts, messages
  ├── Redis       — pub/sub (WebSocket broadcast) + ARQ task queue + trigger activity state
  ├── Neo4j 5     — knowledge graph (entities, relationships, community clusters)
  ├── Qdrant      — vector store (entity embeddings, chunk search, community summaries)
  └── LLM APIs   — OpenAI / Google Gemini (via unified LLMFactory)

ARQ Worker (background)
  ├── dispatch_event_task        — evaluates TriggerPolicy rules on events
  ├── run_workflow_task          — executes a compiled LangGraph workflow
  ├── evaluate_time_triggers_cron — cron: evaluates timer/silence policies every minute
  └── GraphRAG tasks             — entity extraction, community building, full rebuild
```

### Key Architectural Concepts

| Concept | Location | Description |
|---|---|---|
| **Decoupled Workflows** | `models/workflow.py` | `Workflow` is a top-level resource (not bound to a Room). Rooms, APIs, and Webhooks attach to it via `attached_workflow_id` or `TriggerPolicy` |
| **Trigger Dispatcher** | `services/trigger_service.py` | Evaluates `TriggerPolicy` rules on every event; supports `user_message`, `silence`, `timer`, `webhook`, `manual` |
| **ARQ Cron Engine** | `worker.py` | `evaluate_time_triggers_cron` runs each minute to fire time-based and silence-based policies |
| **Redis Activity State** | `chat.py` → `room_activity:{id}` | O(1) Redis key tracks last activity per session for silence detection |
| **GraphRAG Engine** | `services/graphrag_service.py` | Extracts entity graphs from conversations, runs Leiden clustering, enables semantic Q&A |
| **Agent-to-Agent (A2A) Protocol** | `core/a2a/` | Typed message bus for autonomous multi-agent coordination |
| **WebSocket Broadcast** | `core/socket_manager.py` | Per-room real-time delivery via Redis Pub/Sub |
| **Role-Based Access Control** | `permission_service.py` + router guards | Super Admin / Admin / Teacher / TA / Student / Guest |

---

## Tech Stack

### Frontend (`/frontend`)
- **Vue 3** (Composition API + `<script setup>`) + **TypeScript**
- **Vite** · **Pinia** · **Vue Router 4** (with auth + role guards)
- **Tailwind CSS** + **DaisyUI** · **Vue Flow** (Workflow Designer canvas) · **Tiptap** (rich-text)
- Native **WebSockets** with auto-reconnect + exponential backoff

### Backend (`/backend`)
- **FastAPI** (async Python 3.10+) — OpenAPI docs at `/docs`
- **SQLModel** (Pydantic + SQLAlchemy 2.0 async) · **Alembic** (migrations)
- **ARQ + Redis** (background task queue + cron jobs)
- **LangGraph** (compiled multi-agent graph execution engine)
- **JWT HttpOnly Cookies** (OAuth2 + refresh token)
- **OpenAI SDK** + **Google GenAI** via unified `LLMFactory`

### Infrastructure
- **Docker Compose** (single command to run all services)
- **PostgreSQL 16** · **Redis 7-alpine** · **Neo4j 5 Community** (APOC + GDS) · **Qdrant**

---

## Quick Start

### Option A — Docker (Recommended)

**1. Configure environment**

```env
# .env (project root)
SECRET_KEY=change_this_to_a_long_random_string
POSTGRES_SERVER=db
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=coagent_db
BACKEND_CORS_ORIGINS=["http://localhost:5173"]

# AI keys (required for agents and GraphRAG)
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# GraphRAG services (auto-configured in Docker)
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=coagent_neo4j
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

**2. Launch all services**
```bash
docker compose up --build -d
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---

### Option B — Manual Development

```bash
# Start backing services
docker compose up db redis neo4j qdrant -d

# Backend
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# ARQ Worker (required for agents, triggers, GraphRAG)
python -m arq app.worker.WorkerSettings

# Frontend
cd frontend && npm install && npm run dev
```

---

## Project Structure

```
CoAgent-Studio/
├── backend/app/
│   ├── api/api_v1/endpoints/
│   │   ├── chat.py           # WebSocket + state tracking + trigger dispatch
│   │   ├── workflows.py      # Global /workflows CRUD + /execute + legacy room routes
│   │   ├── triggers.py       # TriggerPolicy CRUD (/triggers)
│   │   ├── agents.py         # Agent config + sandbox
│   │   └── graph.py          # GraphRAG build / query / visualize
│   ├── models/
│   │   ├── workflow.py       # Workflow, WorkflowRun (decoupled from Room)
│   │   ├── trigger.py        # TriggerPolicy (event_type, conditions, target_workflow_id)
│   │   └── room.py           # Room (+ attached_workflow_id FK)
│   ├── services/
│   │   ├── trigger_service.py        # TriggerDispatcher + ARQ tasks
│   │   ├── execution/
│   │   │   └── agent_execution_service.py  # execute_workflow() + legacy adapter
│   │   ├── graphrag_service.py       # GraphRAG ARQ tasks
│   │   └── graphrag_consumer.py      # Redis Stream consumer
│   ├── core/
│   │   ├── a2a/              # Agent-to-Agent protocol + compiler
│   │   └── socket_manager.py # WebSocket room broadcaster
│   └── worker.py             # ARQ functions + cron jobs registration
├── frontend/src/
│   ├── views/studio/
│   │   ├── WorkflowsView.vue   # Workflow list + create/delete
│   │   └── TriggersView.vue    # Trigger policy management
│   ├── views/WorkflowEditorView.vue  # Dual-mode: Studio / Legacy Room
│   ├── components/workflow/
│   │   ├── WorkflowEditor.vue  # Vue Flow canvas editor
│   │   ├── AgentNode.vue       # Draggable agent node
│   │   └── PropertiesPanel.vue # Node/edge config panel
│   └── services/workflowService.ts  # Global + legacy + trigger APIs
├── docs/A2A_PROTOCOL.md
├── docker-compose.yml
└── .env
```

---

## Key Features

### 🔀 Workflow Studio (New)
- **Visual Workflow Designer** — Drag-and-drop multi-agent graph canvas
- **Global Workflows** — Workflows are top-level resources, attachable to any room or API
- **Manual Execution** — Trigger any workflow via API or Studio UI
- **Execution History** — Full `WorkflowRun` audit log per workflow

### ⚡ Trigger Engine (New)
- **TriggerPolicy** — Configurable rules linking events to workflows
- **Event Types**: `user_message`, `silence`, `timer`, `webhook`, `manual`
- **Silence Detection** — Redis-backed O(1) last-activity tracking; fires when a room goes quiet
- **Debounce Locking** — Redis SETNX prevents duplicate firing within cooldown windows
- **Cron Polling** — ARQ native cron evaluates time-based policies every minute

### 🏫 Collaborative Rooms (Legacy)
- **Real-Time Chat** — WebSocket broadcast with A2A trace visualization
- **Agent Design IDE** — Version-controlled system prompt editor with live sandbox
- **Kanban Board + Docs + Process Diagrams** — AI-generated workspace artifacts

### 🧠 GraphRAG Knowledge Engine
- **Knowledge Graph** — Entities extracted from conversations via LLM
- **Leiden Community Detection** — Thematic clusters via Neo4j GDS
- **Dual Search** — Global (community summaries) + Local (APOC multi-hop + Qdrant)
- **Incremental Ingestion** — Redis Stream consumer updates graph within ~10s of new messages

### 🔐 Security & Operations
- **RBAC** — Super Admin / Admin / Teacher / TA / Student / Guest per-resource checks
- **Impersonation Mode** — Admins can "view as" any user for debugging
- **Async LLM Jobs** — Heavy inference runs in background via ARQ + Redis

---

## License

> ⚠️ **License not yet specified.** Please consult the project owner before use, redistribution, or contribution.
