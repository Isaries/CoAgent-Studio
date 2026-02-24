# CoAgent Studio — Backend

FastAPI-based backend powering the AI agent orchestration platform: decoupled multi-agent workflow execution, an event-driven trigger engine, real-time WebSockets, async LLM processing, and a GraphRAG knowledge graph engine.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (async Python 3.10+) |
| ORM | SQLModel (SQLAlchemy 2.0 async + Pydantic) |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Task Queue | ARQ + Redis (tasks + cron jobs) |
| Event Bus | Redis Pub/Sub (WebSocket) + Redis Streams (GraphRAG) |
| Activity State | Redis keys `room_activity:{id}` (silence detection) |
| Graph Engine | LangGraph (compiled multi-agent DAG execution) |
| Graph DB | Neo4j 5 Community (APOC + GDS plugins) |
| Vector DB | Qdrant |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM I/O | OpenAI SDK + Google GenAI via `LLMFactory`; `instructor` for structured output |
| Auth | JWT HttpOnly Cookies (OAuth2 + refresh) |
| Testing | pytest + pytest-asyncio |

---

## Project Structure

```
backend/
├── app/
│   ├── api/api_v1/endpoints/
│   │   ├── chat.py            # WebSocket handler + Redis activity tracking + trigger dispatch
│   │   ├── workflows.py       # /workflows CRUD, /workflows/{id}/execute, legacy /rooms/{id}/workflow
│   │   ├── triggers.py        # /triggers CRUD (TriggerPolicy)
│   │   ├── agents.py          # Agent config CRUD + sandbox execution
│   │   ├── graph.py           # GraphRAG build / query / visualize / communities / status
│   │   └── courses.py / rooms.py / users.py / …
│   ├── core/
│   │   ├── config.py          # Pydantic Settings (Neo4j, Qdrant, Redis, JWT, …)
│   │   ├── db.py              # Async engine + get_session / get_session_context
│   │   ├── security.py        # JWT creation + Fernet encryption
│   │   ├── socket_manager.py  # WebSocket room broadcaster (Redis Pub/Sub)
│   │   ├── llm_service.py     # LLMFactory + unified async LLM client
│   │   ├── neo4j_client.py    # Async Neo4j: entity MERGE, Leiden GDS, APOC multi-hop
│   │   ├── qdrant_client.py   # Qdrant vector store: 3 collections, semantic search
│   │   ├── embedding_service.py  # OpenAI text-embedding-3-small batch wrapper
│   │   └── a2a/               # Agent-to-Agent protocol + workflow compiler
│   ├── models/
│   │   ├── workflow.py        # Workflow, WorkflowRun (decoupled — no room_id)
│   │   ├── trigger.py         # TriggerPolicy (event_type, conditions, target_workflow_id)
│   │   ├── room.py            # Room (+ attached_workflow_id FK → workflow.id)
│   │   ├── graph_schemas.py   # GraphRAG Pydantic models (EntityNode, CommunityReport, …)
│   │   └── …                 # agent_config, message, artifact, user, course, …
│   ├── services/
│   │   ├── trigger_service.py          # TriggerDispatcher + dispatch_event_task + run_workflow_task + cron
│   │   ├── execution/
│   │   │   └── agent_execution_service.py  # execute_workflow() (headless) + legacy room adapter
│   │   ├── graphrag_service.py         # ARQ tasks: extract_entities, build_communities, full_graph_rebuild
│   │   ├── graphrag_consumer.py        # Redis Stream consumer — incremental ingestion with per-room debounce
│   │   ├── graph_search_service.py     # Intent router → Global | Local search
│   │   ├── chat_service.py             # Message persistence + GraphRAG event publisher
│   │   └── permission_service.py       # Centralized RBAC checks
│   ├── factories/agent_factory.py      # Builds AgentCore instances from AgentConfig
│   ├── initial_data.py                 # DB seeding (creates default super admin)
│   ├── main.py                         # App entry point, lifespan, service lifecycle
│   └── worker.py                       # ARQ WorkerSettings: functions + cron_jobs
├── alembic/versions/
│   └── e8f2a9b7c3d1_decouple_workflow_from_room.py  # Migration: workflow, trigger_policy tables
├── tests/
├── Dockerfile
├── requirements.txt
└── alembic.ini
```

---

## Local Setup

### Prerequisites
- Python 3.10+
- PostgreSQL 16 + Redis + Neo4j 5 + Qdrant (or run via Docker)

### Steps

**1. Start backing services**
```bash
docker compose up db redis neo4j qdrant -d   # from project root
```

**2. Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**3. Configure environment**

Create `backend/.env` (or use root `.env`):
```env
SECRET_KEY=your_secret_key_min_32_chars
POSTGRES_SERVER=localhost
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=coagent_db
BACKEND_CORS_ORIGINS=["http://localhost:5173"]
FERNET_SECRET_KEY=<base64-url-encoded-32-byte-key>

# AI
OPENAI_API_KEY=sk-...

# GraphRAG
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=coagent_neo4j
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

**4. Run migrations & seed**
```bash
alembic upgrade head
python -m app.initial_data       # Creates default super admin
```

**5. Start dev server**
```bash
uvicorn app.main:app --reload --port 8000
```
→ Swagger UI: http://localhost:8000/docs

**6. Start the ARQ worker**
```bash
python -m arq app.worker.WorkerSettings
```

The worker handles:
- **`dispatch_event_task`** — evaluates `TriggerPolicy` rules on incoming events
- **`run_workflow_task`** — executes a compiled LangGraph multi-agent workflow
- **`evaluate_time_triggers_cron`** — runs every minute to fire `timer` and `silence` policies
- **GraphRAG tasks** — entity extraction, community building, full graph rebuild
- **GraphRAG consumer** — Redis Stream listener for incremental ingestion

---

## Key Concepts

### Decoupled Workflow Architecture

`Workflow` is a **first-class resource** (table: `workflow`), independent of any Room:

```
Workflow (graph topology)
    │  ← attached_workflow_id
    ├── Room  (collaborative chat room)
    │
    │  ← target_workflow_id
    └── TriggerPolicy  (event rule → fires workflow)
```

Use the global `/workflows` API to create and manage workflows.
Use `/rooms/{id}/workflow` (legacy) to attach a workflow to a room.

### Trigger Dispatcher

The `TriggerDispatcher` in `services/trigger_service.py` evaluates policies and fires workflows:

```
user sends message
    │
    ▼  chat.py sets:  SET room_activity:{room_id} = <timestamp>  (in Redis)
    │
    ▼  arq_pool.enqueue_job("dispatch_event_task", "user_message", room_id, payload)
    │
    ▼  dispatch_event_task (ARQ worker)
       └── TriggerDispatcher.resolve_matching_workflows()
           ├── Checks TriggerPolicy (event_type, scope, conditions, debounce lock)
           ├── Falls back to Room.attached_workflow_id if no explicit policy exists
           └── Calls execute_workflow(session, redis, workflow_id, session_id, payload)

evaluate_time_triggers_cron (every minute)
    └── TriggerDispatcher.evaluate_time_triggers()
        ├── silence: compares now() vs Redis room_activity:{id}
        └── timer:   checks interval_mins condition + Redis lock
```

### Debounce / Locking

Implemented via Redis `SETNX trigger_lock:{policy_id}:{session_id}` with configurable TTL:
- Default 10s debounce for event-driven triggers
- Lock TTL = `threshold_mins * 60 / 2` for silence triggers

### execute_workflow — Headless Execution

`agent_execution_service.execute_workflow()` accepts `(session, redis, workflow_id, session_id, trigger_payload)` and does **not** depend on Room or Message models. This makes it callable from any context (API, cron, webhook, etc.).

### GraphRAG Engine

```
New message/artifact
    │  (Redis Stream `graphrag:events`)
    ▼
GraphRAGConsumer  (10s debounce per room)
    └── extract_entities_task  →  Neo4j MERGE + Qdrant upsert
        └── (on demand) build_communities_task  →  Leiden GDS + community summaries

Query time:
    graph_search_service.query_graph()
    ├── intent="global" → Qdrant community search → LLM answer
    └── intent="local"  → Neo4j APOC multi-hop → Qdrant chunk evidence → LLM answer
```

### `get_session` vs `get_session_context`
- **`get_session`** — FastAPI `Depends()` generator. Use for regular HTTP endpoints.
- **`get_session_context`** — Async context manager. For WebSocket handlers and background tasks.

### Permission System
All resource access goes through `permission_service.check(user, action, resource, session)`.

---

## Database Migrations

After modifying any `app/models/*.py` file:
```bash
alembic revision --autogenerate -m "Description of change"
alembic upgrade head
```

Key migration: `e8f2a9b7c3d1` — creates `workflow`, `trigger_policy` tables; migrates `room_workflow` data; adds `attached_workflow_id` to `room`.

---

## Testing

```bash
pytest           # Run all
pytest -v        # Verbose
pytest tests/services/test_artifact_service.py
```

Tests use a real PostgreSQL test database with transaction rollback isolation.

---

## Code Quality

```bash
ruff check app/     # Linting
ruff format app/    # Formatting
mypy app/           # Type checking
```

---

## License

> ⚠️ **License not yet specified.** Please consult the project owner before use, redistribution, or contribution.
